# Skill: find-untranslated

## Purpose
Find empty and missing translations in the Ren'Py split translation files.

## Usage

### Commands:
```bash
# Find empty translations
python find_untranslated.py empty [-v]

# Find missing scenes (no translation file)
python find_untranslated.py missing

# Check manifest
python find_untranslated.py manifest

# Run all checks
python find_untranslated.py check

# Generate report (JSON)
python find_untranslated.py report
```

### Options:
- `-v` / `--verbose` - show empty blocks details
- `--output file.json` - save report to custom location

## Output Formats
- **JSON**: `{"files_with_empties": N, "empty_count": N, "empty_blocks": [...]}`
- **Console**: summary statistics

## Current results (2026-05-11)
- Files with empty translations: **1351**
- Empty blocks: **47433**
- Reports saved to: `.opencode/skills/find-untranslated/reports/`

## Files
- `find_untranslated.py` - main script
- `test_find_untranslated.py` - test suite
- `reports/` - saved JSON reports