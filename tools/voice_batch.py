#!/usr/bin/env python
"""Voice batch generator for TSSR (по мотивам W40KRT tools/cosyvoice3_batch.py).

ВХОД:
  - catalog/voices.json     каталог реплик (uid, old, new, who, arc, category)
  - config/voices.yaml      у кого есть голос (кто НЕ указан — пропускается)

ВЫХОД:
  ai_voice/{lang}/{arc}/{uid}__{variant}.wav   (resumable: существующие скипаются)
  Каждый файл выравнивается levelnorm.py: loudnorm -16 LUFS / TP -1.5

ПОБЕДНЫЙ КОНФИГ (как в W40KRT, 2026-08-29):
  cross_lingual + RL + flow-temp 1.2 + cfg 0.9 + RAS (0.5, 10, 0.15)
  + silent-token-trim ON + seed 42 + s16

ТРИМ: наш trim_tail_burst (паттерн «тишина → короткий всплеск у конца файла»).

Реф берётся ТОЛЬКО из config/voices.yaml (нет записи = не озвучиваем).
--ref перезаписывает путь (для A/B по in_progress-вариантам).

ЗАПУСК (ОБЯЗАТЕЛЬНО через venv CosyVoice):
  C:\\tools\\cosyvoice3\\.venv\\Scripts\\python.exe tools/voice_batch.py \\
      [--arc Prologue] [--char Sarah] [--uid uid1 uid2 ...] [--limit N]
      [--force] [--lang ru|en] [--dry-run]

Лог прогона: output/voice/batch.log
"""

import argparse
import hashlib
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voicekit import catalog, paths, tts_env  # noqa: E402

REPO_DIR = tts_env.cosy_repo_dir()
sys.path.insert(0, REPO_DIR)
sys.path.insert(0, os.path.join(REPO_DIR, 'third_party', 'Matcha-TTS'))
sys.path.insert(0, tts_env.W40K_TOOLS)
sys.path.insert(0, paths.TOOLS_DIR)

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torchaudio  # noqa: E402
from cosyvoice.cli.cosyvoice import AutoModel  # noqa: E402
from cosyvoice.utils.common import set_all_random_seed  # noqa: E402

from cosyvoice3_demo import (CV3_PREFIX, prep_ref, patch_flow_temperature,  # noqa: E402
                             patch_silent_token_trim, make_tuned_model_dir)
from trim_tail_burst import trim as pattern_trim  # noqa: E402

from voicekit import config as _cfg

_B = _cfg.section('batch')
FLOW_TEMP = float(_B.get('flow_temp', 1.2))
CFG_RATE = float(_B.get('cfg_rate', 0.9))
_smp = _B.get('sampling', [0.5, 10.0, 0.15])
SAMPLING = (float(_smp[0]), float(_smp[1]), float(_smp[2]))
DEFAULT_SEED = int(_B.get('seed', 42))
_pres = _B.get('instruct_presets', {})
INSTRUCT_PRESETS = {k: str(v) for k, v in _pres.items()}

LOG_PATH = paths.batch_log()


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
    """Глушим безвредный warning transformers про sliding window."""
    for name in ('transformers', 'transformers.modeling_utils',
                 'transformers.models.qwen2.modeling_qwen2'):
        logging.getLogger(name).setLevel(logging.CRITICAL)


def load_inputs():
    """Каталог и конфиг голосов. Возвращает (entries, voices, who_to_voice)."""
    return (catalog.load_catalog()['entries'],
            catalog.load_voices(),
            catalog.who_to_voice())


def select_phrases(entries, voices, who_to_voice, args):
    """Фильтруем каталог до списка фраз к генерации.

    Критерии: категория dialogue/narration, голос есть в voices.yaml,
    фильтры args. Реф — только из voices.yaml (или --ref).
    --text переопределяет всё: одна фраза с произвольным текстом
    (uid = md5(text), arc = --arc or 'Demo').
    """
    if args.text:
        uid = hashlib.md5(args.text.encode('utf-8')).hexdigest()
        arc = args.arc or 'Demo'
        ref_cfg = voices.get(args.char or '', {}).get('ref')
        if args.ref:
            ref = os.path.abspath(args.ref)
            variant = os.path.splitext(os.path.basename(args.ref))[0]
        elif ref_cfg:
            ref = paths.resolve_ref(ref_cfg)
            variant = os.path.splitext(os.path.basename(ref_cfg))[0]
        else:
            return []
        if args.emotion:
            variant += '_{}'.format(args.emotion_tag)
        out = os.path.join(paths.AI_VOICE_DIR, args.lang,
                           arc, uid + '__' + variant + '.wav')
        return [dict(
            uid=uid, arc=arc, voice=args.char or 'Demo', ref=ref, out=out,
            variant=variant, lang=args.lang,
            text=args.text, text_old=args.text, text_new=args.text,
            emotion=args.emotion,
        )]
    phrases = []
    for e in entries:
        cat = e['category']
        if cat not in ('dialogue', 'narration'):
            continue
        if cat == 'narration':
            voice = who_to_voice.get('narrator')
        else:
            voice = who_to_voice.get(e['who'])
        if voice is None:
            continue
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
            ref = paths.resolve_ref(ref_cfg)
            variant = os.path.splitext(os.path.basename(ref_cfg))[0]
        else:
            continue  # нет записи/рефа в voices.yaml -> не озвучиваем
        if args.emotion:
            variant += '_{}'.format(args.emotion_tag)
        out = os.path.join(paths.AI_VOICE_DIR, args.lang,
                           e['arc'], e['uid'] + '__' + variant + '.wav')
        phrases.append(dict(
            uid=e['uid'], arc=e['arc'], voice=voice, ref=ref, out=out,
            variant=variant, lang=args.lang,
            text=(e['new'] if args.lang == 'ru' else e['old']),
            text_old=e['old'], text_new=e['new'],
            emotion=args.emotion,
        ))
    return phrases


def write_manifest(p, args):
    """Манифест рядом с wav: по какому рефу/конфигу сгенерировано.

    Пишется ДО генерации — файл-описание существует даже если генерация
    упадёт. Путь: {out}.txt (рядом с wav).
    """
    cfg_line = 'flow-temp {}, cfg {}, RAS {}, seed {}, silent-trim ON, speed 1.0'.format(
        args.flow_temp, args.cfg_rate, (args.top_p, args.top_k, args.tau_r),
        args.seed)
    lines = [
        '# TSSR voice manifest',
        'uid: {}'.format(p['uid']),
        'arc: {}'.format(p['arc']),
        'voice: {}'.format(p['voice']),
        'variant: {}'.format(p['variant']),
        'lang: {}'.format(p['lang']),
        'ref: {}'.format(os.path.relpath(p['ref'], paths.ROOT).replace(os.sep, '/')),
        'emotion: {}'.format(p['emotion'] or '-'),
        'text_ru: {}'.format(p['text_new']),
        'text_en: {}'.format(p['text_old']),
        'config: {}'.format(cfg_line),
        'generated: {}'.format(time.strftime('%Y-%m-%d %H:%M')),
    ]
    try:
        os.makedirs(os.path.dirname(p['out']), exist_ok=True)
        with open(p['out'] + '.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception as e:
        log('  !! manifest fail: {}'.format(e))


def gen_one(cosyvoice, text, ref, seed, emotion=None):
    """Одна фраза: реф + текст -> тензор речи.

    emotion — стилевая инструкция: используем instruct2-режим
    (инструкция отдельным аргументом, тот же промпт-формат, что у
    cross_lingual, но модель точно знает, что это стиль).
    """
    prepped = prep_ref(ref)
    set_all_random_seed(seed)
    if emotion:
        instruct = 'You are a helpful assistant. {}.<|endofprompt|>'.format(
            emotion)
        gen = cosyvoice.inference_instruct2(
            text, instruct, prepped, stream=False, speed=1.0,
            text_frontend=False)
    else:
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
    ap.add_argument('--seed', type=int, default=DEFAULT_SEED)
    ap.add_argument('--dry-run', action='store_true',
                    help='только список к генерации, без модели')
    ap.add_argument('--ref', default=None,
                    help='путь к рефу (перезаписывает yaml)')
    ap.add_argument('--emotion', default=None,
                    help='стиль: пресет (angry/sad/happy/fast/slow/loud/soft/'
                         'whisper/russian) или свободная инструкция')
    ap.add_argument('--emotion-tag', default='em',
                    help='суффикс файла для эмоции (default em)')
    ap.add_argument('--text', default=None,
                    help='произвольный текст (демо): одна фраза, '
                         'uid = md5(text), arc = --arc or Demo')
    ap.add_argument('--top-p', type=float, default=SAMPLING[0],
                    help='LLM nucleus sampling (default 0.5)')
    ap.add_argument('--top-k', type=int, default=SAMPLING[1],
                    help='LLM top-k кандидатов (default 10)')
    ap.add_argument('--tau-r', type=float, default=SAMPLING[2],
                    help='RAS штраф повторов (default 0.15)')
    ap.add_argument('--cfg-rate', type=float, default=CFG_RATE,
                    help='LLM classifier-free guidance (default 0.9)')
    ap.add_argument('--flow-temp', type=float, default=FLOW_TEMP,
                    help='температура flow-декодера (default 1.2)')
    args = ap.parse_args()
    if args.emotion and args.emotion in INSTRUCT_PRESETS:
        args.emotion = INSTRUCT_PRESETS[args.emotion]
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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

    model_dir = make_tuned_model_dir(args.top_p, args.top_k, args.tau_r,
                                     rl=True, cfg_rate=args.cfg_rate)
    log('model: {}'.format(model_dir))
    silence_benign_warnings()
    t0 = time.time()
    cosyvoice = AutoModel(model_dir=model_dir)
    patch_flow_temperature(args.flow_temp)
    patch_silent_token_trim()
    log('model loaded in {:.1f}s (flow-temp {}, cfg {}, RAS {}, silent-trim ON)'.format(
        time.time() - t0, args.flow_temp, args.cfg_rate,
        (args.top_p, args.top_k, args.tau_r)))

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
        write_manifest(p, args)  # описание ДО генерации
        try:
            speech = gen_one(cosyvoice, p['text'], p['ref'], args.seed,
                             p.get('emotion'))
            sr = cosyvoice.sample_rate
            trimmed, cuts = pattern_trim(speech, sr)
            os.makedirs(os.path.dirname(p['out']), exist_ok=True)
            torchaudio.save(p['out'], trimmed, sr,
                            encoding='PCM_S', bits_per_sample=16)
            dur = trimmed.shape[1] / sr
            try:
                from levelnorm import normalize_file
                normalize_file(p['out'])
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