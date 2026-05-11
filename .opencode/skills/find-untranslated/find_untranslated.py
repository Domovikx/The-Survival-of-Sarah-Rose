# -*- coding: utf-8 -*-
"""
find_untranslated.py - Find empty and missing translations in Ren'Py split translation files.

Usage:
    python find_untranslated.py [empty|missing|manifest|check] [-v]

Commands:
    empty    - Find blocks with empty translations (original has text, translation is "")
    missing  - Find script.rpy labels without any translation file
    manifest - Check manifest.json exists and is valid
    check    - Run all checks

Examples:
    python find_untranslated.py empty
    python find_untranslated.py empty -v
    python find_untranslated.py missing
    python find_untranslated.py check
"""
import re
import os
import sys
import json
from pathlib import Path

from typing import Optional


def find_empty_translations(split_dir: str, verbose: bool = False) -> dict:
    """
    Находит все блоки перевода с пустым значением перевода.
    Формат блока:
        translate ru SceneName_hash:
            # "Original text"
            ""

    Returns dict с информацией о пустых переводах.
    """
    split_path = Path(split_dir)
    if not split_path.exists():
        return {"valid": False, "error": f"Split directory not found: {split_dir}"}

    results = {
        "valid": True,
        "total_files": 0,
        "total_blocks": 0,
        "files_with_empties": 0,
        "empty_blocks": {},
    }

    for rpy_file in split_path.rglob("*.rpy"):
        if rpy_file.name == "manifest.json":
            continue
        if not rpy_file.name.endswith('.rpy'):
            continue

        results["total_files"] += 1
        rel_path = rpy_file.relative_to(split_path)

        with open(rpy_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped.startswith("translate ru ") and stripped.endswith(":"):
                block_start = i
                block_lines = []
                j = i + 1

                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line.startswith("translate ru ") and next_line.endswith(":"):
                        break
                    if next_line == "" and j == i + 1:
                        pass
                    block_lines.append(lines[j].rstrip("\r\n"))
                    j += 1

                block_text = "".join(block_lines)
                results["total_blocks"] += 1

                orig_text = None
                trans_text = None
                trans_line_idx = None

                for bi, bl in enumerate(block_lines):
                    s = bl.strip()

                    if s.startswith('# "') or s.startswith('# s "') or s.startswith('# t "') \
                       or s.startswith('# m "') or s.startswith('# k "') or s.startswith('# r "') \
                       or s.startswith('# b "') or s.startswith('# n "'):
                        if orig_text is None:
                            m = re.match(r'^# (?:[a-z] )?"(.+)"$', s)
                            if m:
                                orig_text = m.group(1)

                    if s.startswith('"') and not s.startswith('#'):
                        if trans_text is None:
                            trans_text = s.strip().strip('"')
                            trans_line_idx = block_start + 1 + bi

                if orig_text and trans_text == "":
                    archive = rel_path.parts[0] if len(rel_path.parts) > 1 else "Other"
                    filename = rel_path.name
                    if archive not in results["empty_blocks"]:
                        results["empty_blocks"][archive] = []
                    found = False
                    for eb in results["empty_blocks"][archive]:
                        if eb["file"] == filename:
                            eb["empty_count"] += 1
                            found = True
                            break
                    if not found:
                        results["empty_blocks"][archive].append({"file": filename, "empty_count": 1})

                i = j
            else:
                i += 1

    results["files_with_empties"] = sum(len(files) for files in results["empty_blocks"].values())
    results["empty_count"] = sum(eb["empty_count"] for files in results["empty_blocks"].values() for eb in files)

    return results


def find_missing_scenes(script_path: str, split_dir: str) -> dict:
    """
    Находит сцены из script.rpy, для которых нет перевода в split директории.
    """
    script = Path(script_path)
    split_path = Path(split_dir)

    if not script.exists():
        return {"valid": False, "error": f"Script not found: {script_path}"}
    if not split_path.exists():
        return {"valid": False, "error": f"Split directory not found: {split_dir}"}

    with open(script, "r", encoding="utf-8") as f:
        script_content = f.read()

    labels = re.findall(r'^\s*label\s+(\w+):', script_content, re.MULTILINE)

    translated_scenes = set()
    for rpy_file in split_path.rglob("*.rpy"):
        if rpy_file.name == "manifest.json":
            continue

        scene_name = re.match(r'^([A-Za-z]+)(?:_[a-f0-9]{8})?\.rpy$', rpy_file.name)
        if scene_name:
            translated_scenes.add(scene_name.group(1))

    missing = []
    for label in sorted(labels):
        if label in {'start', 'splashscreen'}:
            continue
        if label not in translated_scenes:
            missing.append(label)

    return {
        "valid": True,
        "total_labels": len(labels),
        "translated_scenes": len(translated_scenes),
        "missing_scenes": missing,
        "missing_count": len(missing),
    }


def check_manifest(split_dir: str) -> dict:
    """Проверяет наличие manifest.json и его структуру."""
    split_path = Path(split_dir)
    manifest_path = split_path / "manifest.json"

    if not manifest_path.exists():
        return {"valid": False, "error": "manifest.json not found in split directory"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    return {
        "valid": True,
        "manifest_exists": True,
        "archives": list(manifest.get("archives", {}).keys()),
        "total_scenes": manifest.get("total_scenes", 0),
        "total_lines": manifest.get("total_lines", 0),
    }


def save_report(result: dict, output_path: str, format: str = "json"):
    """Сохраняет отчёт о пустых переводах в файл."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        with open(output, "w", encoding="utf-8") as f:
            json.dump({
                "total_files": result.get("total_files", 0),
                "total_blocks": result.get("total_blocks", 0),
                "files_with_empties": result.get("files_with_empties", 0),
                "empty_count": result.get("empty_count", 0),
                "empty_blocks": result.get("empty_blocks", []),
            }, f, indent=2, ensure_ascii=False)
    elif format == "csv":
        with open(output, "w", encoding="utf-8") as f:
            f.write("file,empty_count\n")
            for entry in result.get("empty_blocks", []):
                f.write(f'"{entry["file"]}",{entry["empty_count"]}\n')
    elif format == "txt":
        with open(output, "w", encoding="utf-8") as f:
            f.write(f"Empty Translation Report\n")
            f.write(f"=" * 50 + "\n")
            f.write(f"Files with empties: {result.get('files_with_empties', 0)}\n")
            f.write(f"Empty blocks: {result.get('empty_count', 0)}\n\n")
            for entry in result.get("empty_blocks", []):
                f.write(f"{entry['file']}: {entry['empty_count']}\n")


if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).parent
    GAME_DIR = SCRIPT_DIR.parent.parent.parent
    SPLIT_DIR = str(GAME_DIR / "game" / "tl" / "ru" / "script" / "split")
    SCRIPT_PATH = str(GAME_DIR / "game" / "script.rpy")
    REPORT_DIR = SCRIPT_DIR / "reports"
    REPORT_DIR.mkdir(exist_ok=True)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "empty":
            verbose = "--verbose" in sys.argv or "-v" in sys.argv
            output_file = None
            for i, arg in enumerate(sys.argv):
                if arg == "--output" and i + 1 < len(sys.argv):
                    output_file = sys.argv[i + 1]

            result = find_empty_translations(SPLIT_DIR, verbose=verbose)
            print(f"Total files: {result.get('total_files', 0)}")
            print(f"Total blocks: {result.get('total_blocks', 0)}")
            print(f"Files with empties: {result.get('files_with_empties', 0)}")
            print(f"Empty blocks: {result.get('empty_count', 0)}")

            if output_file:
                save_report(result, output_file, "json")
                print(f"\nReport saved to: {output_file}")
            elif verbose and result.get('empty_blocks'):
                print("\nEmpty translations by file:")
                for entry in result['empty_blocks'][:50]:
                    print(f"  {entry['file']}: {entry['empty_count']}")

        elif cmd == "missing":
            result = find_missing_scenes(SCRIPT_PATH, SPLIT_DIR)
            print(f"Total labels in script.rpy: {result.get('total_labels', 0)}")
            print(f"Translated scenes: {result.get('translated_scenes', 0)}")
            print(f"Missing scenes: {result.get('missing_count', 0)}")
            if result.get('missing_scenes'):
                print("\nMissing scenes:")
                for s in result['missing_scenes']:
                    print(f"  {s}")

        elif cmd == "manifest":
            result = check_manifest(SPLIT_DIR)
            print(f"Manifest valid: {result.get('valid', False)}")
            if result.get('valid'):
                print(f"Archives: {', '.join(result.get('archives', []))}")
                print(f"Total scenes: {result.get('total_scenes', 0)}")

        elif cmd == "check":
            print("=== Checking empty translations ===")
            r1 = find_empty_translations(SPLIT_DIR)
            print(f"Files with empties: {r1.get('files_with_empties', 0)}")
            print(f"Empty blocks: {r1.get('empty_count', 0)}")

            print("\n=== Checking missing scenes ===")
            r2 = find_missing_scenes(SCRIPT_PATH, SPLIT_DIR)
            print(f"Missing scenes: {r2.get('missing_count', 0)}")
            if r2.get('missing_scenes'):
                for s in r2['missing_scenes'][:10]:
                    print(f"  {s}")

            print("\n=== Manifest ===")
            r3 = check_manifest(SPLIT_DIR)
            print(f"Manifest exists: {r3.get('valid', False)}")

        elif cmd == "report":
            if REPORT_DIR.exists():
                for f in REPORT_DIR.glob("*.json"):
                    f.unlink()
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = REPORT_DIR / f"empty_translations_{timestamp}.json"
            result = find_empty_translations(SPLIT_DIR)
            save_report(result, str(report_path), "json")
            print(f"Report saved: {report_path}")
            print(f"Files with empties: {result.get('files_with_empties', 0)}")
            print(f"Empty blocks: {result.get('empty_count', 0)}")

        else:
            print(f"Unknown command: {cmd}")
            print("Usage: find_untranslated.py [empty|missing|manifest|check|report] [-v] [--output file.json]")
    else:
        result = find_empty_translations(SPLIT_DIR)
        print(f"Files with empty translations: {result.get('files_with_empties', 0)}")
        print(f"Empty translation blocks: {result.get('empty_count', 0)}")