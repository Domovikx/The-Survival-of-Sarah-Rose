import pytest
import tempfile
import os
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent))
from check_consistency import check_consistency, rebuild_from_chunks, parse_translate_blocks

@pytest.fixture
def sample_source():
    content = '''# TODO: Translation updated at 2026-05-08 00:19

# script.rpy:34
translate ru start_2b88e3eb:

    # "«Survival of Sarah Rose» is an epic fantasy game."
    "«Выживание Сары Роуз» — эпическая фэнтези-игра."


# script.rpy:309
translate ru OpeningScene_7a765a1f:

    # "Castle Reinmeer"
    "Замок Рейнмир"


# script.rpy:333
translate ru OpeningSceneFirstMorning_9e6c896e:

    # "Sarah wakes to the first beams of light."
    ""


'''
    return content

@pytest.fixture
def sample_manifest():
    return {
        "archives": {
            "Prologue": {
                "count": 3,
                "scenes": ["start", "OpeningScene", "OpeningSceneFirstMorning"]
            }
        },
        "total_scenes": 3,
        "total_lines": 19,
        "source_lines": 19
    }

@pytest.fixture
def sample_chunks(tmp_path):
    prologue_dir = tmp_path / "Prologue"
    prologue_dir.mkdir()

    (prologue_dir / "start.rpy").write_text('''translate ru start_2b88e3eb:

    # "«Survival of Sarah Rose» is an epic fantasy game."
    "«Выживание Сары Роуз» — эпическая фэнтези-игра."


''', encoding='utf-8')

    (prologue_dir / "OpeningScene.rpy").write_text('''translate ru OpeningScene_7a765a1f:

    # "Castle Reinmeer"
    "Замок Рейнмир"


''', encoding='utf-8')

    (prologue_dir / "OpeningSceneFirstMorning.rpy").write_text('''translate ru OpeningSceneFirstMorning_9e6c896e:

    # "Sarah wakes to the first beams of light."
    ""


''', encoding='utf-8')

    return tmp_path

class TestParseTranslateBlocks:
    def test_parse_basic(self, sample_source):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_source)
            temp_path = f.name

        try:
            blocks = parse_translate_blocks(Path(temp_path))
            assert "start_2b88e3eb" in blocks
            assert "OpeningScene_7a765a1f" in blocks
            assert "OpeningSceneFirstMorning_9e6c896e" in blocks
            assert len(blocks) == 3
        finally:
            os.unlink(temp_path)

    def test_parse_empty_lines(self, sample_source):
        blocks = parse_translate_blocks(Path(__file__))
        assert isinstance(blocks, dict)

class TestCheckConsistency:
    def test_valid_consistency(self, sample_source, sample_chunks, sample_manifest, tmp_path):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_source)
            source = f.name

        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(sample_manifest, f)

        try:
            result = check_consistency(source, str(sample_chunks), manifest_dir=str(tmp_path))
            assert result["valid"] == True
            assert result["missing_in_chunks_count"] == 0
            assert result["extra_in_chunks_count"] == 0
        finally:
            os.unlink(source)

    def test_missing_source(self, tmp_path):
        result = check_consistency("/nonexistent/source.rpy", str(tmp_path))
        assert result["valid"] == False
        assert "Source file not found" in result["error"]

    def test_missing_split_dir(self, sample_source):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_source)
            source = f.name

        try:
            result = check_consistency(source, "/nonexistent/split")
            assert result["valid"] == False
        finally:
            os.unlink(source)

    def test_missing_manifest(self, sample_source, tmp_path):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_source)
            source = f.name

        try:
            result = check_consistency(source, str(tmp_path))
            assert result["valid"] == False
            assert "manifest" in str(result.get("error", "")).lower() or "manifest" in str(result).lower()
        finally:
            os.unlink(source)

class TestRebuildFromChunks:
    def test_rebuild(self, sample_chunks, sample_manifest, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(sample_manifest, f)

        output_file = tmp_path / "rebuilt.rpy"
        result = rebuild_from_chunks(str(sample_chunks), str(tmp_path), str(output_file))

        assert result["valid"] == True
        assert output_file.exists()

        content = output_file.read_text(encoding='utf-8')
        assert 'start_2b88e3eb' in content
        assert 'OpeningScene_7a765a1f' in content
        assert 'Замок Рейнмир' in content

    def test_rebuild_missing_manifest(self, tmp_path):
        result = rebuild_from_chunks(str(tmp_path), str(tmp_path), str(tmp_path / "output.rpy"))
        assert result["valid"] == False

class TestEndToEnd:
    def test_full_workflow(self, sample_source, sample_chunks, sample_manifest, tmp_path):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_source)
            source = f.name

        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(sample_manifest, f)

        try:
            check_result = check_consistency(source, str(sample_chunks), manifest_dir=str(tmp_path))
            assert check_result["valid"] == True

            output_file = tmp_path / "rebuilt.rpy"
            rebuild_result = rebuild_from_chunks(str(sample_chunks), str(tmp_path), str(output_file))
            assert rebuild_result["valid"] == True
        finally:
            os.unlink(source)

    def test_translate_block_count_matches(self, sample_source, sample_chunks, sample_manifest, tmp_path):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(sample_source)
            source = f.name

        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(sample_manifest, f)

        try:
            result = check_consistency(source, str(sample_chunks), manifest_dir=str(tmp_path))

            # Translate blocks must match exactly
            assert result["missing_in_chunks_count"] == 0
            assert result["extra_in_chunks_count"] == 0

        finally:
            os.unlink(source)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])