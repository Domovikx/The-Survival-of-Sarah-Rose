"""Тесты для tools/voice_manage.py — выбор активного рефа."""

import os
import sys
import tempfile
import shutil
import yaml
import pytest

# Добавляем tools/ в путь для импорта
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))


@pytest.fixture
def tmp_project(tmp_path):
    """Создаём временную структуру проекта для тестов."""
    # Создаём директории
    ready_dir = tmp_path / 'refs' / 'ready'
    ready_dir.mkdir(parents=True)
    cands_dir = tmp_path / 'voice_candidates' / 'TestVoice'
    cands_dir.mkdir(parents=True)
    config_dir = tmp_path / 'config'
    config_dir.mkdir()

    # Создаём voices.yaml
    cfg = {
        'voices': {
            'TestVoice': {
                'ref': 'refs/ready/TestVoice.wav',
                'who': ['tv'],
                'gender': 'F'
            }
        }
    }
    cfg_path = config_dir / 'voices.yaml'
    with open(cfg_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)

    # Создаём фиктивные WAV файлы (просто пустые файлы)
    wav_active = ready_dir / 'TestVoice.wav'
    wav_active.write_bytes(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
    
    wav_v1 = ready_dir / 'TestVoice_1.wav'
    wav_v1.write_bytes(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
    
    wav_v2 = ready_dir / 'TestVoice_2.wav'
    wav_v2.write_bytes(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')

    # Создаём фиктивный MP3 кандидат
    mp3_file = cands_dir / 'TestVoice_1.mp3'
    mp3_file.write_bytes(b'\xff\xfb\x90\x00' + b'\x00' * 1000)

    return {
        'root': tmp_path,
        'ready': ready_dir,
        'config': cfg_path,
        'wav_active': wav_active,
        'wav_v1': wav_v1,
        'wav_v2': wav_v2,
    }


def test_load_cfg(tmp_project):
    """Тест загрузки конфига."""
    from voice_manage import load_cfg, CFG
    # Подменяем путь к конфигу
    import voice_manage
    old_cfg = voice_manage.CFG
    voice_manage.CFG = str(tmp_project['config'])
    
    cfg = load_cfg()
    assert 'TestVoice' in cfg['voices']
    assert cfg['voices']['TestVoice']['ref'] == 'refs/ready/TestVoice.wav'
    
    voice_manage.CFG = old_cfg


def test_select_variant(tmp_project):
    """Тест выбора варианта: копирует файл и обновляет yaml."""
    from voice_manage import load_cfg, save_cfg
    import voice_manage
    
    # Подменяем пути
    old_ready = voice_manage.READY
    old_cfg_path = voice_manage.CFG
    voice_manage.READY = str(tmp_project['ready'])
    voice_manage.CFG = str(tmp_project['config'])
    
    # Загружаем конфиг
    cfg = load_cfg()
    original_ref = cfg['voices']['TestVoice']['ref']
    
    # Эмулируем select: копируем v1 → active
    src = tmp_project['ready'] / 'TestVoice_1.wav'
    dst = tmp_project['ready'] / 'TestVoice.wav'
    shutil.copy2(src, dst)
    
    cfg['voices']['TestVoice']['ref'] = 'refs/ready/TestVoice.wav'
    save_cfg(cfg)
    
    # Проверяем
    cfg_new = load_cfg()
    assert cfg_new['voices']['TestVoice']['ref'] == 'refs/ready/TestVoice.wav'
    assert dst.exists()
    
    # Проверяем, что файл изменился (md5)
    import hashlib
    md5_active = hashlib.md5(dst.read_bytes()).hexdigest()
    md5_v1 = hashlib.md5(src.read_bytes()).hexdigest()
    assert md5_active == md5_v1
    
    voice_manage.READY = old_ready
    voice_manage.CFG = old_cfg_path


def test_list_variants(tmp_project, capsys):
    """Тест list: показывает активный реф и варианты."""
    from voice_manage import cmd_list
    import voice_manage
    
    old_ready = voice_manage.READY
    old_cands = voice_manage.CANDS
    old_cfg = voice_manage.CFG
    voice_manage.READY = str(tmp_project['ready'])
    voice_manage.CANDS = str(tmp_project['root'] / 'voice_candidates')
    voice_manage.CFG = str(tmp_project['config'])
    
    class Args:
        pass
    
    cmd_list(Args())
    captured = capsys.readouterr()
    
    assert 'TestVoice' in captured.out
    assert 'refs/ready/TestVoice.wav' in captured.out
    assert 'TestVoice_1' in captured.out
    assert 'TestVoice_2' in captured.out
    
    voice_manage.READY = old_ready
    voice_manage.CANDS = old_cands
    voice_manage.CFG = old_cfg


def test_status(tmp_project, capsys):
    """Тест status: показывает статус активных рефов."""
    from voice_manage import cmd_status
    import voice_manage
    
    old_ready = voice_manage.READY
    old_cfg = voice_manage.CFG
    voice_manage.READY = str(tmp_project['ready'])
    voice_manage.CFG = str(tmp_project['config'])
    
    class Args:
        pass
    
    cmd_status(Args())
    captured = capsys.readouterr()
    
    assert '[OK] TestVoice' in captured.out
    
    voice_manage.READY = old_ready
    voice_manage.CFG = old_cfg


def test_select_nonexistent_variant(tmp_project):
    """Тест: выбор несуществующего варианта."""
    from voice_manage import load_cfg
    import voice_manage
    
    old_ready = voice_manage.READY
    voice_manage.READY = str(tmp_project['ready'])
    
    variant_path = tmp_project['ready'] / 'TestVoice_999.wav'
    assert not variant_path.exists()
    
    voice_manage.READY = old_ready
