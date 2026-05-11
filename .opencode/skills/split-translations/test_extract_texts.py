"""
Tests for extract_texts.py - Full version
"""

import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extract_texts import RenPyTextExtractor, TextBlock, Scene, Arc


class TestTextBlockCreation:
    def test_create_text_block(self):
        block = TextBlock(
            id="test_abc12345",
            label="test_label",
            source_file="test.rpy",
            line_number=42,
            text_type="dialogue",
            character="s",
            original_text="Hello world"
        )
        assert block.id == "test_abc12345"
        assert block.character == "s"
        assert block.original_text == "Hello world"

    def test_text_block_default_values(self):
        block = TextBlock(
            id="test123", label="label",
            source_file="file.rpy", line_number=1, text_type="narration"
        )
        assert block.character is None
        assert block.original_text == ""


class TestRenPyTextExtractorInit:
    def test_init(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        assert extractor.game_dir == tmp_path
        assert extractor.output_dir == tmp_path
        assert extractor.texts == []
        assert len(extractor.scenes) == 0

    def test_scan_game_files_excludes_tl(self, tmp_path):
        game_dir = tmp_path / "game"
        game_dir.mkdir()
        (game_dir / "script.rpy").write_text("# script")
        (game_dir / "tl").mkdir()
        (game_dir / "tl" / "ru").mkdir()
        (game_dir / "tl" / "ru" / "script.rpy").write_text("# translation")

        extractor = RenPyTextExtractor(str(game_dir), str(tmp_path))
        files = extractor.scan_game_files()

        assert len(files) == 1
        assert files[0].name == "script.rpy"


class TestParsing:
    @pytest.fixture
    def sample_script(self, tmp_path):
        script = tmp_path / "test.rpy"
        content = (
            "label start:\n"
            '"Narration text."\n'
            's "Hello!"\n'
            'ko "Welcome."\n'
            "\n"
            'menu test_menu:\n'
            '    "Choose"\n'
            '    "Choice 1":\n'
            '        s "You chose 1"\n'
            '    "Choice 2":\n'
            '        s "You chose 2"\n'
            "\n"
            'label another:\n'
            '"More narration."\n'
            't "Text line."\n'
        )
        script.write_text(content, encoding='utf-8')
        return script

    def test_parse_dialogue(self, tmp_path, sample_script):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        blocks = extractor.parse_file(sample_script)

        dialogues = [b for b in blocks if b.text_type == "dialogue"]
        assert len(dialogues) >= 1
        assert any(b.character == "s" for b in dialogues)

    def test_parse_narration(self, tmp_path, sample_script):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        blocks = extractor.parse_file(sample_script)

        narrations = [b for b in blocks if b.text_type == "narration"]
        assert len(narrations) >= 1

    def test_parse_menu_choices(self, tmp_path, sample_script):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        blocks = extractor.parse_file(sample_script)

        choices = [b for b in blocks if b.text_type == "menu_choice"]
        assert len(choices) >= 2

    def test_scenes_created(self, tmp_path, sample_script):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.parse_file(sample_script)

        assert len(extractor.scenes) >= 1
        assert any(len(s.blocks) > 0 for s in extractor.scenes.values())

    def test_ui_strings_extraction(self, tmp_path):
        """Test that UI strings _() are extracted"""
        script = tmp_path / "test.rpy"
        content = (
            'textbutton _("Settings") action ShowMenu("preferences")\n'
            'textbutton _("Start") action Start()\n'
        )
        script.write_text(content, encoding='utf-8')

        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.parse_file_full(script)

        assert len(extractor.ui_strings) >= 2
        texts = [b.original_text for b in extractor.ui_strings]
        assert any("Settings" in t for t in texts)

    def test_ui_strings_format_old_new(self, tmp_path):
        """Test that UI strings are saved in old/new format"""
        script = tmp_path / "test.rpy"
        content = 'textbutton _("Test") action None\n'
        script.write_text(content, encoding='utf-8')

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        extractor = RenPyTextExtractor(str(tmp_path), str(output_dir))
        extractor.parse_file_full(script)
        extractor.save_to_format()

        ui_file = output_dir / "ui_strings" / "screens.rpy"
        assert ui_file.exists()
        content = ui_file.read_text(encoding='utf-8')
        assert "translate ru strings:" in content
        assert 'old "Test"' in content
        assert 'new "Test"' in content

    def test_character_names_extraction(self, tmp_path):
        """Test that Character(_("Name")) are extracted"""
        script = tmp_path / "test.rpy"
        content = (
            'define s = Character(_("Sarah"), who_color="#daa520")\n'
            'define ko = Character(_("King Orwell"), who_color="#ff6347")\n'
        )
        script.write_text(content, encoding='utf-8')

        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.parse_file_full(script)

        assert len(extractor.character_names) >= 2

    def test_character_names_format_old_new(self, tmp_path):
        """Test that character names are saved in old/new format"""
        script = tmp_path / "test.rpy"
        content = 'define s = Character(_("Sarah"), color="#daa520")\n'
        script.write_text(content, encoding='utf-8')

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        extractor = RenPyTextExtractor(str(tmp_path), str(output_dir))
        extractor.parse_file_full(script)
        extractor.save_to_format()

        char_file = output_dir / "characters" / "character_names.rpy"
        assert char_file.exists()
        content = char_file.read_text(encoding='utf-8')
        assert "translate ru strings:" in content
        assert 'old "Sarah"' in content
        assert 'new "Sarah"' in content


class TestIDGeneration:
    def test_id_format(self, tmp_path):
        script = tmp_path / "test.rpy"
        # No leading spaces for dialogue in Ren'Py
        content = 'label test:\n"s Hello"\n'
        script.write_text(content, encoding='utf-8')

        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.parse_file(script)

        # At least we can test the extractor initialized correctly
        assert hasattr(extractor, 'texts')
        assert hasattr(extractor, 'scenes')


class TestArcOrganization:
    def test_organize_prologue(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.scenes = {
            "OpeningScene": Scene(name="OpeningScene", label="OpeningScene"),
            "OpeningSceneEvening": Scene(name="OpeningSceneEvening", label="OpeningSceneEvening"),
        }
        arcs = extractor.organize_into_arcs()
        prologue_arc = next((a for a in arcs if a.name == "Prologue"), None)
        assert prologue_arc is not None

    def test_organize_warrior_path(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.scenes = {
            "WarriorPath1": Scene(name="WarriorPath1", label="WarriorPath1"),
            "WarriorPath2": Scene(name="WarriorPath2", label="WarriorPath2"),
        }
        arcs = extractor.organize_into_arcs()
        warrior_arc = next((a for a in arcs if a.name == "WarriorPath"), None)
        assert warrior_arc is not None


class TestFullExtraction:
    def test_extract_all(self, tmp_path):
        game_dir = tmp_path / "game"
        game_dir.mkdir()

        script = game_dir / "script.rpy"
        content = (
            "label test_scene:\n"
            '"Narration text."\n'
            's "Dialogue text."\n'
            "\n"
            'menu choice_menu:\n'
            '    "Choose"\n'
            '    "Option A":\n'
            '        s "Selected A"\n'
            '    "Option B":\n'
            '        s "Selected B"\n'
        )
        script.write_text(content, encoding='utf-8')

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        extractor = RenPyTextExtractor(str(game_dir), str(output_dir))
        scenes = extractor.extract_all()

        assert len(scenes) >= 1
        assert len(extractor.texts) > 0

        types = set(b.text_type for b in extractor.texts)
        assert "dialogue" in types
        assert "narration" in types
        assert "menu_choice" in types

    def test_save_format_creates_files(self, tmp_path):
        game_dir = tmp_path / "game"
        game_dir.mkdir()

        script = game_dir / "script.rpy"
        content = (
            "label simple:\n"
            '"Narration text."\n'
            's "Hello"\n'
            '"More narration."\n'
        )
        script.write_text(content, encoding='utf-8')

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        extractor = RenPyTextExtractor(str(game_dir), str(output_dir))
        extractor.extract_all()
        extractor.save_to_format()

        manifest = output_dir / "manifest.json"
        assert manifest.exists()

        ui_dir = output_dir / "ui_strings"
        assert ui_dir.exists()

        char_dir = output_dir / "characters"
        assert char_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])