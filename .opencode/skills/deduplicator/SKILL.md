---
name: deduplicator
description: Удаляет дубликаты из translation файлов безопасно - сохраняет переводы
license: MIT
compatibility: opencode
metadata:
  audience: translators
  task: cleanup
---

## What I do

Удаляет дубликаты из готовых translation файлов. Безопасно — сохраняет переводы, удаляет только повторяющиеся строки.

## When to use me

- "удали дубликаты"
- "очисти переводы"
- "запусти дедупликатор"

## Использование

```bash
python deduplicate.py
python deduplicate.py [source_dir]
```

## Что удаляет

- Дубликаты old/new пар в ui_strings/screens.rpy
- Дубликаты имён персонажей
- Дубликаты в диалоговых файлах

## Тесты

```bash
python -m pytest test_deduplicate.py -v
```