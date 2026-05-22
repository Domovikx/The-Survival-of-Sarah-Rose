"""
Ren'Py Translation Deduplicator
================================
Удаляет дублирующиеся old/new пары в Ren'Py translation files.
В Ren'Py одна и та же строка old не может встречаться в разных файлах
одного перевода — это вызывает исключение.

Скрипт сканирует все .rpy файлы в game/tl/<lang>/,
находит одинаковые old строки в разных файлах,
оставляет первый экземпляр, удаляет дубликаты из остальных файлов.

Использование:
    python dedup_translations.py                    # дедупликация ru (по умолчанию)
    python dedup_translations.py --lang de          # другой язык
    python dedup_translations.py --dry-run          # предпросмотр
    python dedup_translations.py --verbose          # подробный вывод
    python dedup_translations.py --project /path    # указать проект
"""

import os
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

if sys.platform == 'win32' and sys.stdout.encoding and sys.stdout.encoding.lower() in ('cp1251', 'cp866'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


VERSION = 1


# ============================================================
# Parsing
# ============================================================

OLD_RE = re.compile(
    r'^[ \t]*old +"((?:[^"\\]|\\.)*)"[ \t]*$',
    re.MULTILINE,
)

NEW_RE = re.compile(
    r'^[ \t]*new +"((?:[^"\\]|\\.)*)"[ \t]*$',
    re.MULTILINE,
)


def parse_translate_blocks(text: str) -> list[tuple[int, str, str]]:
    """
    Парсит translate <lang> strings: блоки, возвращает список
    (line_number, old_text, new_text).
    Учитывает многострочные old/new (с конкатенацией).
    """
    results = []
    lines = text.split('\n')
    in_block = False
    current_old = None
    current_new = None
    old_lineno = None
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Определяем начало блока translate <lang> strings:
        if not in_block and stripped.startswith('translate ') and stripped.endswith('strings:'):
            in_block = True
            i += 1
            continue

        if not in_block:
            i += 1
            continue

        # Комментарий внутри блока — пропускаем
        if stripped.startswith('#'):
            i += 1
            continue

        # Пустая строка внутри блока — просто пропускаем
        if stripped == '':
            i += 1
            continue

        # Достигнут конец translate блока — начинается новый translate
        if stripped.startswith('translate '):
            if current_old is not None and current_new is not None:
                results.append((old_lineno, current_old, current_new))
                current_old = None
                current_new = None
                old_lineno = None
            in_block = True
            i += 1
            continue

        old_match = OLD_RE.match(line)
        new_match = NEW_RE.match(line)

        if old_match:
            # Если был предыдущий незавершённый — сохраняем
            if current_old is not None and current_new is not None:
                results.append((old_lineno, current_old, current_new))
            current_old = old_match.group(1)
            current_new = None
            old_lineno = i
        elif new_match:
            current_new = new_match.group(1)

        i += 1

    # Последняя пара
    if current_old is not None and current_new is not None:
        results.append((old_lineno, current_old, current_new))

    return results


# ============================================================
# Deduplication
# ============================================================

def find_all_entries(tl_dir: Path, lang: str) -> list[dict]:
    """
    Сканирует все .rpy файлы в tl/<lang>/ и собирает все old/new пары.
    Возвращает список словарей:
        {'file': Path, 'line': int, 'old': str, 'new': str, 'full_line': str}
    """
    entries = []
    rpy_files = sorted(tl_dir.rglob('*.rpy'))

    if not rpy_files:
        print(f"  [WARN] .rpy файлы не найдены в {tl_dir}")
        return entries

    for rpy_file in rpy_files:
        try:
            text = rpy_file.read_text(encoding='utf-8')
        except Exception:
            try:
                text = rpy_file.read_text(encoding='utf-8-sig')
            except Exception as e:
                print(f"  [ERROR] Не удалось прочитать {rpy_file}: {e}")
                continue

        pairs = parse_translate_blocks(text)
        for line_no, old_text, new_text in pairs:
            entries.append({
                'file': rpy_file,
                'line': line_no,
                'old': old_text,
                'new': new_text,
            })

    return entries


def find_duplicates(entries: list[dict]) -> dict[str, list[dict]]:
    """
    Группирует записи по old строке, возвращает только те,
    что встречаются >1 раза, отсортированные по файлу и строке.
    """
    groups: dict[str, list[dict]] = defaultdict(list)

    for entry in entries:
        key = entry['old']
        groups[key].append(entry)

    duplicates = {}
    for key, group in groups.items():
        if len(group) > 1:
            duplicates[key] = sorted(group, key=lambda e: (str(e['file']), e['line']))

    return duplicates


def deduplicate(
    tl_dir: Path,
    lang: str = 'ru',
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Основная функция дедупликации.

    Args:
        tl_dir: Путь к tl/<lang>/
        lang: Язык (используется только для заголовков)
        dry_run: Если True — только показать, не удалять
        verbose: Подробный вывод

    Returns:
        dict с ключами:
            'total_entries': всего найдено old/new пар
            'total_duplicates': всего дубликатов (включая первый)
            'duplicates_removed': сколько дубликатов удалено
            'files_modified': сколько файлов изменено
    """
    print(f"\n{'='*60}")
    print(f"  Ren'Py Translation Deduplicator v{VERSION}")
    print(f"{'='*60}")
    print(f"  Язык: {lang}")
    print(f"  Директория: {tl_dir}")
    print(f"  Режим: {'ПРЕДПРОСМОТР (без изменений)' if dry_run else 'ДЕДУПЛИКАЦИЯ'}")
    print(f"{'='*60}\n")

    if not tl_dir.exists():
        print(f"  [ERROR] Директория не найдена: {tl_dir}")
        return {'total_entries': 0, 'total_duplicates': 0, 'duplicates_removed': 0, 'files_modified': 0}

    # Собираем все записи
    entries = find_all_entries(tl_dir, lang)
    print(f"  Найдено old/new пар: {len(entries)}")

    if not entries:
        print("  Нет записей для обработки.")
        return {'total_entries': 0, 'total_duplicates': 0, 'duplicates_removed': 0, 'files_modified': 0}

    # Находим дубликаты
    duplicates = find_duplicates(entries)
    total_dup_groups = len(duplicates)
    total_dup_entries = sum(len(group) for group in duplicates.values())

    print(f"  Дублирующихся old строк: {total_dup_groups}")
    print(f"  Всего дублирующихся вхождений: {total_dup_entries}")

    if total_dup_entries == 0:
        print("\n  Дубликаты не найдены — всё чисто! [OK]")
        return {'total_entries': len(entries), 'total_duplicates': 0, 'duplicates_removed': 0, 'files_modified': 0}

    # Собираем статистику по файлам
    files_to_modify: dict[str, list[tuple[int, str]]] = {}

    for old_text, group in sorted(duplicates.items()):
        # Первый экземпляр — оставляем
        first = group[0]
        rest = group[1:]

        print(f"\n  old: {old_text[:80]}{'...' if len(old_text) > 80 else ''}")
        print(f"    [KEEP] {first['file'].relative_to(tl_dir.parent.parent)}:{first['line']+1}")

        for entry in rest:
            rel_path = entry['file'].relative_to(tl_dir.parent.parent)
            print(f"    [DUPLICATE] {rel_path}:{entry['line']+1}")

            key = str(entry['file'])
            if key not in files_to_modify:
                files_to_modify[key] = []
            files_to_modify[key].append((entry['line'], old_text))

    print(f"\n  Файлов с дубликатами: {len(files_to_modify)}")

    if dry_run:
        print(f"\n  Предпросмотр завершён. Будет удалено {total_dup_entries - total_dup_groups} дублирующихся записей.")
        return {
            'total_entries': len(entries),
            'total_duplicates': total_dup_entries,
            'duplicates_removed': 0,
            'files_modified': 0,
        }

    # Удаляем дубликаты
    removed_count = 0
    modified_count = 0

    for filepath_str, lines_to_remove in sorted(files_to_modify.items()):
        filepath = Path(filepath_str)
        rel = filepath.relative_to(tl_dir.parent.parent)

        try:
            text = filepath.read_text(encoding='utf-8')
        except Exception:
            try:
                text = filepath.read_text(encoding='utf-8-sig')
            except Exception as e:
                print(f"  [ERROR] Не удалось прочитать для записи {filepath}: {e}")
                continue

        lines = text.split('\n')

        # Сортируем строки для удаления в обратном порядке (с конца файла)
        # чтобы не сбивать номера строк
        lines_to_remove_sorted = sorted(
            set((ln, old) for ln, old in lines_to_remove),
            key=lambda x: -x[0],
        )

        file_modified = False

        for line_no, old_text in lines_to_remove_sorted:
            # Проверяем, что строка действительно содержит old "..." 
            if OLD_RE.match(lines[line_no]):
                # Удаляем эту строку и следующую за ней new строку
                # Находим old строку и соответствующую new строку
                delete_lines = {line_no}

                # Ищем new на следующей строке
                if line_no + 1 < len(lines) and NEW_RE.match(lines[line_no + 1]):
                    delete_lines.add(line_no + 1)

                # Удаляем строки в обратном порядке
                for ln in sorted(delete_lines, reverse=True):
                    del lines[ln]

                file_modified = True
                removed_count += 1

        if file_modified:
            # Чистим множественные пустые строки (оставляем максимум 2 подряд)
            cleaned = []
            empty_count = 0
            for line in lines:
                if line.strip() == '':
                    empty_count += 1
                    if empty_count <= 2:
                        cleaned.append(line)
                else:
                    empty_count = 0
                    cleaned.append(line)

            new_text = '\n'.join(cleaned)
            filepath.write_text(new_text, encoding='utf-8')
            modified_count += 1
            if verbose:
                print(f"  [MODIFIED] {rel}")

    result = {
        'total_entries': len(entries),
        'total_duplicates': total_dup_entries,
        'duplicates_removed': removed_count,
        'files_modified': modified_count,
    }

    print(f"\n{'='*60}")
    print(f"  Результат:")
    print(f"    Всего old/new пар: {result['total_entries']}")
    print(f"    Дублирующихся вхождений: {result['total_duplicates']}")
    print(f"    Удалено дубликатов: {result['duplicates_removed']}")
    print(f"    Изменено файлов: {result['files_modified']}")
    print(f"{'='*60}\n")

    return result


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Дедупликация Ren'Py переводов — удаление повторяющихся old строк"
    )
    parser.add_argument(
        '--lang', '-l',
        default='ru',
        help='Язык перевода (по умолчанию: ru)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Предпросмотр без изменений'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод'
    )
    parser.add_argument(
        '--project', '-p',
        help='Путь к корню проекта Ren\'Py (где лежит game/)'
    )

    args = parser.parse_args()

    # Определяем tl_dir
    if args.project:
        project_dir = Path(args.project)
    else:
        script_dir = Path(__file__).parent
        project_dir = script_dir.parent.parent.parent
        if not (project_dir / 'game').exists():
            project_dir = project_dir.parent

    tl_dir = project_dir / 'game' / 'tl' / args.lang

    if not tl_dir.exists():
        print(f"ERROR: Директория не найдена: {tl_dir}")
        sys.exit(1)

    result = deduplicate(
        tl_dir,
        lang=args.lang,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if result['duplicates_removed'] > 0 or (args.dry_run and result['total_duplicates'] > 0):
        pass  # Всё выведено


if __name__ == '__main__':
    main()
