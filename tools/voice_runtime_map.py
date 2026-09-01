#!/usr/bin/env python
"""Генерит catalog/who_variant.json — рантайм-мапу «кто -> активный вариант».

Зачем: game/voice_config.rpy при резолве знает только кто говорит
(_last_say_who) и текст. Мапа позволяет игре искать СНАЧАЛА файл активного
варианта из voices.yaml ({uid}__{variant}.wav), а потом фолбэчиться на
любой {uid}*.wav. Переключил ref в voices.yaml -> перегенерил мапу ->
в игре зазвучал новый вариант (без удаления старых файлов).

ВХОД:
  config/voices.yaml          голоса, ref-пути, who-списки
  catalog/voices.json         characters: who -> имя отображения

ВЫХОД:
  catalog/who_variant.json
    {"names": {display_name: variant}, "narrator": variant}

Запуск:
  python tools/voice_runtime_map.py
Вызывается автоматически: voice_manage.py select (после смены рефа).
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, 'config', 'voices.yaml')
CATALOG = os.path.join(ROOT, 'catalog', 'voices.json')
OUT = os.path.join(ROOT, 'catalog', 'who_variant.json')


def main():
    if not os.path.exists(CFG):
        print('нет config/voices.yaml')
        return 1

    try:
        import yaml
    except ImportError:
        print('нет pyyaml (pip install pyyaml)')
        return 1

    with open(CFG, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    characters = {}
    if os.path.exists(CATALOG):
        with open(CATALOG, encoding='utf-8') as f:
            characters = json.load(f).get('characters', {})

    names = {}
    narrator = ''
    for vname, vcfg in cfg.get('voices', {}).items():
        ref = vcfg.get('ref') or ''
        variant = os.path.splitext(os.path.basename(ref))[0] if ref else vname
        names.setdefault(vname, variant)  # имя голоса == имя персонажа
        for w in vcfg.get('who', []) or []:
            if w == 'narrator':
                narrator = variant
                continue
            disp = characters.get(w)
            if disp:
                names.setdefault(disp, variant)

    out = {'names': names, 'narrator': narrator}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)

    print('who_variant.json: {} персонажей, narrator={}'.format(
        len(names), narrator or '—'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
