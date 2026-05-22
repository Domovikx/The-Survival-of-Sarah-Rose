---
name: renpy-dedup
description: Поиск и удаление дублирующихся old строк в Ren'Py translation файлах. Ren'Py не допускает одинаковые old строки в разных файлах одного перевода — это вызывает исключение. Скрипт сканирует все .rpy файлы в game/tl/<lang>/, оставляет первый экземпляр, удаляет дубликаты.
license: MIT
compatibility: opencode
metadata:
  engine: renpy
  task: translations-maintenance
  source: https://www.renpy.org/doc/html/translation.html
---

## What I do

Удаляю дублирующиеся `old`/`new` пары в Ren'Py translation файлах.

### Проблема

Ren'Py выбрасывает исключение, если одна и та же строка `old "..."` встречается
в **разных** файлах одного перевода:

```
Exception: A translation for "Raza" already exists at game/tl/ru/HyralArc/HyralGoblin.rpy:8.
```

### Решение

Скрипт `dedup_translations.py`:
1. Сканирует все `.rpy` файлы в `game/tl/<lang>/`
2. Парсит блоки `translate <lang> strings:`
3. Находит одинаковые `old` строки в разных файлах
4. Оставляет первый экземпляр (по алфавиту пути файла)
5. Удаляет дубликаты из остальных файлов

## Использование

```bash
# Дедупликация русского перевода (по умолчанию)
python dedup_translations.py

# Предпросмотр (без изменений)
python dedup_translations.py --dry-run

# Другой язык
python dedup_translations.py --lang de

# Указать корень проекта вручную
python dedup_translations.py --project /path/to/game

# Подробный вывод
python dedup_translations.py --verbose
```

## Как это работает

Скрипт обрабатывает только блоки `translate <lang> strings:`:
```rpy
translate ru strings:

    old "Raza"
    new "Раза"
```

При обнаружении дубликата:
- Первый файл по алфавиту — **KEEP** (оставляем)
- Остальные файлы — **DUPLICATE** (удаляем)

## Тесты

```bash
# Запуск тестов из директории скила
cd .opencode/skills/renpy-dedup
python -m pytest test_dedup_translations.py -v
```

### Что проверяется

- `parse_translate_blocks` — парсинг translate блоков
- `find_all_entries` — сбор всех old/new пар
- `find_duplicates` — поиск дубликатов
- `deduplicate` — дедупликация (dry-run и реальная)
- `test_integration` — сложные сценарии с 3+ файлами
- Корректность: уникальные строки не удаляются
- Парсинг old/new regex с экранированными кавычками

## Структура файлов

```
.opencode/skills/renpy-dedup/
├── SKILL.md                      # Этот файл
├── manifest.json                 # Манифест
├── dedup_translations.py         # Основной скрипт
└── test_dedup_translations.py    # Тесты
```

## Примечания

- Дубликаты внутри одного файла не вызывают ошибок в Ren'Py (одинаковый `old` в одном файле допустим)
- Скрипт удаляет `old` + следующую за ней `new` строку
- После удаления чистит множественные пустые строки (максимум 2 подряд)
- Лучше запускать с `--dry-run` перед реальным удалением
