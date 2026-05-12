---
name: renpy-translate
description: Перевод строк текста для Ren'Py визуальных новелл с соблюдением формата translate-блоков
license: MIT
compatibility: opencode
metadata:
  audience: translators
  task: translation
---

## What I do

Перевожу тексты для Ren'Py игр с соблюдением правильного формата перевода.

## When to use me

- "переведи эту строку"
- "переведи фразу"
- "нужен перевод этого"
- "как перевести этот текст"

## Форматы перевода

### Диалоги и нарратив

```rpy
translate ru {id}:
    # character "Оригинал"
    character "Перевод"
```

### UI строки и Menu choices

```rpy
translate ru strings:
    old "Оригинал"
    new "Перевод"
```

### Имена персонажей

```rpy
translate ru strings:
    old "Sarah"
    new "Сара"
```

## Типичные ошибки

### Menu choices — ТОЛЬКО через old/new

```rpy
# Неправильно:
translate ru menu_id:
    "Pressure him."
    "Надавить на него."

# Правильно:
translate ru strings:
    old "Pressure him."
    new "Надавить на него."
```

### Пустые переводы
```bash
grep -rn '    ""' game/tl/ru/source/
```

### Слова английского в переводе
**Плохо:** `"Текст like this"`
**Хорошо:** `"Текст, подобный этому"` (передача смысла)

## Критерии качества

- Чистый грамотный русский
- Естественное звучание
- Правильное согласование (род, число, падеж)
- Передача смысла, а не дословный перевод
