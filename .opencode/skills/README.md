# Скилы (Skills)

SKILL.md — файлы с инструкциями для агентов. Загружаются через `skill({ name: "..." })` внутри агента.

**Документация:** https://opencode.ai/docs/skills/

**Формат:**
```
---
name: skill-name
description: Что делает (1-1024 символа)
license: MIT
compatibility: opencode
metadata:
  ключ: значение
---

Инструкции для агента, который загрузил этот скил...
```

**Правила:**
- Каждый скил — отдельная папка `skills/<name>/SKILL.md`
- `name` должен совпадать с именем папки
- `name` только lowercase + дефисы (regex: `^[a-z0-9]+(-[a-z0-9]+)*$`)
- `description` обязателен, 1-1024 символа

**Текущие скилы:**

- `batch-translate` — инструкция для запуска пакетного перевода
- `renpy-translate` — инструкция для перевода одного файла Ren'Py
