#!/usr/bin/env python
"""Отчёт по голосам: у кого есть голос, а кого ещё надо найти.

Склеивает два источника:
  - catalog/voices.json   (каталог реплик: uid, old, new, who, arc, category)
  - config/voices.yaml    (у кого готов реф голоса)

Выход:
  - console: сводка по каждому персонажу (сколько реплик, есть ли голос)
  - catalog/missing_voices.md — «заглушки»: список персонажей БЕЗ голоса,
    отсортированный по числу реплик. Это твой чек-лист «какие голоса найти».

Правило озвучки: персонажа нет в config/voices.yaml -> его реплики
ПРОПУСКАЮТСЯ генератором (тишина в игре, видно в этом отчёте).

Запуск:
  python tools/voice_status.py
"""

import json
import os
from collections import defaultdict

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_catalog():
    """Каталог реплик. Возвращает (entries, characters {who: имя})."""
    with open(os.path.join(ROOT, 'catalog', 'voices.json'), encoding='utf-8') as f:
        data = json.load(f)
    return data['entries'], data.get('characters', {})


def load_voices():
    """Готовые голоса из config/voices.yaml. Возвращает
    {имя_голоса: {ref, who:[...], gender}}."""
    path = os.path.join(ROOT, 'config', 'voices.yaml')
    with open(path, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    return cfg.get('voices', {})


def main():
    entries, characters = load_catalog()
    voices = load_voices()

    # who -> голос (из списков who: в voices.yaml)
    who_to_voice = {}
    for vname, vcfg in voices.items():
        for w in vcfg.get('who', []):
            who_to_voice[w] = vname

    # считаем озвучиваемые реплики (диалог + наррация) по персонажам
    # structure: lines[имя][category] = count
    lines = defaultdict(lambda: defaultdict(int))
    arcs = defaultdict(set)
    for e in entries:
        if e['category'] not in ('dialogue', 'narration'):
            continue  # ui и menu не озвучиваем вообще
        if e['category'] == 'narration':
            name = 'Narrator'
        else:
            name = e['who_name'] or e['who'] or '(unknown)'
        lines[name][e['category']] += 1
        arcs[name].add(e['arc'])

    # готовые голоса (есть в voices.yaml И встречаются в каталоге)
    ready = []
    missing = []
    for name in sorted(lines, key=lambda n: -sum(lines[n].values())):
        total = sum(lines[name].values())
        if total == 0:
            continue
        info = dict(
            name=name,
            dialogue=lines[name]['dialogue'],
            narration=lines[name]['narration'],
            total=total,
            arcs=len(arcs[name]),
            voice=(who_to_voice.get(name, None)
                   or (name if name in voices else None)),
        )
        if name in voices or name in who_to_voice:
            ready.append(info)
        else:
            missing.append(info)

    # console-сводка
    voiced_total = sum(i['total'] for i in ready)
    missing_total = sum(i['total'] for i in missing)
    print('ГОТОВЫЕ ГОЛОСА ({}):'.format(len(ready)))
    for i in ready:
        print('  {:22s} {:6d} реплик ({:5d} диалог / {:5d} нарр.) {:2d} арок'.format(
            i['name'], i['total'], i['dialogue'], i['narration'], i['arcs']))
    print('БЕЗ ГОЛОСА ({} персонажей, {} реплик пропускаем):'.format(
        len(missing), missing_total))
    for i in missing:
        print('  {:22s} {:6d} реплик ({:5d} диалог / {:5d} нарр.) {:2d} арок'.format(
            i['name'], i['total'], i['dialogue'], i['narration'], i['arcs']))

    # catalog/missing_voices.md — чек-лист «какие голоса найти»
    out = os.path.join(ROOT, 'catalog', 'missing_voices.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('# Голоса, которых не хватает (заглушки)\n\n')
        f.write('Правило: персонажа нет в `config/voices.yaml` — его реплики '
                'не озвучиваются.\n')
        f.write('Этот файл генерируется: `python tools/voice_status.py`\n\n')
        f.write('## Готово ({}, {} реплик)\n\n'.format(len(ready), voiced_total))
        f.write('| Голос | Реплик | Диалог | Наррация | Арок |\n')
        f.write('|---|---|---|---|---|\n')
        for i in ready:
            f.write('| {} | {} | {} | {} | {} |\n'.format(
                i['name'], i['total'], i['dialogue'], i['narration'], i['arcs']))
        f.write('\n## Найти ({} персонажей, {} реплик)\n\n'.format(
            len(missing), missing_total))
        f.write('| # | Персонаж | Реплик | Диалог | Наррация | Арок |\n')
        f.write('|---|---|---|---|---|---|\n')
        for n, i in enumerate(missing, 1):
            f.write('| {} | {} | {} | {} | {} | {} |\n'.format(
                n, i['name'], i['total'], i['dialogue'],
                i['narration'], i['arcs']))
    print('\nwrote {}'.format(out))


if __name__ == '__main__':
    main()
