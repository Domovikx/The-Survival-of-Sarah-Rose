#!/usr/bin/env python
"""Добавление нового голоса-кандидата в проект (инкрементально).

ЧТО ДЕЛАЕТ (по шагам, существующие файлы НЕ пересоздаются):
  1. Сканирует voice_candidates/{Голос}/*.mp3  (имя папки = имя голоса)
  2. Первые 10 секунд -> refs/raw/{Голос}.wav (нарезка из кандидата)
  3. Whisper-транскрипт нарезки -> refs/raw/{Голос}.txt
     (.txt нужен ТОЛЬКО режиму zero_shot; cross_lingual его не читает)
  4. Вылеченная копия -> refs/voices/{Голос}.wav
     (денойз + EQ + loudnorm, см. clean_refs.py; voices.yaml ссылается
      именно на refs/voices/ — рабочие рефы ВСЕГДА вылеченные)
  5. Печатает готовый фрагмент для config/voices.yaml

СТРУКТУРА REFS (3 папки, без дублей):
  refs/raw/       грязная нарезка + txt (пересобирается из кандидатов)
  refs/voices/    РАБОЧИЕ рефы RU: вылечены + громкость выровнена
  refs/voices_en/ рефы EN (настоящие EN-кандидаты; пока может быть пусто)

ЗАПУСК (обязательно через venv CosyVoice — там стоит whisper):
  C:\\tools\\cosyvoice3\\.venv\\Scripts\\python.exe tools/add_candidate.py
  ... add_candidate.py --only "King Orwell Rose"   # только один голос
  ... add_candidate.py --whisper small             # лёгкая модель (~0.5 ГБ)
                                                    # large-v3 (~2.9 ГБ) — точнее

ПРИМЕР РАБОТЫ:
  Положил voice_candidates/Hassar/abc.mp3 -> запустил тул ->
  refs/raw/Hassar.wav(+txt) + refs/voices/Hassar.wav готовы,
  в консоли напечатан фрагмент для config/voices.yaml.
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
RAW_DIR = os.path.join(ROOT, 'refs', 'raw')      # нарезка + txt (грязные)
VOICES_DIR = os.path.join(ROOT, 'refs', 'voices')  # рабочие (вылеченные)

TARGET_LEN = 10.0   # сколько секунд рефа оставляем для CosyVoice
SR_RATE = 24000     # частота дискретизации рефа (такая же у CV3)


def find_candidates():
    """Возвращает {имя_голоса: путь_к_mp3} для всех папок-кандидатов.

    Файлы не-MP3 (например cast.md) игнорируются.
    """
    found = {}
    if not os.path.isdir(CANDIDATES_DIR):
        return found
    for name in sorted(os.listdir(CANDIDATES_DIR)):
        folder = os.path.join(CANDIDATES_DIR, name)
        if not os.path.isdir(folder):
            continue  # cast.md и прочие файлы пропускаем
        mp3s = sorted(f for f in os.listdir(folder)
                      if f.lower().endswith('.mp3'))
        if mp3s:
            found[name] = os.path.join(folder, mp3s[0])
    return found


def cut_ref(name, mp3_path):
    """Шаг 2: первые 10с кандидата -> refs/raw/{name}.wav (24 kHz mono)."""
    dst = os.path.join(RAW_DIR, name + '.wav')
    if os.path.exists(dst):
        return dst, False  # уже есть — не трогаем
    os.makedirs(RAW_DIR, exist_ok=True)
    # длительность исходника (вдруг он короче 10с)
    dur = float(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=duration',
         '-of', 'csv=p=0', mp3_path]).decode().strip().splitlines()[0])
    cut_end = min(TARGET_LEN, dur)
    subprocess.run(['ffmpeg', '-y', '-ss', '0', '-to', '{:.3f}'.format(cut_end),
                    '-i', mp3_path, '-ac', '1', '-ar', str(SR_RATE), dst],
                   check=True, capture_output=True)
    return dst, True


def transcribe(name, ref_wav, model):
    """Шаг 3: whisper-транскрипт нарезки -> refs/raw/{name}.txt."""
    dst_txt = os.path.join(RAW_DIR, name + '.txt')
    if os.path.exists(dst_txt):
        return dst_txt, False  # уже есть — не трогаем
    r = model.transcribe(ref_wav, language='ru', fp16=False,
                         word_timestamps=True)
    txt = r.get('text', '').strip()
    with open(dst_txt, 'w', encoding='utf-8') as fh:
        fh.write(txt + '\n')
    return dst_txt, True


def yaml_snippet(name, who_map):
    """Шаг 5: печатаем фрагмент для config/voices.yaml.

    who_map: {имя_персонажа: [список who-идентификаторов из script.rpy]}
    Берётся из catalog/voices.json (characters), чтобы не искать вручную.
    """
    print('  --- добавь в config/voices.yaml: ---')
    print('  {}:'.format(name))
    print('    ref: refs/voices/{}.wav'.format(name))
    print('    gender: ???   # заполни: M / F')
    if name in who_map:
        print('    who: {}'.format(', '.join(sorted(who_map[name]))))
    print('  ----------------------------------')


def load_who_map():
    """Из catalog/voices.json достаём {имя: [who]} (например Sarah: [s])."""
    import json
    path = os.path.join(ROOT, 'catalog', 'voices.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    chars = data.get('characters', {})   # {who: имя} из define в script.rpy
    who_map = {}
    for who, name in chars.items():
        who_map.setdefault(name, []).append(who)
    return who_map


def main():
    ap = argparse.ArgumentParser(description='Добавление голоса-кандидата')
    ap.add_argument('--only', default=None,
                    help='обработать только этот голос (имя папки)')
    ap.add_argument('--whisper', default='large-v3',
                    help='модель whisper: large-v3 / small / base (default large-v3)')
    ap.add_argument('--no-transcribe', action='store_true',
                    help='пропустить шаг 3 (txt не нужен для cross_lingual)')
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
    print('Кандидатов: {}'.format(len(candidates)))

    # Модель whisper грузим ОДИН раз на весь прогон (файл ~2.9 ГБ —
    # качать и держать в памяти единожды, а не на каждого кандидата)
    model = None
    if not args.no_transcribe:
        import whisper
        print('Загрузка модели whisper: {} ...'.format(args.whisper))
        model = whisper.load_model(args.whisper)

    for name, mp3 in sorted(candidates.items()):
        print('\n=== {} ==='.format(name))
        raw_wav, made = cut_ref(name, mp3)
        print('  [2/5] refs/raw {:<33s} {}'.format(
            name + '.wav', 'НОВЫЙ' if made else 'уже был'))
        if not args.no_transcribe:
            _, made = transcribe(name, raw_wav, model)
            print('  [3/5] refs/raw {:<33s} {}'.format(
                name + '.txt', 'НОВЫЙ' if made else 'уже был'))
        else:
            print('  [3/5] транскрипт ПРОПУЩЕН (--no-transcribe)')

        # Шаг 4: вылеченная копия (денойз + EQ + loudnorm) — voices.yaml ссылается на неё
        clean_dst = os.path.join(VOICES_DIR, name + '.wav')
        made = clean_file(raw_wav, clean_dst)
        print('  [4/5] refs/voices {:<30s} {}'.format(
            name + '.wav', 'НОВЫЙ' if made else 'уже был'))
        yaml_snippet(name, who_map)

    print('\nГотово. Осталось вписать фрагменты в config/voices.yaml,')
    print('потом: tools/voice_status.py (обновить отчёт-заглушки).')


if __name__ == '__main__':
    sys.exit(main())
