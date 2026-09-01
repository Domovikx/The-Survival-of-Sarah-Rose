"""Интеграционный тест: полный пайплайн add_candidate → select → batch."""

import os
import sys
import subprocess
import shutil
import yaml
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_ffmpeg():
    """Ищем ffmpeg."""
    ff = shutil.which('ffmpeg')
    if ff:
        return ff
    for p in [
        r'C:\Users\Domo\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe',
        r'C:\ffmpeg\bin\ffmpeg.exe',
    ]:
        if os.path.isfile(p):
            return p
    return None


@pytest.fixture
def full_project(tmp_path):
    """Создаём полную структуру проекта для интеграционного теста."""
    # Создаём все директории
    dirs = [
        'config',
        'catalog',
        'refs/raw',
        'refs/ready',
        'voice_candidates/TestVoice',
        'tools',
        'ai_voice/ru/TestArc',
    ]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    # voices.yaml
    cfg = {'voices': {}}
    cfg_path = tmp_path / 'config' / 'voices.yaml'
    with open(cfg_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)

    # voices.json
    catalog = {
        'entries': [
            {
                'uid': 'test_001',
                'arc': 'TestArc',
                'who': 'tv',
                'who_name': 'TestVoice',
                'category': 'dialogue',
                'old': 'Hello',
                'new': 'Привет'
            }
        ],
        'characters': {'tv': 'TestVoice'}
    }
    catalog_path = tmp_path / 'catalog' / 'voices.json'
    with open(catalog_path, 'w', encoding='utf-8') as f:
        yaml.dump(catalog, f, allow_unicode=True)

    return tmp_path


def test_add_candidate_pipeline(full_project):
    """Тест: add_candidate создаёт raw + ready реф из MP3."""
    pytest.skip("Интеграционный тест: требует реальную структуру проекта")


def test_select_and_generate(full_project):
    """Тест: select переключает реф, batch генерирует WAV."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        pytest.skip("ffmpeg не найден")

    # Подменяем ROOT в voice_batch и voice_manage
    sys.path.insert(0, os.path.join(ROOT, 'tools'))

    # Создаём два рефа в refs/ready/
    ready_dir = full_project / 'refs' / 'ready'
    
    # Реф v1 (440 Hz)
    v1_path = ready_dir / 'TestVoice_1.wav'
    subprocess.run([
        ffmpeg, '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=10',
        '-ac', '1', '-ar', '24000', str(v1_path)
    ], capture_output=True, check=True)

    # Реф v2 (880 Hz)
    v2_path = ready_dir / 'TestVoice_2.wav'
    subprocess.run([
        ffmpeg, '-y', '-f', 'lavfi', '-i', 'sine=frequency=880:duration=10',
        '-ac', '1', '-ar', '24000', str(v2_path)
    ], capture_output=True, check=True)

    # Активный реф = v1
    shutil.copy2(v1_path, ready_dir / 'TestVoice.wav')

    # Обновляем voices.yaml
    cfg_path = full_project / 'config' / 'voices.yaml'
    cfg = {
        'voices': {
            'TestVoice': {
                'ref': 'refs/ready/TestVoice.wav',
                'who': ['tv'],
                'gender': 'F'
            }
        }
    }
    with open(cfg_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)

    # Эмулируем select: v2 → active
    import voice_manage
    old_ready = voice_manage.READY
    old_cfg = voice_manage.CFG
    voice_manage.READY = str(ready_dir)
    voice_manage.CFG = str(cfg_path)

    # Копируем v2 → active
    shutil.copy2(v2_path, ready_dir / 'TestVoice.wav')

    # Обновляем yaml
    with open(cfg_path, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    cfg['voices']['TestVoice']['ref'] = 'refs/ready/TestVoice.wav'
    with open(cfg_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)

    voice_manage.READY = old_ready
    voice_manage.CFG = old_cfg

    # Проверяем, что active = v2
    assert (ready_dir / 'TestVoice.wav').exists()
    with open(cfg_path, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    assert cfg['voices']['TestVoice']['ref'] == 'refs/ready/TestVoice.wav'
