---
name: split-translations
description: Декомпозиция большого файла перевода Ren'Py на семантические части по аркам/сценам
license: MIT
compatibility: opencode
---

## What I do

Декомпозирую большой файл перевода на структурированные части:
- По аркам (story arcs)
- По сценам внутри арок (scenes within arcs)

## Структура вывода

```
tl/<lang>/script/split/
├── Arc1/
│   ├── Scene1.rpy
│   └── Scene1Variation.rpy
├── Arc2/
│   └── ...
├── ...
└── manifest.json
```

## Скрипт

`split_translations.py` — основной скрипт:

```bash
# Декомпозиция
python split_translations.py

# Проверка консистентности
python split_translations.py verify
```

## Проверка консистентности

После декомпозиции:
1. manifest.json содержит статистику
2. verify — сравнивает строки исходника и сумму чанков
3. Должно быть полное совпадение

## Workflow

1. Сплит исходника на чанки
2. Работа с отдельными файлами перевода
3. Проверка консистентности
4. При необходимости — сборка обратно

## Источники

- OpenCode Agent Skills Documentation
- Ren'Py Translation Documentation
