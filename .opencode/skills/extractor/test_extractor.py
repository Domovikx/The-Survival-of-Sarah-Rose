"""
Tests for extractor.py
"""

import pytest
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent))
from extractor import Extractor, TextBlock, Scene


class TestExtractorInit:
    def test_init(self, tmp_path):
        extractor = Extractor(str(tmp_path), str(tmp_path))
        assert extractor.game_dir == tmp_path
        assert extractor.output_dir == tmp_path
        assert len(extractor.scenes) == 0
        assert len(extractor.extracted) == 0

    def test_scan_game_files_excludes_tl(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()
        tl = game / "tl"
        tl.mkdir()

        (game / "script.rpy").write_text("label test:\ns 'Hello'")
        (tl / "translated.rpy").write_text("translate ru test:")

        extractor = Extractor(str(game), str(tmp_path))
        files = extractor.scan_game_files()

        assert len(files) == 1
        assert "script.rpy" in str(files[0])


class TestExtractorPatterns:
    def test_parse_string(self, tmp_path):
        extractor = Extractor(str(tmp_path), str(tmp_path))

        assert extractor._parse_string('"Hello"') == "Hello"
        assert extractor._parse_string('"Hello World"') == "Hello World"
        assert extractor._parse_string('\\"Hello\\"') == '"Hello"'

    def test_generate_id(self, tmp_path):
        extractor = Extractor(str(tmp_path), str(tmp_path))

        id1 = extractor._generate_id("test", "Hello", "dialogue")
        id2 = extractor._generate_id("test", "Hello", "dialogue")
        id3 = extractor._generate_id("test", "World", "dialogue")

        # Одинаковые тексты = одинаковые ID
        assert id1 == id2
        # Разные тексты = разные ID
        assert id1 != id3


class TestExtractorFile:
    def test_extract_dialogue(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        script = game / "test.rpy"
        script.write_text('label test:\ns "Hello world"\ns "Second line"', encoding='utf-8')

        extractor = Extractor(str(game), str(tmp_path))
        extractor.extract_file(script)

        assert len(extractor.extracted) == 2
        assert extractor.extracted[0].original_text == "Hello world"
        assert extractor.extracted[0].text_type == "dialogue"
        assert extractor.extracted[0].character == "s"

    def test_extract_narration(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        script = game / "test.rpy"
        script.write_text('label test:\n"Narration text"', encoding='utf-8')

        extractor = Extractor(str(game), str(tmp_path))
        extractor.extract_file(script)

        narrations = [b for b in extractor.extracted if b.text_type == 'narration']
        assert len(narrations) == 1
        assert narrations[0].original_text == "Narration text"

    def test_extract_menu_choice(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        script = game / "test.rpy"
        script.write_text('''label test:
menu:
    "Choose"
    "Option A":
        pass
    "Option B":
        pass
''', encoding='utf-8')

        extractor = Extractor(str(game), str(tmp_path))
        extractor.extract_file(script)

        menu = [b for b in extractor.extracted if b.text_type == 'menu_choice']
        assert len(menu) == 2  # "Choose" skipped
        texts = {b.original_text for b in menu}
        assert "Option A" in texts
        assert "Option B" in texts

    def test_extract_ui_string(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        script = game / "test.rpy"
        script.write_text('label test:\nscreen main_menu():\n    text _("Save")\n    text _("Load")', encoding='utf-8')

        extractor = Extractor(str(game), str(tmp_path))
        extractor.extract_file(script)

        ui = [b for b in extractor.extracted if b.text_type == 'ui_string']
        assert len(ui) == 2

    def test_extract_character_name(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        script = game / "test.rpy"
        script.write_text('label test:\ndefine s = Character(_("Sarah"))', encoding='utf-8')

        extractor = Extractor(str(game), str(tmp_path))
        extractor.extract_file(script)

        chars = [b for b in extractor.extracted if b.text_type == 'character_name']
        assert len(chars) == 1
        assert chars[0].original_text == "Sarah"


class TestExtractorOrganize:
    def test_organize_scenes(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        script = game / "OpeningScene.rpy"
        script.write_text('label OpeningScene:\n"Test"', encoding='utf-8')

        extractor = Extractor(str(game), str(tmp_path))
        extractor.extract_file(script)

        arcs = extractor.organize_scenes()
        assert 'Prologue' in arcs
        assert len(arcs['Prologue']) == 1


class TestExtractorFull:
    def test_extract_all(self, tmp_path):
        game = tmp_path / "game"
        game.mkdir()

        (game / "script1.rpy").write_text('label test1:\ns "Hello"', encoding='utf-8')
        (game / "script2.rpy").write_text('label test2:\n"World"', encoding='utf-8')

        extractor = Extractor(str(game), str(tmp_path))
        extractor.extract_all()

        assert len(extractor.extracted) >= 2
        assert len(extractor.scenes) >= 2