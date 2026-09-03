"""Раскладка проекта — ЕДИНСТВЕННОЕ место, где живут пути.

Структура voice_candidates/{Name}/:
  generated/     сырьё от voice_design (01.mp3, 02.mp3, ...)
  gen_selected/  отобранные вручную ({Name}.mp3, {Name}_1.mp3)
  in_progress/   рабочие рефы: чистки, фильтры, A/B-варианты
  ref/           финальный реф {Name}.wav (voices.yaml ссылается сюда)

Правило: скриптам запрещено хардкодить пути — только через этот модуль.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TOOLS_DIR = os.path.join(ROOT, 'tools')
VOICE_CANDIDATES = os.path.join(ROOT, 'voice_candidates')
CATALOG_DIR = os.path.join(ROOT, 'catalog')
CONFIG_DIR = os.path.join(ROOT, 'config')
OUTPUT_DIR = os.path.join(ROOT, 'output')
AI_VOICE_DIR = os.path.join(ROOT, 'ai_voice')

VOICES_YAML = os.path.join(CONFIG_DIR, 'voices.yaml')
VOICES_JSON = os.path.join(CATALOG_DIR, 'voices.json')
LABEL_ARC_JSON = os.path.join(CATALOG_DIR, 'label_arc.json')
WHO_VARIANT_JSON = os.path.join(CATALOG_DIR, 'who_variant.json')
CAST_SUMMARY_YAML = os.path.join(VOICE_CANDIDATES, 'voice_candidates.yaml')
MISSING_VOICES_MD = os.path.join(CATALOG_DIR, 'missing_voices.md')
SYNC_REPORT_MD = os.path.join(CATALOG_DIR, 'voice_sync_report.md')

CHAR_SUBDIRS = ('generated', 'gen_selected', 'in_progress', 'ref')


def char_dir(name):
    return os.path.join(VOICE_CANDIDATES, name)


def char_subdir(name, sub):
    if sub not in CHAR_SUBDIRS:
        raise ValueError('неизвестная подпапка: {!r}'.format(sub))
    return os.path.join(char_dir(name), sub)


def char_yaml(name):
    return os.path.join(char_dir(name), name + '.yaml')


def ref_active(name):
    return os.path.join(char_subdir(name, 'ref'), name + '.wav')


def ref_voices(name):
    return 'voice_candidates/{}/ref/{}.wav'.format(name, name)


def resolve_ref(ref):
    return ref if os.path.isabs(ref) else os.path.join(ROOT, ref)


def batch_log():
    return os.path.join(OUTPUT_DIR, 'voice', 'batch.log')