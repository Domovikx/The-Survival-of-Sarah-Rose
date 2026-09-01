"""Тесты для tools/voice_batch.py — разрешение рефов и генерация."""

import os
import sys
import yaml
import pytest
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Мокаем ВСЕ CosyVoice3 импорты ДО импорта voice_batch
cosyvoice_modules = [
    'cosyvoice', 'cosyvoice.cli', 'cosyvoice.cli.cosyvoice',
    'cosyvoice.utils', 'cosyvoice.utils.file_utils', 'cosyvoice.utils.common',
    'hyperpyyaml', 'torch', 'torchaudio', 'numpy',
]
for mod in cosyvoice_modules:
    sys.modules[mod] = MagicMock()

sys.path.insert(0, os.path.join(ROOT, 'tools'))


@pytest.fixture
def mock_config(tmp_path):
    """Создаём мок-конфиг для тестов voice_batch."""
    # Создаём структуру
    ready_dir = tmp_path / 'refs' / 'ready'
    ready_dir.mkdir(parents=True)
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    catalog_dir = tmp_path / 'catalog'
    catalog_dir.mkdir()

    # voices.yaml
    cfg = {
        'voices': {
            'TestVoice': {
                'ref': 'refs/ready/TestVoice.wav',
                'who': ['tv'],
                'gender': 'F'
            },
            'NoRefVoice': {
                'who': ['nr'],
                'gender': 'M'
            }
        }
    }
    cfg_path = config_dir / 'voices.yaml'
    with open(cfg_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)

    # voices.json
    catalog = {
        'entries': [
            {
                'uid': 'test_uid_001',
                'arc': 'TestArc',
                'who': 'tv',
                'who_name': 'TestVoice',
                'category': 'dialogue',
                'old': 'Hello world',
                'new': 'Привет мир'
            },
            {
                'uid': 'test_uid_002',
                'arc': 'TestArc',
                'who': 'nr',
                'who_name': 'NoRefVoice',
                'category': 'dialogue',
                'old': 'Goodbye',
                'new': 'Пока'
            },
            {
                'uid': 'test_uid_003',
                'arc': 'TestArc',
                'who': None,
                'who_name': None,
                'category': 'narration',
                'old': 'Narrator speaks',
                'new': 'Рассказчик говорит'
            }
        ],
        'characters': {
            'tv': 'TestVoice',
            'nr': 'NoRefVoice'
        }
    }
    catalog_path = catalog_dir / 'voices.json'
    import json
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False)

    # Создаём фиктивный WAV
    wav_path = ready_dir / 'TestVoice.wav'
    wav_path.write_bytes(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')

    return {
        'root': tmp_path,
        'config': cfg_path,
        'catalog': catalog_path,
        'ready': ready_dir,
    }


def test_load_inputs(mock_config):
    """Тест: load_inputs читает каталог и конфиг."""
    import voice_batch
    
    old_root = voice_batch.ROOT
    voice_batch.ROOT = str(mock_config['root'])
    
    entries, voices, who_to_voice = voice_batch.load_inputs()
    
    assert len(entries) == 3
    assert 'TestVoice' in voices
    assert who_to_voice.get('tv') == 'TestVoice'
    
    voice_batch.ROOT = old_root


def test_select_phrases_with_ref(mock_config):
    """Тест: select_phrases находит фразы с рефом."""
    import voice_batch
    
    old_root = voice_batch.ROOT
    voice_batch.ROOT = str(mock_config['root'])
    
    entries, voices, who_to_voice = voice_batch.load_inputs()
    
    class Args:
        arc = None
        char = 'TestVoice'
        uid = None
        lang = 'ru'
        ref = None
    
    phrases = voice_batch.select_phrases(entries, voices, who_to_voice, Args())
    
    assert len(phrases) == 1
    assert phrases[0]['uid'] == 'test_uid_001'
    assert phrases[0]['voice'] == 'TestVoice'
    assert 'TestVoice.wav' in phrases[0]['ref']
    
    voice_batch.ROOT = old_root


def test_select_phrases_skips_no_ref(mock_config):
    """Тест: select_phrases использует дефолтный путь если ref не указан."""
    import voice_batch
    
    old_root = voice_batch.ROOT
    voice_batch.ROOT = str(mock_config['root'])
    
    entries, voices, who_to_voice = voice_batch.load_inputs()
    
    class Args:
        arc = None
        char = 'NoRefVoice'
        uid = None
        lang = 'ru'
        ref = None
    
    phrases = voice_batch.select_phrases(entries, voices, who_to_voice, Args())
    
    # NoRefVoice не имеет ref → используется дефолтный путь refs/ready/NoRefVoice.wav
    assert len(phrases) == 1
    assert 'NoRefVoice.wav' in phrases[0]['ref']
    
    voice_batch.ROOT = old_root


def test_select_phrases_narration(mock_config):
    """Тест: наррация маппится на 'narrator' голос."""
    import voice_batch
    
    old_root = voice_batch.ROOT
    voice_batch.ROOT = str(mock_config['root'])
    
    # Добавляем narrator в конфиг
    cfg_path = mock_config['config']
    with open(cfg_path, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    cfg['voices']['narrator'] = {
        'ref': 'refs/ready/Narrator.wav',
        'who': ['narrator']
    }
    with open(cfg_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)
    
    # Создаём реф для narrator
    wav_path = mock_config['ready'] / 'Narrator.wav'
    wav_path.write_bytes(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
    
    entries, voices, who_to_voice = voice_batch.load_inputs()
    
    class Args:
        arc = None
        char = None
        uid = None
        lang = 'ru'
        ref = None
    
    phrases = voice_batch.select_phrases(entries, voices, who_to_voice, Args())
    
    # Наррация должна быть включена (narrator голос есть)
    narration = [p for p in phrases if p['uid'] == 'test_uid_003']
    assert len(narration) == 1
    
    voice_batch.ROOT = old_root


def test_ref_path_uses_yaml_ref(mock_config):
    """Тест: voice_batch берёт ref из voices.yaml, а не дефолтного пути."""
    import voice_batch
    
    old_root = voice_batch.ROOT
    voice_batch.ROOT = str(mock_config['root'])
    
    # Меняем ref в yaml на нестандартный путь
    cfg_path = mock_config['config']
    with open(cfg_path, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    cfg['voices']['TestVoice']['ref'] = 'refs/ready/custom_path.wav'
    with open(cfg_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)
    
    # Создаём файл по нестандартному пути
    custom_wav = mock_config['ready'] / 'custom_path.wav'
    custom_wav.write_bytes(b'custom')
    
    entries, voices, who_to_voice = voice_batch.load_inputs()
    
    class Args:
        arc = None
        char = 'TestVoice'
        uid = None
        lang = 'ru'
        ref = None
    
    phrases = voice_batch.select_phrases(entries, voices, who_to_voice, Args())
    
    assert len(phrases) == 1
    assert 'custom_path.wav' in phrases[0]['ref']
    
    voice_batch.ROOT = old_root
