import pytest
import tempfile
import os
from pathlib import Path
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GAME_DIR = SCRIPT_DIR.parent.parent.parent
SPLIT_DIR = str(GAME_DIR / "game" / "tl" / "ru" / "script" / "split")
SCRIPT_PATH = str(GAME_DIR / "game" / "script.rpy")

sys.path.insert(0, str(SCRIPT_DIR))
from find_untranslated import find_empty_translations, find_missing_scenes, check_manifest


class TestFindEmptyTranslations:
    def test_known_empty_file(self):
        """Test against the known file with empty translations: AskingRazaphelQuestionsMage.rpy"""
        result = find_empty_translations(SPLIT_DIR)

        found_asking = False
        for archive, files in result.get("empty_blocks", {}).items():
            for entry in files:
                if "AskingRazaphelQuestionsMage.rpy" in entry["file"]:
                    found_asking = True
                    assert "empty_count" in entry
                    assert entry["empty_count"] > 0
                    break
            if found_asking:
                break

        assert found_asking, f"Expected to find empty blocks in AskingRazaphelQuestionsMage.rpy. Found {result.get('empty_count', 0)} empty blocks total."

    def test_returns_all_fields(self):
        result = find_empty_translations(SPLIT_DIR)
        assert "total_files" in result
        assert "total_blocks" in result
        assert "empty_blocks" in result
        assert "files_with_empties" in result
        assert "empty_count" in result

    def test_empty_blocks_format(self):
        result = find_empty_translations(SPLIT_DIR)
        assert isinstance(result["empty_blocks"], dict)
        for archive, files in result.get("empty_blocks", {}).items():
            assert isinstance(archive, str)
            for entry in files:
                assert "file" in entry
                assert "empty_count" in entry
                assert isinstance(entry["empty_count"], int)

    def test_nonexistent_dir(self):
        result = find_empty_translations("/nonexistent/path")
        assert result["valid"] == False
        assert "error" in result

    def test_verbose_flag(self):
        result = find_empty_translations(SPLIT_DIR, verbose=True)
        assert result["valid"] == True


class TestFindMissingScenes:
    def test_script_exists(self):
        result = find_missing_scenes(SCRIPT_PATH, SPLIT_DIR)
        assert result["valid"] == True
        assert result["total_labels"] > 200

    def test_nonexistent_script(self):
        result = find_missing_scenes("/nonexistent/script.rpy", SPLIT_DIR)
        assert result["valid"] == False

    def test_nonexistent_split(self):
        result = find_missing_scenes(SCRIPT_PATH, "/nonexistent/split")
        assert result["valid"] == False

    def test_excludes_start_and_splashscreen(self):
        result = find_missing_scenes(SCRIPT_PATH, SPLIT_DIR)
        missing = result.get("missing_scenes", [])
        assert "start" not in missing
        assert "splashscreen" not in missing


class TestCheckManifest:
    def test_manifest_exists(self):
        result = check_manifest(SPLIT_DIR)
        if result.get("valid"):
            assert "archives" in result

    def test_nonexistent_dir(self):
        result = check_manifest("/nonexistent")
        assert result["valid"] == False

    def test_manifest_returns_structure(self):
        result = check_manifest(SPLIT_DIR)
        if result.get("valid"):
            assert "total_scenes" in result or "archives" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])