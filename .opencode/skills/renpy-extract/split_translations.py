import re
import os
from pathlib import Path
from collections import defaultdict

ARCHIVE_MAPPING = {
    "Prologue": ["start", "OpeningScene"],
    "WarriorPath": ["Warrior", "Hyral", "GallowCreek"],
    "MagePath": ["Mage", "TheBlackMonolith", "TheHollowWorld"],
    "MarionPath": ["Marion", "Varga", "WarCouncil", "CouncilMeeting", "WarStrategy"],
    "SailorPath": ["Sailor", "Belmont", "CallOut", "EscapeLethram", "NoMoney"],
    "HassarPath": ["Hassar", "Jaeid", "Desert"],
    "UnionKingdom": ["Union"],
    "Relationships": ["Kate", "Lily", "Samayra", "Nick", "Carolyn", "Cassius"],
    "Bagrad": ["Bagrad", "Bribe"],
    "SakarPath": ["Sakar"],
    "DemonArc": ["DemonArc", "Razaphel"],
    "Other": []
}

def is_hex(s):
    return len(s) >= 6 and len(s) <= 8 and all(c in '0123456789abcdef' for c in s.lower())

def get_scene_name(key: str) -> str:
    parts = key.rsplit("_", 1)
    if len(parts) == 1:
        return key
    last = parts[-1]
    if last.isdigit():
        parts2 = parts[0].rsplit("_", 1)
        if len(parts2) > 1 and is_hex(parts2[-1]):
            return parts2[0]
        return parts[0]
    if is_hex(last):
        return parts[0]
    return key

def get_archive(scene_name: str) -> str:
    for archive, prefixes in ARCHIVE_MAPPING.items():
        if archive == "Other":
            continue
        for prefix in prefixes:
            if scene_name.startswith(prefix):
                return archive
    return "Other"

def parse_rpy(filepath: Path) -> dict[str, list[str]]:
    blocks = defaultdict(list)
    current_block = []
    current_key = None
    skip_next_empty = False

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            match = re.match(r'^# script\.rpy:(\d+)$', line.strip())
            if match:
                continue

            match = re.match(r'^translate ru ([A-Za-z0-9]+)_([a-f0-9]+)(?:_(\d+))?:$', line.strip())
            if match:
                if current_key:
                    blocks[current_key] = current_block
                scene_name = match.group(1)
                hash_part = match.group(2)
                suffix = match.group(3)
                current_key = f"{scene_name}_{hash_part}" if not suffix else f"{scene_name}_{hash_part}_{suffix}"
                current_block = [line]
                skip_next_empty = True
            elif current_key:
                if skip_next_empty and not line.strip():
                    skip_next_empty = False
                    continue
                current_block.append(line)
                skip_next_empty = False
            else:
                if not line.strip():
                    current_block.append(line)

    if current_key and current_block:
        blocks[current_key] = current_block

    return blocks

def split_translations(source_path: str, output_dir: str, manifest_dir: str = None) -> dict:
    source = Path(source_path)
    output = Path(output_dir)
    script_dir = Path(__file__).parent if not manifest_dir else Path(manifest_dir)
    manifest_path = script_dir / "manifest.json"

    if output.exists():
        for item in output.rglob("*"):
            if item.is_file():
                item.unlink()
        for item in list(output.rglob("*")):
            if item.is_dir() and not any(item.iterdir()):
                item.rmdir()
    output.mkdir(parents=True, exist_ok=True)

    blocks = parse_rpy(source)

    archive_files = defaultdict(list)
    total_lines = 0

    for key, lines in blocks.items():
        scene_name = get_scene_name(key)
        archive = get_archive(scene_name)
        archive_dir = output / archive
        archive_dir.mkdir(exist_ok=True)

        filepath = archive_dir / f"{scene_name}.rpy"
        with open(filepath, "a", encoding="utf-8") as f:
            f.writelines(lines)

        if scene_name not in archive_files[archive]:
            archive_files[archive].append(scene_name)
        total_lines += len(lines)

    manifest = {
        "archives": {},
        "total_scenes": len(blocks),
        "total_lines": total_lines,
        "source_lines": sum(1 for _ in open(source, encoding="utf-8"))
    }

    for archive, scenes in archive_files.items():
        manifest["archives"][archive] = {
            "count": len(scenes),
            "scenes": sorted(scenes)
        }

    manifest_path = script_dir / "manifest.json"
    import json
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest

def verify_consistency(source_path: str, output_dir: str, manifest_dir: str = None) -> dict:
    source = Path(source_path)
    output = Path(output_dir)
    script_dir = Path(__file__).parent if not manifest_dir else Path(manifest_dir)

    manifest_path = script_dir / "manifest.json"
    if not manifest_path.exists():
        return {"valid": False, "error": "manifest.json not found"}

    import json
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    total_output_lines = 0
    for rpy_file in output.rglob("*.rpy"):
        if rpy_file.name == "manifest.json":
            continue
        with open(rpy_file, encoding="utf-8") as f:
            total_output_lines += sum(1 for _ in f)

    return {
        "valid": manifest["total_lines"] == total_output_lines,
        "source_lines": manifest["source_lines"],
        "output_lines": total_output_lines,
        "manifest_total_lines": manifest["total_lines"],
        "manifest_source_lines": manifest["source_lines"]
    }

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    script_dir = Path(__file__).parent
    game_dir = script_dir.parent.parent.parent

    parser = argparse.ArgumentParser(description="Split/verify Ren'Py translations")
    parser.add_argument("--source", default=str(game_dir / "game" / "tl" / "ru" / "script" / "__.script.__rpy"),
                        help="Source translation file")
    parser.add_argument("--output", default=str(game_dir / "game" / "tl" / "ru" / "script" / "split"),
                        help="Output directory for split files")
    parser.add_argument("--manifest", default=str(script_dir / "manifest.json"),
                        help="Path to manifest.json")
    parser.add_argument("command", nargs="?", default="split", choices=["split", "verify"],
                        help="Command: split or verify")

    args = parser.parse_args()

    if args.command == "verify":
        result = verify_consistency(args.source, args.output)
        print(f"Valid: {result['valid']}")
        print(f"Source lines: {result['source_lines']}")
        print(f"Output lines: {result['output_lines']}")
    else:
        manifest = split_translations(args.source, args.output)
        print(f"Split {manifest['total_scenes']} scenes into {args.output}")
        for archive, data in manifest["archives"].items():
            print(f"  {archive}: {data['count']} scenes")