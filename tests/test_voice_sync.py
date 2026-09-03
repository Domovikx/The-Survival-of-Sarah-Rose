"""Тесты voice_sync: классификация mp3, ref-план миграции, update."""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import yaml  # noqa: E402

from voicekit import paths  # noqa: E402
import voice_sync  # noqa: E402


def test_mp3_classify_basic():
    c = voice_sync.mp3_classify
    assert c('Alaric', 'Alaric.mp3') == ('gen_selected', 'Alaric.mp3')
    assert c('Alaric', '01.mp3') == ('generated', '01.mp3')
    assert c('Alaric', 'qwen_01.mp3') == ('generated', 'qwen_01.mp3')
    assert c('Alaric', 'Alaric_1.mp3') == ('gen_selected', 'Alaric_1.mp3')


def test_mp3_classify_duplicate_name():
    assert voice_sync.mp3_classify(
        'Captain Belmont', 'Captain Captain Belmont.mp3') == \
        ('gen_selected', 'Captain Belmont.mp3')
    assert voice_sync.mp3_classify(
        'Generic Female Mature', 'Generic Female Generic Female Mature.mp3') == \
        ('gen_selected', 'Generic Female Mature.mp3')
    assert voice_sync.mp3_classify(
        'King Orwell Rose', 'King Orwell King Orwell Rose.mp3') == \
        ('gen_selected', 'King Orwell Rose.mp3')
    assert voice_sync.mp3_classify(
        'Shah Mahda', 'Shah Shah Mahda.mp3') == \
        ('gen_selected', 'Shah Mahda.mp3')


def test_mp3_classify_name_prefix_number():
    assert voice_sync.mp3_classify('Duke Antonio', 'Duke 01.mp3') == \
        ('generated', '01.mp3')
    assert voice_sync.mp3_classify('Marshal Edmond', 'Marshal 03.mp3') == \
        ('generated', '03.mp3')


def test_ref_owner():
    assert voice_sync.ref_owner('Carolyn_1') == ('Carolyn', '1')
    assert voice_sync.ref_owner('Gorak_u3') == ('Gorak', 'u3')
    assert voice_sync.ref_owner('Duke Antonio') == ('Duke Antonio', None)
    assert voice_sync.ref_owner('Raza_u5') == ('Raza', 'u5')


def patch_all_paths(monkeypatch, tmp_path):
    """Подменяет ВСЕ пути voicekit на tmp (защита реального проекта)."""
    for attr, val in (
        ('ROOT', tmp_path),
        ('VOICE_CANDIDATES', tmp_path / 'voice_candidates'),
        ('CATALOG_DIR', tmp_path / 'catalog'),
        ('CONFIG_DIR', tmp_path / 'config'),
        ('VOICES_YAML', tmp_path / 'config' / 'voices.yaml'),
        ('VOICES_JSON', tmp_path / 'catalog' / 'voices.json'),
        ('CAST_SUMMARY_YAML', tmp_path / 'voice_candidates'
         / 'voice_candidates.yaml'),
        ('MISSING_VOICES_MD', tmp_path / 'catalog' / 'missing_voices.md'),
        ('SYNC_REPORT_MD', tmp_path / 'catalog' / 'voice_sync_report.md'),
    ):
        monkeypatch.setattr(paths, attr, str(val))


@pytest.fixture
def tmp_layout(tmp_path, monkeypatch):
    """Временная раскладка: refs/ + voice_candidates + voices.yaml."""
    refs = tmp_path / 'refs'
    refs.mkdir()
    for f in ('Alaric.wav', 'Carolyn_1.wav', 'Duke Antonio.wav',
              'Gorak_u3.wav', 'Samayra.wav'):
        (refs / f).write_bytes(b'RIFF')

    vc = tmp_path / 'voice_candidates'
    for name in ('Alaric', 'Carolyn', 'Duke Antonio', 'Gorak', 'Samayra'):
        d = vc / name
        d.mkdir(parents=True)
        (d / (name + '.yaml')).write_text(
            'name: {}\ngender: M\n'.format(name), encoding='utf-8')

    (tmp_path / 'config').mkdir()
    cfg = {'voices': {
        'Alaric': {'ref': 'refs/Alaric.wav', 'who': ['al'], 'gender': 'M'},
        'Carolyn': {'ref': 'refs/Carolyn_1.wav', 'who': ['c'], 'gender': 'F'},
        'Duke Antonio': {'ref': 'refs/Duke Antonio_1.wav', 'who': ['ant'],
                         'gender': 'M'},
        'Samayra': {'ref': 'refs/Carolyn_1.wav', 'who': ['sa'], 'gender': 'F'},
    }}
    with open(tmp_path / 'config' / 'voices.yaml', 'w',
              encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)

    (tmp_path / 'catalog').mkdir()
    with open(tmp_path / 'catalog' / 'voices.json', 'w',
              encoding='utf-8') as f:
        import json
        json.dump({'entries': [], 'characters': {}}, f)

    patch_all_paths(monkeypatch, tmp_path)
    return tmp_path


def test_migrate_plan_refs(tmp_layout):
    plan = voice_sync.migrate_plan()
    by_dst = {}
    for action, src, dst in plan['moves']:
        by_dst.setdefault(os.path.basename(dst), []).append((action, src))

    assert ('move', os.path.join(str(tmp_layout), 'refs', 'Alaric.wav')) in \
        by_dst['Alaric.wav']
    assert str(by_dst['Alaric.wav'][0][1]).endswith('refs\\Alaric.wav')

    carolyn = [x for x in plan['moves']
               if 'Carolyn' in x[2] and x[0] == 'copy']
    assert len(carolyn) == 1
    assert os.path.normpath(carolyn[0][2]).endswith(os.path.normpath('Carolyn/ref/Carolyn.wav'))

    prog = [x for x in plan['moves']
            if x[0] == 'move' and x[2].endswith('Carolyn_1.wav')]
    assert len(prog) == 1
    assert 'in_progress' in prog[0][2]

    gorak = [x for x in plan['moves'] if 'Gorak_u3' in x[2]]
    assert len(gorak) == 1 and 'in_progress' in gorak[0][2]

    voices_new = plan['voices']
    assert voices_new['Alaric']['ref'] == \
        'voice_candidates/Alaric/ref/Alaric.wav'
    assert voices_new['Carolyn']['ref'] == \
        'voice_candidates/Carolyn/ref/Carolyn.wav'
    assert voices_new['Duke Antonio']['ref'] == \
        'voice_candidates/Duke Antonio/ref/Duke Antonio.wav'
    assert voices_new['Samayra']['ref'] == \
        'voice_candidates/Carolyn/ref/Carolyn.wav'
    assert ('Duke Antonio', 'Duke Antonio_1') in plan['fixed_refs']
    assert ('Samayra', 'Carolyn') in plan['notes']['foreign']


def test_migrate_apply_moves_files(tmp_layout):
    import shutil
    voice_sync.cmd_migrate(type('A', (), {'apply': True})())
    assert (tmp_layout / 'refs').exists() is False or \
        not list((tmp_layout / 'refs').glob('*.wav'))
    assert (tmp_layout / 'voice_candidates' / 'Alaric' / 'ref'
            / 'Alaric.wav').exists()
    assert (tmp_layout / 'voice_candidates' / 'Carolyn' / 'ref'
            / 'Carolyn.wav').exists()
    assert (tmp_layout / 'voice_candidates' / 'Carolyn' / 'in_progress'
            / 'Carolyn_1.wav').exists()
    assert (tmp_layout / 'voice_candidates' / 'Gorak' / 'in_progress'
            / 'Gorak_u3.wav').exists()
    with open(tmp_layout / 'config' / 'voices.yaml', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    assert cfg['voices']['Carolyn']['ref'] == \
        'voice_candidates/Carolyn/ref/Carolyn.wav'
    assert cfg['voices']['Duke Antonio']['ref'] == \
        'voice_candidates/Duke Antonio/ref/Duke Antonio.wav'


def test_migrate_apply_restores_variant_fix(tmp_layout, monkeypatch):
    """Повторный migrate (refs пуст) восстанавливает фиксацию варианта."""
    voice_sync.cmd_migrate(type('A', (), {'apply': True})())
    ref_wav = (tmp_layout / 'voice_candidates' / 'Carolyn' / 'ref'
               / 'Carolyn.wav')
    ref_wav.unlink()
    voice_sync.cmd_migrate(type('A', (), {'apply': True})())
    assert ref_wav.exists()


def test_update_creates_structure(tmp_path, monkeypatch):
    patch_all_paths(monkeypatch, tmp_path)
    vc = paths.VOICE_CANDIDATES
    os.makedirs(vc, exist_ok=True)
    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    os.makedirs(paths.CATALOG_DIR, exist_ok=True)
    import json
    with open(paths.VOICES_JSON, 'w', encoding='utf-8') as f:
        json.dump({'entries': [], 'characters': {'zz': 'Zed'}}, f)
    with open(paths.VOICES_YAML, 'w', encoding='utf-8') as f:
        yaml.dump({'voices': {}}, f)

    voice_sync.cmd_update(type('A', (), {'apply': True})())
    d = os.path.join(vc, 'Zed')
    assert os.path.isdir(d)
    assert all(os.path.isdir(os.path.join(d, sub))
               for sub in paths.CHAR_SUBDIRS)
    assert os.path.exists(os.path.join(d, 'Zed.yaml'))
    cast = voice_sync.catalog.load_cast('Zed')
    assert cast['name'] == 'Zed'
    assert cast['texts'] == []