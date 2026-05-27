"""
Tests for extract_texts.py v4
Practical tests that document and verify the extractor behavior.
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_texts import (
     RenPyExtractor, generate_rpy, generate_engine_rpy,
     count_engine_translations, _find_renpy_common_dir,
     _hash, _esc, _unescape,
     VERSION, ARC_PATTERNS,
 )


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d)


@pytest.fixture
def sample_script(tmp_dir):
    """Минимальный скрипт для тестирования всех типов строк."""
    content = (
        'define config.name = _("The Survival Game")\n'
        '\n'
        'label start:\n'
        '    "This is a narration line."\n'
        '    s "Hello, my name is Sarah."\n'
        '    "Another narration."\n'
        '\n'
        'menu my_menu:\n'
        '    "Yes":\n'
        '        pass\n'
        '    "No":\n'
        '        pass\n'
        '\n'
        'label another_scene:\n'
        '    ko "King speaking."\n'
        '    ko "Another line from king."\n'
    )
    script = tmp_dir / "test_game" / "script.rpy"
    script.parent.mkdir(parents=True)
    script.write_text(content, encoding='utf-8')
    return tmp_dir / "test_game"


@pytest.fixture
def dup_script(tmp_dir):
    """Скрипт с дублирующимися строками — проверяем dedup."""
    content = (
        'define s = Character(_("Sarah"), who_color="#daa520")\n'
        'define ko = Character(_("King Orwell"), who_color="#ff6347")\n'
        '\n'
        'label start:\n'
        '    "This line appears once."\n'
        '    "This line appears once."\n'
        '    s "Dialogue A"\n'
        '    s "Dialogue A"\n'
        '    "This line appears once."\n'
        '\n'
        'label second:\n'
        '    "This line appears once."\n'
    )
    script = tmp_dir / "test_game" / "script.rpy"
    script.parent.mkdir(parents=True)
    script.write_text(content, encoding='utf-8')
    return tmp_dir / "test_game"


@pytest.fixture
def multi_file_script(tmp_dir):
    """Несколько файлов с одинаковыми строками — проверяем dedup между файлами."""
    content1 = (
        'label start:\n'
        '    "Shared narration line."\n'
        '    s "Hello"\n'
    )
    content2 = (
        'label quest1:\n'
        '    "Shared narration line."\n'
        '    s "Hello"\n'
        '    "Unique to quest."\n'
    )
    sub = tmp_dir / "test_game" / "subdir"
    sub.mkdir(parents=True)
    (tmp_dir / "test_game" / "script.rpy").write_text(content1, encoding='utf-8')
    (sub / "quest1.rpy").write_text(content2, encoding='utf-8')
    return tmp_dir / "test_game"


# ============================================================
# Unit Tests: Extraction
# ============================================================

class TestExtractionBasics:
    """Проверяем что все типы строк извлекаются корректно."""

    def test_narration_extraction(self, sample_script):
        ext = RenPyExtractor(str(sample_script))
        ext.parse_file(sample_script / "script.rpy")

        assert len(ext.arcs) > 0
        # Нарратив должен быть в arc blocks
        arc_blocks = sum(
            len(s['blocks'])
            for arc in ext.arcs.values()
            for s in arc.values()
        )
        assert arc_blocks >= 4  # 3 narration + 2 dialogue - menu choices

    def test_dialogue_extraction(self, sample_script):
        ext = RenPyExtractor(str(sample_script))
        ext.parse_file(sample_script / "script.rpy")

        # Ищем "Hello, my name is Sarah." в arc blocks
        found = False
        for arc in ext.arcs.values():
            for scene in arc.values():
                for bd in scene['blocks'].values():
                    if 'Hello, my name is Sarah' in bd.get('original', ''):
                        found = True
                        assert bd['type'] == 'dialogue'
                        assert bd['character'] == 's'
        assert found, "Dialogue line not found"

    def test_menu_choice_included(self, sample_script):
        ext = RenPyExtractor(str(sample_script))
        ext.parse_file(sample_script / "script.rpy")

        # Menu choices должны быть в arc blocks
        arc_blocks = sum(
            len(s['blocks'])
            for arc in ext.arcs.values()
            for s in arc.values()
        )
        # Yes + No
        assert arc_blocks >= 2

    def test_ui_string_extraction(self, sample_script):
        ext = RenPyExtractor(str(sample_script))
        ext.parse_file(sample_script / "script.rpy")

        # Menu choices are captured as arc blocks (menu_choice type)
        # not as ui_blocks — so check arc blocks for "Yes" / "No"
        arc_blocks = sum(
            len(s['blocks'])
            for arc in ext.arcs.values()
            for s in arc.values()
        )
        assert arc_blocks >= 2  # "Yes", "No" menu choices

    def test_character_name_extraction(self, tmp_dir):
        """Character(_("Name")) должен извлекаться отдельно."""
        content = 'define s = Character(_("Sarah"), who_color="#daa520")\n'
        script = tmp_dir / "script.rpy"
        script.write_text(content, encoding='utf-8')

        ext = RenPyExtractor(str(tmp_dir))
        ext.parse_file(script)

        assert len(ext.character_blocks) == 1
        block = list(ext.character_blocks.values())[0]
        assert block['original'] == 'Sarah'
        assert block['type'] == 'character_name'

    def test_character_name_plain(self, tmp_dir):
        """Character("Name") без _() тоже должен извлекаться."""
        content = 'define s = Character("Sarah")\n'
        script = tmp_dir / "script.rpy"
        script.write_text(content, encoding='utf-8')

        ext = RenPyExtractor(str(tmp_dir))
        ext.parse_file(script)

        assert len(ext.character_blocks) == 1
        block = list(ext.character_blocks.values())[0]
        assert block['original'] == 'Sarah'
        assert block['type'] == 'character_name'

    def test_define_extraction(self, tmp_dir):
        """define config.name = _("Name") должен извлекаться."""
        content = 'define config.name = _("My Game Name")\n'
        script = tmp_dir / "script.rpy"
        script.write_text(content, encoding='utf-8')

        ext = RenPyExtractor(str(tmp_dir))
        ext.parse_file(script)

        assert len(ext.define_blocks) == 1
        block = list(ext.define_blocks.values())[0]
        assert block['original'] == 'My Game Name'


class TestDeduplication:
    """Проверяем что дубликаты не создаются."""

    def test_duplicate_narration_same_scene(self, dup_script):
        """Одинаковые строки нарратива в одной сцене — только 1."""
        ext = RenPyExtractor(str(dup_script))
        ext.parse_file(dup_script / "script.rpy")

        seen_originals = set()
        for arc in ext.arcs.values():
            for scene in arc.values():
                for dk, bd in scene['blocks'].items():
                    assert bd['original'] not in seen_originals, f"Duplicate in scene: {bd['original']}"
                    seen_originals.add(bd['original'])

        # "This line appears once." appears 3 times in file
        # Should be only 1 in blocks
        count = sum(
            1 for arc in ext.arcs.values()
            for scene in arc.values()
            for bd in scene['blocks'].values()
            if bd['original'] == "This line appears once."
        )
        assert count == 1

    def test_duplicate_dialogue_same_scene(self, dup_script):
        """Одинаковый диалог в одной сцене — только 1."""
        ext = RenPyExtractor(str(dup_script))
        ext.parse_file(dup_script / "script.rpy")

        count = sum(
            1 for arc in ext.arcs.values()
            for scene in arc.values()
            for bd in scene['blocks'].values()
            if bd['original'] == "Dialogue A"
        )
        assert count == 1

    def test_duplicate_across_scenes(self, dup_script):
        """Одинаковая строка в разных сценах — только 1 (благодаря global dedup)."""
        ext = RenPyExtractor(str(dup_script))
        ext.parse_file(dup_script / "script.rpy")

        # "This line appears once." appears in both start and second labels
        count = sum(
            1 for arc in ext.arcs.values()
            for scene in arc.values()
            for bd in scene['blocks'].values()
            if bd['original'] == "This line appears once."
        )
        assert count == 1

    def test_duplicate_across_files(self, multi_file_script):
        """Одинаковая строка в разных файлах — только 1."""
        ext = RenPyExtractor(str(multi_file_script))
        ext.scan()

        count = sum(
            1 for arc in ext.arcs.values()
            for scene in arc.values()
            for bd in scene['blocks'].values()
            if bd['original'] == "Shared narration line."
        )
        assert count == 1


class TestArcOrganization:
    """Проверяем что строки попадают в правильные арки."""

    def test_prologue_arc(self, sample_script):
        ext = RenPyExtractor(str(sample_script))
        ext.scan()

        assert 'Prologue' in ext.arcs or 'Other' in ext.arcs

    def test_start_scene_exists(self, sample_script):
        ext = RenPyExtractor(str(sample_script))
        ext.scan()

        # scene "start" должен существовать
        found = False
        for arc in ext.arcs.values():
            if 'start' in arc:
                found = True
        assert found, "Scene 'start' not found in any arc"


class TestTranslationPreservation:
    """Проверяем что существующие переводы сохраняются."""

    def test_load_existing_translations(self, tmp_dir):
        """Если в tl/ru/ уже есть переводы, они подгружаются."""
        # Создаём mock tl/ru/ файл
        screens = tmp_dir / "tl" / "ru" / "screens.rpy"
        screens.parent.mkdir(parents=True)
        screens.write_text(
            'translate ru strings:\n'
            '    old "Hello"\n'
            '    new "Привет"\n\n',
            encoding='utf-8'
        )

        # Создаём game с "Hello"
        script = tmp_dir / "game" / "script.rpy"
        script.parent.mkdir(parents=True)
        script.write_text('label start:\n    "Hello"\n', encoding='utf-8')

        ext = RenPyExtractor(str(tmp_dir / "game"))
        ext.set_existing_translations(tmp_dir / "tl" / "ru")
        ext.scan()

        # "Hello" должен быть в arc blocks
        found = None
        for arc in ext.arcs.values():
            for scene in arc.values():
                for bd in scene['blocks'].values():
                    if bd['original'] == 'Hello':
                        found = bd

        assert found is not None
        assert found['translated'] == 'Привет', f"Expected 'Привет', got '{found['translated']}'"

    def test_new_string_empty_translation(self, tmp_dir):
        """Новая строка без перевода — translated = ''."""
        script = tmp_dir / "game" / "script.rpy"
        script.parent.mkdir(parents=True)
        script.write_text('label start:\n    "New string"\n', encoding='utf-8')

        ext = RenPyExtractor(str(tmp_dir / "game"))
        ext.scan()

        found = None
        for arc in ext.arcs.values():
            for scene in arc.values():
                for bd in scene['blocks'].values():
                    if bd['original'] == 'New string':
                        found = bd

        assert found is not None
        assert found['translated'] == '', f"Expected '', got '{found['translated']}'"


# ============================================================
# Integration Tests: generate_rpy
# ============================================================

class TestGenerateRPY:
    """Проверяем что generate_rpy создаёт правильный формат."""

    def test_rpy_format_no_translation(self, tmp_dir):
        """Когда нет перевода — new = original (не пустая строка)."""
        data = {
            'arcs': {
                'Prologue': {
                    'start': {
                        'source_file': 'script.rpy',
                        'source_line': 0,
                        'blocks': {
                            'test_narration': {
                                'id': 'start_abc123',
                                'original': 'Hello world',
                                'translated': '',
                                'type': 'narration',
                                'character': None,
                                'source_file': 'script.rpy',
                                'source_line': 1,
                            }
                        }
                    }
                }
            },
            'ui_by_file': {},
            'characters_by_file': {},
            'defines_by_file': {},
        }

        out_dir = tmp_dir / "tl" / "ru"
        generate_rpy(data, out_dir)

        result_file = out_dir / "Prologue" / "start.rpy"
        assert result_file.exists()

        content = result_file.read_text(encoding='utf-8')
        assert 'translate ru strings:' in content
        assert 'old "Hello world"' in content
        assert 'new "Hello world"' in content  # fallback to original

    def test_rpy_format_with_translation(self, tmp_dir):
        """Когда есть перевод — new = translated."""
        data = {
            'arcs': {
                'Prologue': {
                    'start': {
                        'source_file': 'script.rpy',
                        'source_line': 0,
                        'blocks': {
                            'test_narration': {
                                'id': 'start_abc123',
                                'original': 'Hello world',
                                'translated': 'Привет мир',
                                'type': 'narration',
                                'character': None,
                                'source_file': 'script.rpy',
                                'source_line': 1,
                            }
                        }
                    }
                }
            },
            'ui_by_file': {},
            'characters_by_file': {},
            'defines_by_file': {},
        }

        out_dir = tmp_dir / "tl" / "ru"
        generate_rpy(data, out_dir)

        content = (out_dir / "Prologue" / "start.rpy").read_text(encoding='utf-8')
        assert 'old "Hello world"' in content
        assert 'new "Привет мир"' in content

    def test_screens_rpy_format(self, tmp_dir):
        """UI строки генерируются в screens.rpy."""
        data = {
            'arcs': {},
            'ui_by_file': {
                'screens.rpy': [
                    {
                        'id': 'ui_abc123',
                        'original': 'Start',
                        'translated': 'Начать',
                        'type': 'ui_string',
                        'character': None,
                        'source_file': 'screens.rpy',
                        'source_line': 10,
                    }
                ]
            },
            'characters_by_file': {},
            'defines_by_file': {},
        }

        out_dir = tmp_dir / "tl" / "ru"
        generate_rpy(data, out_dir)

        content = (out_dir / "screens.rpy").read_text(encoding='utf-8')
        assert 'translate ru strings:' in content
        assert 'old "Start"' in content
        assert 'new "Начать"' in content

    def test_misc_strings_format(self, tmp_dir):
        """Characters + Defines генерируются в misc_strings.rpy."""
        data = {
            'arcs': {},
            'ui_by_file': {},
            'characters_by_file': {
                'script.rpy': [
                    {
                        'id': 'char_abc123',
                        'original': 'Sarah',
                        'translated': 'Сара',
                        'type': 'character_name',
                        'character': None,
                        'source_file': 'script.rpy',
                        'source_line': 5,
                    }
                ]
            },
            'defines_by_file': {},
        }

        out_dir = tmp_dir / "tl" / "ru"
        generate_rpy(data, out_dir)

        content = (out_dir / "misc_strings.rpy").read_text(encoding='utf-8')
        assert 'old "Sarah"' in content
        assert 'new "Сара"' in content

    def test_existing_translations_loaded(self, tmp_dir):
        """Переводы из ранее сгенерированных .rpy загружаются."""
        # Сначала сгенерируем переводы
        data = {
            'arcs': {
                'Prologue': {
                    'start': {
                        'source_file': 'script.rpy',
                        'source_line': 0,
                        'blocks': {
                            'nar1': {
                                'id': 'start_abc',
                                'original': 'Test string',
                                'translated': 'Перевод',
                                'type': 'narration',
                                'character': None,
                                'source_file': 'script.rpy',
                                'source_line': 1,
                            }
                        }
                    }
                }
            },
            'ui_by_file': {},
            'characters_by_file': {},
            'defines_by_file': {},
        }

        # Генерируем исходные .rpy с переводами
        out_dir = tmp_dir / "tl" / "ru"
        generate_rpy(data, out_dir)

        # Имитируем сканирование game и загрузку переводов
        game_dir = tmp_dir / "game"
        game_dir.mkdir()
        (game_dir / "script.rpy").write_text(
            'label start:\n'
            '    "Test string"\n',
            encoding='utf-8'
        )

        ext = RenPyExtractor(str(game_dir))
        ext.set_existing_translations(out_dir)
        assert 'Test string' in ext._existing_translations


# ============================================================
# Full Pipeline Test
# ============================================================

class TestFullPipeline:
    """Тест полного цикла: extract → generate → verify."""

    def test_roundtrip(self, tmp_dir):
        """Полный цикл: извлечение → генерация → загрузка → проверка."""
        # 1. Game files
        game_dir = tmp_dir / "game"
        game_dir.mkdir()
        (game_dir / "script.rpy").write_text(
            'label start:\n'
            '    "Intro narration."\n'
            '    s "Hello!"\n'
            '\n'
            'menu test:\n'
            '    "Option 1":\n'
            '        pass\n'
            '    "Option 2":\n'
            '        pass\n',
            encoding='utf-8'
        )
        (game_dir / "screens.rpy").write_text(
            'textbutton _("Start") action Start()\n',
            encoding='utf-8'
        )

        # 2. Extract
        tl_dir = tmp_dir / "tl" / "ru"
        ext = RenPyExtractor(str(game_dir))
        data = ext.scan()

        # "start" doesn't match any ARC_PATTERN, so it goes to "Other"
        assert 'Other' in data['arcs']
        assert len(ext.ui_blocks) >= 1  # "Start"

        # 3. Generate .rpy files
        generate_rpy(data, tl_dir)

        # 4. Check that generated file parses correctly
        start_file = tl_dir / "Other" / "start.rpy"
        assert start_file.exists()
        content = start_file.read_text(encoding='utf-8')
        assert 'translate ru strings:' in content
        assert 'old "Intro narration."' in content
        assert 'new "Intro narration."' in content  # default = original

        # 5. Re-scan and load translations — only actual translations are loaded
        # (new == original means "not translated yet", which is correctly skipped)
        ext2 = RenPyExtractor(str(game_dir))
        ext2.set_existing_translations(tl_dir)
        # No translations were set since new == original for all entries
        # This is correct behavior — nothing to load
        assert len(ext2._existing_translations) == 0

    def test_no_dedup_across_arcs(self, tmp_dir):
        """Строки из разных сцен НЕ дедуплицируются между arc-файлами."""
        game_dir = tmp_dir / "game"
        game_dir.mkdir()
        (game_dir / "script.rpy").write_text(
            'label scene1:\n'
            '    "Unique to scene1."\n'
            '\n'
            'label scene2:\n'
            '    "Unique to scene2."\n',
            encoding='utf-8'
        )

        ext = RenPyExtractor(str(game_dir))
        data = ext.scan()

        # Должно быть 2 блока в разных сценах
        total = sum(
            len(s['blocks'])
            for arc in data['arcs'].values()
            for s in arc.values()
        )
        assert total == 2


# ============================================================
# Utility Tests
# ============================================================
# Quoted Dialogue: "Character" "text"
# ============================================================

@pytest.fixture
def quoted_dialogue_script(tmp_dir):
    """Скрипт с диалогами в формате "Character" "text"."""
    content = (
        'label start:\n'
        '    "Raza" "Good. Good."\n'
        '    "Raza" "They call me Raza."\n'
        '    "This is narration without character."\n'
        '    "Raza" "No. Not now."\n'
        '    s "Hello from defined character."\n'
        '    "Guard Captain" "There she goes!"\n'
    )
    script = tmp_dir / "test_game" / "script.rpy"
    script.parent.mkdir(parents=True)
    script.write_text(content, encoding='utf-8')
    return tmp_dir / "test_game"


class TestQuotedDialogue:
    """Проверяем что "Character" "dialogue" не схлопывается в нарратив."""

    def test_quoted_dialogue_not_narration(self, quoted_dialogue_script):
        ext = RenPyExtractor(str(quoted_dialogue_script))
        ext.parse_file(quoted_dialogue_script / "script.rpy")

        found_raza_lines = []
        found_narration = []
        for arc in ext.arcs.values():
            for scene in arc.values():
                for bd in scene['blocks'].values():
                    orig = bd.get('original', '')
                    if 'Raza' in orig or 'Good. Good.' in orig or 'They call me Raza' in orig or 'No. Not now' in orig:
                        found_raza_lines.append(bd)
                    if 'narration' in bd.get('type', ''):
                        found_narration.append(bd)

        # Raza lines должны быть dialogue, НЕ narration
        for bd in found_raza_lines:
            assert bd['type'] == 'dialogue', \
                f"Expected dialogue, got {bd['type']}: {bd.get('original', '')}"

        # Narration должна быть только одна (без Raza)
        assert len(found_narration) == 1
        assert found_narration[0]['original'] == 'This is narration without character.'

    def test_quoted_dialogue_text_without_character(self, quoted_dialogue_script):
        """Текст диалога не должен содержать имя персонажа."""
        ext = RenPyExtractor(str(quoted_dialogue_script))
        ext.parse_file(quoted_dialogue_script / "script.rpy")

        for arc in ext.arcs.values():
            for scene in arc.values():
                for bd in scene['blocks'].values():
                    orig = bd.get('original', '')
                    if bd['type'] == 'dialogue':
                        # Текст диалога не должен содержать имя персонажа
                        assert '\\"' not in orig, \
                            f"Dialogue text contains escaped quotes: {orig}"
                        assert not orig.startswith('Raza'), \
                            f"Dialogue text starts with character name: {orig}"

    def test_quoted_dialogue_character_name(self, quoted_dialogue_script):
        """Имя персонажа извлекается в поле character и в character_blocks."""
        ext = RenPyExtractor(str(quoted_dialogue_script))
        ext.parse_file(quoted_dialogue_script / "script.rpy")

        raza_lines = []
        for arc in ext.arcs.values():
            for scene in arc.values():
                for bd in scene['blocks'].values():
                    if bd.get('character') == 'Raza':
                        raza_lines.append(bd)

        assert len(raza_lines) == 3  # 3 Raza dialogue lines
        for bd in raza_lines:
            assert bd['type'] == 'dialogue'

        # Raza должен быть в character_blocks для перевода
        assert 'Raza' in ext.character_blocks
        assert ext.character_blocks['Raza']['type'] == 'character_name'

        # s (переменная, не display name) не должен попадать в character_blocks
        assert 's' not in ext.character_blocks

        # Multi-word character "Guard Captain" должен корректно парситься
        guard_captain_lines = []
        for arc in ext.arcs.values():
            for scene in arc.values():
                for bd in scene['blocks'].values():
                    if bd.get('character') == 'Guard Captain':
                        guard_captain_lines.append(bd)
        assert len(guard_captain_lines) == 1
        assert guard_captain_lines[0]['original'] == 'There she goes!'
        # Guard Captain должен быть в character_blocks
        assert 'Guard Captain' in ext.character_blocks

    def test_generated_rpy_no_combined_format(self, quoted_dialogue_script, tmp_dir):
        """В сгенерированном .rpy не должно быть combined формата "Char\" \"text"."""
        ext = RenPyExtractor(str(quoted_dialogue_script))
        ext.parse_file(quoted_dialogue_script / "script.rpy")
        data = ext.scan()

        out_dir = tmp_dir / "tl" / "ru"
        generate_rpy(data, out_dir)

        # Ищем сгенерированные файлы
        for rpy_file in out_dir.rglob("*.rpy"):
            content = rpy_file.read_text(encoding='utf-8')
            # Проверяем: нет ли строк вида old "Char\" \"text"
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('old '):
                    # Не должно быть Raza\" \" в old строке
                    assert 'Raza\\" \\"' not in stripped, \
                        f"Combined format found: {stripped}"
                    # Не должно быть \\" \\" вообще в old строке
                    assert '\\" \\"' not in stripped, \
                        f"Escaped quote pair found in old: {stripped}"

    def test_generated_rpy_has_split_format(self, quoted_dialogue_script, tmp_dir):
        """Диалог Raza должен быть split-форматом: old "text" без персонажа."""
        ext = RenPyExtractor(str(quoted_dialogue_script))
        ext.parse_file(quoted_dialogue_script / "script.rpy")
        data = ext.scan()

        out_dir = tmp_dir / "tl" / "ru"
        generate_rpy(data, out_dir)

        found_good = False
        for rpy_file in out_dir.rglob("*.rpy"):
            content = rpy_file.read_text(encoding='utf-8')
            if 'Good. Good.' in content:
                found_good = True
                assert 'old "Good. Good."' in content
                # Не должно быть Raza в этой строке
                assert 'Raza' not in content.split('old "Good. Good."')[0][-20:], \
                    "Character name prepended to dialogue in old"
        assert found_good, "Dialogue 'Good. Good.' not found in generated output"


# ============================================================

class TestUtilities:
    def test_hash_consistency(self):
        """Хэш должен быть детерминированным."""
        assert _hash("test") == _hash("test")

    def test_esc_quotes(self):
        assert _esc('He said "hello"') == 'He said \\"hello\\"'

    def test_esc_backslash(self):
        assert _esc("path\\to\\file") == "path\\\\to\\\\file"

    def test_unescape(self):
        # \" → "
        assert _unescape('Say \\"hello\\"') == 'Say "hello"'
        # \\ → \
        assert _unescape('back\\\\slash') == 'back\\slash'
        # \\\" → \" (backslash preserved before quote)
        assert _unescape('\\\\\\"') == '\\"'


# ============================================================

class TestEscapedQuotesRoundtrip:
    """Проверка roundtrip для строк с \" внутри (Ren'Py escape)."""

    def test_narration_with_escaped_quotes(self, tmp_dir):
        """Нарратив с \" должен корректно проходить unescape → _esc."""
        content = (
            'label start:\n'
            '    "She said \\"hello\\" to me."\n'
        )
        script = tmp_dir / "test_game" / "script.rpy"
        script.parent.mkdir(parents=True)
        script.write_text(content, encoding='utf-8')

        ext = RenPyExtractor(str(tmp_dir / "test_game"))
        ext.parse_file(script)
        data = ext.scan()

        out_dir = tmp_dir / "tl" / "ru"
        generate_rpy(data, out_dir)

        generated = list(out_dir.rglob("*.rpy"))
        assert generated, "No files generated"
        gen_content = generated[0].read_text(encoding='utf-8')

        # old строка должна содержать правильно экранированную кавычку
        assert 'old "She said \\"hello\\" to me."' in gen_content, \
            f"Wrong escaping in generated: {gen_content}"

    def test_unescape_preserves_text_meaning(self, tmp_dir):
        """Текст после unescape должен совпадать с тем, что видит игрок."""
        content = (
            'label start:\n'
            '    "The title reads: \\"A Tale of Two Cities\\"."\n'
        )
        script = tmp_dir / "test_game" / "script.rpy"
        script.parent.mkdir(parents=True)
        script.write_text(content, encoding='utf-8')

        ext = RenPyExtractor(str(tmp_dir / "test_game"))
        ext.parse_file(script)

        found = False
        for arc in ext.arcs.values():
            for scene in arc.values():
                for bd in scene['blocks'].values():
                    orig = bd.get('original', '')
                    if 'A Tale of Two Cities' in orig:
                        found = True
                        # После unescape не должно быть обратных слешей перед кавычкой
                        assert '\\"' not in orig, \
                            f"Text still has escaped quotes: {orig}"
                        # Текст должен содержать чистые кавычки
                        assert '"' in orig, \
                            f"Text should have plain quotes: {orig}"
        assert found, "Extracted text not found"


# ============================================================
# Engine Built-in Tests
# ============================================================

class TestEngineBuiltins:
    """Tests for scan_engine_builtins and generate_engine_rpy."""

    def test_scan_engine_builtins_finds_strings(self, tmp_dir):
        """scan_engine_builtins finds _(\"text\") in common/00*.rpy files."""
        common_dir = tmp_dir / "renpy" / "common"
        common_dir.mkdir(parents=True)
        (common_dir / "00gui.rpy").write_text(
            'init python:\n'
            '    class gui:\n'
            '        QUIT = _("Are you sure you want to quit?")\n'
            '        DELETE = _("Are you sure you want to delete this save?")\n',
            encoding='utf-8'
        )
        (common_dir / "00layout.rpy").write_text(
            'init python:\n'
            '    layout.QUIT = _("Are you sure you want to quit?")\n',
            encoding='utf-8'
        )
        game_dir = tmp_dir / "game"
        game_dir.mkdir()
        (game_dir / "script.rpy").write_text('label start:\n    "Hello"\n', encoding='utf-8')

        ext = RenPyExtractor(str(game_dir))
        blocks = ext.scan_engine_builtins(common_dir)

        # 2 unique strings (the duplicate "Are you sure you want to quit?" is deduped)
        assert len(blocks) == 2
        texts = {b['original'] for b in blocks}
        assert "Are you sure you want to quit?" in texts
        assert "Are you sure you want to delete this save?" in texts

    def test_scan_respects_seen_originals(self, tmp_dir):
        """Strings already seen in game/ are not duplicated in engine blocks."""
        common_dir = tmp_dir / "renpy" / "common"
        common_dir.mkdir(parents=True)
        (common_dir / "00gui.rpy").write_text(
            'init python:\n'
            '    QUIT = _("Hello")\n',
            encoding='utf-8'
        )
        game_dir = tmp_dir / "game"
        game_dir.mkdir()
        (game_dir / "script.rpy").write_text('label start:\n    "Hello"\n', encoding='utf-8')

        ext = RenPyExtractor(str(game_dir))
        ext.parse_file(game_dir / "script.rpy")
        blocks = ext.scan_engine_builtins(common_dir)

        # "Hello" already seen in game, should be excluded from engine blocks
        assert len(blocks) == 0

    def test_generate_engine_rpy_creates_file(self, tmp_dir):
        """generate_engine_rpy creates renpy_common.rpy with correct format.
        Note: translations come from existing file on disk, not from block['translated'].
        """
        blocks = [
            {
                'id': 'engine_abc',
                'original': 'Are you sure you want to quit?',
                'translated': '',
                'type': 'engine_string',
                'source_file': 'renpy/common/00gui.rpy',
                'source_line': 42,
            },
            {
                'id': 'engine_def',
                'original': 'Are you sure?',
                'translated': '',
                'type': 'engine_string',
                'source_file': 'renpy/common/00gui.rpy',
                'source_line': 40,
            },
        ]
        tl_dir = tmp_dir / "tl" / "ru"
        tl_dir.mkdir(parents=True)

        generated = generate_engine_rpy(blocks, tl_dir)
        assert generated == ['renpy_common.rpy']

        result = tl_dir / "renpy_common.rpy"
        assert result.exists()
        content = result.read_text(encoding='utf-8')
        assert 'translate ru strings:' in content
        assert 'old "Are you sure you want to quit?"' in content
        assert 'new "Are you sure you want to quit?"' in content  # fallback = original
        assert 'old "Are you sure?"' in content
        assert 'new "Are you sure?"' in content  # no existing translation

    def test_generate_engine_rpy_preserves_existing(self, tmp_dir):
        """Existing translations in renpy_common.rpy are preserved."""
        tl_dir = tmp_dir / "tl" / "ru"
        tl_dir.mkdir(parents=True)
        old = tl_dir / "renpy_common.rpy"
        old.write_text(
            'translate ru strings:\n'
            '    old "Are you sure you want to quit?"\n'
            '    new "Вы уверены, что хотите выйти?"\n\n',
            encoding='utf-8'
        )

        blocks = [
            {
                'id': 'engine_abc',
                'original': 'Are you sure you want to quit?',
                'translated': '',
                'type': 'engine_string',
                'source_file': 'renpy/common/00gui.rpy',
                'source_line': 42,
            },
        ]
        generated = generate_engine_rpy(blocks, tl_dir)
        content = (tl_dir / "renpy_common.rpy").read_text(encoding='utf-8')
        assert 'new "Вы уверены, что хотите выйти?"' in content

    def test_count_engine_translations(self, tmp_dir):
        """count_engine_translations returns correct totals."""
        tl_dir = tmp_dir / "tl" / "ru"
        tl_dir.mkdir(parents=True)
        f = tl_dir / "renpy_common.rpy"
        f.write_text(
            'translate ru strings:\n'
            '    old "String one"\n'
            '    new "Строка один"\n\n'
            '    old "String two"\n'
            '    new "String two"\n\n'
            '    old "String three"\n'
            '    new "Строка три"\n\n',
            encoding='utf-8'
        )

        total, done = count_engine_translations(tl_dir)
        assert total == 3
        assert done == 2

    def test_count_no_file(self, tmp_dir):
        """count_engine_translations returns 0,0 if file doesn't exist."""
        tl_dir = tmp_dir / "tl" / "ru"
        total, done = count_engine_translations(tl_dir)
        assert total == 0
        assert done == 0

    def test_find_renpy_common_dir(self, tmp_dir):
        """_find_renpy_common_dir finds the SDK common directory."""
        common_dir = tmp_dir / "renpy-8.5.2-sdk" / "renpy" / "common"
        common_dir.mkdir(parents=True)
        (common_dir / "00gui.rpy").write_text('', encoding='utf-8')

        from extract_texts import _find_renpy_common_dir
        found = _find_renpy_common_dir(tmp_dir)
        assert found == common_dir


if __name__ == '__main__':
    pytest.main([__file__, '-v'])