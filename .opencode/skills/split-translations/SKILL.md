---
name: split-translations
description: Извлечение и сохранение переводов из Ren'Py игр с поддержкой инкрементального обновления
license: MIT
compatibility: opencode
metadata:
  audience: translators
  workflow: extraction
---

## What I do

Извлекаю тексты из Ren'Py игр для перевода с сохранением уже переведённых фрагментов.

## When to use me

- "извлеки тексты для перевода"
- "запусти extract_texts.py"
- "подготовь файлы перевода"
- "обнови переводы после изменений в игре"

## extract_texts.py

### Использование

```bash
# Извлечение с сохранением переводов
python extract_texts.py

# Полная очистка и переизвлечение
python extract_texts.py --clean
```

### Выходной формат

**Диалоги и нарратив** → `{Arc}/{Scene}.rpy`
```rpy
translate ru {SceneName}_{hash}:
    # character "Original text"
    character "Перевод"
```

**UI строки и Menu choices** → `ui_strings/screens.rpy`
```rpy
translate ru strings:
    old "Original text"
    new "Перевод"
```

**Имена персонажей** → `characters/character_names.rpy`
```rpy
translate ru strings:
    old "Sarah"
    new "Сара"
```

## Workflow

```
1. extract_texts.py → Извлечение в game/tl/ru/source/
2. Перевод → Заполнение пустых строк
3. Повторный запуск → Сохранение переводов
```

## Структура арок

| Arc | Содержит |
|-----|----------|
| Prologue | OpeningScene, OpeningSceneEvening |
| WarriorPath | WarriorPath1-5, WarriorRahayal |
| SailorPath | SailorPath1-10 |
| и другие... |

## Источники

- [Ren'Py Translation Documentation](https://www.renpy.org/doc/html/translation.html)
