#!/usr/bin/env python
"""Генерит catalog/who_variant.json — рантайм-мапу «кто -> активный вариант».

Мапа позволяет игре искать СНАЧАЛА файл активного варианта из voices.yaml
({uid}__{variant}.wav), потом фолбэчиться на любой {uid}*.wav.
Переключил ref в voices.yaml -> перегенерил мапу -> в игре зазвучал новый
вариант (без удаления старых файлов).

ВХОД:
  config/voices.yaml          голоса, ref-пути, who-списки
  catalog/voices.json         characters: who -> имя отображения

ВЫХОД:
  catalog/who_variant.json    {"names": {display_name: variant}, "narrator": variant}

Запуск: python tools/voice_runtime_map.py
Вызывается автоматически: voice_manage.py select (после смены рефа).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voicekit import catalog, paths  # noqa: E402


def main():
    if not os.path.exists(paths.VOICES_YAML):
        print('нет config/voices.yaml')
        return 1

    voices = catalog.load_voices()
    characters = {}
    if os.path.exists(paths.VOICES_JSON):
        characters = catalog.load_catalog().get('characters', {})

    names = {}
    narrator = ''
    for vname, vcfg in voices.items():
        ref = vcfg.get('ref') or ''
        variant = os.path.splitext(os.path.basename(ref))[0] if ref else vname
        names.setdefault(vname, variant)
        for w in vcfg.get('who', []) or []:
            if w == 'narrator':
                narrator = variant
                continue
            disp = characters.get(w)
            if disp:
                names.setdefault(disp, variant)

    out = {'names': names, 'narrator': narrator}
    os.makedirs(os.path.dirname(paths.WHO_VARIANT_JSON), exist_ok=True)
    with open(paths.WHO_VARIANT_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)

    print('who_variant.json: {} персонажей, narrator={}'.format(
        len(names), narrator or '—'))
    return 0


if __name__ == '__main__':
    sys.exit(main())