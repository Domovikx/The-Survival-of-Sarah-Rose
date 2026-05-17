# Команды (Commands)

Кастомные слэш-команды. Определяются в `.opencode/commands/<name>.md` или в `opencode.json`.

**Документация:** https://opencode.ai/docs/commands/

**Формат Markdown:**
```
---
description: Что делает команда
mode: subagent  # опционально
---
Шаблон промпта для команды. $ARGUMENTS подставляется из аргументов.
```

**Формат JSON:**
```json
{
  "command": {
    "my-command": {
      "template": "Сделай то-то с $ARGUMENTS",
      "description": "Описание"
    }
  }
}
```

**Пример:**
```
---
description: Запустить тесты с покрытием
---

Запусти полный набор тестов с отчётом о покрытии:
$ARGUMENTS
```

Эта директория пока пуста. Чтобы создать команду, добавь `<имя>.md`.
