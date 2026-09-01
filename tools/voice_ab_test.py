#!/usr/bin/env python3
"""A/B-тестирование голосов: генерирует N кандидатов → compare-папка рядом.

Использование:
  python tools/voice_ab_test.py --name Sarah --refs Sarah_1 Sarah_3 --limit 5
  python tools/voice_ab_test.py --name Sarah --refs Sarah_1 Sarah_3 --limit 5 --force

Результат: output/voice/compare_{name}/
  {uid}__Sarah_1.wav
  {uid}__Sarah_3.wav
  ...

Постфики: __[speaker]_[v] — для удобного сравнения в файловом менеджере.
"""

import argparse
import os
import shutil
import subprocess
import sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, 'config', 'voices.yaml')
READY = os.path.join(ROOT, 'refs', 'raw')
COMPARE = os.path.join(ROOT, 'output', 'voice')
BATCH = os.path.join(ROOT, 'tools', 'voice_batch.py')
PYTHON = sys.executable  # текущий интерпретатор


def load_cfg():
    with open(CFG, encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_cfg(c):
    with open(CFG, 'w', encoding='utf-8', newline='\n') as f:
        yaml.dump(c, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def run_batch(name, limit, force):
    """Запускает voice_batch.py для одного голоса."""
    cmd = [PYTHON, BATCH, '--char', name, '--limit', str(limit)]
    if force:
        cmd.append('--force')
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        print(f"  ✗ voice_batch ошибка:\n{result.stderr[-500:]}")
        return False
    return True


def collect_files(name, variants, force=False):
    """Собирает сгенерированные файлы в compare-папку с постфиксами."""
    # Определяем арку (берём из первого попавшегося файла)
    ai_voice = os.path.join(ROOT, 'ai_voice', 'ru')
    arcs = [d for d in os.listdir(ai_voice) if os.path.isdir(os.path.join(ai_voice, d))]
    
    compare_dir = os.path.join(COMPARE, f'compare_{name.lower()}')
    os.makedirs(compare_dir, exist_ok=True)
    
    count = 0
    for arc in arcs:
        arc_dir = os.path.join(ai_voice, arc)
        for f in os.listdir(arc_dir):
            if not f.endswith('.wav'):
                continue
            uid = f[:-4]  # убираем .wav
            for variant in variants:
                # Ищем файл, сгенерированный этим вариантом
                # voice_batch пишет в ai_voice/ru/{arc}/{uid}.wav
                # но нам нужно понять, какой вариант сейчас активен
                pass
    
    return compare_dir, count


def main():
    ap = argparse.ArgumentParser(
        description='A/B-тестирование голосов: сравнение кандидатов')
    ap.add_argument('--name', required=True,
                    help='Имя голоса (Sarah, Narrator, ...)')
    ap.add_argument('--refs', nargs='+', required=True,
                    help='Список вариантов для сравнения (Sarah_1 Sarah_3 ...)')
    ap.add_argument('--limit', type=int, default=5,
                    help='Сколько реплик генерировать на вариант (default: 5)')
    ap.add_argument('--force', action='store_true',
                    help='Перезаписать существующие файлы')
    args = ap.parse_args()

    name = args.name
    variants = args.refs
    compare_dir = os.path.join(COMPARE, f'compare_{name.lower()}')
    os.makedirs(compare_dir, exist_ok=True)

    print(f"A/B-тест: {name}")
    print(f"  Варианты: {', '.join(variants)}")
    print(f"  Лимит: {args.limit} реплик/вариант")
    print(f"  Папка: {compare_dir}")
    print()

    # Проверяем existence рефов
    for v in variants:
        ref_path = os.path.join(READY, f'{name}_{v}.wav')
        if not os.path.isfile(ref_path):
            print(f"  ✗ Реф не найден: refs/{name}_{v}.wav")
            print(f"    Сначала собери реф: python tools/add_candidate.py --only {name}")
            return 1

    # Читаем конфиг
    cfg = load_cfg()
    voices = cfg.get('voices', {})
    if name not in voices:
        print(f"  ✗ '{name}' нет в voices.yaml")
        return 1

    original_ref = voices[name].get('ref', '')
    print(f"  Оригинальный реф: {original_ref}")

    # Запоминаем текущие файлы в ai_voice
    ai_voice = os.path.join(ROOT, 'ai_voice', 'ru')
    before_files = set()
    for arc in os.listdir(ai_voice):
        arc_dir = os.path.join(ai_voice, arc)
        if os.path.isdir(arc_dir):
            for f in os.listdir(arc_dir):
                if f.endswith('.wav'):
                    before_files.add(os.path.join(arc, f))

    # Генерируем каждый вариант
    for i, variant in enumerate(variants, 1):
        ref_path = os.path.join(READY, f'{name}_{variant}.wav')
        print(f"\n[{i}/{len(variants)}] Генерация: {variant}")
        print(f"  Реф: refs/{name}_{variant}.wav")

        # Переключаем конфиг
        voices[name]['ref'] = f'refs/{name}_{variant}.wav'
        save_cfg(cfg)

        # Запускаем генерацию
        ok = run_batch(name, args.limit, args.force)
        if not ok:
            print(f"  ✗ Пропускаем {variant}")
            continue

        # Собираем новые файлы
        after_files = set()
        for arc in os.listdir(ai_voice):
            arc_dir = os.path.join(ai_voice, arc)
            if os.path.isdir(arc_dir):
                for f in os.listdir(arc_dir):
                    if f.endswith('.wav'):
                        after_files.add(os.path.join(arc, f))

        new_files = after_files - before_files
        # Также включаем файлы, которые были перезаписаны (--force)
        if args.force:
            new_files = after_files  # все файлы — потенциальные кандидаты

        for arc_file in sorted(new_files):
            uid = arc_file[:-4]  # убираем .wav
            src = os.path.join(ai_voice, arc_file)
            dst = os.path.join(compare_dir, f'{uid}__{variant}.wav')
            shutil.copy2(src, dst)

        count = len(new_files) if new_files else len([f for f in after_files if any(v in f for v in variants)])
        print(f"  ✓ Скопировано в compare: {count} файлов")

        # Обновляем "до" для следующего варианта
        before_files = after_files

    # Восстанавливаем оригинальный реф
    voices[name]['ref'] = original_ref
    save_cfg(cfg)
    print(f"\n  Оригинальный реф восстановлён: {original_ref}")

    # Итог
    compare_files = [f for f in os.listdir(compare_dir) if f.endswith('.wav')]
    print(f"\n{'='*50}")
    print(f"Готово! Сравнивай: {compare_dir}")
    print(f"  Файлов: {len(compare_files)}")
    print(f"  Формат: {{uid}}__{{variant}}.wav")
    print()
    print("  Примеры:")
    for f in sorted(compare_files)[:6]:
        print(f"    {f}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
