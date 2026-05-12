"""
Extractor - Извлекает оригинальные тексты из Ren'Py игр
Атомарный скрипт: только извлечение, не трогает переводы
"""

import re
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set
from datetime import datetime


@dataclass
class TextBlock:
    """Блок текста для перевода"""
    id: str
    label: str
    source_file: str
    line_number: int
    text_type: str  # dialogue, narration, menu_choice, ui_string, character_name
    character: str = None
    original_text: str = ""


@dataclass
class Scene:
    """Сцена"""
    name: str
    label: str
    blocks: List[TextBlock] = field(default_factory=list)
    source_file: str = ""


class Extractor:
    """Извлекает тексты из Ren'Py скриптов"""

    # Паттерны для разных типов текста
    PATTERNS = {
        'dialogue': re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+"(.+)"$'),
        'narration': re.compile(r'^"(.+)"$'),
        'menu_choice': re.compile(r'^\s+"(.+?)"\s*:\s*$'),
        'ui_string': re.compile(r'_\("([^"]+)"\)'),
        'character': re.compile(r'Character\s*\(\s*_\("([^"]+)"\)'),
    }

    # Исключения
    SKIP_CHARS = {'Choose', 'gy_MC'}

    def __init__(self, game_dir: str, output_dir: str):
        self.game_dir = Path(game_dir)
        self.output_dir = Path(output_dir)
        self.scenes: Dict[str, Scene] = {}
        self.extracted: List[TextBlock] = []

    def scan_game_files(self) -> List[Path]:
        """Находит все .rpy файлы в game/ (исключая tl/)"""
        rpy_files = []
        for rpy_file in self.game_dir.rglob("*.rpy"):
            if '/tl/' in str(rpy_file) or '\\tl\\' in str(rpy_file):
                continue
            if rpy_file.suffix == '.rpyc':
                continue
            rpy_files.append(rpy_file)
        return rpy_files

    def _parse_string(self, text: str) -> str:
        """Убирает внешние кавычки и экранирование"""
        text = text.strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        return text.replace('\\"', '"').replace("\\'", "'")

    def _generate_id(self, label: str, text: str, text_type: str) -> str:
        """Генерирует стабильный ID на основе текста"""
        hash_input = f"{label}:{text_type}:{text}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{label}_{short_hash}"

    def extract_file(self, file_path: Path):
        """Извлекает тексты из одного файла"""
        current_label = file_path.stem
        current_scene = Scene(name=current_label, label=current_label, source_file=str(file_path))

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Метка сцены
            label_match = re.match(r'^label\s+([a-zA-Z_][a-zA-Z0-9_]*):', line)
            if label_match:
                current_label = label_match.group(1)
                if current_scene.blocks:
                    self.scenes[current_label] = current_scene
                current_scene = Scene(name=current_label, label=current_label, source_file=str(file_path))

            # Диалог: character "text"
            match = self.PATTERNS['dialogue'].match(line)
            if match:
                char = match.group(1)
                if char not in self.SKIP_CHARS:
                    text = self._parse_string(match.group(2))
                    if text.strip():
                        block = TextBlock(
                            id=self._generate_id(current_label, text, 'dialogue'),
                            label=current_label,
                            source_file=str(file_path),
                            line_number=i + 1,
                            text_type='dialogue',
                            character=char,
                            original_text=text
                        )
                        current_scene.blocks.append(block)
                        self.extracted.append(block)

            # Нарратив: "text"
            elif self.PATTERNS['narration'].match(line):
                if not line.startswith('menu ') and not line.startswith('"Choose"') and line.strip() != '""':
                    text = self._parse_string(line)
                    if text.strip():
                        block = TextBlock(
                            id=self._generate_id(current_label, text, 'narration'),
                            label=current_label,
                            source_file=str(file_path),
                            line_number=i + 1,
                            text_type='narration',
                            original_text=text
                        )
                        current_scene.blocks.append(block)
                        self.extracted.append(block)

            # Menu choice
            match = self.PATTERNS['menu_choice'].match(line)
            if match:
                text = match.group(1)
                if text.strip() and text != "Choose":
                    block = TextBlock(
                        id=f"menu_{hashlib.md5(text.encode()).hexdigest()[:8]}",
                        label="menu_choices",
                        source_file=str(file_path),
                        line_number=i + 1,
                        text_type='menu_choice',
                        original_text=text
                    )
                    # Menu choices идут в отдельный список
                    self.extracted.append(block)

            # UI строки в текущей строке
            for ui_match in self.PATTERNS['ui_string'].finditer(line):
                text = ui_match.group(1)
                if text.strip():
                    block = TextBlock(
                        id=f"ui_{hashlib.md5(text.encode()).hexdigest()[:8]}",
                        label="ui_strings",
                        source_file=str(file_path),
                        line_number=i + 1,
                        text_type='ui_string',
                        original_text=text
                    )
                    self.extracted.append(block)

            # Character names - ищем в нескольких строках
            if i + 1 < len(lines):
                combined = line + ' ' + lines[i+1].strip()
                char_match = self.PATTERNS['character'].search(combined)
                if char_match:
                    name = char_match.group(1)
                    if name.strip():
                        block = TextBlock(
                            id=f"char_{hashlib.md5(name.encode()).hexdigest()[:8]}",
                            label="characters",
                            source_file=str(file_path),
                            line_number=i + 1,
                            text_type='character_name',
                            original_text=name
                        )
                        self.extracted.append(block)

            i += 1

        if current_scene.blocks:
            self.scenes[current_label] = current_scene

    def organize_scenes(self) -> Dict[str, List[Scene]]:
        """Организует сцены в арки"""
        arcs = {
            'Prologue': [],
            'StoryBeginnings': [],
            'UnionKingdom': [],
            'WarriorPath': [],
            'SailorPath': [],
            'MagePath': [],
            'HassarPath': [],
            'SakarPath': [],
            'AlfredArc': [],
            'DemonArc': [],
            'BlackMonolith': [],
            'HollowWorld': [],
            'Training': [],
            'VargaMarionPath': [],
            'HyralArc': [],
            'LifeInRahayal': [],
            'PrisonArc': [],
            'SailorArc': [],
            'WarArc': [],
            'Other': [],
        }

        ARC_PATTERNS = [
            (r'^Opening', 'Prologue'),
            (r'^(DayOfTheFuneral|SecondPartOfFuneral|MeetingOnTheBattlements|MeetingKateInTheGarden|SarahsBedroomAfterFuneral|TheMorningAfterKate|SarahAndThomasSpeak|TheInsidePathBegins|ChooseThePath|CoronationDay)', 'StoryBeginnings'),
            (r'^Union(Kingdom|Loop|Decision)', 'UnionKingdom'),
            (r'^Warrior(Path|Queen|Rahayal)', 'WarriorPath'),
            (r'^SailorPath', 'SailorPath'),
            (r'^MagePath', 'MagePath'),
            (r'^(Hassar|Jaeid)Path', 'HassarPath'),
            (r'^Sakar', 'SakarPath'),
            (r'^(CampSlave|Unmarried|MariusMarriage|GallowCreek)', 'AlfredArc'),
            (r'^DemonArc', 'DemonArc'),
            (r'^(The)?BlackMonolith', 'BlackMonolith'),
            (r'^TheHollowWorld', 'HollowWorld'),
            (r'^(TrainingPath|ChoosingAMentor|GeneralPathBegins)', 'Training'),
            (r'^(Varga|Marion)Path', 'VargaMarionPath'),
            (r'^(HyralGoblin|HyralOrc|HyralTown)', 'HyralArc'),
            (r'^(SarahAndNick|LifeInRahayal|ServantOfGilead|TailorRoute)', 'LifeInRahayal'),
            (r'^(OutsideAndAlone|PrisonPath|UnderworldPath)', 'PrisonArc'),
            (r'^(TheOldRoad|SarahLeaves|SarahExplores)', 'SailorArc'),
            (r'^(TheBattleForTheCapital|WarCouncil)', 'WarArc'),
        ]

        for scene_name, scene in self.scenes.items():
            arc_name = 'Other'
            for pattern, name in ARC_PATTERNS:
                if re.match(pattern, scene_name):
                    arc_name = name
                    break
            arcs[arc_name].append(scene)

        return {k: v for k, v in arcs.items() if v}

    def extract_all(self):
        """Извлекает из всех файлов"""
        files = self.scan_game_files()
        print(f"Found {len(files)} .rpy files")

        for file_path in files:
            print(f"  Extracting: {file_path.name}")
            self.extract_file(file_path)

        print(f"\nExtracted: {len(self.extracted)} blocks")

        by_type = {}
        for block in self.extracted:
            if block.text_type not in by_type:
                by_type[block.text_type] = 0
            by_type[block.text_type] += 1

        for t, c in sorted(by_type.items()):
            print(f"  - {t}: {c}")


def main():
    import sys
    from pathlib import Path

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent

    game_dir = project_root / 'game'
    output_dir = project_root / 'game' / 'tl' / 'ru' / 'source'

    if len(sys.argv) > 1:
        game_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    print(f"Game dir: {game_dir}")
    print(f"Output dir: {output_dir}\n")

    extractor = Extractor(str(game_dir), str(output_dir))
    extractor.extract_all()

    print("\nDone! Use checker to verify.")


if __name__ == '__main__':
    main()