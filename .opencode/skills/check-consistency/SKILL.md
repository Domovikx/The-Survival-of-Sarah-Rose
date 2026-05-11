---
name: check-consistency
description: Проверка консистентности между исходным файлом перевода и декомпозированными чанками
license: MIT
compatibility: opencode
---

## What I do

Проверяю консистентность между исходным файлом перевода и декомпозированными чанками в `tl/<lang>/script/split/`.

## Проверки

1. **Hash consistency** — все уникальные строки из исходника присутствуют в чанках (и наоборот)
2. **Line count** — сравнение количества строк
3. **Block comparison** — сравнение translate-блоков
4. **Manifest validation** — проверка наличия manifest.json

## Скрипт

`check_consistency.py`:

```bash
# Базовая проверка
python check_consistency.py

# Подробная проверка
python check_consistency.py check --verbose

# Показать различия
python check_consistency.py diff

# Пересобрать исходник из чанков
python check_consistency.py rebuild [output.rpy]
```

## Быстрая проверка пустых переводов

```bash
grep -rn '    ""' tl/<lang>/script/split/
```

## Проверка дубликатов блоков

```bash
grep -n 'translate <lang> SceneName_hash' file.rpy | sort | uniq -d
```

## Workflow

1. После изменений в чанках — запустить проверку
2. Если valid=False — смотреть missing_in_chunks_count и extra_in_chunks_count
3. С помощью diff найти проблемные блоки
4. После фикса — пересобрать исходник для проверки

## Источники

- OpenCode Agent Skills Documentation
- Ren'Py Translation Documentation
