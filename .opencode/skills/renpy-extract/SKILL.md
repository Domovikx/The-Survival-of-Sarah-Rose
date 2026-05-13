---
name: renpy-extract
description: Извлечение текстов из оригинала Ren'Py и декомпозиция переводов на семантические части по аркам/сценам
license: MIT
compatibility: opencode
metadata:
  engine: renpy
  task: extraction
  source: https://www.renpy.org/doc/html/translation.html
---

## Overview

Этот скил предоставляет инструменты для работы с переводами Ren'Py игр:
1. **extract_texts.py** — извлечение текстов из оригинальных файлов
2. **split_translations.py** — декомпозиция переводов на части

## Структура данных

### Оригинальная игра
```
game/
├── script.rpy          # Основной скрипт (36k строк перевода)
├── screens.rpy         # Экраны
├── options.rpy         # Опции
├── characters.rpy      # Персонажи
├── gui.rpy             # UI
├── language.rpy        # Язык
├── libs/               # Библиотеки
└── tl/ru/              # Текущие переводы (устаревшие)
```

### Целевая структура для переводов
```
game/tl/ru/
├── source/                               # Извлечённые оригиналы (для перевода)
│   └── Prologue/
│       ├── OpeningScene.rpy
│       ├── OpeningSceneEvening.rpy
│       └── ...
│   └── WarriorPath/
├── script/                               # Существующие переводы
│   └── split/
│       └── Prologue/
└── *.rpy                                 # Корневые переводы (screens, options, etc.)
```

## extract_texts.py

### Использование

```bash
# Извлечение всех текстов (автоматически определяет пути)
python extract_texts.py

# С указанием путей
python extract_texts.py /path/to/game /path/to/output
```

### Выходной формат: Ren'Py

```
tl/raw/renpy_format/{ArcName}/{SceneName}.rpy
```

Пример файла:

```rpy
# -*- encoding: utf-8 -*-
# Extracted from: .../script.rpy
# Scene: OpeningScene
# Total blocks: 23

# OpeningScene_5c73d663 (line 333)
translate ru OpeningScene_5c73d663:
    # "King Orwell has returned from his travels..."
    ""

# OpeningScene_ddeb1da1 (line 336)
translate ru OpeningScene_ddeb1da1:
    # ko "Finally, home again."
    ko ""
```

### Структура арок

| Arc Name | Содержит |
|----------|----------|
| Prologue | OpeningScene, OpeningSceneEvening, start |
| WarriorPath | WarriorPath1-5, WarriorRahayal, WarriorQueen |
| SailorPath | SailorPath1-10, LifeInRahayal |
| MagePath | MagePath1-12, MageInTheRuins |
| HassarPath | HassarPath1-5, JaeidPath |
| UnionKingdom | UnionKingdom1-13, UnionLoop |
| BlackMonolith | TheBlackMonolithWarrior, TheBlackMonolithMage |
| HollowWorld | TheHollowWorldWarrior, TheHollowWorldMage |
| Training | TrainingPathKate, TrainingPathCaleb, TrainingPathAtilla |
| StoryBeginnings | DayOfTheFuneral, MeetingOnTheBattlements, etc. |

### Важно: Menu choices

Menu choices (варианты меню) извлекаются в блок `translate strings:` (ui_strings), а НЕ в scene-файлы. Это необходимо для корректной работы перевода меню в Ren'Py.

```rpy
# В screens.rpy:
translate ru strings:
    old "Pressure him."
    new "Давить на него."
```

## ID блоков

Формат: `{label}_{8-char-hash}`

- `label` — имя лейбла сцены
- `8-char-hash` — MD5 хэш (файл:строка:текст)

Пример: `OpeningScene_5c73d663`

Важно: ID нельзя менять — Ren'Py использует их для сопоставления перевода с оригиналом.

## Workflow

```
1. extract_texts.py → Извлечение оригинала в game/tl/ru/raw/renpy_format/
2. Переводчики работают с файлами .rpy в arc/сценах
3. Перевод подставляется в пустые кавычки ""
4. Финальные файлы копируются в game/tl/ru/script/split/
```

## Проверка консистентности (TODO)

```bash
python extract_texts.py verify
```

Проверяет:
- Все ли блоки переведены
- Нет ли дубликатов ID
- Совпадение количества строк с оригиналом

## Источники

- Ren'Py Translation Documentation: https://www.renpy.org/doc/html/translation.html
