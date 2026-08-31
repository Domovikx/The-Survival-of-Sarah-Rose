#!/usr/bin/env python
"""TSSR Voice Generator — генерация голосов для The Survival of Sarah Rose.

Запуск ОБЯЗАТЕЛЬНО через venv CosyVoice (Python 3.10):
  C:\\tools\\cosyvoice3\\.venv\\Scripts\\python.exe tools/voice_gen.py

Примеры:
  # Одна фраза
  python tools/voice_gen.py --text "Привет, мир!" --ref refs/samples_ru_cosy/Sarah.wav --out game/tl/ru/voice/test.wav

  # Из файла со списком фраз
  python tools/voice_gen.py --phrases phrases.txt --ref refs/samples_ru_cosy/Sarah.wav --out-dir game/tl/ru/voice/

  # С указанием ID (для auto_voice)
  python tools/voice_gen.py --text "ОТЕЦ!" --id start_abc123 --ref refs/samples_ru_cosy/Sarah.wav
"""

import argparse
import os
import random
import re
import sys
import time

COSY_ROOT = r'C:\tools\cosyvoice3'
REPO_DIR = os.path.join(COSY_ROOT, 'CosyVoice')
MODEL_DIR = os.path.join(COSY_ROOT, 'pretrained_models', 'Fun-CosyVoice3-0.5B')
sys.path.insert(0, REPO_DIR)
sys.path.insert(0, os.path.join(REPO_DIR, 'third_party', 'Matcha-TTS'))

import numpy as np
import torch
import torchaudio
import yaml
from cosyvoice.cli.cosyvoice import AutoModel
from cosyvoice.utils.common import set_all_random_seed

CV3_PREFIX = 'You are a helpful assistant.<|endofprompt|>'
GAP = 0.25

SILENT_TOKENS = frozenset({1, 2, 28, 29, 55, 248, 494, 2241, 2242, 2322, 2323})


def make_tuned_model_dir(top_p=None, top_k=None, tau_r=None, rl=False, cfg_rate=None):
    """Create tuned model directory with modified YAML config."""
    tag = []
    if top_p is not None:
        tag.append('p{}'.format(top_p))
    if top_k is not None:
        tag.append('k{}'.format(top_k))
    if tau_r is not None:
        tag.append('t{}'.format(tau_r))
    if cfg_rate is not None:
        tag.append('c{}'.format(cfg_rate))
    if rl:
        tag.append('rl')
    dst = MODEL_DIR + ('_' + '_'.join(tag) if tag else '')
    if not os.path.exists(os.path.join(dst, 'cosyvoice3.yaml')):
        print('making tuned model dir:', dst)
        link_tree(MODEL_DIR, dst)
    yaml_path = os.path.join(dst, 'cosyvoice3.yaml')
    with open(yaml_path, encoding='utf-8') as f:
        text = f.read()
    if top_p is not None:
        text = re.sub(r'top_p: [0-9.]+', 'top_p: {}'.format(top_p), text, count=1)
    if top_k is not None:
        text = re.sub(r'top_k: [0-9.]+', 'top_k: {}'.format(top_k), text, count=1)
    if tau_r is not None:
        text = re.sub(r'tau_r: [0-9.]+', 'tau_r: {}'.format(tau_r), text, count=1)
    if cfg_rate is not None:
        text = re.sub(r'inference_cfg_rate: [0-9.]+', 'inference_cfg_rate: {}'.format(cfg_rate), text, count=1)
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(text)
    if rl:
        llm_pt = os.path.join(dst, 'llm.pt')
        rl_pt = os.path.join(dst, 'llm.rl.pt')
        base_pt = os.path.join(dst, 'llm.base.pt')
        if os.path.exists(rl_pt) and not os.path.exists(base_pt):
            os.rename(llm_pt, base_pt)
            os.rename(rl_pt, llm_pt)
    return dst


def link_tree(src, dst):
    """Create hardlinks for model files."""
    import shutil
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isfile(s):
            if not os.path.exists(d):
                try:
                    os.link(s, d)
                except OSError:
                    shutil.copy2(s, d)
        elif os.path.isdir(s):
            link_tree(s, d)


def patch_flow_temperature(temp):
    """Patch flow temperature for CosyVoice3."""
    from cosyvoice.flow.flow_matching import CausalConditionalCFM
    orig = CausalConditionalCFM.forward

    def wrapped(self, mu, mask, n_timesteps, temperature=1.0, spks=None,
                cond=None, streaming=False, **kw):
        return orig(self, mu, mask, n_timesteps, temperature=temp, spks=spks,
                    cond=cond, streaming=streaming, **kw)

    CausalConditionalCFM.forward = wrapped


def patch_silent_token_trim():
    """Trim silent/breath tokens before flow."""
    from cosyvoice.cli.model import CosyVoice3Model
    orig = CosyVoice3Model.token2wav

    def wrapped(self, token, *a, **kw):
        toks = token[0].tolist()
        i = len(toks)
        while i > 0 and toks[i - 1] in SILENT_TOKENS:
            i -= 1
        if i == 0:
            i = 1
        return orig(self, token[:, :i], *a, **kw)

    CosyVoice3Model.token2wav = wrapped


def compute_rms(wave, frame_size=240):
    """Compute RMS energy per frame."""
    n = wave.shape[1] // frame_size
    if n < 1:
        return torch.tensor([])
    rms = []
    for i in range(n):
        seg = wave[:, i * frame_size:(i + 1) * frame_size]
        rms.append(float((seg ** 2).mean().sqrt()))
    return torch.tensor(rms)


def compute_rms_db(wave, frame_size=240):
    """Compute RMS energy in dB per frame."""
    rms = compute_rms(wave, frame_size)
    if len(rms) == 0:
        return rms
    # Convert to dB, avoid log(0)
    rms_db = 20 * torch.log10(rms + 1e-10)
    return rms_db


def detect_segments_by_threshold(rms, threshold_db, min_duration_ms=50, sample_rate=24000):
    """Detect segments above threshold with minimum duration.
    
    Returns list of (start_frame, end_frame, duration_ms) tuples.
    """
    thr = 10 ** (threshold_db / 20)
    above = rms > thr
    
    frame_size = int(sample_rate * 0.01)  # 10ms frames
    min_frames = int(min_duration_ms / 10)
    
    segments = []
    in_segment = False
    start = 0
    
    for i in range(len(above)):
        if above[i] and not in_segment:
            start = i
            in_segment = True
        elif not above[i] and in_segment:
            if i - start >= min_frames:
                duration_ms = (i - start) * 10
                segments.append((start, i, duration_ms))
            in_segment = False
    
    if in_segment and len(above) - start >= min_frames:
        duration_ms = (len(above) - start) * 10
        segments.append((start, len(above), duration_ms))
    
    return segments


def find_speech_end(rms, speech_threshold_db=-30.0, min_speech_ms=100, sample_rate=24000):
    """Find the end of the last significant speech segment.
    
    Returns (end_frame, end_time_ms) or None if no speech found.
    """
    speech_segments = detect_segments_by_threshold(rms, speech_threshold_db, min_speech_ms, sample_rate)
    
    if not speech_segments:
        return None
    
    # Get last speech segment
    last_end_frame = speech_segments[-1][1]
    last_end_time_ms = last_end_frame * 10
    
    return (last_end_frame, last_end_time_ms)


def detect_breath_pattern(rms, start_frame, speech_threshold_db=-30.0, 
                          breath_threshold_db=-35.0, min_gap_ms=50, 
                          max_breath_ms=500, sample_rate=24000):
    """Detect breath pattern after speech end.
    
    Breath pattern:
    1. Silence gap (>= min_gap_ms)
    2. Followed by sound burst (breath)
    3. Burst duration typically 0.1s - 0.5s
    
    Returns (breath_start_frame, breath_end_frame, breath_duration_ms) or None.
    """
    frame_size = int(sample_rate * 0.01)  # 10ms frames
    min_gap_frames = int(min_gap_ms / 10)
    max_breath_frames = int(max_breath_ms / 10)
    
    # Search window after speech
    search_start = start_frame
    search_end = min(len(rms), start_frame + max_breath_frames)
    
    # Find silence gap
    gap_frames = 0
    gap_start = search_start
    
    for i in range(search_start, search_end):
        if rms[i] < 10 ** (breath_threshold_db / 20):
            gap_frames += 1
        else:
            break
    
    # If gap is too short, no breath detected
    if gap_frames < min_gap_frames:
        return None
    
    # After gap, look for breath sound
    breath_start = search_start + gap_frames
    breath_frames = 0
    
    for i in range(breath_start, search_end):
        if rms[i] >= 10 ** (breath_threshold_db / 20):
            breath_frames += 1
        else:
            break
    
    # If breath is too short or too long, ignore
    if breath_frames < 3 or breath_frames > max_breath_frames:
        return None
    
    breath_duration_ms = breath_frames * 10
    
    return (breath_start, breath_start + breath_frames, breath_duration_ms)


def dynamic_trim_breath(wave, sr, speech_threshold_db=-30.0, breath_threshold_db=-35.0,
                        min_gap_ms=50, max_breath_ms=500, padding_ms=30, fade_ms=30):
    """Dynamic breath trim - detects and measures breath length before trimming.
    
    Logic:
    1. Find end of real speech
    2. Detect breath pattern (gap + burst)
    3. Measure breath length dynamically
    4. Trim to end of speech + padding
    
    Args:
        wave: (1, n_samples) tensor
        sr: sample rate
        speech_threshold_db: threshold for speech detection
        breath_threshold_db: threshold for breath detection (lower)
        min_gap_ms: minimum gap to consider as separation
        max_breath_ms: maximum breath duration to detect
        padding_ms: padding to keep after speech
        fade_ms: fade-out duration
    
    Returns: (trimmed_wave, breath_info) where breath_info is dict with details
    """
    frame_size = int(sr * 0.01)  # 10ms frames
    rms = compute_rms(wave, frame_size)
    
    if len(rms) < 5:
        return wave, None
    
    # Find end of speech
    speech_end = find_speech_end(rms, speech_threshold_db, 100, sr)
    
    if speech_end is None:
        return wave, None
    
    speech_end_frame, speech_end_ms = speech_end
    
    # Detect breath pattern
    breath_info = detect_breath_pattern(
        rms, speech_end_frame, speech_threshold_db, breath_threshold_db,
        min_gap_ms, max_breath_ms, sr
    )
    
    if breath_info is None:
        # No breath detected, just trim silence
        trim_frame = speech_end_frame + int(padding_ms / 10)
        trim_sample = min(wave.shape[1], trim_frame * frame_size)
        return wave[:, :trim_sample], None
    
    breath_start, breath_end, breath_duration_ms = breath_info
    
    # Trim to end of speech + padding (before breath)
    trim_frame = speech_end_frame + int(padding_ms / 10)
    trim_sample = min(wave.shape[1], trim_frame * frame_size)
    
    # Apply fade-out
    fade_samples = int(sr * fade_ms / 1000)
    if fade_samples > 0 and trim_sample > fade_samples:
        fade_start = trim_sample - fade_samples
        wave = wave.clone()
        fade_env = torch.linspace(1.0, 0.0, fade_samples).unsqueeze(0)
        wave[:, fade_start:trim_sample] *= fade_env
    
    result_info = {
        'speech_end_ms': speech_end_ms,
        'breath_start_ms': breath_start * 10,
        'breath_end_ms': breath_end * 10,
        'breath_duration_ms': breath_duration_ms,
        'trimmed_ms': (wave.shape[1] - trim_sample) / sr * 1000,
    }
    
    return wave[:, :trim_sample], result_info


def advanced_trim(wave, sr, 
                  speech_threshold_db=-30.0,
                  silence_threshold_db=-40.0,
                  min_speech_ms=50,
                  min_gap_ms=80,
                  fade_ms=30,
                  padding_ms=20):
    """Advanced trim combining multiple strategies.
    
    1. Trim silence from start/end
    2. Detect and trim breath artifacts (dynamic length)
    3. Apply fade-out
    
    Args:
        wave: (1, n_samples) tensor
        sr: sample rate
        speech_threshold_db: threshold for speech detection
        silence_threshold_db: threshold for silence detection
        min_speech_ms: minimum speech segment duration
        min_gap_ms: minimum gap to consider as separation
        fade_ms: fade-out duration
        padding_ms: padding to keep
    
    Returns: trimmed waveform
    """
    # Step 1: Dynamic breath trim (handles both silence and breath)
    wave, breath_info = dynamic_trim_breath(
        wave, sr, 
        speech_threshold_db=speech_threshold_db,
        breath_threshold_db=silence_threshold_db - 5,
        min_gap_ms=min_gap_ms,
        max_breath_ms=500,
        padding_ms=padding_ms,
        fade_ms=fade_ms
    )
    
    return wave


def tail_trim_fade(wave, sr, fade_ms=60, thresh_db=-40.0):
    """Trim quiet tail (breaths/noise) + fade-out."""
    return advanced_trim(wave, sr, 
                        speech_threshold_db=thresh_db + 10,
                        silence_threshold_db=thresh_db,
                        min_gap_ms=80,
                        fade_ms=fade_ms)


def prep_ref(ref_path):
    """Prepare reference audio for CosyVoice3."""
    import librosa
    speech, sr = torchaudio.load(ref_path)
    if sr != 16000:
        speech = torchaudio.transforms.Resample(sr, 16000)(speech)
    # Trim silence
    speech, _ = librosa.effects.trim(speech, top_db=20)
    # Normalize
    speech = speech / (speech.abs().max() + 1e-6)
    return speech


def gen_one(cosyvoice, text, ref, args):
    """Generate one speech segment."""
    prepped = prep_ref(ref)
    if args.seed is None:
        seed = random.randint(1, 100000000)
    else:
        seed = args.seed
    set_all_random_seed(seed)
    tgt = text
    if args.lang_token:
        tgt = '<|{}|>{}'.format(args.lang_token, tgt)
    if args.mode == 'zero_shot':
        transcript_path = os.path.splitext(ref)[0] + '.txt'
        if not os.path.exists(transcript_path):
            raise ValueError('для zero_shot нужен транскрипт {}.txt'.format(ref))
        with open(transcript_path, encoding='utf-8') as f:
            transcript = f.read().strip()
        prompt_text = CV3_PREFIX + transcript
        print('    prompt_text: {}'.format(prompt_text[:90]))
        gen = cosyvoice.inference_zero_shot(tgt, prompt_text, prepped, stream=False, speed=args.speed, text_frontend=False)
    elif args.mode == 'instruct2':
        instruct_text = args.instruct_text or 'You are a helpful assistant. Please speak in Russian, with a natural native accent.<|endofprompt|>'
        print('    instruct: {}'.format(instruct_text[:90]))
        gen = cosyvoice.inference_instruct2(tgt, instruct_text, prepped, stream=False, speed=args.speed, text_frontend=False)
    else:
        gen = cosyvoice.inference_cross_lingual(CV3_PREFIX + tgt, prepped, stream=False, speed=args.speed, text_frontend=False)
    for j in gen:
        return j['tts_speech']


def main():
    parser = argparse.ArgumentParser(description='TSSR Voice Generator')
    parser.add_argument('--text', default=None, help='одиночная фраза')
    parser.add_argument('--phrases', default=None, help='файл со списком фраз (по одной на строку, формат: id|text|ref)')
    parser.add_argument('--ref', required=True, help='путь к референсу голоса (.wav)')
    parser.add_argument('--out', default=None, help='выходной файл (.wav)')
    parser.add_argument('--out-dir', default=None, help='директория для выходных файлов')
    parser.add_argument('--id', default=None, help='translation ID для auto_voice')
    parser.add_argument('--speed', type=float, default=1.0)
    parser.add_argument('--mode', choices=['cross_lingual', 'zero_shot', 'instruct2'], default='cross_lingual')
    parser.add_argument('--lang-token', default='ru', help='языковой токен (default: ru)')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--sampling', default='0.5,10,0.15', help='top_p,top_k,tau_r')
    parser.add_argument('--cfg', type=float, default=0.9)
    parser.add_argument('--flow-temp', type=float, default=1.2)
    parser.add_argument('--rl', action='store_true', default=True)
    parser.add_argument('--base', action='store_true')
    parser.add_argument('--gap', type=float, default=GAP)
    parser.add_argument('--tail-trim', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--fade-ms', type=int, default=60)
    parser.add_argument('--s16', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--no-silent-trim', action='store_true')
    args = parser.parse_args()

    if args.sampling:
        top_p, top_k, tau_r = (float(x) for x in args.sampling.split(','))
    else:
        top_p = top_k = tau_r = None
    rl = args.rl and not args.base
    model_dir = make_tuned_model_dir(top_p, top_k, tau_r, rl, cfg_rate=args.cfg)

    # Parse phrases from file
    phrases = []
    if args.phrases:
        with open(args.phrases, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) >= 2:
                    phrase_id = parts[0].strip()
                    text = parts[1].strip()
                    ref = parts[2].strip() if len(parts) > 2 else args.ref
                    phrases.append((phrase_id, text, ref))
    elif args.text:
        phrase_id = args.id or 'manual'
        phrases.append((phrase_id, args.text, args.ref))
    else:
        print('ERROR: specify --text or --phrases')
        sys.exit(1)

    print('model  :', model_dir)
    print('mode   :', args.mode, '| lang-token:', args.lang_token, '| seed:', args.seed)
    print('phrases:', len(phrases))

    t0 = time.time()
    cosyvoice = AutoModel(model_dir=model_dir)
    if args.flow_temp is not None:
        patch_flow_temperature(args.flow_temp)
        print('flow temperature patched:', args.flow_temp)
    if not args.no_silent_trim:
        patch_silent_token_trim()
        print('silent/breath token trim: ON')
    print('model loaded in {:.1f}s'.format(time.time() - t0))

    out_dir = args.out_dir or os.path.dirname(args.out or '.')
    os.makedirs(out_dir, exist_ok=True)

    for phrase_id, text, ref in phrases:
        print('\n--- {} : "{}"'.format(phrase_id, text[:60]))
        t1 = time.time()
        speech = gen_one(cosyvoice, text, ref, args)
        if args.tail_trim:
            speech = tail_trim_fade(speech, cosyvoice.sample_rate, fade_ms=args.fade_ms)
        
        if args.out and len(phrases) == 1:
            out_path = args.out
        else:
            out_path = os.path.join(out_dir, '{}.wav'.format(phrase_id))
        
        if args.s16:
            torchaudio.save(out_path, speech, cosyvoice.sample_rate, encoding='PCM_S', bits_per_sample=16)
        else:
            torchaudio.save(out_path, speech, cosyvoice.sample_rate)
        
        duration = speech.shape[1] / cosyvoice.sample_rate
        rtf = (time.time() - t1) / duration
        print('    saved {} ({:.2f}s, rtf {:.2f})'.format(out_path, duration, rtf))

    print('\nDone! {} phrases generated.'.format(len(phrases)))


if __name__ == '__main__':
    main()
