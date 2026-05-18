# Агенты

Определения кастомных агентов. Каждый `.md` файл описывает агента с frontmatter.

**Документация:** https://opencode.ai/docs/agents/

**Как работает:** Каждый файл — это Markdown с YAML frontmatter. Имя файла (без .md) становится именем агента.

```
---
description: Что делает агент
mode: subagent        # primary | subagent | all
model: provider/model # опционально
permission:
  edit: deny
  bash: ask
---

Системный промпт агента...
```

**Виды:**
- `primary` — основные агенты (переключаются Tab)
- `subagent` — вызываются через `@name` или `task()`
- `all` — может быть и тем и другим

**Доступные permissions:** read, edit, glob, grep, bash, task, skill, webfetch, websearch, question, lsp

**Текущие агенты:**

- `orchestrator` — оркестратор пакетного перевода Ren'Py
