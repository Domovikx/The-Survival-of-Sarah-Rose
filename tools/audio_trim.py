#!/usr/bin/env python
"""Advanced audio trim tools for TSSR voice files.

Usage:
  C:\\tools\\cosyvoice3\\.venv\\Scripts\\python.exe tools/audio_trim.py input.wav output.wav
  C:\\tools\\cosyvoice3\\.venv\\Scripts\\python.exe tools/audio_trim.py --batch input_dir/ output_dir/
"""

import argparse
import os
import sys
import torch
import torchaudio


def load_audio(path):
    """Load audio file and return (waveform, sample_rate)."""
    wave, sr = torchaudio.load(path)
    # Convert to mono if stereo
    if wave.shape[0] > 1:
        wave = wave.mean(dim=0, keepdim=True)
    return wave, sr


def save_audio(path, wave, sr, bits=16):
    """Save audio file."""
    if bits == 16:
        torchaudio.save(path, wave, sr, encoding='PCM_S', bits_per_sample=16)
    else:
        torchaudio.save(path, wave, sr)


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


def detect_speech_segments(rms, threshold_db=-30.0, min_speech_ms=50, sample_rate=24000):
    """Detect speech segments above threshold.
    
    Returns list of (start_frame, end_frame) tuples.
    """
    thr = 10 ** (threshold_db / 20)
    above = rms > thr
    
    frame_size = int(sample_rate * 0.01)  # 10ms frames
    min_speech_frames = int(min_speech_ms / 10)
    
    segments = []
    in_speech = False
    start = 0
    
    for i in range(len(above)):
        if above[i] and not in_speech:
            start = i
            in_speech = True
        elif not above[i] and in_speech:
            if i - start >= min_speech_frames:
                segments.append((start, i))
            in_speech = False
    
    if in_speech and len(above) - start >= min_speech_frames:
        segments.append((start, len(above)))
    
    return segments


def trim_silence(wave, sr, threshold_db=-30.0, min_silence_ms=100, padding_ms=20):
    """Trim silence from start and end.
    
    Args:
        wave: (1, n_samples) tensor
        sr: sample rate
        threshold_db: silence threshold in dB
        min_silence_ms: minimum silence duration to trim
        padding_ms: padding to keep after/before speech
    
    Returns: trimmed waveform
    """
    frame_size = int(sr * 0.01)  # 10ms frames
    rms = compute_rms(wave, frame_size)
    
    if len(rms) == 0:
        return wave
    
    segments = detect_speech_segments(rms, threshold_db, min_silence_ms, sr)
    
    if not segments:
        # No speech detected, return empty
        return wave[:, :int(sr * 0.1)]
    
    # Find first and last speech segments
    first_start = segments[0][0]
    last_end = segments[-1][1]
    
    # Convert to samples with padding
    start_sample = max(0, first_start * frame_size - int(sr * padding_ms / 1000))
    end_sample = min(wave.shape[1], last_end * frame_size + int(sr * padding_ms / 1000))
    
    return wave[:, start_sample:end_sample]


def trim_breath(wave, sr, threshold_db=-30.0, breath_threshold_db=-35.0, 
                min_gap_ms=80, max_breath_ms=300, fade_ms=30):
    """Trim breath/inhale artifacts at the end of speech.
    
    Strategy:
    1. Find last speech segment
    2. Look for breath-like patterns after it (short bursts after silence)
    3. Trim if found
    
    Args:
        wave: (1, n_samples) tensor
        sr: sample rate
        threshold_db: speech threshold
        breath_threshold_db: breath detection threshold (lower than speech)
        min_gap_ms: minimum gap between speech and breath to consider it a breath
        max_breath_ms: maximum breath duration to trim
        fade_ms: fade-out duration
    
    Returns: trimmed waveform
    """
    frame_size = int(sr * 0.01)  # 10ms frames
    rms = compute_rms(wave, frame_size)
    
    if len(rms) < 3:
        return wave
    
    # Find speech segments
    speech_segments = detect_speech_segments(rms, threshold_db, 50, sr)
    
    if not speech_segments:
        return wave
    
    # Get last speech segment
    last_speech_end = speech_segments[-1][1]
    
    # Look for breath after last speech
    breath_thr = 10 ** (breath_threshold_db / 20)
    min_gap_frames = int(min_gap_ms / 10)
    max_breath_frames = int(max_breath_ms / 10)
    
    # Search for breath patterns in the tail
    search_start = last_speech_end
    search_end = min(len(rms), last_speech_end + max_breath_frames)
    
    # Find silence gap after speech
    gap_frames = 0
    for i in range(search_start, search_end):
        if rms[i] < breath_thr:
            gap_frames += 1
        else:
            break
    
    # If there's a gap followed by sound, it's likely a breath
    if gap_frames >= min_gap_frames:
        breath_start = search_start + gap_frames
        if breath_start < search_end:
            # Found breath - trim to end of speech + small padding
            trim_frame = last_speech_end + int(20 / 10)  # 20ms padding
            trim_sample = min(wave.shape[1], trim_frame * frame_size)
            
            # Apply fade-out
            fade_samples = int(sr * fade_ms / 1000)
            if fade_samples > 0 and trim_sample > fade_samples:
                fade_start = trim_sample - fade_samples
                wave = wave.clone()
                wave[:, fade_start:trim_sample] *= torch.linspace(1.0, 0.0, fade_samples).unsqueeze(0)
            
            return wave[:, :trim_sample]
    
    # Also check for isolated bursts (original logic)
    last_loud = None
    for i in range(len(rms) - 1, -1, -1):
        if rms[i] > 10 ** (threshold_db / 20):
            last_loud = i
            break
    
    if last_loud is None:
        return wave
    
    # Find previous loud frame
    prev_loud = None
    for i in range(last_loud - 1, -1, -1):
        if rms[i] > 10 ** (threshold_db / 20):
            prev_loud = i
            break
    
    # Check if there's a gap between them
    if prev_loud is not None:
        gap = last_loud - prev_loud - 1
        if gap >= min_gap_frames:
            # Isolated burst - trim to prev_loud
            trim_frame = prev_loud + int(20 / 10)  # 20ms padding
            trim_sample = min(wave.shape[1], trim_frame * frame_size)
            return wave[:, :trim_sample]
    
    return wave


def advanced_trim(wave, sr, 
                  speech_threshold_db=-30.0,
                  silence_threshold_db=-40.0,
                  min_speech_ms=50,
                  min_gap_ms=80,
                  fade_ms=30,
                  padding_ms=20):
    """Advanced trim combining multiple strategies.
    
    1. Trim silence from start/end
    2. Detect and trim breath artifacts
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
    # Step 1: Trim silence
    wave = trim_silence(wave, sr, silence_threshold_db, min_speech_ms, padding_ms)
    
    # Step 2: Trim breath
    wave = trim_breath(wave, sr, speech_threshold_db, silence_threshold_db - 5,
                       min_gap_ms, 300, fade_ms)
    
    return wave


def batch_trim(input_dir, output_dir, **kwargs):
    """Batch trim all WAV files in directory."""
    os.makedirs(output_dir, exist_ok=True)
    
    for fname in os.listdir(input_dir):
        if fname.lower().endswith('.wav'):
            in_path = os.path.join(input_dir, fname)
            out_path = os.path.join(output_dir, fname)
            
            try:
                wave, sr = load_audio(in_path)
                trimmed = advanced_trim(wave, sr, **kwargs)
                save_audio(out_path, trimmed, sr)
                
                orig_duration = wave.shape[1] / sr
                new_duration = trimmed.shape[1] / sr
                print('{}: {:.2f}s -> {:.2f}s (trimmed {:.0f}ms)'.format(
                    fname, orig_duration, new_duration, (orig_duration - new_duration) * 1000))
            except Exception as e:
                print('ERROR {}: {}'.format(fname, e))


def main():
    parser = argparse.ArgumentParser(description='Advanced audio trim for TSSR voice files')
    parser.add_argument('input', help='input WAV file or directory')
    parser.add_argument('output', help='output WAV file or directory')
    parser.add_argument('--batch', action='store_true', help='batch process directory')
    parser.add_argument('--speech-threshold', type=float, default=-30.0, help='speech threshold dB')
    parser.add_argument('--silence-threshold', type=float, default=-40.0, help='silence threshold dB')
    parser.add_argument('--min-gap', type=float, default=80, help='min gap ms')
    parser.add_argument('--fade', type=float, default=30, help='fade-out ms')
    parser.add_argument('--padding', type=float, default=20, help='padding ms')
    args = parser.parse_args()
    
    kwargs = dict(
        speech_threshold_db=args.speech_threshold,
        silence_threshold_db=args.silence_threshold,
        min_gap_ms=args.min_gap,
        fade_ms=args.fade,
        padding_ms=args.padding,
    )
    
    if args.batch:
        batch_trim(args.input, args.output, **kwargs)
    else:
        wave, sr = load_audio(args.input)
        trimmed = advanced_trim(wave, sr, **kwargs)
        save_audio(args.output, trimmed, sr)
        
        orig_duration = wave.shape[1] / sr
        new_duration = trimmed.shape[1] / sr
        print('Trimmed: {:.2f}s -> {:.2f}s (removed {:.0f}ms)'.format(
            orig_duration, new_duration, (orig_duration - new_duration) * 1000))


if __name__ == '__main__':
    main()
