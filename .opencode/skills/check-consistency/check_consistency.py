import re
import json
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Optional

def hash_line(line: str) -> str:
    return hashlib.md5(line.encode('utf-8')).hexdigest()[:8]

def parse_translate_blocks(filepath: Path) -> dict[str, list[str]]:
    blocks = defaultdict(list)
    current_key = None
    current_block = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            match = re.match(r'^# script\.rpy:(\d+)$', line.strip())
            if match:
                continue

            match = re.match(r'^translate ru ([A-Za-z]+)_([a-f0-9]+)(?:_(\d+))?:$', line.strip())
            if match:
                if current_key:
                    blocks[current_key] = current_block
                scene_name = match.group(1)
                hash_part = match.group(2)
                suffix = match.group(3)
                current_key = f"{scene_name}_{hash_part}" if not suffix else f"{scene_name}_{hash_part}_{suffix}"
                current_block = [line]
            elif current_key:
                current_block.append(line)
            else:
                if not line.strip():
                    current_block.append(line)

    if current_key and current_block:
        blocks[current_key] = current_block

    return blocks

def block_to_hash_lines(block: list[str]) -> list[tuple[str, str]]:
    return [(hash_line(line), line) for line in block]

def check_consistency(source_path: str, split_dir: str, manifest_dir: str = None, verbose: bool = False) -> dict:
    source = Path(source_path)
    split_output = Path(split_dir)
    script_dir = Path(__file__).parent if not manifest_dir else Path(manifest_dir)

    if not source.exists():
        return {"valid": False, "error": f"Source file not found: {source}"}

    if not split_output.exists():
        return {"valid": False, "error": f"Split directory not found: {split_output}"}

    manifest_path = script_dir / "manifest.json"
    if not manifest_path.exists():
        return {"valid": False, "error": "manifest.json not found"}

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    source_line_count = sum(1 for _ in open(source, encoding="utf-8"))

    chunk_line_count = 0
    for rpy_file in split_output.rglob("*.rpy"):
        if rpy_file.name == "manifest.json":
            continue
        chunk_line_count += sum(1 for _ in open(rpy_file, encoding="utf-8"))

    source_blocks = parse_translate_blocks(source)

    chunk_blocks = defaultdict(list)
    for rpy_file in split_output.rglob("*.rpy"):
        if rpy_file.name == "manifest.json":
            continue
        blocks = parse_translate_blocks(rpy_file)
        for key, block in blocks.items():
            chunk_blocks[key].extend(block)

    source_hashes = set()
    for block in source_blocks.values():
        for line_hash, line in block_to_hash_lines(block):
            source_hashes.add(line_hash)

    chunk_hashes = set()
    for block in chunk_blocks.values():
        for line_hash, line in block_to_hash_lines(block):
            chunk_hashes.add(line_hash)

    missing_in_chunks = source_hashes - chunk_hashes
    extra_in_chunks = chunk_hashes - source_hashes

    block_comparison = {}
    for key in set(source_blocks.keys()) | set(chunk_blocks.keys()):
        source_block = source_blocks.get(key, [])
        chunk_block = chunk_blocks.get(key, [])
        source_lines = [l for l in source_block if l.strip()]
        chunk_lines = [l for l in chunk_block if l.strip()]

        source_translate = len([l for l in source_lines if l.startswith('translate ')])
        chunk_translate = len([l for l in chunk_lines if l.startswith('translate ')])

        block_comparison[key] = {
            "in_source": key in source_blocks,
            "in_chunks": key in chunk_blocks,
            "source_lines": len(source_lines),
            "chunk_lines": len(chunk_lines),
            "source_translate_blocks": source_translate,
            "chunk_translate_blocks": chunk_translate,
            "match": source_lines == chunk_lines
        }

    result = {
        "valid": len(missing_in_chunks) == 0 and len(extra_in_chunks) == 0,
        "source_file": str(source),
        "split_dir": str(split_output),
        "source_blocks": len(source_blocks),
        "chunk_blocks": len(chunk_blocks),
        "source_line_count": source_line_count,
        "chunk_line_count": chunk_line_count,
        "line_match": source_line_count == chunk_line_count,
        "missing_in_chunks_count": len(missing_in_chunks),
        "extra_in_chunks_count": len(extra_in_chunks),
        "manifest": manifest
    }

    if verbose or len(missing_in_chunks) > 0 or len(extra_in_chunks) > 0:
        result["missing_hashes"] = list(missing_in_chunks)[:100]
        result["extra_hashes"] = list(extra_in_chunks)[:100]
        result["block_comparison"] = block_comparison

    return result

def rebuild_from_chunks(split_dir: str, manifest_dir: str, output_path: str) -> dict:
    split_output = Path(split_dir)
    output = Path(output_path)
    script_dir = Path(__file__).parent if not manifest_dir else Path(manifest_dir)

    manifest_path = script_dir / "manifest.json"
    if not manifest_path.exists():
        return {"valid": False, "error": "manifest.json not found"}

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    all_blocks = []

    for archive, data in manifest["archives"].items():
        archive_dir = split_output / archive
        for scene_name in data["scenes"]:
            scene_file = archive_dir / f"{scene_name}.rpy"
            if scene_file.exists():
                with open(scene_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    all_blocks.append(content)
                    all_blocks.append("\n")

    with open(output, "w", encoding="utf-8") as f:
        f.write("".join(all_blocks))

    return {
        "valid": True,
        "output": str(output),
        "blocks_written": len(all_blocks)
    }

if __name__ == "__main__":
    import sys

    source_file = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\The Survival of Sarah Rose\\game\\tl\\ru\\script\\__.script.rpy"
    split_dir = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\The Survival of Sarah Rose\\game\\tl\\ru\\script\\split"

    if len(sys.argv) > 1:
        if sys.argv[1] == "check":
            result = check_consistency(source_file, split_dir, verbose="--verbose" in sys.argv)
            print(f"Valid: {result['valid']}")
            print(f"Source blocks: {result['source_blocks']}")
            print(f"Chunk blocks: {result['chunk_blocks']}")
            print(f"Line match: {result['line_match']}")
            print(f"Source lines: {result['source_line_count']}")
            print(f"Chunk lines: {result['chunk_line_count']}")
            if result.get('missing_in_chunks_count'):
                print(f"Missing in chunks: {result['missing_in_chunks_count']}")
            if result.get('extra_in_chunks_count'):
                print(f"Extra in chunks: {result['extra_in_chunks_count']}")
        elif sys.argv[1] == "rebuild":
            output_file = sys.argv[2] if len(sys.argv) > 2 else source_file + ".rebuilt"
            result = rebuild_from_chunks(split_dir, output_file)
            print(f"Rebuilt: {result['output']}")
            print(f"Blocks written: {result.get('blocks_written', 0)}")
        elif sys.argv[1] == "diff":
            result = check_consistency(source_file, split_dir, verbose=True)
            if "block_comparison" in result:
                for block_name, comparison in result["block_comparison"].items():
                    if not comparison["match"]:
                        print(f"\n{block_name}:")
                        print(f"  Source lines: {comparison['source_lines']}, Chunk lines: {comparison['chunk_lines']}")
                        print(f"  In source: {comparison['in_source']}, In chunks: {comparison['in_chunks']}")
        else:
            print("Usage: python check_consistency.py [check|rebuild|diff] [--verbose]")
    else:
        result = check_consistency(source_file, split_dir)
        print(f"Valid: {result['valid']}")
        print(f"Source lines: {result['source_line_count']}, Chunk lines: {result['chunk_line_count']}")
        print(f"Line match: {result['line_match']}")