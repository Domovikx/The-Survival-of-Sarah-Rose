"""
Tests for deduplicate.py
"""

import pytest
import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent))
from deduplicate import deduplicate_file, deduplicate_ui_strings_file, find_duplicates, TranslationEntry


class TestFindDuplicates:
    def test_find_duplicates_single(self):
        entries = [
            TranslationEntry("block1", "Hello", "Привет", 1, 3),
        ]
        result = find_duplicates(entries)
        assert len(result) == 0

    def test_find_duplicates_multiple(self):
        entries = [
            TranslationEntry("block1", "Hello", "Привет", 1, 3),
            TranslationEntry("block2", "Hello", "", 4, 6),
            TranslationEntry("block3", "World", "Мир", 7, 9),
        ]
        result = find_duplicates(entries)
        assert "Hello" in result
        assert len(result["Hello"]) == 2


class TestDeduplicateUIStrings:
    def test_no_duplicates(self, tmp_path):
        file = tmp_path / "screens.rpy"
        file.write_text('''# -*- encoding: utf-8 -*-
translate ru strings:

    old "Hello"
    new "Привет"

    old "World"
    new "Мир"
''', encoding='utf-8')

        count = deduplicate_ui_strings_file(file)
        assert count == 0
        content = file.read_text(encoding='utf-8')
        assert "Hello" in content
        assert "World" in content

    def test_removes_duplicates(self, tmp_path):
        file = tmp_path / "screens.rpy"
        file.write_text('''# -*- encoding: utf-8 -*-
translate ru strings:

    old "Save"
    new "Сохранить"

    old "Save"
    new "Сохранить"

    old "Load"
    new "Загрузить"
''', encoding='utf-8')

        count = deduplicate_ui_strings_file(file)
        assert count == 1  # 1 pair removed (old + new = 2 lines, we count pairs)

        content = file.read_text(encoding='utf-8')
        # Должен остаться только один Save
        assert content.count('old "Save"') == 1
        assert content.count('old "Load"') == 1

    def test_preserves_different_strings(self, tmp_path):
        file = tmp_path / "screens.rpy"
        file.write_text('''# -*- encoding: utf-8 -*-
translate ru strings:

    old "Save"
    new "Сохранить"

    old "Load"
    new "Загрузить"

    old "Save"
    new "Сохранить"
''', encoding='utf-8')

        count = deduplicate_ui_strings_file(file)
        assert count == 1  # 1 duplicate pair removed

        content = file.read_text(encoding='utf-8')
        assert content.count('old "Save"') == 1
        assert content.count('old "Load"') == 1


class TestDeduplicateDialogue:
    def test_no_duplicates_dialogue(self, tmp_path):
        file = tmp_path / "scene.rpy"
        file.write_text('''# -*- encoding: utf-8 -*-
translate ru block1:
    s "Hello"
    "Привет"

translate ru block2:
    s "World"
    "Мир"
''', encoding='utf-8')

        count = deduplicate_file(file)
        assert count == 0

    def test_same_block_id_different_content(self, tmp_path):
        # Одинаковый block_id с разным содержанием - это не дубликат
        file = tmp_path / "scene.rpy"
        file.write_text('''# -*- encoding: utf-8 -*-
translate ru block1:
    s "Hello"
    "Привет"

translate ru block1:
    s "World"
    "Мир"
''', encoding='utf-8')

        count = deduplicate_file(file)
        # Это разные блоки, не удаляем
        assert count == 0


class TestDeduplicateDirectory:
    def test_full_directory(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Создаём ui_strings/screens.rpy с дубликатами
        ui_dir = output_dir / "ui_strings"
        ui_dir.mkdir()
        screens = ui_dir / "screens.rpy"
        screens.write_text('''# -*- encoding: utf-8 -*-
translate ru strings:

    old "Save"
    new "Сохранить"

    old "Save"
    new "Сохранить"

    old "Back"
    new "Назад"
''', encoding='utf-8')

        # Создаём characters с дубликатами
        char_dir = output_dir / "characters"
        char_dir.mkdir()
        chars = char_dir / "character_names.rpy"
        chars.write_text('''# -*- encoding: utf-8 -*-
translate ru strings:

    old "Sarah"
    new "Сара"

    old "Sarah"
    new "Сара"
''', encoding='utf-8')

        # Запускаем main
        from deduplicate import deduplicate_directory
        results = deduplicate_directory(output_dir)

        assert len(results) >= 2
        assert 'ui_strings/screens.rpy' in results
        assert 'characters/character_names.rpy' in results

    def test_file_not_exists(self, tmp_path):
        file = tmp_path / "nonexistent.rpy"
        count = deduplicate_file(file)
        assert count == 0

    def test_invalid_encoding(self, tmp_path):
        file = tmp_path / "test.rpy"
        file.write_bytes(b'\x00\x01\x02')
        count = deduplicate_file(file)
        assert count == 0