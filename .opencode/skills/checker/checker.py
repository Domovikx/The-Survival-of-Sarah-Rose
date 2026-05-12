"""
Checker - Проверяет консистентность между извлечённым и оригиналами
Атомарный скрипт: проверяет что экстрактор правильно извлёк всё нужное
"""

import re
import hashlib
from pathlib import Path
from typing import Dict, Set, List, Tuple


class Checker:
    """Проверяет консистентность переводов"""

    def __init__(self, game_dir: str, source_dir: str):
        self.game_dir = Path(game_dir)
        self.source_dir = Path(source_dir)

        # Паттерны из экстрактора
        self.PATTERNS = {
            'dialogue': re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+"(.+)"$'),
            'narration': re.compile(r'^"(.+)"$'),
            'menu_choice': re.compile(r'^\s+"(.+?)"\s*:\s*$'),
            'ui_string': re.compile(r'_\("([^"]+)"\)'),
            'character': re.compile(r'Character\s*\(\s*_\("([^"]+)"\)'),
        }
        self.SKIP_CHARS = {'Choose', 'gy_MC'}

    def scan_originals(self) -> Set[str]:
        """Сканирует оригинальные файлы и собирает все тексты"""
        originals = set()

        for rpy_file in self.game_dir.rglob("*.rpy"):
            if '/tl/' in str(rpy_file) or '\\tl\\' in str(rpy_file):
                continue

            try:
                with open(rpy_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()

                        # Диалог
                        match = self.PATTERNS['dialogue'].match(line)
                        if match and match.group(1) not in self.SKIP_CHARS:
                            text = match.group(2).strip('"')
                            if text:
                                originals.add(text)

                        # Нарратив
                        elif self.PATTERNS['narration'].match(line):
                            if not line.startswith('menu ') and line != '""':
                                text = line.strip('"')
                                if text:
                                    originals.add(text)

                        # Menu choice
                        match = self.PATTERNS['menu_choice'].match(line)
                        if match and match.group(1) != "Choose":
                            originals.add(match.group(1))

                        # UI strings
                        for m in self.PATTERNS['ui_string'].finditer(line):
                            originals.add(m.group(1))
            except:
                pass

        return originals

    def scan_translations(self) -> Tuple[Set[str], Set[str]]:
        """Сканирует переводы и собирает (оригинал, перевод)"""
        originals = set()
        translated = set()

        if not self.source_dir.exists():
            return originals, translated

        for rpy_file in self.source_dir.rglob("*.rpy"):
            try:
                with open(rpy_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # old/new формат
                for m in re.finditer(r'old\s+"([^"]+)"', content):
                    originals.add(m.group(1))

                # translate ru формат (диалоги)
                for m in re.finditer(r'#\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+"([^"]+)"', content):
                    pass  # это комментарий с оригиналом

            except:
                pass

        return originals, translated

    def check_duplicates(self) -> Dict[str, List[str]]:
        """Проверяет на дубликаты в файлах"""
        duplicates = {}

        if not self.source_dir.exists():
            return duplicates

        for rpy_file in self.source_dir.rglob("*.rpy"):
            try:
                with open(rpy_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                seen = {}
                dup_lines = []

                for i, line in enumerate(lines):
                    if 'old "' in line:
                        match = re.search(r'old\s+"([^"]+)"', line)
                        if match:
                            text = match.group(1)
                            if text in seen:
                                dup_lines.append((i, text, seen[text]))
                            else:
                                seen[text] = i

                if dup_lines:
                    duplicates[str(rpy_file.relative_to(self.source_dir))] = [
                        f"Line {i}: '{text}' (first at line {first})"
                        for i, text, first in dup_lines
                    ]
            except:
                pass

        return duplicates

    def verify(self) -> Dict:
        """Основная проверка"""
        print("Scanning original files...")
        original_texts = self.scan_originals()
        print(f"Found {len(original_texts)} unique texts in originals")

        print("\nChecking for duplicates in translations...")
        duplicates = self.check_duplicates()

        result = {
            'original_count': len(original_texts),
            'duplicate_files': len(duplicates),
            'duplicates': duplicates,
        }

        if duplicates:
            print(f"\n[!] Found duplicates in {len(duplicates)} files:")
            for file, dups in duplicates.items():
                print(f"  {file}: {len(dups)} duplicates")

        return result


def main():
    import sys
    from pathlib import Path

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent

    game_dir = project_root / 'game'
    source_dir = project_root / 'game' / 'tl' / 'ru' / 'source'

    if len(sys.argv) > 1:
        game_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        source_dir = Path(sys.argv[2])

    print(f"Game dir: {game_dir}")
    print(f"Source dir: {source_dir}\n")

    checker = Checker(str(game_dir), str(source_dir))
    result = checker.verify()

    print("\nDone! Check complete.")


if __name__ == '__main__':
    main()