"""
Deduplication Script
Удаляет дубликаты из готовых translation файлов
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class TranslationEntry:
    block_id: str
    old_text: str
    new_text: str
    line_start: int
    line_end: int


def parse_translate_block(lines: List[str], start_idx: int) -> TranslationEntry:
    """Парсит один блок translate"""
    block_id_match = re.match(r'translate ru (\S+):', lines[start_idx])
    if not block_id_match:
        return None

    block_id = block_id_match.group(1)
    old_text = ""
    new_text = ""
    line_start = start_idx

    # Ищем old "..." и new "..." в блоке
    i = start_idx + 1
    while i < len(lines) and lines[i].strip():
        old_match = re.match(r'\s+old "((?:[^"\\]|\\.)*)"', lines[i])
        if old_match:
            old_text = old_match.group(1)

        new_match = re.match(r'\s+new "((?:[^"\\]|\\.)*)"', lines[i])
        if new_match:
            new_text = new_match.group(1)

        # Конец блока
        if re.match(r'\s*$', lines[i]) or re.match(r'translate ', lines[i]):
            break
        i += 1

    line_end = i
    return TranslationEntry(block_id, old_text, new_text, line_start, line_end)


def find_duplicates(entries: List[TranslationEntry]) -> Dict[str, List[TranslationEntry]]:
    """Группирует дубликаты по old_text"""
    duplicates = {}
    for entry in entries:
        key = entry.old_text
        if key not in duplicates:
            duplicates[key] = []
        duplicates[key].append(entry)
    return {k: v for k, v in duplicates.items() if len(v) > 1}


def deduplicate_file(file_path: Path) -> int:
    """Удаляет дубликаты из файла, возвращает количество удалённых"""
    if not file_path.exists():
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return 0

    # Парсим все блоки
    entries = []
    i = 0
    while i < len(lines):
        if 'translate ru ' in lines[i]:
            entry = parse_translate_block(lines, i)
            if entry and entry.old_text:
                entries.append(entry)
        i += 1

    # Находим дубликаты
    duplicates = find_duplicates(entries)
    if not duplicates:
        return 0

    # Удаляем дубликаты (оставляем только первый)
    lines_to_delete = set()
    for old_text, entry_list in duplicates.items():
        # Оставляем первый, удаляем остальные
        for entry in entry_list[1:]:
            for line_num in range(entry.line_start, entry.line_end):
                lines_to_delete.add(line_num)

    if not lines_to_delete:
        return 0

    # Удаляем дубликаты
    new_lines = [line for i, line in enumerate(lines) if i not in lines_to_delete]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    return len(lines_to_delete)


def deduplicate_ui_strings_file(file_path: Path) -> int:
    """Удаляет дубликаты из old/new формата (screens.rpy)"""
    if not file_path.exists():
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return 0

    # Ищем все old "..." в формате translate ru strings
    seen_old = {}
    lines_to_delete = []

    i = 0
    while i < len(lines):
        match = re.match(r'\s+old "((?:[^"\\]|\\.)*)"', lines[i])
        if match:
            old_text = match.group(1)
            if old_text in seen_old:
                # Дубликат - удаляем old строку
                lines_to_delete.append(i)
                # Удаляем также следующую строку (new)
                if i + 1 < len(lines) and re.match(r'\s+new ', lines[i+1]):
                    lines_to_delete.append(i + 1)
            else:
                seen_old[old_text] = i
        i += 1

    if not lines_to_delete:
        return 0

    # Удаляем дубликаты (толькоold строки, new остаются для уникальных)
    new_lines = [line for i, line in enumerate(lines) if i not in lines_to_delete]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    # Возвращаем количество удалённых old-new пар
    return len([x for x in lines_to_delete if 'old' in lines[x]])


def deduplicate_directory(output_dir: Path) -> Dict[str, int]:
    """Обрабатывает всю директорию переводов"""
    results = {}

    # Обрабатываем old/new формат (ui_strings, characters)
    ui_strings_dir = output_dir / 'ui_strings'
    if ui_strings_dir.exists():
        screens = ui_strings_dir / 'screens.rpy'
        if screens.exists():
            count = deduplicate_ui_strings_file(screens)
            results['ui_strings/screens.rpy'] = count
            if count > 0:
                print(f"  Removed {count} duplicates from {screens}")

    characters_dir = output_dir / 'characters'
    if characters_dir.exists():
        char_file = characters_dir / 'character_names.rpy'
        if char_file.exists():
            count = deduplicate_ui_strings_file(char_file)
            results['characters/character_names.rpy'] = count
            if count > 0:
                print(f"  Removed {count} duplicates from {char_file}")

    # Обрабатываем все остальные файлы (диалоги)
    for arc_dir in output_dir.iterdir():
        if arc_dir.is_dir() and arc_dir.name not in ['ui_strings', 'characters', 'manifest.json']:
            for rpy_file in arc_dir.glob('*.rpy'):
                count = deduplicate_file(rpy_file)
                if count > 0:
                    results[str(rpy_file.relative_to(output_dir))] = count
                    print(f"  Removed {count} duplicates from {rpy_file}")

    return results


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent
    output_dir = project_root / 'game' / 'tl' / 'ru' / 'source'

    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])

    print(f"Deduplicating: {output_dir}\n")

    if not output_dir.exists():
        print("Output directory not found!")
        return

    results = deduplicate_directory(output_dir)

    total = sum(results.values())
    print(f"\nTotal: {total} duplicates removed from {len(results)} files")

    if total == 0:
        print("No duplicates found.")


if __name__ == '__main__':
    main()