"""
Ren'Py Cache Cleaner
====================
Удаляет файлы кэша Ren'Py (*.rpyc, __pycache__/, *.log)
для решения проблем с устаревшими переводами и отладки.

Использование:
    python clear_cache.py              # Очистить game/
    python clear_cache.py /path/to/game  # Указать путь
    python clear_cache.py --dry-run    # Показать что будет удалено без удаления
    python clear_cache.py --verbose    # Подробный вывод
"""

import os
import sys
import argparse
from pathlib import Path


VERSION = 1

# Расширения файлов для удаления
CACHE_EXTENSIONS = {'.rpyc', '.log', '.tmp'}

# Имена директорий для удаления
CACHE_DIRS = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}


def find_cache_files(game_dir: Path) -> list[Path]:
    """Находит все файлы кэша в директории игры."""
    cache_files = []
    for root, dirs, files in os.walk(game_dir):
        # Пропускаем .git
        dirs[:] = [d for d in dirs if d != '.git']

        root_path = Path(root)

        # Файлы с расширениями кэша
        for f in files:
            if Path(f).suffix.lower() in CACHE_EXTENSIONS:
                cache_files.append(root_path / f)

        # Директории кэша
        for d in dirs:
            if d in CACHE_DIRS:
                cache_dir = root_path / d
                for cache_file in cache_dir.rglob('*'):
                    if cache_file.is_file():
                        cache_files.append(cache_file)

    return cache_files


def find_cache_dirs(game_dir: Path) -> list[Path]:
    """Находит все директории кэша (пустые после удаления файлов)."""
    cache_dirs = []
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d != '.git']
        for d in dirs:
            if d in CACHE_DIRS:
                cache_dirs.append(Path(root) / d)
    return cache_dirs


def size_str(size_bytes: int) -> str:
    """Форматирует размер в читаемый вид."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def clear_cache(game_dir: Path, dry_run: bool = False, verbose: bool = False) -> dict:
    """
    Очищает кэш Ren'Py.

    Args:
        game_dir: Путь к директории игры
        dry_run: Если True — только показать, не удалять
        verbose: Подробный вывод

    Returns:
        dict с ключами: 'files_removed', 'dirs_removed', 'space_freed'
    """
    if not game_dir.exists():
        print(f"ERROR: Директория не найдена: {game_dir}")
        return {'files_removed': 0, 'dirs_removed': 0, 'space_freed': 0}

    # Проверяем, что game_dir — это действительно директория игры
    if not (game_dir / "game").exists() and not any(game_dir.glob("*.rpy")):
        print(f"WARNING: {game_dir} не выглядит как директория игры Ren'Py")

    cache_files = find_cache_files(game_dir)
    cache_dirs = find_cache_dirs(game_dir)

    total_size = sum(f.stat().st_size for f in cache_files if f.exists())
    results = {
        'files_removed': 0,
        'dirs_removed': 0,
        'space_freed': 0,
    }

    if not cache_files and not cache_dirs:
        print("Кэш не найден — всё чисто! ✓")
        return results

    print(f"\n{'='*50}")
    print(f"  Ren'Py Cache Cleaner v{VERSION}")
    print(f"{'='*50}")
    print(f"  Директория: {game_dir}")
    print(f"  Файлов кэша: {len(cache_files)}")
    print(f"  Директорий кэша: {len(cache_dirs)}")
    print(f"  Место для освобождения: {size_str(total_size)}")
    if dry_run:
        print(f"  Режим: ПРЕВПРОСМОТР (без удаления)")
    print(f"{'='*50}\n")

    # Удаление файлов
    for f in sorted(cache_files):
        rel = f.relative_to(game_dir) if game_dir in f.parents or f == game_dir else f
        if verbose or not dry_run:
            print(f"  [{'DRY-RUN' if dry_run else 'DEL'}] {rel}")
        if not dry_run:
            try:
                f.unlink()
                results['files_removed'] += 1
            except OSError as e:
                print(f"    ОШИБКА: {e}")

    # Удаление пустых директорий кэша
    for d in sorted(cache_dirs, key=str, reverse=True):
        rel = d.relative_to(game_dir) if game_dir in d.parents or d == game_dir else d
        if not dry_run:
            try:
                if d.exists() and not any(d.iterdir()):
                    d.rmdir()
                    results['dirs_removed'] += 1
                    if verbose:
                        print(f"  [DEL DIR] {rel}")
                elif verbose:
                    print(f"  [SKIP DIR] {rel} (не пуста)")
            except OSError as e:
                if verbose:
                    print(f"  [SKIP DIR] {rel}: {e}")

    results['space_freed'] = total_size if not dry_run else 0

    print(f"\n{'='*50}")
    if dry_run:
        print(f"  Превью завершено. Будет удалено {len(cache_files)} файлов, "
              f"освобождено {size_str(total_size)}")
    else:
        print(f"  Удалено файлов: {results['files_removed']}")
        print(f"  Удалено директорий: {results['dirs_removed']}")
        print(f"  Освобождено: {size_str(results['space_freed'])}")
    print(f"{'='*50}\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Очистка кэша Ren'Py (*.rpyc, __pycache__, *.log)"
    )
    parser.add_argument(
        'gamedir',
        nargs='?',
        default='.',
        help='Путь к директории игры (по умолчанию: текущая)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Показать что будет удалено без фактического удаления'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод'
    )

    args = parser.parse_args()

    # Определяем game_dir
    script_dir = Path(__file__).parent
    if args.gamedir == '.':
        # Автоопределение: поднимаемся до корня проекта
        game_dir = script_dir.parent.parent.parent / 'game'
        if not game_dir.exists():
            game_dir = script_dir.parent.parent.parent.parent / 'game'
    else:
        game_dir = Path(args.gamedir)

    clear_cache(game_dir, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == '__main__':
    main()