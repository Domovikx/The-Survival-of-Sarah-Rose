#!/usr/bin/env python3
"""Быстрое управление голосами: list, status, select, compare."""

import argparse
import os
import shutil
import subprocess
import sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READY = os.path.join(ROOT, 'refs')
CANDS = os.path.join(ROOT, 'voice_candidates')
CFG = os.path.join(ROOT, 'config', 'voices.yaml')
AB_TEST = os.path.join(ROOT, 'tools', 'voice_ab_test.py')
PYTHON = sys.executable


def load_cfg():
    with open(CFG, encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_cfg(c):
    with open(CFG, 'w', encoding='utf-8', newline='\n') as f:
        yaml.dump(c, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def cmd_list(_):
    cfg = load_cfg()
    ready = set(os.listdir(READY)) if os.path.isdir(READY) else set()
    for name, v in cfg.get('voices', {}).items():
        d = os.path.join(CANDS, name)
        cands = sorted(f[:-4] for f in os.listdir(d) if f.endswith('.mp3')) if os.path.isdir(d) else []
        ref_path = v.get('ref', '')
        ref_file = os.path.basename(ref_path)
        has_active = ref_file in ready
        variants = sorted(f[:-4] for f in ready if f.startswith(f"{name}_") and f.endswith('.wav'))
        print(f"{'[OK]' if has_active else '[--]'} {name}")
        print(f"  ref: {ref_path}")
        if variants:
            print(f"  variants: {', '.join(variants)}")
        if cands:
            print(f"  candidates: {', '.join(cands)}")


def cmd_select(args):
    cfg = load_cfg()
    voices = cfg.get('voices', {})
    if args.name not in voices:
        print(f"✗ '{args.name}' нет в voices.yaml")
        return 1

    variant = f"{args.name}_{args.variant}"
    src = os.path.join(READY, f"{variant}.wav")
    if not os.path.isfile(src):
        print(f"✗ refs/{variant}.wav не найден")
        return 1

    dst = os.path.join(READY, f"{args.name}.wav")
    shutil.copy2(src, dst)
    voices[args.name]['ref'] = f"refs/{args.name}.wav"
    save_cfg(cfg)
    print(f"✓ {variant}.wav → {args.name}.wav")
    return 0


def cmd_compare(args):
    cfg = load_cfg()
    voices = cfg.get('voices', {})
    if args.name not in voices:
        print(f"✗ '{args.name}' нет в voices.yaml")
        return 1

    # Ищем доступные варианты в refs/
    variants = []
    for f in sorted(os.listdir(READY)):
        if f.startswith(f"{args.name}_") and f.endswith('.wav'):
            variant = f[len(args.name)+1:-4]  # убираем {name}_ и .wav
            variants.append(variant)

    if not variants:
        print(f"✗ Нет вариантов для {args.name} в refs/")
        print(f"  Добавь рефы: refs/{args.name}_1.wav, refs/{args.name}_2.wav")
        return 1

    # Фильтруем по --refs если указаны
    if args.refs:
        variants = [v for v in variants if v in args.refs]
        if not variants:
            print(f"✗ Указанные варианты не найдены: {args.refs}")
            return 1

    print(f"Сравнение: {args.name}")
    print(f"  Варианты: {', '.join(variants)}")
    print(f"  Лимит: {args.limit} реплик/вариант")
    print()

    # Запускаем voice_ab_test.py
    cmd = [PYTHON, AB_TEST, '--name', args.name, '--refs'] + variants + ['--limit', str(args.limit)]
    if args.force:
        cmd.append('--force')

    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def cmd_status(_):
    cfg = load_cfg()
    ready = set(os.listdir(READY)) if os.path.isdir(READY) else set()
    print("Статус озвучки:")
    for name, v in cfg.get('voices', {}).items():
        ref_path = v.get('ref', '')
        ref_file = os.path.basename(ref_path)
        has = ref_file in ready
        print(f"  {'[OK]' if has else '[--]'} {name}")


def main():
    p = argparse.ArgumentParser(description='Управление голосами')
    s = p.add_subparsers(dest='cmd')

    s.add_parser('list', help='Показать все голоса и варианты')
    s.add_parser('status', help='Статус активных рефов')

    sel = s.add_parser('select', help='Выбрать активный вариант')
    sel.add_argument('name', help='Имя голоса (Sarah)')
    sel.add_argument('variant', help='Номер варианта (1, 3, ...)')

    cmp = s.add_parser('compare', help='Сравнить варианты (A/B-тест)')
    cmp.add_argument('name', help='Имя голоса')
    cmp.add_argument('--refs', nargs='*', help='Какие варианты сравнивать (все по умолчанию)')
    cmp.add_argument('--limit', type=int, default=5, help='Реплик на вариант (5)')
    cmp.add_argument('--force', action='store_true', help='Перезаписать существующие')

    args = p.parse_args()
    if args.cmd == 'list':
        return cmd_list(args)
    elif args.cmd == 'select':
        return cmd_select(args)
    elif args.cmd == 'compare':
        return cmd_compare(args)
    elif args.cmd == 'status':
        return cmd_status(args)
    else:
        p.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
