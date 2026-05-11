"""
Ren'Py Text Extractor
Извлекает тексты из оригинальных .rpy файлов для перевода
"""

import os
import re
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class TextBlock:
    """Блок текста для перевода"""
    id: str
    label: str
    source_file: str
    line_number: int
    text_type: str  # 'dialogue', 'narration', 'menu_choice', 'menu'
    character: Optional[str] = None
    original_text: str = ""
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)


@dataclass
class Scene:
    """Сцена (логическая единица текста)"""
    name: str
    label: str
    blocks: List[TextBlock] = field(default_factory=list)
    source_file: str = ""


@dataclass
class Arc:
    """Арка (группа сцен)"""
    name: str
    scenes: List[Scene] = field(default_factory=list)


class RenPyTextExtractor:
    """Извлекает тексты из Ren'Py скриптов"""

    # Регулярные выражения для парсинга
    DIALOGUE_PATTERN = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+"(.+)"$')
    NARRATION_PATTERN = re.compile(r'^"(.+)"$')
    MENU_CHOICE_PATTERN = re.compile(r'^\s+"(.+?)"\s*:\s*$')  # "Choice": с отступом
    LABEL_PATTERN = re.compile(r'^label\s+([a-zA-Z_][a-zA-Z0-9_]*):')

    def __init__(self, game_dir: str, output_dir: str):
        self.game_dir = Path(game_dir)
        self.output_dir = Path(output_dir)
        self.texts: List[TextBlock] = []
        self.scenes: Dict[str, Scene] = {}

    def scan_game_files(self) -> List[Path]:
        """Находит все .rpy файлы в game/ (исключая tl/)"""
        rpy_files = []
        game_path = Path(self.game_dir)

        for rpy_file in game_path.rglob("*.rpy"):
            # Исключаем файлы переводов
            if '/tl/' in str(rpy_file) or '\\tl\\' in str(rpy_file):
                continue
            # Исключаем .rpyc файлы
            if rpy_file.suffix == '.rpyc':
                continue
            rpy_files.append(rpy_file)

        return rpy_files

    def parse_file(self, file_path: Path) -> List[TextBlock]:
        """Парсит один файл и извлекает тексты"""
        blocks = []
        current_label = "unknown"
        current_scene = Scene(name="unknown", label=current_label, source_file=str(file_path))

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Определяем метку
            label_match = self.LABEL_PATTERN.match(line)
            if label_match:
                current_label = label_match.group(1)
                # Сохраняем текущую сцену и создаём новую
                if current_scene.blocks:
                    self.scenes[current_label] = current_scene
                current_scene = Scene(
                    name=current_label,
                    label=current_label,
                    source_file=str(file_path)
                )

            # Диалог: character "text"
            dialogue_match = self.DIALOGUE_PATTERN.match(line)
            if dialogue_match:
                character = dialogue_match.group(1)
                text = dialogue_match.group(2)
                block = self._create_block(
                    label=current_label,
                    text_type='dialogue',
                    character=character,
                    original_text=text,
                    line_number=i + 1,
                    source_file=str(file_path)
                )
                blocks.append(block)
                current_scene.blocks.append(block)
                self.texts.append(block)

# Нарратив: "text"
            # Исключаем пустые строки и menu/label
            elif (self.NARRATION_PATTERN.match(line) and
                  not line.startswith('menu ') and
                  not line.startswith('"Choose"') and
                  not line.strip() == '""'):
                text = self.NARRATION_PATTERN.match(line).group(1)
                # Пропускаем пустые
                if text.strip():
                    block = self._create_block(
                        label=current_label,
                        text_type='narration',
                        character=None,
                        original_text=text,
                        line_number=i + 1,
                        source_file=str(file_path)
                    )
                    blocks.append(block)
                    current_scene.blocks.append(block)
                    self.texts.append(block)

            # Menu choice:     "Choice text":
            menu_match = self.MENU_CHOICE_PATTERN.match(line)
            if menu_match:
                text = menu_match.group(1)
                block = self._create_block(
                    label=current_label,
                    text_type='menu_choice',
                    character=None,
                    original_text=text,
                    line_number=i + 1,
                    source_file=str(file_path)
                )
                blocks.append(block)
                current_scene.blocks.append(block)
                self.texts.append(block)

            i += 1

        # Сохраняем последнюю сцену
        if current_scene.blocks:
            self.scenes[current_label] = current_scene

        return blocks

    def _create_block(self, label: str, text_type: str, character: Optional[str],
                      original_text: str, line_number: int, source_file: str) -> TextBlock:
        """Создаёт блок текста с уникальным ID"""
        # Генерируем ID на основе хэша
        hash_input = f"{source_file}:{line_number}:{original_text}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]

        return TextBlock(
            id=f"{label}_{short_hash}",
            label=label,
            source_file=source_file,
            line_number=line_number,
            text_type=text_type,
            character=character,
            original_text=original_text
        )

    def extract_all(self) -> Dict[str, Scene]:
        """Извлекает тексты из всех файлов"""
        print(f"Scanning {self.game_dir}...")

        files = self.scan_game_files()
        print(f"Found {len(files)} .rpy files")

        for file_path in files:
            print(f"  Parsing: {file_path.name}")
            self.parse_file(file_path)

        print(f"\nExtracted {len(self.texts)} text blocks from {len(self.scenes)} scenes")
        return self.scenes

    def organize_into_arcs(self) -> List[Arc]:
        """Организует сцены в арки по префиксам"""
        arcs_dict: Dict[str, List[Scene]] = {}

        # Определяем основные арки по ключевым словам
        ARC_PATTERNS = [
            # (pattern, arc_name)
            (r'^Opening', 'Prologue'),
            (r'^(DayOfTheFuneral|SecondPartOfFuneral|MeetingOnTheBattlements|MeetingKateInTheGarden|SarahsBedroomAfterFuneral|TheMorningAfterKate|SarahAndThomasSpeak|TheInsidePathBegins|ChooseThePath|CoronationDay)', 'StoryBeginnings'),
            (r'^Union(Kingdom|Loop|Decision)', 'UnionKingdom'),
            (r'^WarriorPath', 'WarriorPath'),
            (r'^WarriorQueen', 'WarriorPath'),
            (r'^WarriorRahayal', 'WarriorPath'),
            (r'^SailorPath', 'SailorPath'),
            (r'^MagePath', 'MagePath'),
            (r'^HassarPath', 'HassarPath'),
            (r'^JaeidPath', 'HassarPath'),
            (r'^Sakar', 'SakarPath'),
            (r'^(CampSlave|Unmarried|MariusMarriage|GallowCreek)', 'AlfredArc'),
            (r'^DemonArc', 'DemonArc'),
            (r'^(TheBlackMonolith|BlackMonolith)', 'BlackMonolith'),
            (r'^TheHollowWorld', 'HollowWorld'),
            (r'^(TrainingPath|ChoosingAMentor|GeneralPathBegins)', 'Training'),
            (r'^(VargaPath|MarionOrVarga|MarionPath)', 'VargaMarionPath'),
            (r'^(HyralGoblin|HyralOrc|HyralTown)', 'HyralArc'),
            (r'^(SarahAndNick|LifeInRahayal|ServantOfGilead|TailorRoute)', 'LifeInRahayal'),
            (r'^(OutsideAndAlone|PrisonPath|UnderworldPath)', 'PrisonArc'),
            (r'^(TheOldRoad|SarahLeavesLethram|SarahExploresLethram)', 'SailorArc'),
            (r'^(TheBattleForTheCapital|WarCouncil)', 'WarArc'),
            (r'^ArrivingInAlGahaem', 'WarriorPath'),
            (r'^(MageInTheRuins|FallOfLethram)', 'MagePath'),
        ]

        for scene_name, scene in self.scenes.items():
            arc_name = 'Other'

            for pattern, name in ARC_PATTERNS:
                if re.match(pattern, scene_name):
                    arc_name = name
                    break

            if arc_name not in arcs_dict:
                arcs_dict[arc_name] = []
            arcs_dict[arc_name].append(scene)

        arcs = [Arc(name=name, scenes=sorted(scenes, key=lambda s: s.name))
                for name, scenes in sorted(arcs_dict.items())]

        return arcs

    def save_to_format(self, output_format: str = 'json'):
        """Сохраняет извлечённые тексты в нужном формате"""

        if output_format == 'json':
            self._save_json()
        elif output_format == 'renpy':
            self._save_renpy_format()
        elif output_format == 'markdown':
            self._save_markdown()

    def _save_json(self):
        """Сохраняет в JSON формат"""
        output_path = self.output_dir / 'all_texts.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'metadata': {
                'extracted_at': datetime.now().isoformat(),
                'total_scenes': len(self.scenes),
                'total_blocks': len(self.texts)
            },
            'scenes': {name: asdict(scene) for name, scene in sorted(self.scenes.items())}
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved to {output_path}")

    def _save_renpy_format(self):
        """Сохраняет в формате Ren'Py translate блоков"""
        output_dir = self.output_dir / 'renpy_format'
        output_dir.mkdir(parents=True, exist_ok=True)

        arcs = self.organize_into_arcs()

        manifest = {
            'extracted_at': datetime.now().isoformat(),
            'arcs': []
        }

        for arc in arcs:
            arc_dir = output_dir / arc.name
            arc_dir.mkdir(parents=True, exist_ok=True)

            arc_info = {'name': arc.name, 'scenes': []}

            for scene in arc.scenes:
                scene_file = arc_dir / f"{scene.name}.rpy"
                with open(scene_file, 'w', encoding='utf-8') as f:
                    f.write(f"# -*- encoding: utf-8 -*-\n")
                    f.write(f"# Extracted from: {scene.source_file}\n")
                    f.write(f"# Scene: {scene.name}\n")
                    f.write(f"# Total blocks: {len(scene.blocks)}\n\n")

                    for block in scene.blocks:
                        if block.text_type == 'dialogue':
                            f.write(f"# {block.id} (line {block.line_number})\n")
                            f.write(f"translate ru {block.id}:\n")
                            f.write(f"    # {block.character} \"{block.original_text}\"\n")
                            f.write(f'    {block.character} ""\n\n')
                        elif block.text_type == 'menu_choice':
                            f.write(f"# {block.id} (line {block.line_number})\n")
                            f.write(f"translate ru {block.id}:\n")
                            f.write(f'    # "{block.original_text}"\n')
                            f.write(f'    "{block.original_text}" ""\n\n')
                        else:  # narration
                            f.write(f"# {block.id} (line {block.line_number})\n")
                            f.write(f"translate ru {block.id}:\n")
                            f.write(f'    # "{block.original_text}"\n')
                            f.write(f'    ""\n\n')

                arc_info['scenes'].append({
                    'name': scene.name,
                    'file': str(scene_file.relative_to(output_dir)),
                    'blocks': len(scene.blocks)
                })

            manifest['arcs'].append(arc_info)

        manifest_path = output_dir / 'manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"Saved Ren'Py format to {output_dir}")

    def _save_markdown(self):
        """Сохраняет в Markdown формате для переводчиков"""
        output_dir = self.output_dir / 'markdown'
        output_dir.mkdir(parents=True, exist_ok=True)

        arcs = self.organize_into_arcs()

        for arc in arcs:
            arc_dir = output_dir / arc.name
            arc_dir.mkdir(parents=True, exist_ok=True)

            arc_readme = [f"# {arc.name}\n"]
            arc_readme.append(f"Scenes: {len(arc.scenes)}\n")

            for scene in arc.scenes:
                scene_file = arc_dir / f"{scene.name}.md"
                lines = [f"# {scene.name}\n"]
                lines.append(f"Source: `{scene.source_file}`\n")
                lines.append(f"Blocks: {len(scene.blocks)}\n\n")

                # Группируем по типу
                dialogues = [b for b in scene.blocks if b.text_type == 'dialogue']
                narrations = [b for b in scene.blocks if b.text_type == 'narration']

                if dialogues:
                    lines.append("## Dialogues\n\n")
                    for block in dialogues:
                        lines.append(f"### {block.id}\n")
                        lines.append(f"**Character:** `{block.character}`\n")
                        lines.append(f"**Original:** {block.original_text}\n")
                        lines.append(f"**Translation:** \n\n")

                if narrations:
                    lines.append("## Narrations\n\n")
                    for block in narrations:
                        lines.append(f"### {block.id}\n")
                        lines.append(f"**Original:** {block.original_text}\n")
                        lines.append(f"**Translation:** \n\n")

                with open(scene_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))

                arc_readme.append(f"- [{scene.name}]({scene.name}/{scene.name}.md) ({len(scene.blocks)} blocks)")

            arc_readme_path = arc_dir / 'README.md'
            with open(arc_readme_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(arc_readme))

        print(f"Saved Markdown format to {output_dir}")


def main():
    import sys

    # Пути по умолчанию - поднимаемся из skills/split-translations до корня проекта
    script_dir = Path(__file__).parent  # .opencode/skills/split-translations
    project_root = script_dir.parent.parent.parent  # корень проекта
    game_dir = project_root / 'game'
    output_dir = project_root / 'game' / 'tl' / 'ru' / 'source'

    # Аргументы командной строки
    if len(sys.argv) > 1:
        game_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    print(f"Project root: {project_root}")
    print(f"Game dir: {game_dir}")
    print(f"Output dir: {output_dir}")

    extractor = RenPyTextExtractor(str(game_dir), str(output_dir))
    extractor.extract_all()

    # Сохраняем в формате Ren'Py
    print("\nSaving to Ren'Py format...")
    extractor.save_to_format('renpy')

    print("\nDone!")


if __name__ == '__main__':
    main()