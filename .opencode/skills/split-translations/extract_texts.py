"""
Ren'Py Text Extractor - Full Version
Извлекает ВСЕ переводимые тексты из оригинальных .rpy файлов
"""

import os
import re
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime


@dataclass
class TextBlock:
    """Блок текста для перевода"""
    id: str
    label: str
    source_file: str
    line_number: int
    text_type: str  # 'dialogue', 'narration', 'menu_choice', 'ui_string', 'character_name', 'define_string'
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
    """Извлекает тексты из Ren'Py скриптов - Полная версия"""

    def __init__(self, game_dir: str, output_dir: str):
        self.game_dir = Path(game_dir)
        self.output_dir = Path(output_dir)
        self.texts: List[TextBlock] = []
        self.scenes: Dict[str, Scene] = {}
        self.ui_strings: List[TextBlock] = []
        self.character_names: List[TextBlock] = []
        self.define_strings: List[TextBlock] = []
        self.seen_strings: Set[str] = set()  # Для избежания дубликатов

    def scan_game_files(self) -> List[Path]:
        """Находит все .rpy файлы в game/ (исключая tl/)"""
        rpy_files = []
        game_path = Path(self.game_dir)

        for rpy_file in game_path.rglob("*.rpy"):
            if '/tl/' in str(rpy_file) or '\\tl\\' in str(rpy_file):
                continue
            if rpy_file.suffix == '.rpyc':
                continue
            rpy_files.append(rpy_file)

        return rpy_files

    def _add_block(self, block: TextBlock, scene: Scene, blocks_list: List[TextBlock]):
        """Добавляет блок если его ещё нет"""
        # Создаём уникальный ключ
        key = f"{block.source_file}:{block.line_number}:{block.text_type}:{block.original_text}"
        if key not in self.seen_strings and block.original_text.strip():
            self.seen_strings.add(key)
            blocks_list.append(block)
            scene.blocks.append(block)
            self.texts.append(block)

    def _parse_string_content(self, text: str) -> str:
        """Извлекает содержимое строки с учётом экранирования"""
        # Убираем внешние кавычки
        text = text.strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        # Убираем экранированные кавычки
        text = text.replace('\\"', '"').replace("\\'", "'")
        return text

    def _find_all_strings_in_line(self, line: str, filename: str, line_num: int, context: str = "ui") -> List[TextBlock]:
        """Находит все строки _("...") или _('...') в строке"""
        blocks = []
        # Паттерн для _(...) или _("...")
        patterns = [
            r'_\("(.*?)"\)',      # _("text")
            r"_\\('(.*?)\\'\\)",    # _('text')
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, line):
                text = match.group(1)
                if text.strip():
                    hash_input = f"{filename}:{line_num}:{context}:{text}"
                    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
                    block = TextBlock(
                        id=f"ui_{short_hash}",
                        label="ui_strings",
                        source_file=filename,
                        line_number=line_num,
                        text_type='ui_string' if context == 'ui' else context,
                        original_text=text
                    )
                    blocks.append(block)

        return blocks

    def parse_file_full(self, file_path: Path) -> Tuple[List[TextBlock], List[TextBlock], List[TextBlock]]:
        """Полный парсинг одного файла - извлекает все типы строк"""
        dialogue_blocks = []
        ui_blocks = []
        character_blocks = []

        current_label = file_path.stem  # Имя файла как fallback
        current_scene = Scene(name=current_label, label=current_label, source_file=str(file_path))

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            full_line = lines[i].rstrip()
            prev_lines = lines[max(0, i-2):i]
            next_lines = lines[min(len(lines)-1, i+1):min(len(lines), i+3)]

            # Определяем метку
            label_match = re.match(r'^label\s+([a-zA-Z_][a-zA-Z0-9_]*):', line)
            if label_match:
                current_label = label_match.group(1)
                if current_scene.blocks:
                    self.scenes[current_label] = current_scene
                current_scene = Scene(name=current_label, label=current_label, source_file=str(file_path))

            # === 1. Диалог: character "text" ===
            dialogue_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+"(.+)"$', line)
            if dialogue_match:
                character = dialogue_match.group(1)
                text = self._parse_string_content(dialogue_match.group(2))
                if text.strip():
                    hash_input = f"{file_path}:{i+1}:dialogue:{text}"
                    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
                    block = TextBlock(
                        id=f"{current_label}_{short_hash}",
                        label=current_label,
                        source_file=str(file_path),
                        line_number=i + 1,
                        text_type='dialogue',
                        character=character,
                        original_text=text,
                        context_before=prev_lines,
                        context_after=next_lines
                    )
                    self._add_block(block, current_scene, dialogue_blocks)

            # === 2. Нарратив: "text" (без персонажа) ===
            elif re.match(r'^"(.+)"$', line):
                if not line.startswith('menu ') and not line.startswith('"Choose"') and line.strip() != '""':
                    text = self._parse_string_content(line)
                    if text.strip():
                        hash_input = f"{file_path}:{i+1}:narration:{text}"
                        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
                        block = TextBlock(
                            id=f"{current_label}_{short_hash}",
                            label=current_label,
                            source_file=str(file_path),
                            line_number=i + 1,
                            text_type='narration',
                            original_text=text,
                            context_before=prev_lines,
                            context_after=next_lines
                        )
                        self._add_block(block, current_scene, dialogue_blocks)

            # === 3. Menu choice:     "Choice text": ===
            menu_match = re.match(r'^\s+"(.+?)"\s*:\s*$', line)
            if menu_match:
                text = menu_match.group(1)
                if text.strip() and text != "Choose":
                    hash_input = f"{file_path}:{i+1}:menu_choice:{text}"
                    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
                    block = TextBlock(
                        id=f"menu_{short_hash}",
                        label="menu_choices",
                        source_file=str(file_path),
                        line_number=i + 1,
                        text_type='menu_choice',
                        original_text=text,
                        context_before=prev_lines,
                        context_after=next_lines
                    )
                    # Menu choices НЕ добавляются в scene.blocks - они идут в screens.rpy
                    if block.original_text.strip():
                        key = f"{block.source_file}:{block.line_number}:{block.text_type}:{block.original_text}"
                        if key not in self.seen_strings:
                            self.seen_strings.add(key)
                            self.ui_strings.append(block)  # Добавляем в ui_strings для old/new формата

            # === 4. UI строки: _("...") или _("...") ===
            ui_in_line = self._find_all_strings_in_line(line, str(file_path), i + 1, 'ui_string')
            for block in ui_in_line:
                self._add_block(block, current_scene, ui_blocks)
                # Проверка на дубликаты для UI-строк
                key = f"{block.source_file}:{block.line_number}:{block.text_type}:{block.original_text}"
                if key not in self.seen_strings:
                    self.seen_strings.add(key)
                    self.ui_strings.append(block)

            # === 5. Character definitions: Character(_("Name"), ...) ===
            # Ищем в текущей и следующих строках
            combined_line = line
            for j in range(i+1, min(i+5, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith('#'):
                    combined_line += ' ' + next_line
                    if ')' in combined_line:
                        break

            # Character name extraction
            char_name_match = re.search(r'Character\s*\(\s*_\("(.*?)"\)', combined_line)
            if char_name_match:
                name = char_name_match.group(1)
                hash_input = f"{file_path}:{i+1}:character_name:{name}"
                short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
                block = TextBlock(
                    id=f"char_{short_hash}",
                    label="characters",
                    source_file=str(file_path),
                    line_number=i + 1,
                    text_type='character_name',
                    original_text=name
                )
                if block.original_text.strip():
                    self._add_block(block, current_scene, character_blocks)
                    self.character_names.append(block)

            # === 6. Define strings: define config.name = _("...") ===
            define_match = re.search(r'_("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', line)
            if define_match:
                text = self._parse_string_content(define_match.group(1))
                if text.strip() and text not in ['Back', 'History', 'Skip', 'Auto', 'Save', 'Q.Save', 'Q.Load', 'Prefs', 'Hide UI', 'Start', 'Load', 'Settings', 'End Replay', 'Main Menu', 'Quit', 'Return']:
                    hash_input = f"{file_path}:{i+1}:define:{text}"
                    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
                    block = TextBlock(
                        id=f"def_{short_hash}",
                        label="defines",
                        source_file=str(file_path),
                        line_number=i + 1,
                        text_type='define_string',
                        original_text=text
                    )
                    self._add_block(block, current_scene, character_blocks)
                    self.define_strings.append(block)

            i += 1

        # Сохраняем последнюю сцену
        if current_scene.blocks:
            self.scenes[current_label] = current_scene

        # Сохраняем в экземпляре для доступа через extractor.ui_strings
        self.ui_strings.extend(ui_blocks)
        self.texts.extend(dialogue_blocks)
        self.character_names.extend(character_blocks)

        return dialogue_blocks, ui_blocks, character_blocks

    def parse_file(self, file_path: Path) -> List[TextBlock]:
        """Обёртка для обратной совместимости"""
        blocks, _, _ = self.parse_file_full(file_path)
        return blocks

    def extract_all(self) -> Dict[str, Scene]:
        """Извлекает тексты из всех файлов"""
        print(f"Scanning {self.game_dir}...")

        files = self.scan_game_files()
        print(f"Found {len(files)} .rpy files\n")

        total_dialogue = 0
        total_ui = 0
        total_chars = 0

        for file_path in files:
            print(f"  Parsing: {file_path.name}")
            d, u, c = self.parse_file_full(file_path)
            total_dialogue += len(d)
            total_ui += len(u)
            total_chars += len(c)

        print(f"\n{'='*50}")
        print(f"Extraction Summary:")
        print(f"  - Dialogue/Narration blocks: {total_dialogue}")
        print(f"  - UI strings: {total_ui}")
        print(f"  - Character names: {total_chars}")
        print(f"  - Total unique texts: {len(self.texts)}")
        print(f"  - Scenes: {len(self.scenes)}")
        print(f"{'='*50}")

        return self.scenes

    def organize_into_arcs(self) -> List[Arc]:
        """Организует сцены в арки по префиксам"""
        arcs_dict: Dict[str, List[Scene]] = {}

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

        return [Arc(name=name, scenes=sorted(scenes, key=lambda s: s.name))
                for name, scenes in sorted(arcs_dict.items())]

    def save_to_format(self):
        """Сохраняет в формате Ren'Py"""
        self._save_renpy_format()
        self._save_ui_strings()
        self._save_characters()

    def _load_existing_translations(self, output_dir: Path) -> Dict[str, str]:
        """Загружает существующие переводы из output_dir"""
        existing = {}
        if not output_dir.exists():
            return existing

        # Ищем все .rpy файлы в output
        for rpy_file in output_dir.rglob("*.rpy"):
            try:
                with open(rpy_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Паттерн для translate блоков с содержимым
                block_pattern = re.compile(
                    r'translate ru (\S+):\s*\n((?:[^\n]*\n)*?)(?=\ntranslate|\n#|\Z)',
                    re.MULTILINE
                )

                for block_match in block_pattern.finditer(content):
                    block_id = block_match.group(1)
                    block_body = block_match.group(2)

                    # dialogue format: character "translation"
                    dialogue_pattern = re.compile(r'(\S+)\s+"((?:[^"\\]|\\.)*)"')
                    # narration/plain format: "translation" or ""
                    # Две группы: (1) для пустых кавычек (""), (2) для текста
                    narration_pattern = re.compile(r'^(\s+""\s*)$|^(\s+"(.*?)"\s*)$', re.MULTILINE)

                    for d_match in dialogue_pattern.finditer(block_body):
                        char = d_match.group(1)
                        translation = d_match.group(2)
                        if translation:  # Не пустой перевод
                            existing[f"{block_id}_{char}"] = f'"{translation}"'

                    for n_match in narration_pattern.finditer(block_body):
                        # Группа 1 - для пустых кавычек (""), Группа 2/3 - для текста
                        if n_match.group(1) is not None:
                            # Пустые кавычки - сохраняем пустую строку
                            existing[block_id] = '""'
                        elif n_match.group(3) is not None:
                            # Текст в кавычках - сохраняем текст
                            existing[block_id] = f'"{n_match.group(3)}"'

            except Exception as e:
                print(f"Warning: Could not read {rpy_file}: {e}")

        return existing

    def _save_renpy_format(self):
        """Сохраняет основные диалоги/нарратив (НЕ menu choices!)
        С сохраняет уже переведённые блоки"""
        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Загружаем существующие переводы
        existing_translations = self._load_existing_translations(output_dir)

        arcs = self.organize_into_arcs()

        manifest = {
            'extracted_at': datetime.now().isoformat(),
            'arcs': [],
            'total_dialogue_blocks': len([t for t in self.texts if t.text_type in ['dialogue', 'narration']]),
            'total_ui_strings': len(self.ui_strings),
            'total_character_names': len(self.character_names),
            'total_menu_choices': len([t for t in self.texts if t.text_type == 'menu_choice']),
            'preserved_translations': len(existing_translations)
        }

        for arc in arcs:
            arc_dir = output_dir / arc.name
            arc_dir.mkdir(parents=True, exist_ok=True)

            arc_info = {'name': arc.name, 'scenes': []}

            for scene in arc.scenes:
                scene_file = arc_dir / f"{scene.name}.rpy"

                # Читаем существующий файл если есть
                existing_scene = {}
                if scene_file.exists():
                    existing_scene = self._load_existing_translations(scene_file.parent)

                with open(scene_file, 'w', encoding='utf-8') as f:
                    f.write("# -*- encoding: utf-8 -*-\n")
                    f.write(f"# Extracted from: {scene.source_file}\n")
                    f.write(f"# Scene: {scene.name}\n")
                    f.write(f"# Total blocks: {len(scene.blocks)}\n\n")

                    for block in scene.blocks:
                        # Menu choices НЕ попадают в этот файл
                        if block.text_type == 'menu_choice':
                            continue

                        # Проверяем есть ли уже перевод
                        if block.text_type == 'dialogue':
                            key = f"{block.id}_{block.character}"
                            existing_translation = existing_translations.get(key) or existing_scene.get(key)
                        else:
                            existing_translation = existing_translations.get(block.id) or existing_scene.get(block.id)

                        translation = existing_translation if existing_translation else '""'

                        if block.text_type == 'dialogue':
                            f.write(f"# {block.id} (line {block.line_number})\n")
                            f.write(f"translate ru {block.id}:\n")
                            f.write(f"    # {block.character} \"{block.original_text}\"\n")
                            f.write(f'    {block.character} {translation}\n\n')
                        else:  # narration
                            f.write(f"# {block.id} (line {block.line_number})\n")
                            f.write(f"translate ru {block.id}:\n")
                            f.write(f'    # "{block.original_text}"\n')
                            f.write(f'    {translation}\n\n')

                arc_info['scenes'].append({
                    'name': scene.name,
                    'file': str(scene_file.relative_to(output_dir)),
                    'blocks': len(scene.blocks)
                })

            manifest['arcs'].append(arc_info)

        manifest_path = output_dir / 'manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"Saved dialogue/narration to {output_dir}")
        if existing_translations:
            print(f"  Preserved {len(existing_translations)} existing translations")

    def _save_ui_strings(self):
        """Сохраняет UI строки и menu choices в формате old/new"""
        output_dir = self.output_dir / 'ui_strings'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Дедупликация: собираем все уникальные строки
        seen_texts = set()
        unique_strings = []

        # Добавляем UI-строки
        for block in self.ui_strings:
            if block.original_text not in seen_texts:
                seen_texts.add(block.original_text)
                unique_strings.append(block.original_text)

        # Добавляем menu choices (тоже дедуплицируем)
        menu_choices = [t for t in self.texts if t.text_type == 'menu_choice']
        for block in menu_choices:
            if block.original_text not in seen_texts:
                seen_texts.add(block.original_text)
                unique_strings.append(block.original_text)

        ui_file = output_dir / 'screens.rpy'
        with open(ui_file, 'w', encoding='utf-8') as f:
            f.write("# -*- encoding: utf-8 -*-\n")
            f.write("# UI Strings & Menu Choices\n")
            f.write(f"# Total: {len(unique_strings)} strings\n\n")

            f.write("translate ru strings:\n\n")

            for text in unique_strings:
                f.write(f'    old "{text}"\n')
                f.write(f'    new "{text}"\n\n')

        print(f"Saved {len(unique_strings)} unique UI strings and menu choices to {ui_file}")

    def _save_characters(self):
        """Сохраняет имена персонажей - в формате old/new"""
        output_dir = self.output_dir / 'characters'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Дедупликация имён персонажей
        seen_names = set()
        unique_blocks = []
        for block in self.character_names:
            if block.original_text not in seen_names:
                seen_names.add(block.original_text)
                unique_blocks.append(block)

        char_file = output_dir / 'character_names.rpy'
        with open(char_file, 'w', encoding='utf-8') as f:
            f.write("# -*- encoding: utf-8 -*-\n")
            f.write("# Character Names\n")
            f.write(f"# Total: {len(unique_blocks)} names\n\n")

            f.write("translate ru strings:\n\n")

            for block in unique_blocks:
                f.write(f'    old "{block.original_text}"\n')
                f.write(f'    new "{block.original_text}"\n\n')

        print(f"Saved character names to {char_file}")


def main():
    import sys

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent
    game_dir = project_root / 'game'
    output_dir = project_root / 'game' / 'tl' / 'ru' / 'source'

    if len(sys.argv) > 1:
        game_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    print(f"Project root: {project_root}")
    print(f"Game dir: {game_dir}")
    print(f"Output dir: {output_dir}\n")

    # Очищаем предыдущие результаты ТОЛЬКО если передан флаг --clean
    if '--clean' in sys.argv and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print("Cleaned output directory.\n")

    extractor = RenPyTextExtractor(str(game_dir), str(output_dir))
    extractor.extract_all()

    print("\nSaving formats...")
    extractor.save_to_format()

    print("\nDone!")


if __name__ == '__main__':
    main()