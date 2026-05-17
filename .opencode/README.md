# .opencode — структура проекта для OpenCode

Директория `.opencode/` содержит конфигурацию и расширения для [OpenCode](https://opencode.ai) — AI coding agent.

Официальная документация: https://opencode.ai/docs/

## Состав директорий

| Директория | Назначение | Документация |
|------------|-----------|--------------|
| `agents/` | Кастомные агенты (subagent) в .md файлах | https://opencode.ai/docs/agents/ |
| `skills/` | SKILL.md — инструкции, загружаемые через `skill()` | https://opencode.ai/docs/skills/ |
| `commands/` | Кастомные слэш-команды | https://opencode.ai/docs/commands/ |
| `tools/` | Кастомные тулы (TypeScript) | https://opencode.ai/docs/custom-tools/ |
| `plugins/` | Плагины для расширения функциональности | https://opencode.ai/docs/plugins/ |

## Архитектура перевода

```
Primary (Build agent)
  └── task(agent-orchestrator) → цикл для каждого файла
        ├── task(general) → agent-translator + skill-translate-rpy
        ├── task(general) → agent-reviewer   + skill-review-rpy
        ├── если rejected → повтор translate → review (до 10 попыток)
        └── ...
```

| Компонент | Тип | Назначение |
|-----------|-----|------------|
| `skill-batch-translate` | skill | Инструкция для Primary: «запусти оркестратор со списком файлов» |
| `agent-orchestrator` | agent | Управляет очередью, циклом translate→review→repeat |
| `agent-translator` | agent | Переводит один .rpy файл |
| `agent-reviewer` | agent | Проверяет качество, возвращает approved/rejected |
| `skill-translate-rpy` | skill | Детальная инструкция по переводу .rpy |
| `skill-review-rpy` | skill | Детальная инструкция по проверке качества |
