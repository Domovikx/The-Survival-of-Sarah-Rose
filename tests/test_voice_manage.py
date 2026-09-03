"""Тесты для tools/voice_manage.py — выбор активного рефа.

Новая структура: select копирует in_progress/{Name}_{v}.wav ->
ref/{Name}.wav и обновляет voices.yaml.
"""

import os
import sys
import shutil
import yaml
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from voicekit import paths  # noqa: E402


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Временная раскладка проекта для тестов."""
    for attr, val in (
        ('ROOT', tmp_path),
        ('VOICE_CANDIDATES', tmp_path / 'voice_candidates'),
        ('CATALOG_DIR', tmp_path / 'catalog'),
        ('CONFIG_DIR', tmp_path / 'config'),
        ('VOICES_YAML', tmp_path / 'config' / 'voices.yaml'),
        ('VOICES_JSON', tmp_path / 'catalog' / 'voices.json'),
        ('WHO_VARIANT_JSON', tmp_path / 'catalog' / 'who_variant.json'),
    ):
        monkeypatch.setattr(paths, attr, str(val))

    (tmp_path / 'config').mkdir()
    (tmp_path / 'catalog').mkdir()
    char_dir = tmp_path / 'voice_candidates' / 'TestVoice'
    ref_dir = char_dir / 'ref'
    prog_dir = char_dir / 'in_progress'
    ref_dir.mkdir(parents=True)
    prog_dir.mkdir()

    cfg = {
        'voices': {
            'TestVoice': {
                'ref': 'voice_candidates/TestVoice/ref/TestVoice.wav',
                'who': ['tv'],
                'gender': 'F'
            }
        }
    }
    with open(tmp_path / 'config' / 'voices.yaml', 'w',
              encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)

    wav_active = ref_dir / 'TestVoice.wav'
    wav_active.write_bytes(b'RIFFactive')

    wav_v1 = prog_dir / 'TestVoice_1.wav'
    wav_v1.write_bytes(b'RIFFvariant1')
    wav_v2 = prog_dir / 'TestVoice_2.wav'
    wav_v2.write_bytes(b'RIFFvariant2')

    import json
    with open(tmp_path / 'catalog' / 'voices.json', 'w',
              encoding='utf-8') as f:
        json.dump({'entries': [], 'characters': {}}, f)
    return tmp_path


def test_load_cfg(tmp_project):
    from voicekit import catalog
    voices = catalog.load_voices()
    assert 'TestVoice' in voices
    assert voices['TestVoice']['ref'] == \
        'voice_candidates/TestVoice/ref/TestVoice.wav'


def test_select_variant(tmp_project, monkeypatch):
    """select 1: копирует in_progress/TestVoice_1.wav -> ref/TestVoice.wav."""
    import voice_manage
    monkeypatch.setattr(voice_manage, 'regen_runtime_map',
                        lambda: True)
    rc = voice_manage.cmd_select(
        type('A', (), {'name': 'TestVoice', 'variant': '1'}))
    assert rc == 0

    from voicekit import catalog
    cfg = catalog.load_voices()
    assert cfg['TestVoice']['ref'] == \
        'voice_candidates/TestVoice/ref/TestVoice.wav'
    dst = paths.ref_active('TestVoice')
    assert os.path.exists(dst)
    assert open(dst, 'rb').read() == b'RIFFvariant1'


def test_select_nonexistent_variant(tmp_project):
    import voice_manage
    rc = voice_manage.cmd_select(
        type('A', (), {'name': 'TestVoice', 'variant': '999'}))
    assert rc == 1


def test_select_unknown_voice(tmp_project):
    import voice_manage
    rc = voice_manage.cmd_select(
        type('A', (), {'name': 'Nobody', 'variant': '1'}))
    assert rc == 1


def test_list_variants(tmp_project, capsys, monkeypatch):
    import voice_manage
    monkeypatch.setattr(voice_manage, 'regen_runtime_map', lambda: True)
    voice_manage.cmd_list(type('A', (), {}))
    captured = capsys.readouterr()
    assert 'TestVoice' in captured.out
    assert 'in_progress: TestVoice_1, TestVoice_2' in captured.out
    assert 'voice_candidates/TestVoice/ref/TestVoice.wav' in captured.out


def test_status(tmp_project, capsys):
    import voice_manage
    voice_manage.cmd_status(type('A', (), {}))
    captured = capsys.readouterr()
    assert '[OK] TestVoice' in captured.out


def test_runtime_map_regen(tmp_project, monkeypatch):
    """regen_runtime_map пишет who_variant.json."""
    import voice_manage
    import voice_runtime_map
    monkeypatch.setattr(voice_manage, 'regen_runtime_map',
                        lambda: voice_runtime_map.main() == 0)
    assert voice_manage.regen_runtime_map()
    import json
    with open(paths.WHO_VARIANT_JSON, encoding='utf-8') as f:
        d = json.load(f)
    assert d['names']['TestVoice'] == 'TestVoice'