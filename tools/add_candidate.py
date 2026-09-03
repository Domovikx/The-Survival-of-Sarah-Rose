#!/usr/bin/env python
"""Добавление нового голоса-кандидата в проект (инкрементально).

ЧТО ДЕЛАЕТ (по шагам, существующие файлы НЕ пересоздаются):
  1. Сканирует voice_candidates/{Голос}/gen_selected/*.mp3
     (сюда кладёшь отобранные на слух клипы; имя = {Name}.mp3 или {Name}_1.mp3)
  2. Первые 10 секунд -> чистка -> voice_candidates/{Голос}/in_progress/
     (рабочая зона: рефы для A/B и экспериментов с фильтрами)
  3. Финальный реф (после A/B) фиксируется в ref/ через voice_manage select

ЗАПУСК:
  python tools/add_candidate.py
  python tools/add_candidate.py --only "King Orwell Rose"
"""

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clean_refs import clean_file, compress_pauses_file, pause_params  # noqa: E402
from voicekit import catalog, paths  # noqa: E402

from voicekit import config as _cfg

TARGET_LEN = float(_cfg.get('refs', 'target_len', 10.0))
SR_RATE = int(_cfg.get('audio', 'sr', 24000))


def find_candidates():
    """{имя_голоса: [пути_к_mp3]} по gen_selected/ всех персонажей."""
    found = {}
    if not os.path.isdir(paths.VOICE_CANDIDATES):
        return found
    for name in sorted(os.listdir(paths.VOICE_CANDIDATES)):
        folder = paths.char_subdir(name, 'gen_selected')
        if not os.path.isdir(folder):
            continue
        mp3s = sorted(
            f for f in os.listdir(folder)
            if f.lower().endswith('.mp3')
        )
        if mp3s:
            found[name] = [os.path.join(folder, f) for f in mp3s]
    return found


def cut_and_clean(name, mp3_path, variant=None):
    """Нарезка 10с + чистка -> in_progress/{name}[_{variant}].wav."""
    suffix = '_{}'.format(variant) if variant else ''
    dst = os.path.join(paths.char_subdir(name, 'in_progress'),
                       name + suffix + '.wav')
    if os.path.exists(dst):
        return dst, False

    os.makedirs(os.path.dirname(dst), exist_ok=True)

    tmp_cut = os.path.join(paths.char_subdir(name, 'in_progress'),
                           name + '_tmp.wav')
    dur = float(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=duration',
         '-of', 'csv=p=0', mp3_path]).decode().strip().splitlines()[0])
    cut_end = min(TARGET_LEN, dur)
    subprocess.run(['ffmpeg', '-y', '-ss', '0', '-to', '{:.3f}'.format(cut_end),
                    '-i', mp3_path, '-ac', '1', '-ar', str(SR_RATE), tmp_cut],
                   check=True, capture_output=True)

    n_cut, max_pause = compress_pauses_file(tmp_cut, SR_RATE)
    if n_cut:
        print('    паузы: сжато {} (макс {:.2f}с -> {:.2f}с)'.format(
            n_cut, max_pause, pause_params()[0]))

    clean_file(tmp_cut, dst)
    os.remove(tmp_cut)
    return dst, True


def yaml_snippet(name, who_map):
    """Печатаем фрагмент для config/voices.yaml."""
    print('  --- добавь в config/voices.yaml: ---')
    print('  {}:'.format(name))
    print('    ref: {}'.format(paths.ref_voices(name)))
    print('    gender: ???   # заполни: M / F')
    if name in who_map:
        print('    who: {}'.format(', '.join(sorted(who_map[name]))))
    print('  ----------------------------------')


def load_who_map():
    """Из catalog/voices.json достаём {имя: [who]}."""
    import json
    path = paths.VOICES_JSON
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    chars = data.get('characters', {})
    who_map = {}
    for who, name in chars.items():
        who_map.setdefault(name, []).append(who)
    return who_map


def main():
    ap = argparse.ArgumentParser(description='Добавление голоса-кандидата')
    ap.add_argument('--only', default=None,
                    help='обработать только этот голос (имя папки)')
    args = ap.parse_args()

    candidates = find_candidates()
    if args.only:
        if args.only not in candidates:
            print('НЕТ кандидата "{}". Есть: {}'.format(
                args.only, ', '.join(sorted(candidates)) or '—'))
            return 1
        candidates = {args.only: candidates[args.only]}

    if not candidates:
        print('В gen_selected/ нет ни одного .mp3.')
        return 0

    who_map = load_who_map()
    print('Кандидатов: {} голосов'.format(len(candidates)))

    for name, mp3s in sorted(candidates.items()):
        print('\n=== {} ==='.format(name))
        for mp3_path in mp3s:
            mp3_name = os.path.splitext(os.path.basename(mp3_path))[0]
            if mp3_name.startswith(name + '_'):
                variant = mp3_name[len(name) + 1:]
            elif mp3_name == name:
                variant = None
            else:
                variant = mp3_name
            ref_path, made = cut_and_clean(name, mp3_path, variant)
            print('  {:<40s} {}'.format(
                os.path.relpath(ref_path, paths.ROOT),
                'НОВЫЙ' if made else 'уже был'))
        yaml_snippet(name, who_map)

    print('\nГотово. Рабочие рефы в in_progress/. '
          'Финальный реф: voice_manage select.')
    return 0


if __name__ == '__main__':
    sys.exit(main())