---
name: checker
description: Проверяет консистентность между оригиналами и переводами, находит дубликаты
license: MIT
compatibility: opencode
metadata:
  audience: translators
  task: verification
---

## What I do

Проверяет что экстрактор правильно извлёк всё нужное. Находит дубликаты в translation файлах.

## When to use me

- "проверь переводы"
- "запусти чекер"
- "найди дубликаты"

## Использование

```bash
python checker.py
python checker.py [game_dir] [source_dir]
```

## Что проверяет

- Сканирует оригинальные файлы
- Ищет дубликаты в translation файлах
- Показывает статистику

## Тесты

```bash
python -m pytest test_checker.py -v
```