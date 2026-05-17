---
name: skill-batch-translate
description: "Пакетный перевод файлов Ren'Py — нормализует пути и делегирует скилу orchestrator для параллельной обработки через task(general)"
license: MIT
compatibility: opencode
metadata:
  engine: renpy
  task: batch-translation
---

Делегирует перевод скилу `orchestrator`.

## Инструкция

### 1. Нормализация путей

| Формат | Действие |
|---|---|
| `game/tl/ru/Arc/file.rpy` | Оставить как есть |
| `C:\полный\путь\game\tl\ru\...` | Обрезать до `game/tl/ru/...` |
| Просто `file.rpy` | Запросить полный относительный путь |
| Имя арки (`PrisonArc`) | Найти все `.rpy` в `game/tl/ru/<Arc>/` |

### 2. Запуск

Загрузи скил `orchestrator` и передай ему нормализованный список файлов.
Скил сам запустит параллельные `task(general)` — по одному на файл.

### 3. Ожидание отчёта

Скил возвращает:
```
ГОТОВО: X/Y файлов переведено (Z с ошибками)
```
Передай это пользователю.
