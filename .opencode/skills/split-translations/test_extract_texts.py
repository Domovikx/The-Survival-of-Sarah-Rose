"""
Tests for extract_texts.py
"""

import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from extract_texts import RenPyTextExtractor, TextBlock, Scene, Arc


class TestTextBlockCreation:
    """Test TextBlock dataclass"""

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
        assert block.label == "test_label"
        assert block.character == "s"
        assert block.original_text == "Hello world"

    def test_text_block_default_values(self):
        block = TextBlock(
            id="test123",
            label="label",
            source_file="file.rpy",
            line_number=1,
            text_type="narration"
        )
        assert block.character is None
        assert block.original_text == ""
        assert block.context_before == []


class TestRenPyTextExtractorInit:
    """Test RenPyTextExtractor initialization"""

    def test_init(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        assert extractor.game_dir == tmp_path
        assert extractor.output_dir == tmp_path
        assert extractor.texts == []
        assert extractor.scenes == {}

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
    """Test parsing of Ren'Py scripts"""

    @pytest.fixture
    def sample_script(self, tmp_path):
        script = tmp_path / "test.rpy"
        content = (
            "label start:\n"
            '"This is narration."\n'
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
        assert any("narration" in b.original_text.lower() for b in narrations)

    def test_parse_menu_choices(self, tmp_path, sample_script):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        blocks = extractor.parse_file(sample_script)

        choices = [b for b in blocks if b.text_type == "menu_choice"]
        assert len(choices) >= 2
        assert any("Choice" in b.original_text for b in choices)

    def test_scenes_created(self, tmp_path, sample_script):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.parse_file(sample_script)

        assert len(extractor.scenes) >= 1
        assert any(len(s.blocks) > 0 for s in extractor.scenes.values())

    def test_empty_lines_ignored(self, tmp_path, sample_script):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        blocks = extractor.parse_file(sample_script)

        for block in blocks:
            if block.text_type in ["dialogue", "narration", "menu_choice"]:
                assert block.original_text.strip() != ""


class TestIDGeneration:
    """Test unique ID generation"""

    def test_id_format(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        block = extractor._create_block(
            label="test",
            text_type="dialogue",
            character="s",
            original_text="Hello",
            line_number=1,
            source_file="test.rpy"
        )

        assert block.id.startswith("test_")
        assert len(block.id.split("_")[1]) == 8

    def test_different_texts_different_ids(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))

        block1 = extractor._create_block(
            label="test", text_type="dialogue", character="s",
            original_text="Text 1", line_number=1, source_file="test.rpy"
        )
        block2 = extractor._create_block(
            label="test", text_type="dialogue", character="s",
            original_text="Text 2", line_number=2, source_file="test.rpy"
        )

        assert block1.id != block2.id


class TestArcOrganization:
    """Test scene organization into arcs"""

    def test_organize_prologue(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.scenes = {
            "OpeningScene": Scene(name="OpeningScene", label="OpeningScene"),
            "OpeningSceneEvening": Scene(name="OpeningSceneEvening", label="OpeningSceneEvening"),
        }

        arcs = extractor.organize_into_arcs()
        prologue_arc = next((a for a in arcs if a.name == "Prologue"), None)

        assert prologue_arc is not None
        assert len(prologue_arc.scenes) == 2

    def test_organize_warrior_path(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.scenes = {
            "WarriorPath1": Scene(name="WarriorPath1", label="WarriorPath1"),
            "WarriorPath2": Scene(name="WarriorPath2", label="WarriorPath2"),
            "WarriorRahayal1": Scene(name="WarriorRahayal1", label="WarriorRahayal1"),
        }

        arcs = extractor.organize_into_arcs()
        warrior_arc = next((a for a in arcs if a.name == "WarriorPath"), None)

        assert warrior_arc is not None
        assert len(warrior_arc.scenes) == 3

    def test_organize_union_kingdom(self, tmp_path):
        extractor = RenPyTextExtractor(str(tmp_path), str(tmp_path))
        extractor.scenes = {
            "UnionKingdom1": Scene(name="UnionKingdom1", label="UnionKingdom1"),
            "UnionKingdom2": Scene(name="UnionKingdom2", label="UnionKingdom2"),
            "UnionLoop": Scene(name="UnionLoop", label="UnionLoop"),
        }

        arcs = extractor.organize_into_arcs()
        union_arc = next((a for a in arcs if a.name == "UnionKingdom"), None)

        assert union_arc is not None
        assert len(union_arc.scenes) == 3


class TestFullExtraction:
    """Test full extraction pipeline"""

    def test_extract_all(self, tmp_path):
        game_dir = tmp_path / "game"
        game_dir.mkdir()

        script = game_dir / "script.rpy"
        content = (
            "label test_scene:\n"
            '"Narration text."\n'
            's "Dialogue text."\n'
            't "Another dialogue."\n'
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

    def test_save_renpy_format(self, tmp_path):
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

        assert len(extractor.texts) >= 2

        extractor.save_to_format('renpy')

        manifest = output_dir / "manifest.json"
        assert manifest.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])