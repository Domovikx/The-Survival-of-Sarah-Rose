# Конвейер перевода

## 1 — Извлечение
`skill({ name: "renpy-extract" })`

## 2 — Перевод
`skill({ name: "skill-translate-rpy" })`

## 3 — Проверка
`skill({ name: "skill-review-rpy" })`

Блоки 2+3 загружать последовательно в одном агенте.

## 4 — Параллельная обработка
`skill({ name: "orchestrator" })`

Запускает блоки 2+3 для нескольких файлов (до 5 одновременно).

## 5 — Очистка кэша
`skill({ name: "renpy-clear-cache" })`

Или вручную: `python .opencode/skills/renpy-clear-cache/clear_cache.py "game"`

---

### Вспомогательные
- `renpy-dedup` — удаление дублей `old` строк
- `list-translation-files` — статус перевода по аркам
