---
name: split-translations
description: Декомпозиция большого файла перевода Ren'Py на семантические части по аркам/сценам
license: MIT
compatibility: opencode
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

### Выходной формат

#### 1. Диалоги и нарратив (`{Arc}/{Scene}.rpy`)
```rpy
translate ru {id}:
    # character "Original text"
    character "Translated text"
```

#### 2. UI строки и Menu choices (`ui_strings/screens.rpy`)
```rpy
translate ru strings:

    old "Original text"
    new "Translated text"
```
**Важно:** Menu choices (текст вариантов меню) должны переводиться через `translate ru strings`, а не через `translate ru {id}`!

#### 3. Имена персонажей (`characters/character_names.rpy`)
```rpy
translate ru strings:

    old "Sarah"
    new "Сара"
```

### Пример файла диалога

```rpy
# -*- encoding: utf-8 -*-
# Extracted from: .../script.rpy
# Scene: OpeningScene
# Total blocks: 23

# OpeningScene_5c73d663 (line 333)
translate ru OpeningScene_5c73d663:
    # "King Orwell has returned from his travels..."
    "Король Орвелл вернулся из путешествия..."

# OpeningScene_ddeb1da1 (line 336)
translate ru OpeningScene_ddeb1da1:
    # ko "Finally, home again."
    ko "Наконец-то дома."
```

### Пример файла UI/Menu

```rpy
# -*- encoding: utf-8 -*-
# UI Strings & Menu Choices

translate ru strings:

    old "Save"
    new "Сохранить"

    old "Load"
    new "Загрузить"

    old "Pressure him."
    new "Надавить на него."

    old "Let it be."
    new "Оставить как есть."
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

## ID блоков

Формат: `{label}_{8-char-hash}`

- `label` — имя лейбла сцены
- `8-char-hash` — MD5 хэш (файл:строка:текст)

Пример: `OpeningScene_5c73d663`

Важно: ID нельзя менять — Ren'Py использует их для сопоставления перевода с оригиналом.

## Workflow

```
1. extract_texts.py → Извлечение текстов в game/tl/ru/source/
   - Диалоги/нарратив → {Arc}/{Scene}.rpy (translate ru {id})
   - UI/Menu choices → ui_strings/screens.rpy (translate ru strings)
   - Имена персонажей → characters/character_names.rpy

2. Переводчики работают с файлами:
   - Диалоги: заполняют пустые кавычки в {id} блоках
   - UI/Menu: заполняют "new" в old/new парах
   - Персонажи: заполняют "new" для имён

3. Очистка кэша перед тестом:
   del game/*.rpyc game/*.rpyb
```

## Важные правила перевода

### Menu choices — ТОЛЬКО через old/new
```rpy
# НЕПРАВИЛЬНО (не работает для меню):
translate ru menu_choice_id:
    "Pressure him."
    "Надавить на него."

# ПРАВИЛЬНО:
translate ru strings:
    old "Pressure him."
    new "Надавить на него."
```

### Диалоги — через translate ru {id}
```rpy
translate ru OpeningScene_abc12345:
    # ko "Text"
    ko "Переведённый текст"
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
