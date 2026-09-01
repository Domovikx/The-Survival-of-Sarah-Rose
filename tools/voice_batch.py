#!/usr/bin/env python
"""Voice batch generator for TSSR (по мотивам W40KRT tools/cosyvoice3_batch.py).

ВХОД:
  - catalog/voices.json     каталог реплик (uid, old, new, who, arc, category)
  - config/voices.yaml      у кого есть голос (кто НЕ указан — пропускается)

ВЫХОД:
  ai_voice/{lang}/{arc}/{uid}__{variant}.wav   (resumable: существующие скипаются)
  Каждый файл выравнивается levelnorm.py: loudnorm -16 LUFS / TP -1.5
  (CV3 гуляет по уровню — иначе реплики -14...-18 LUFS, TP до +0.2).

ПОБЕДНЫЙ КОНФИГ (как в W40KRT, 2026-08-29):
  cross_lingual + RL + flow-temp 1.2 + cfg 0.9 + RAS (0.5, 10, 0.15)
  + silent-token-trim ON + seed 42 + s16

ТРИМ: наш trim_tail_burst (паттерн «тишина → короткий всплеск у конца файла»).

ЗАПУСК (ОБЯЗАТЕЛЬНО через venv CosyVoice):
  C:\\tools\\cosyvoice3\\.venv\\Scripts\\python.exe tools/voice_batch.py \\
      [--arc Prologue] [--char Sarah] [--uid uid1 uid2 ...] [--limit N]
      [--force] [--lang ru|en] [--dry-run]

Лог прогона: output/voice/batch.log
"""

import argparse
import json
import logging
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W40K_TOOLS = os.path.join(
    r'C:\Users\Domo\AppData\LocalLow\Owlcat Games\Warhammer 40000 Rogue Trader',
    'UnityModManager', 'W40KRTAudioDirectMod', 'tools')
COSY_ROOT = r'C:\tools\cosyvoice3'
REPO_DIR = os.path.join(COSY_ROOT, 'CosyVoice')
sys.path.insert(0, REPO_DIR)
sys.path.insert(0, os.path.join(REPO_DIR, 'third_party', 'Matcha-TTS'))
sys.path.insert(0, W40K_TOOLS)      # cosyvoice3_demo (helper-функции)
sys.path.insert(0, os.path.join(ROOT, 'tools'))  # trim_tail_burst

import numpy as np
import torch
import torchaudio
import yaml
from cosyvoice.cli.cosyvoice import AutoModel
from cosyvoice.utils.common import set_all_random_seed

from cosyvoice3_demo import (CV3_PREFIX, prep_ref, patch_flow_temperature,
                             patch_silent_token_trim, make_tuned_model_dir)
from trim_tail_burst import trim as pattern_trim

FLOW_TEMP = 1.2
CFG_RATE = 0.9
SAMPLING = (0.5, 10.0, 0.15)

LOG_PATH = os.path.join(ROOT, 'output', 'voice', 'batch.log')


def log(msg):
    """Пишем строку в консоль и в лог прогона."""
    print(msg)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%H:%M:%S ') + msg + '\n')
    except Exception:
        pass


def silence_benign_warnings():
    """Глушим безвредный warning transformers про sliding window.

    Он печатается при загрузке модели, выглядит пугающе («ERROR: Sliding
    Window Attention...»), но на генерацию НЕ влияет (logger.warning_once
    в transformers/models/qwen2/modeling_qwen2.py).
    """
    for name in ('transformers', 'transformers.modeling_utils',
                 'transformers.models.qwen2.modeling_qwen2'):
        logging.getLogger(name).setLevel(logging.CRITICAL)


def load_inputs():
    """Читаем каталог и конфиг голосов. Возвращаем (entries, voices, who_to_voice)."""
    with open(os.path.join(ROOT, 'catalog', 'voices.json'), encoding='utf-8') as f:
        data = json.load(f)
    entries = data['entries']
    with open(os.path.join(ROOT, 'config', 'voices.yaml'), encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    voices = cfg.get('voices', {})
    who_to_voice = {}
    for vname, vcfg in voices.items():
        for w in vcfg.get('who', []):
            who_to_voice[w] = vname
    return entries, voices, who_to_voice


def select_phrases(entries, voices, who_to_voice, args):
    """Фильтруем каталог до списка фраз к генерации.

    Возвращает список dict: uid, arc, text, voice (имя голоса), ref, out.
    Критерии: категория dialogue/narration, голос есть, фильтры args.
    """
    phrases = []
    for e in entries:
        cat = e['category']
        if cat not in ('dialogue', 'narration'):
            continue  # ui / menu не озвучиваем
        if cat == 'narration':
            voice = who_to_voice.get('narrator')   # наррация -> Narrator
        else:
            voice = who_to_voice.get(e['who'])     # диалог -> голос спикера
        if voice is None:
            continue  # голоса нет -> пропускаем (правило «не озвучивать»)
        if args.arc and e['arc'] != args.arc:
            continue
        if args.char and (e['who_name'] or 'Narrator') != args.char:
            continue
        if args.uid and e['uid'] not in args.uid:
            continue
        ref_cfg = voices.get(voice, {}).get('ref')
        if args.ref:
            ref = os.path.abspath(args.ref)
            variant = os.path.splitext(os.path.basename(args.ref))[0]
        elif ref_cfg:
            ref = os.path.join(ROOT, ref_cfg)
            variant = os.path.splitext(os.path.basename(ref_cfg))[0]
        else:
            ref = os.path.join(ROOT, 'refs', voice + '.wav')  # плоский refs/
            variant = voice
        out = os.path.join(ROOT, 'ai_voice', args.lang,
                           e['arc'], e['uid'] + '__' + variant + '.wav')
        phrases.append(dict(
            uid=e['uid'], arc=e['arc'], voice=voice, ref=ref, out=out,
            text=(e['new'] if args.lang == 'ru' else e['old']),
        ))
    return phrases


def gen_one(cosyvoice, text, ref, seed):
    """Одна фраза: реф + текст -> тензор речи (cross_lingual + RL)."""
    prepped = prep_ref(ref)
    set_all_random_seed(seed)
    gen = cosyvoice.inference_cross_lingual(CV3_PREFIX + text, prepped,
                                            stream=False, speed=1.0,
                                            text_frontend=False)
    for j in gen:
        return j['tts_speech']


def main():
    ap = argparse.ArgumentParser(description='TSSR voice batch (CV3)')
    ap.add_argument('--arc', default=None, help='только эта арка')
    ap.add_argument('--char', default=None, help='только этот персонаж (who_name)')
    ap.add_argument('--uid', nargs='*', default=None, help='только эти uid')
    ap.add_argument('--limit', type=int, default=None, help='максимум фраз за прогон')
    ap.add_argument('--force', action='store_true', help='перегенерировать существующие')
    ap.add_argument('--lang', default='ru', choices=['ru', 'en'])
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--dry-run', action='store_true',
                    help='только список к генерации, без модели')
    ap.add_argument('--ref', default=None,
                    help='путь к рефу (перезаписывает yaml)')
    args = ap.parse_args()

    entries, voices, who_to_voice = load_inputs()
    phrases = select_phrases(entries, voices, who_to_voice, args)
    log('фраз к генерации: {} (lang={}, force={})'.format(
        len(phrases), args.lang, args.force))
    for p in phrases[:10]:
        log('  {} | {} | {} | {}'.format(
            p['uid'][:8], p['arc'], p['voice'], p['text'][:60]))
    if len(phrases) > 10:
        log('  ...')
    if args.dry_run:
        return

    model_dir = make_tuned_model_dir(*SAMPLING, rl=True, cfg_rate=CFG_RATE)
    log('model: {}'.format(model_dir))
    silence_benign_warnings()   # ДО загрузки модели — чтобы warning не просочился
    t0 = time.time()
    cosyvoice = AutoModel(model_dir=model_dir)
    patch_flow_temperature(FLOW_TEMP)
    patch_silent_token_trim()
    log('model loaded in {:.1f}s (flow-temp {}, cfg {}, RAS {}, silent-trim ON)'.format(
        time.time() - t0, FLOW_TEMP, CFG_RATE, SAMPLING))

    done = skipped = failed = 0
    total = len(phrases)
    t_start = time.time()
    for idx, p in enumerate(phrases):
        if os.path.exists(p['out']) and not args.force:
            skipped += 1
            continue
        if args.limit and done >= args.limit:
            break
        log('[{}/{}] {} {} {}: {}'.format(
            idx + 1, total, p['uid'][:8], p['arc'], p['voice'], p['text'][:60]))
        try:
            speech = gen_one(cosyvoice, p['text'], p['ref'], args.seed)
            sr = cosyvoice.sample_rate
            trimmed, cuts = pattern_trim(speech, sr)
            os.makedirs(os.path.dirname(p['out']), exist_ok=True)
            torchaudio.save(p['out'], trimmed, sr,
                            encoding='PCM_S', bits_per_sample=16)
            dur = trimmed.shape[1] / sr
            try:
                from levelnorm import normalize_file
                normalize_file(p['out'])  # CV3 гуляет по уровню -> -16 LUFS
            except Exception:
                pass
            trim_info = ''
            if cuts:
                trim_info = ' | trim: ' + ', '.join(
                    'burst {:.0f}ms after {:.0f}ms gap'.format(c['dur_ms'], c['gap_ms'])
                    for c in cuts)
            eta = (time.time() - t_start) / max(done + 1, 1) * (total - idx - 1)
            log('  saved {} ({:.1f}s){}, eta ~{:.0f} мин'.format(
                p['out'], dur, trim_info, eta / 60))
            done += 1
        except Exception as e:
            failed += 1
            log('  !! FAIL {}: {}'.format(p['uid'], e))

    log('done={} skipped={} failed={} total={}'.format(done, skipped, failed, total))


if __name__ == '__main__':
    main()
