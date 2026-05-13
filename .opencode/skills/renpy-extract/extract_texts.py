"""
Ren'Py Translation Extractor v4
=================================
Извлекает все переводимые строки из game/ → .rpy файлы в tl/ru/

Порядок проверок (важно!):
  1. dialogue   — character "text"
  2. narration  — "text"
  3. menu       — "Choice":
  4. character  — Character(_("Name"), ...)
  5. define     — define xxx = _("text")
  6. ui         — _("text")  (catch-all, последний)

Формат .rpy:
  translate ru strings:
      old "English"
      new "Russian"     ← или оригинал если нет перевода
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


VERSION = 4

ARC_PATTERNS = [
    (re.compile(r'^Opening'), 'Prologue'),
    (re.compile(r'^(DayOfTheFuneral|SecondPartOfFuneral|MeetingOnTheBattlements|MeetingKateInTheGarden|SarahsBedroomAfterFuneral|TheMorningAfterKate|SarahAndThomasSpeak|TheInsidePathBegins|ChooseThePath|CoronationDay)'), 'StoryBeginnings'),
    (re.compile(r'^Union(Kingdom|Loop|Decision)'), 'UnionKingdom'),
    (re.compile(r'^Warrior(Path|Queen|Rahayal)'), 'WarriorPath'),
    (re.compile(r'^SailorPath'), 'SailorPath'),
    (re.compile(r'^MagePath'), 'MagePath'),
    (re.compile(r'^(Hassar|Jaeid)Path'), 'HassarPath'),
    (re.compile(r'^Sakar'), 'SakarPath'),
    (re.compile(r'^(CampSlave|Unmarried|MariusMarriage|GallowCreek)'), 'AlfredArc'),
    (re.compile(r'^DemonArc'), 'DemonArc'),
    (re.compile(r'^(The)?BlackMonolith'), 'BlackMonolith'),
    (re.compile(r'^TheHollowWorld'), 'HollowWorld'),
    (re.compile(r'^(TrainingPath|ChoosingAMentor|GeneralPathBegins)'), 'Training'),
    (re.compile(r'^(Varga|Marion)Path'), 'VargaMarionPath'),
    (re.compile(r'^(HyralGoblin|HyralOrc|HyralTown)'), 'HyralArc'),
    (re.compile(r'^(SarahAndNick|LifeInRahayal|ServantOfGilead|TailorRoute)'), 'LifeInRahayal'),
    (re.compile(r'^(OutsideAndAlone|PrisonPath|UnderworldPath)'), 'PrisonArc'),
    (re.compile(r'^(TheOldRoad|SarahLeaves|SarahExplores)'), 'SailorArc'),
    (re.compile(r'^(TheBattleForTheCapital|WarCouncil)'), 'WarArc'),
    (re.compile(r'^(MageInTheRuins|FallOfLethram)'), 'MagePath'),
]


def _hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]


def _esc(text: str) -> str:
    return text.replace('\\', '\\\\').replace('"', '\\"')


class RenPyExtractor:
    """
    Извлекает строки без дубликатов.
    Ключ дедупликации = original text (нормализованный, с учётом регистра).
    """

    def __init__(self, game_dir: str):
        self.game_dir = Path(game_dir)
        self.arcs: Dict[str, dict] = {}
        self.ui_blocks: Dict[str, dict] = {}
        self.character_blocks: Dict[str, dict] = {}
        self.define_blocks: Dict[str, dict] = {}
        self._seen_originals: set[str] = set()
        self._existing_translations: Dict[str, str] = {}

    @staticmethod
    def _norm(text: str) -> str:
        return text.strip()

    def _get_arc(self, label: str) -> str:
        for pattern, arc_name in ARC_PATTERNS:
            if pattern.match(label):
                return arc_name
        return 'Other'

    def set_existing_translations(self, tl_dir: Path):
        """Читает существующие .rpy файлы в tl/ru/ и извлекает переводы."""
        existing: Dict[str, str] = {}
        if not tl_dir.exists():
            return

        for rpy_file in tl_dir.rglob("*.rpy"):
            try:
                content = rpy_file.read_text(encoding='utf-8')
                in_translate = False
                current_orig = None
                for line in content.split('\n'):
                    s = line.strip()
                    if s.startswith('translate ru strings:'):
                        in_translate = True
                        current_orig = None
                        continue
                    if in_translate and s.startswith('old '):
                        m = re.match(r'old "(.*)"\s*$', s)
                        if m:
                            current_orig = m.group(1)
                        continue
                    if in_translate and current_orig is not None and s.startswith('new '):
                        m = re.match(r'new "(.*)"\s*$', s)
                        if m:
                            trans = m.group(1)
                            if trans and trans != current_orig:
                                existing[self._norm(current_orig)] = trans
                        current_orig = None
                        continue
                    if in_translate and s and not s.startswith(('old ', 'new ', '#')):
                        in_translate = False
            except Exception:
                pass

        self._existing_translations = existing

    def _existing(self, original: str) -> str:
        return self._existing_translations.get(self._norm(original), "")

    def _dedup_key(self, text: str) -> str:
        return text.strip()

    def parse_file(self, file_path: Path):
        source_file = str(file_path)
        current_label = file_path.stem

        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='latin-1')

        lines = content.split('\n')
        in_menu = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # Label
            lbl = re.match(r'^label\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:', stripped)
            if lbl:
                current_label = lbl.group(1)
                in_menu = False
                continue

            # Menu start
            if re.match(r'^menu\b', stripped):
                in_menu = True
                continue

            # Выход из menu context
            if in_menu and not line[0].isspace() and not stripped.startswith('#'):
                in_menu = False

            # ── 1. Диалог: character "text" ──
            m = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+"(.+)"\s*$', stripped)
            if m:
                char = m.group(1)
                text = m.group(2)
                if text and not text.startswith('#'):
                    self._add_to_arc(
                        arc_name=self._get_arc(current_label),
                        scene_name=current_label,
                        source_file=source_file,
                        source_line=i + 1,
                        original=text,
                        block_type='dialogue',
                        character=char,
                    )
                continue

            # ── 2. Нарратив: "text" ──
            m = re.match(r'^"(.+)"\s*$', stripped)
            if m and not stripped.startswith('menu'):
                text = m.group(1)
                self._add_to_arc(
                    arc_name=self._get_arc(current_label),
                    scene_name=current_label,
                    source_file=source_file,
                    source_line=i + 1,
                    original=text,
                    block_type='narration',
                    character=None,
                )
                continue

            # ── 3. Menu choice: "Choice": ──
            m = re.match(r'^\s*"(.+?)"\s*:\s*$', stripped)
            if m and in_menu:
                text = m.group(1).strip()
                if text and text != 'Choose':
                    self._add_to_arc(
                        arc_name=self._get_arc(current_label),
                        scene_name=current_label,
                        source_file=source_file,
                        source_line=i + 1,
                        original=text,
                        block_type='menu_choice',
                        character=None,
                    )
                continue

            # ── 4. Character definition: define s = Character(_("Name"), ...) ──
            combined = stripped
            for j in range(i + 1, min(i + 5, len(lines))):
                nxt = lines[j].strip()
                if nxt and not nxt.startswith('#'):
                    combined += ' ' + nxt
                    if combined.count('(') <= combined.count(')'):
                        break

            char_match = re.search(r'Character\(_\("([^"]+)"', combined)
            if char_match:
                name = char_match.group(1)
                dk = self._dedup_key(name)
                if dk not in self._seen_originals:
                    self._seen_originals.add(dk)
                    self.character_blocks[dk] = {
                        'id': f"char_{_hash(f'{source_file}:{i+1}:char:{name}')}",
                        'original': name,
                        'translated': self._existing(name),
                        'type': 'character_name',
                        'character': None,
                        'source_file': source_file,
                        'source_line': i + 1,
                    }
                continue

            # ── 5. Define: define config.name = _("text") ──
            # (до UI, чтобы не перехватывать _("..."))
            if re.match(r'^(define|default)\s+', stripped):
                # Важно: на одной строке может быть несколько _() вызовов,
                # поэтому используем finditer вместо search
                for dm in re.finditer(r'_\(p?"([^"]+)"\)', stripped):
                    text = dm.group(1)
                    if text and text not in {
                        'Back', 'History', 'Skip', 'Auto', 'Save', 'Q.Save', 'Q.Load',
                        'Prefs', 'Hide UI', 'Start', 'Load', 'Settings', 'End Replay',
                        'Main Menu', 'Quit', 'Return',
                    }:
                        dk = self._dedup_key(text)
                        if dk not in self._seen_originals:
                            self._seen_originals.add(dk)
                            self.define_blocks[dk] = {
                                'id': f"def_{_hash(f'{source_file}:{i+1}:def:{text}')}",
                                'original': text,
                                'translated': self._existing(text),
                                'type': 'define_string',
                                'character': None,
                                'source_file': source_file,
                                'source_line': i + 1,
                            }
                # Пропускаем UI-обработку для define/default строк
                continue

            # ── 6. UI: _("text") — catch-all ──
            for m in re.finditer(r'_\("([^"]+)"\)', stripped):
                text = m.group(1)
                if text:
                    dk = self._dedup_key(text)
                    if dk not in self._seen_originals:
                        self._seen_originals.add(dk)
                        self.ui_blocks[dk] = {
                            'id': f"ui_{_hash(f'{source_file}:{i+1}:ui:{text}')}",
                            'original': text,
                            'translated': self._existing(text),
                            'type': 'ui_string',
                            'character': None,
                            'source_file': source_file,
                            'source_line': i + 1,
                        }
            # Также проверяем одинарные кавычки (например, _('Hide UI'))
            for m in re.finditer(r"""_\('([^']+)'\)""", stripped):
                text = m.group(1)
                if text:
                    dk = self._dedup_key(text)
                    if dk not in self._seen_originals:
                        self._seen_originals.add(dk)
                        self.ui_blocks[dk] = {
                            'id': f"ui_{_hash(f'{source_file}:{i+1}:ui:{text}')}",
                            'original': text,
                            'translated': self._existing(text),
                            'type': 'ui_string',
                            'character': None,
                            'source_file': source_file,
                            'source_line': i + 1,
                        }

    def _add_to_arc(self, arc_name, scene_name, source_file, source_line, original, block_type, character):
        dk = self._dedup_key(original)
        if dk in self._seen_originals:
            return
        self._seen_originals.add(dk)

        if arc_name not in self.arcs:
            self.arcs[arc_name] = {}
        if scene_name not in self.arcs[arc_name]:
            self.arcs[arc_name][scene_name] = {
                'source_file': source_file,
                'source_line': source_line,
                'blocks': {}
            }
        self.arcs[arc_name][scene_name]['blocks'][dk] = {
            'id': f"{scene_name}_{_hash(f'{source_file}:{source_line}:{block_type}:{original}')}",
            'original': original,
            'translated': self._existing(original),
            'type': block_type,
            'character': character,
            'source_file': source_file,
            'source_line': source_line,
        }

    def scan(self) -> dict:
        files = sorted(
            p for p in self.game_dir.rglob("*.rpy")
            if '/tl/' not in str(p) and '\\tl\\' not in str(p)
        )
        print(f"Scanning {self.game_dir}...")
        print(f"Found {len(files)} .rpy files\n")

        for f in files:
            print(f"  Parsing: {f.name}")
            self.parse_file(f)

        total_arc = sum(
            len(s['blocks'])
            for arc in self.arcs.values()
            for s in arc.values()
        )

        print(f"\n{'='*50}")
        print(f"  Arc blocks:       {total_arc}")
        print(f"  UI strings:       {len(self.ui_blocks)}")
        print(f"  Character names:  {len(self.character_blocks)}")
        print(f"  Define strings:   {len(self.define_blocks)}")
        print(f"  Arcs:             {len(self.arcs)}")
        print(f"{'='*50}")

        return self._build_result()

    def _build_result(self) -> dict:
        ui_by_file = {}
        for dk, b in self.ui_blocks.items():
            sf = b['source_file']
            ui_by_file.setdefault(sf, []).append(b)

        char_by_file = {}
        for dk, b in self.character_blocks.items():
            sf = b['source_file']
            char_by_file.setdefault(sf, []).append(b)

        define_by_file = {}
        for dk, b in self.define_blocks.items():
            sf = b['source_file']
            define_by_file.setdefault(sf, []).append(b)

        return {
            'meta': {
                'version': VERSION,
                'extracted_at': datetime.now().isoformat(),
                'total_arc_blocks': sum(len(s['blocks']) for a in self.arcs.values() for s in a.values()),
                'total_ui_strings': len(self.ui_blocks),
                'total_character_names': len(self.character_blocks),
                'total_define_strings': len(self.define_blocks),
                'arcs_count': len(self.arcs),
            },
            'arcs': self.arcs,
            'ui_by_file': ui_by_file,
            'characters_by_file': char_by_file,
            'defines_by_file': define_by_file,
        }


def generate_rpy(data: dict, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    # Arc files
    for arc_name, scenes in data.get('arcs', {}).items():
        for scene_name, scene in scenes.items():
            sf = scene.get('source_file', 'unknown')
            out = output_dir / arc_name / f"{scene_name}.rpy"
            out.parent.mkdir(parents=True, exist_ok=True)

            blocks = scene.get('blocks', {})
            if not blocks:
                continue

            with open(out, 'w', encoding='utf-8') as f:
                f.write("# -*- encoding: utf-8 -*-\n")
                f.write(f"# Arc: {arc_name} | Scene: {scene_name}\n")
                f.write(f"# Source: {sf}\n\n")
                f.write("translate ru strings:\n\n")
                for dk, bd in blocks.items():
                    o = _esc(bd.get('original', ''))
                    t_raw = bd.get('translated', '')
                    t = _esc(t_raw if t_raw else bd.get('original', ''))
                    f.write(f'    old "{o}"\n')
                    f.write(f'    new "{t}"\n\n')

            generated.append(str(out.relative_to(output_dir)))

    # UI strings
    ui_data = data.get('ui_by_file', {})
    if ui_data:
        out = output_dir / 'screens.rpy'
        all_blocks = []
        for blocks in ui_data.values():
            all_blocks.extend(blocks)
        all_blocks.sort(key=lambda b: b['original'].lower())

        with open(out, 'w', encoding='utf-8') as f:
            f.write("# -*- encoding: utf-8 -*-\n")
            f.write("# UI Strings - Buttons, Menus, etc.\n\n")
            f.write("translate ru strings:\n\n")
            for bd in all_blocks:
                o = _esc(bd.get('original', ''))
                t_raw = bd.get('translated', '')
                t = _esc(t_raw if t_raw else bd.get('original', ''))
                f.write(f'    old "{o}"\n')
                f.write(f'    new "{t}"\n\n')
        generated.append('screens.rpy')

    # Characters + Defines
    extra_blocks = []
    for blocks in data.get('characters_by_file', {}).values():
        extra_blocks.extend(blocks)
    for blocks in data.get('defines_by_file', {}).values():
        extra_blocks.extend(blocks)

    if extra_blocks:
        extra_blocks.sort(key=lambda b: b['original'].lower())
        out = output_dir / 'misc_strings.rpy'
        with open(out, 'w', encoding='utf-8') as f:
            f.write("# -*- encoding: utf-8 -*-\n")
            f.write("# Character names + Define strings\n\n")
            f.write("translate ru strings:\n\n")
            for bd in extra_blocks:
                o = _esc(bd.get('original', ''))
                t_raw = bd.get('translated', '')
                t = _esc(t_raw if t_raw else bd.get('original', ''))
                f.write(f'    old "{o}"\n')
                f.write(f'    new "{t}"\n\n')
        generated.append('misc_strings.rpy')

    print(f"\nGenerated {len(generated)} .rpy files in {output_dir}")
    return generated


def verify_integrity(original_dir: Path, tl_dir: Path):
    extractor = RenPyExtractor(str(original_dir))
    data = extractor.scan()

    total = 0
    done = 0

    for arc in data['arcs'].values():
        for scene in arc.values():
            for bd in scene['blocks'].values():
                total += 1
                if bd['translated']:
                    done += 1

    for blocks in data['ui_by_file'].values():
        for bd in blocks:
            total += 1
            if bd['translated']:
                done += 1

    for blocks in data['characters_by_file'].values():
        for bd in blocks:
            total += 1
            if bd['translated']:
                done += 1

    for blocks in data['defines_by_file'].values():
        for bd in blocks:
            total += 1
            if bd['translated']:
                done += 1

    print()
    print("=" * 40)
    print("  Integrity Check")
    print("=" * 40)
    print(f"  Total strings:  {total}")
    print(f"  Translated:     {done}")
    print(f"  Untranslated:   {total - done}")
    print(f"  Progress:       {100*done/total:.1f}%")
    print("=" * 40)
    return total, done


def main():
    import sys

    if len(sys.argv) < 2:
        print("Commands:")
        print("  extract           Scan game/ -> .rpy in tl/ru/")
        print("  verify            Check game/ vs tl/ru/")
        print("  stats             Show translation statistics")
        return

    cmd = sys.argv[1]
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent
    game_dir = project_root / 'game'
    tl_dir = project_root / 'game' / 'tl' / 'ru'

    if cmd == 'extract':
        extractor = RenPyExtractor(str(game_dir))
        extractor.set_existing_translations(tl_dir)
        data = extractor.scan()
        generate_rpy(data, tl_dir)
        print("Done!")

    elif cmd == 'verify':
        if not tl_dir.exists():
            print("ERROR: tl/ru directory not found!")
            return
        verify_integrity(game_dir, tl_dir)

    elif cmd == 'stats':
        verify_integrity(game_dir, tl_dir)

    else:
        print("Unknown command:", cmd)


if __name__ == '__main__':
    main()