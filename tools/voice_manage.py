#!/usr/bin/env python3
"""Быстрое управление голосами: list, status, select.

A/B-сравнение: voice_batch.py --ref voice_candidates/{Name}/{Name}_v.wav
генерит {uid}__{Name}_v.wav в ai_voice/ — слушаешь варианты рядом,
победителя фиксируешь через `select` ({Name}_v.wav -> {Name}.wav).
"""

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voicekit import catalog, paths  # noqa: E402


def regen_runtime_map():
    """Перегенерирует catalog/who_variant.json (кто -> активный вариант)."""
    try:
        tool = os.path.join(paths.TOOLS_DIR, 'voice_runtime_map.py')
        r = subprocess.run([sys.executable, tool], cwd=paths.ROOT,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print('  ! мапа НЕ обновлена: {}'.format(r.stderr.strip()[-200:]))
            return False
        return True
    except Exception:
        return False


def cmd_list(_):
    voices = catalog.load_voices()
    for name, v in voices.items():
        ref_path = v.get('ref', '')
        has_active = os.path.exists(paths.resolve_ref(ref_path))
        cdir = paths.char_dir(name)
        variants = sorted(
            f[:-4] for f in os.listdir(cdir)
            if f.endswith('.wav') and f.startswith(name + '_'))             if os.path.isdir(cdir) else []
        gen_sel = paths.char_subdir(name, 'gen_selected')
        cands = sorted(
            f[:-4] for f in os.listdir(gen_sel)
            if f.endswith('.mp3')) if os.path.isdir(gen_sel) else []
        print('{} {}'.format('[OK]' if has_active else '[--]', name))
        print('  ref: {}'.format(ref_path))
        if variants:
            print('  варианты: {}'.format(', '.join(variants)))
        if cands:
            print('  gen_selected: {}'.format(', '.join(cands)))


def cmd_select(args):
    voices = catalog.load_voices()
    if args.name not in voices:
        print('✗ {!r} нет в voices.yaml'.format(args.name))
        return 1

    variant = args.name if not args.variant else '{}_{}'.format(args.name, args.variant)
    src = os.path.join(paths.char_dir(args.name), variant + '.wav')
    if not os.path.isfile(src):
        print('✗ нет {}/{}.wav в корне каста'.format(args.name, variant))
        return 1

    dst = paths.ref_active(args.name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    voices[args.name]['ref'] = paths.ref_voices(args.name)
    catalog.save_voices(voices)
    print('✓ {} → {}'.format(
        os.path.relpath(src, paths.ROOT),
        os.path.relpath(dst, paths.ROOT)))
    if regen_runtime_map():
        print('  ✓ who_variant.json обновлена — в игре зазвучит этот вариант')
    return 0


def cmd_status(_):
    voices = catalog.load_voices()
    print('Статус озвучки:')
    for name, v in voices.items():
        has = os.path.exists(paths.resolve_ref(v.get('ref', '')))
        print('  {} {}'.format('[OK]' if has else '[--]', name))


def main():
    p = argparse.ArgumentParser(description='Управление голосами')
    s = p.add_subparsers(dest='cmd')

    s.add_parser('list', help='Показать все голоса и варианты')
    s.add_parser('status', help='Статус активных рефов')

    sel = s.add_parser('select', help='Выбрать активный вариант')
    sel.add_argument('name', help='Имя голоса (Sarah)')
    sel.add_argument('variant', help='Номер варианта (1, 3, ...)')

    args = p.parse_args()
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    if args.cmd == 'list':
        return cmd_list(args)
    elif args.cmd == 'select':
        return cmd_select(args)
    elif args.cmd == 'status':
        return cmd_status(args)
    else:
        p.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())