"""
Tests for clear_cache.py
=========================
Проверяем что кэш-файлы корректно находим и удаляем.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

sys_path_backup = None


def setup_module():
    global sys_path_backup
    sys_path_backup = __import__('sys').path.copy()
    __import__('sys').path.insert(0, str(Path(__file__).parent))


def teardown_module():
    __import__('sys').path = sys_path_backup


from clear_cache import (
    clear_cache, find_cache_files, find_cache_dirs,
    CACHE_EXTENSIONS, CACHE_DIRS, size_str, VERSION,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def tmp_game_dir():
    """Создаёт временную директорию с имитацией игры и кэша."""
    d = Path(tempfile.mkdtemp())
    game = d / "game"
    game.mkdir()

    # Обычные файлы игры — НЕ должны удаляться
    (game / "script.rpy").write_text('label start:\n    "Hello"\n')
    (game / "screens.rpy").write_text('screen test:\n    pass\n')
    (game / "options.rpy").write_text('## Options\n')
    (game / "gui.rpy").write_text('## GUI\n')

    # Кэш-файлы — ДОЛЖНЫ удаляться
    (game / "script.rpyc").write_bytes(b'\x00\x00\x00')
    (game / "screens.rpyc").write_bytes(b'\x00\x00\x00')
    (game / "error.log").write_text('Traceback...\n')

    # __pycache__ директории — ДОЛЖНЫ удаляться
    pycache = game / "__pycache__"
    pycache.mkdir()
    (pycache / "script.cpython-314.pyc").write_bytes(b'\x00')
    (pycache / "screens.cpython-314.pyc").write_bytes(b'\x00')

    # Вложенная структура
    subdir = game / "submod"
    subdir.mkdir()
    (subdir / "module.rpyc").write_bytes(b'\x00')
    sub_pycache = subdir / "__pycache__"
    sub_pycache.mkdir()
    (sub_pycache / "module.cpython-314.pyc").write_bytes(b'\x00')

    # .pytest_cache — ДОЛЖНА удаляться
    pytest_cache = game / ".pytest_cache"
    pytest_cache.mkdir()
    (pytest_cache / "CACHEDIR.TAG").write_text("Signature: 8a477f597d28d172789f06886806bc55")

    yield d

    shutil.rmtree(d, ignore_errors=True)


# ============================================================
# Unit Tests: find_cache_files
# ============================================================

class TestFindCacheFiles:

    def test_finds_rpyc_files(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        files = find_cache_files(game)
        names = [f.name for f in files]
        assert "script.rpyc" in names
        assert "screens.rpyc" in names
        assert "module.rpyc" in names

    def test_finds_log_files(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        files = find_cache_files(game)
        names = [f.name for f in files]
        assert "error.log" in names

    def test_finds_pycache_files(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        files = find_cache_files(game)
        names = [f.name for f in files]
        assert "script.cpython-314.pyc" in names
        assert "module.cpython-314.pyc" in names

    def test_ignores_actual_rpy_files(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        files = find_cache_files(game)
        names = [f.name for f in files]
        assert "script.rpy" not in names
        assert "screens.rpy" not in names

    def test_ignores_git_directory(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        git_dir = game / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config")
        (git_dir / "hooks").mkdir()
        files = find_cache_files(game)
        assert not any(".git" in str(f) for f in files)


# ============================================================
# Unit Tests: find_cache_dirs
# ============================================================

class TestFindCacheDirs:

    def test_finds_pycache_dirs(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        dirs = find_cache_dirs(game)
        dir_names = [d.name for d in dirs]
        assert "__pycache__" in dir_names

    def test_finds_pytest_cache_dirs(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        dirs = find_cache_dirs(game)
        dir_names = [d.name for d in dirs]
        assert ".pytest_cache" in dir_names


# ============================================================
# Unit Tests: clear_cache
# ============================================================

class TestClearCache:

    def test_dry_run_does_not_delete(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        rpyc = game / "script.rpyc"
        assert rpyc.exists()

        clear_cache(game, dry_run=True)
        # Файл всё ещё должен существовать
        assert rpyc.exists()

    def test_actual_delete_removes_rpyc(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        rpyc = game / "script.rpyc"
        assert rpyc.exists()

        result = clear_cache(game, dry_run=False)
        assert not rpyc.exists()
        assert result['files_removed'] >= 1

    def test_actual_delete_removes_logs(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        log = game / "error.log"
        assert log.exists()

        clear_cache(game, dry_run=False)
        assert not log.exists()

    def test_actual_delete_removes_pycache(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        pycache = game / "__pycache__"
        assert pycache.exists()

        clear_cache(game, dry_run=False)
        assert not pycache.exists()

    def test_does_not_delete_rpy_files(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        rpy = game / "script.rpy"

        clear_cache(game, dry_run=False)
        assert rpy.exists(), "Файлы .rpy не должны удаляться!"

    def test_does_not_delete_screens_rpy(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        screens = game / "screens.rpy"

        clear_cache(game, dry_run=False)
        assert screens.exists(), "Файлы .rpy не должны удаляться!"

    def test_returns_correct_counts(self, tmp_game_dir):
        game = tmp_game_dir / "game"
        result = clear_cache(game, dry_run=False)

        assert result['files_removed'] > 0
        assert result['space_freed'] >= 0


# ============================================================
# Utility Tests
# ============================================================

class TestUtilities:

    def test_size_str_bytes(self):
        assert size_str(100) == "100 B"

    def test_size_str_kb(self):
        assert size_str(2048) == "2.0 KB"

    def test_size_str_mb(self):
        assert size_str(1048576) == "1.0 MB"

    def test_version_is_int(self):
        assert isinstance(VERSION, int)
        assert VERSION == 1


# ============================================================
# Integration: full clean then verify no cache left
# ============================================================

class TestIntegration:

    def test_full_clean_leaves_no_cache(self, tmp_game_dir):
        game = tmp_game_dir / "game"

        # Убеждаемся что кэш есть
        assert len(find_cache_files(game)) > 0

        # Чистим
        result = clear_cache(game, dry_run=False)

        # Убеждаемся что кэша нет
        remaining = find_cache_files(game)
        assert len(remaining) == 0, f"Остались файлы кэша: {remaining}"

        # Убеждаемся что .rpy файлы на месте
        assert (game / "script.rpy").exists()
        assert (game / "screens.rpy").exists()