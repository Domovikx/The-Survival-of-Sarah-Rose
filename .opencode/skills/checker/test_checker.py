"""
Tests for checker.py
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from checker import Checker


class TestCheckerInit:
    def test_init(self, tmp_path):
        game = tmp_path / "game"
        source = tmp_path / "source"
        game.mkdir()
        source.mkdir()

        checker = Checker(str(game), str(source))
        assert checker.game_dir == game
        assert checker.source_dir == source


class TestCheckerDuplicates:
    def test_no_duplicates(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()

        file = source / "test.rpy"
        file.write_text('''# -*- encoding: utf-8 -*-
translate ru strings:
    old "Hello"
    new "Привет"

    old "World"
    new "Мир"
''', encoding='utf-8')

        checker = Checker(str(tmp_path), str(source))
        result = checker.check_duplicates()

        assert len(result) == 0

    def test_finds_duplicates(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()

        file = source / "screens.rpy"
        file.write_text('''# -*- encoding: utf-8 -*-
translate ru strings:
    old "Save"
    new "Сохранить"

    old "Save"
    new "Сохранить"

    old "Load"
    new "Загрузить"
''', encoding='utf-8')

        checker = Checker(str(tmp_path), str(source))
        result = checker.check_duplicates()

        assert "screens.rpy" in result
        assert len(result["screens.rpy"]) >= 1


class TestCheckerScanOriginals:
    def test_scan_empty_game(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        checker = Checker(str(game), str(tmp_path))
        originals = checker.scan_originals()

        assert len(originals) == 0

    def test_scan_dialogue(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        script = game / "test.rpy"
        script.write_text('label test:\ns "Hello world"', encoding='utf-8')

        checker = Checker(str(game), str(tmp_path))
        originals = checker.scan_originals()

        assert "Hello world" in originals


class TestCheckerVerify:
    def test_verify_empty(self, tmp_path):
        game = tmp_path / "game"
        source = tmp_path / "source"
        game.mkdir()
        source.mkdir()

        checker = Checker(str(game), str(source))
        result = checker.verify()

        assert result['original_count'] == 0
        assert result['duplicate_files'] == 0