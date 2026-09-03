"""Загрузка каталога реплик, конфига голосов и каста персонажей."""

import json
import os

import yaml

from . import paths


def load_catalog():
    """catalog/voices.json -> dict (entries, characters, totals, ...)."""
    with open(paths.VOICES_JSON, encoding='utf-8') as f:
        return json.load(f)


def load_voices():
    """config/voices.yaml -> {имя_голоса: {ref, who, gender, ...}}."""
    with open(paths.VOICES_YAML, encoding='utf-8') as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get('voices', {}) or {}


def save_voices(voices):
    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    with open(paths.VOICES_YAML, 'w', encoding='utf-8', newline='\n') as f:
        yaml.dump({'voices': voices}, f, allow_unicode=True,
                  default_flow_style=False, sort_keys=False)


def who_to_voice(voices=None):
    """who-код -> имя голоса (из who-списков voices.yaml)."""
    if voices is None:
        voices = load_voices()
    m = {}
    for vname, vcfg in voices.items():
        for w in vcfg.get('who', []) or []:
            m[w] = vname
    return m


def load_cast(name):
    """voice_candidates/{Name}/{Name}.yaml -> dict (или None)."""
    p = paths.char_yaml(name)
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_cast(name, data):
    os.makedirs(paths.char_dir(name), exist_ok=True)
    with open(paths.char_yaml(name), 'w', encoding='utf-8', newline='\n') as f:
        yaml.dump(data, f, allow_unicode=True,
                  default_flow_style=False, sort_keys=False)


def cast_names():
    """Имена персонажей, у которых есть контракт {Name}.yaml."""
    if not os.path.isdir(paths.VOICE_CANDIDATES):
        return []
    out = []
    for name in sorted(os.listdir(paths.VOICE_CANDIDATES)):
        d = os.path.join(paths.VOICE_CANDIDATES, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, name + '.yaml')):
            out.append(name)
    return out


def characters_by_category(categories=('dialogue', 'narration')):
    """{имя_персонажа: {dialogue: n, narration: n, arcs: set}} из каталога."""
    from collections import defaultdict
    data = load_catalog()
    lines = defaultdict(lambda: defaultdict(int))
    arcs = defaultdict(set)
    for e in data['entries']:
        if e['category'] not in categories:
            continue
        if e['category'] == 'narration':
            name = 'Narrator'
        else:
            name = e['who_name'] or e['who'] or '(unknown)'
        lines[name][e['category']] += 1
        arcs[name].add(e['arc'])
    return lines, arcs