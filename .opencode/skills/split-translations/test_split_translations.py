import pytest
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from split_translations import split_translations, verify_consistency, get_archive, parse_rpy, get_scene_name

@pytest.fixture
def sample_rpy():
    content = '''# TODO: Translation updated at 2026-05-08 00:19

# script.rpy:34
translate ru start_2b88e3eb:

    # "«Survival of Sarah Rose» is an epic fantasy game. TSSR development is still ongoing."
    "«Выживание Сары Роуз» — эпическая фэнтези-игра. Разработка TSSR всё ещё продолжается."

# script.rpy:309
translate ru OpeningScene_7a765a1f:

    # "Castle Reinmeer"
    "Замок Рейнмир"

# script.rpy:333
translate ru OpeningSceneFirstMorning_9e6c896e:

    # "Sarah wakes to the first beams of light breaking through her curtains."
    ""

# script.rpy:702
translate ru OpeningSceneFirstMorning_2c781ead_1:

    # "She watches herself in the mirror as she tries out a series of different dresses."
    ""
'''
    return content

class TestGetArchive:
    def test_prologue_scenes(self):
        assert get_archive("start") == "Prologue"
        assert get_archive("OpeningScene") == "Prologue"
        assert get_archive("OpeningSceneSequence2") == "Prologue"

    def test_warrior_scenes(self):
        assert get_archive("WarriorQueen1") == "WarriorPath"
        assert get_archive("HyralOrc") == "WarriorPath"
        assert get_archive("GallowCreek1") == "WarriorPath"

    def test_mage_scenes(self):
        assert get_archive("MagePath") == "MagePath"
        assert get_archive("TheBlackMonolithMage1") == "MagePath"
        assert get_archive("TheHollowWorldWarrior1") == "MagePath"

    def test_marion_scenes(self):
        assert get_archive("MarionPath") == "MarionPath"
        assert get_archive("WarCouncil") == "MarionPath"
        assert get_archive("VargaPath1") == "MarionPath"

    def test_sailor_scenes(self):
        assert get_archive("SailorPath1") == "SailorPath"
        assert get_archive("BelmontTalkback") == "SailorPath"

    def test_other_scenes(self):
        assert get_archive("SomeUnknownScene") == "Other"
        assert get_archive("RandomName") == "Other"

class TestParseRpy:
    def test_parse_blocks(self, sample_rpy):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_rpy)
            temp_path = f.name

        try:
            blocks = parse_rpy(Path(temp_path))
            assert "start_2b88e3eb" in blocks
            assert "OpeningScene_7a765a1f" in blocks
            assert "OpeningSceneFirstMorning_2c781ead_1" in blocks
            assert len(blocks) == 4
        finally:
            os.unlink(temp_path)

    def test_parse_blocks_with_numbered_scenes(self):
        """Test that parse_rpy correctly handles scene names with trailing numbers like HyralOrc2."""
        content = '''translate ru HyralOrc_c3fc8560:

    # "Original text"
    "Translated"

translate ru HyralOrc2_d4cd0950:

    # "Another text"
    "Another translated"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            blocks = parse_rpy(Path(temp_path))
            assert "HyralOrc_c3fc8560" in blocks, "Basic scene should be parsed"
            assert "HyralOrc2_d4cd0950" in blocks, "Numbered scene should be parsed"
            assert len(blocks) == 2
        finally:
            os.unlink(temp_path)

    def test_parse_real_file_all_blocks_parsed(self):
        """Test against the actual translation file to ensure all blocks are parsed."""
        source = Path(__file__).parent.parent.parent.parent / "game" / "tl" / "ru" / "script" / "split" / "Prologue" / "start.rpy"
        if source.exists():
            blocks = parse_rpy(source)
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read()
            import re
            expected = len(re.findall(r'^translate ru [^:]+:', content, re.MULTILINE))
            assert len(blocks) == expected, f"Expected {expected} blocks but got {len(blocks)}"

class TestGetSceneName:
    def test_extracts_scene_name(self):
        assert get_scene_name("start") == "start"
        assert get_scene_name("OpeningSceneFirstMorning") == "OpeningSceneFirstMorning"
        assert get_scene_name("OpeningSceneFirstMorning_2") == "OpeningSceneFirstMorning"

    def test_scene_name_with_trailing_number(self):
        assert get_scene_name("HyralOrc2_c3fc8560") == "HyralOrc2"
        assert get_scene_name("SailorPath10_b1646d8b") == "SailorPath10"
        assert get_scene_name("TheOldRoad5_1336f621") == "TheOldRoad5"
        assert get_scene_name("UnionKingdom2_7f7d77be") == "UnionKingdom2"

class TestSplitTranslations:
    def test_split_creates_directories(self, sample_rpy):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_rpy)
            source = f.name

        output_dir = tempfile.mkdtemp()

        try:
            manifest = split_translations(source, output_dir)

            assert Path(output_dir, "Prologue").is_dir()
            assert manifest["total_scenes"] == 4

            assert Path(output_dir, "Prologue", "start.rpy").exists()
            assert Path(output_dir, "Prologue", "OpeningScene.rpy").exists()
            assert Path(output_dir, "Prologue", "OpeningSceneFirstMorning.rpy").exists()
        finally:
            os.unlink(source)
            import shutil
            shutil.rmtree(output_dir)

    def test_verify_consistency(self, sample_rpy):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_rpy)
            source = f.name

        output_dir = tempfile.mkdtemp()

        try:
            split_translations(source, output_dir)
            result = verify_consistency(source, output_dir)

            assert result["valid"] == True
        finally:
            os.unlink(source)
            import shutil
            shutil.rmtree(output_dir)

class TestDuplicateScenes:
    @pytest.fixture
    def sample_with_duplicates(self):
        content = '''# script.rpy:100
translate ru Scene_abc123:

    # "Original text 1"
    "Translated 1"

# script.rpy:200
translate ru Scene_def456_1:

    # "Original text 2"
    "Translated 2"

# script.rpy:300
translate ru Scene_def456_2:

    # "Original text 3"
    "Translated 3"

# script.rpy:400
translate ru Scene_ghi789_1:

    # "Original text 4"
    "Translated 4"
'''
        return content

    def test_duplicate_scenes_merged(self, sample_with_duplicates):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_with_duplicates)
            source = f.name

        output_dir = tempfile.mkdtemp()

        try:
            manifest = split_translations(source, output_dir)

            # Scene appears, should be in one file (Other archive since no prefix matches)
            scene_file = Path(output_dir) / "Other" / "Scene.rpy"
            assert scene_file.exists(), f"Scene with duplicates should be in one file at {scene_file}"

            with open(scene_file, encoding='utf-8') as f:
                content = f.read()

            # All blocks should be present
            assert 'Scene_def456_1' in content, "Block _1 should be in merged file"
            assert 'Scene_def456_2' in content, "Block _2 should be in merged file"
            assert 'Original text 2' in content, "Original text from block _1"
            assert 'Original text 3' in content, "Original text from block _2"

            # All scenes should be in manifest
            all_scenes = []
            for archive_data in manifest["archives"].values():
                all_scenes.extend(archive_data["scenes"])
            assert "Scene" in all_scenes

        finally:
            os.unlink(source)
            import shutil
            shutil.rmtree(output_dir)

    def test_duplicate_count_matches(self, sample_with_duplicates):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_with_duplicates)
            source = f.name

        output_dir = tempfile.mkdtemp()

        try:
            split_translations(source, output_dir)

            # Count translate blocks in source
            source_blocks = 0
            with open(source, encoding='utf-8') as f:
                for line in f:
                    if line.startswith('translate ru '):
                        source_blocks += 1

            # Count translate blocks in chunks
            chunk_blocks = 0
            for rpy in Path(output_dir).rglob('*.rpy'):
                with open(rpy, encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('translate ru '):
                            chunk_blocks += 1

            assert source_blocks == chunk_blocks, f"Blocks mismatch: source={source_blocks}, chunks={chunk_blocks}"

        finally:
            os.unlink(source)
            import shutil
            shutil.rmtree(output_dir)

class TestEndToEnd:
    def test_full_workflow(self, sample_rpy):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_rpy)
            source = f.name

        output_dir = tempfile.mkdtemp()

        try:
            manifest = split_translations(source, output_dir)

            result = verify_consistency(source, output_dir)
            assert result["valid"] == True

            for archive, data in manifest["archives"].items():
                for scene in data["scenes"]:
                    scene_path = Path(output_dir) / archive / f"{scene}.rpy"
                    assert scene_path.exists(), f"Missing: {scene_path}"
        finally:
            os.unlink(source)
            import shutil
            shutil.rmtree(output_dir)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])