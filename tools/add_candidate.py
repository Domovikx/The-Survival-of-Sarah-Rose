#!/usr/bin/env python
"""Добавление нового голоса-кандидата в проект (инкрементально).

ЧТО ДЕЛАЕТ (по шагам, существующие файлы НЕ пересоздаются):
  1. Сканирует voice_candidates/{Голос}/*.mp3  (имя папки = имя голоса)
  2. Первые 10 секунд → очистка → refs/{Голос}.wav
     (denoise + EQ + loudnorm, всё сразу; voices.yaml ссылается сюда)

СТРУКТУРА REFS:
  refs/     ГОТОВЫЕ рефы: нарезка 10с + чистка + loudnorm
                (voice_batch.py читает отсюда)

ЗАПУСК:
  python tools/add_candidate.py
  python tools/add_candidate.py --only "King Orwell Rose"

ПРИМЕР РАБОТЫ:
  Положил voice_candidates/Hassar/abc.mp3 → запустил тул →
  refs/Hassar.wav готов, в консоли фрагмент для config/voices.yaml.
"""

import argparse
import os
import subprocess
import sys

# импорт чистильщика из этого же каталога tools/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean_refs import clean_file

# Пути проекта (абсолютные — тул можно запускать из любого каталога)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES_DIR = os.path.join(ROOT, 'voice_candidates')
RAW_DIR = os.path.join(ROOT, 'refs')

TARGET_LEN = 10.0   # сколько секунд рефа оставляем для CosyVoice
SR_RATE = 24000     # частота дискретизации рефа (такая же у CV3)


def find_candidates():
    """Возвращает {имя_голоса: [пути_к_mp3]} для всех папок-кандидатов."""
    found = {}
    if not os.path.isdir(CANDIDATES_DIR):
        return found
    for name in sorted(os.listdir(CANDIDATES_DIR)):
        folder = os.path.join(CANDIDATES_DIR, name)
        if not os.path.isdir(folder):
            continue
        mp3s = sorted(f for f in os.listdir(folder)
                      if f.lower().endswith('.mp3'))
        if mp3s:
            found[name] = [os.path.join(folder, f) for f in mp3s]
    return found


def cut_and_clean(name, mp3_path, variant=None):
    """Нарезка 10с + чистка → refs/{name}_{variant}.wav или refs/{name}.wav."""
    suffix = f"_{variant}" if variant else ""
    dst = os.path.join(RAW_DIR, name + suffix + '.wav')
    if os.path.exists(dst):
        return dst, False

    os.makedirs(RAW_DIR, exist_ok=True)

    # Нарезка во временный файл
    tmp_cut = os.path.join(RAW_DIR, name + '_tmp.wav')
    dur = float(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=duration',
         '-of', 'csv=p=0', mp3_path]).decode().strip().splitlines()[0])
    cut_end = min(TARGET_LEN, dur)
    subprocess.run(['ffmpeg', '-y', '-ss', '0', '-to', '{:.3f}'.format(cut_end),
                    '-i', mp3_path, '-ac', '1', '-ar', str(SR_RATE), tmp_cut],
                   check=True, capture_output=True)

    # Чистка: denoise + EQ + loudnorm → refs/{name}.wav
    clean_file(tmp_cut, dst)
    os.remove(tmp_cut)
    return dst, True


def yaml_snippet(name, who_map):
    """Печатаем фрагмент для config/voices.yaml."""
    print('  --- добавь в config/voices.yaml: ---')
    print('  {}:'.format(name))
    print('    ref: refs/{}.wav'.format(name))
    print('    gender: ???   # заполни: M / F')
    if name in who_map:
        print('    who: {}'.format(', '.join(sorted(who_map[name]))))
    print('  ----------------------------------')


def load_who_map():
    """Из catalog/voices.json достаём {имя: [who]}."""
    import json
    path = os.path.join(ROOT, 'catalog', 'voices.json')
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
        print('В voice_candidates/ нет ни одной папки с .mp3.')
        return 0

    who_map = load_who_map()
    print('Кандидатов: {} голосов'.format(len(candidates)))

    for name, mp3s in sorted(candidates.items()):
        print('\n=== {} ==='.format(name))
        for mp3_path in mp3s:
            # Извлекаем имя варианта из имени файла: Sarah_1.mp3 → 1
            mp3_name = os.path.splitext(os.path.basename(mp3_path))[0]
            # Убираем имя голоса из начала: Sarah_1 → 1, Sarah → None
            if mp3_name.startswith(name + "_"):
                variant = mp3_name[len(name)+1:]
            elif mp3_name == name:
                variant = None
            else:
                variant = mp3_name
            ref_path, made = cut_and_clean(name, mp3_path, variant)
            print('  refs/{:<35s} {}'.format(
                os.path.basename(ref_path), 'НОВЫЙ' if made else 'уже был'))
        yaml_snippet(name, who_map)

    print('\nГотово. Осталось вписать фрагменты в config/voices.yaml.')


if __name__ == '__main__':
    sys.exit(main())
