---
name: extractor
description: Извлекает оригинальные тексты из Ren'Py игр по паттернам. Не трогает существующие переводы.
license: MIT
compatibility: opencode
metadata:
  audience: translators
  task: extraction
---

## What I do

Извлекает тексты из оригинальных .rpy файлов Ren'Py игры. Работает чисто — только извлекает, не модифицирует существующие переводы.

## When to use me

- "извлеки тексты из игры"
- "запусти экстрактор"
- "подготовь файлы для перевода"

## Использование

```bash
python extractor.py
python extractor.py [game_dir] [output_dir]
```

## Типы извлекаемых текстов

- dialogue: character "text"
- narration: "text"
- menu_choice: "Choice text":
- ui_string: _("text")
- character_name: Character(_("Name"))

## Тесты

```bash
python -m pytest test_extractor.py -v
```