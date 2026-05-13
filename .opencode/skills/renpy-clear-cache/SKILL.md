---
name: renpy-clear-cache
description: Удаление файлов кэша Ren'Py (*.rpyc, __pycache__, *.log)
license: MIT
compatibility: opencode
metadata:
  engine: renpy
  task: maintenance
---

## Overview

Скил для очистки кэша Ren'Py. Решает проблемы:
- Устаревшие `.rpyc` файлы, из-за которых перевод не обновляется
- Занятое место от `__pycache__` и логов
- Ошибки при отладке из-за «призрачного» старого кода

## Использование

```bash
# Очистить game/ в текущем проекте
python clear_cache.py

# Указать путь к игре
python clear_cache.py /path/to/game

# Предпросмотр — что будет удалено (без фактического удаления)
python clear_cache.py --dry-run

# Подробный вывод каждого удалённого файла
python clear_cache.py --verbose
```

## Что удаляется

| Тип | Примеры | Зачем |
|-----|---------|-------|
| `*.rpyc` | `script.rpyc`, `screens.rpyc` | Скомпилированный байткод Ren'Py |
| `*.log` | `error.log`, `renpylog.txt` | Логи выполнения |
| `*.tmp` | — | Временные файлы |
| `__pycache__/` | `game/__pycache__/` | Кэш Python-модулей |
| `.pytest_cache/` | `.pytest_cache/` | Кэш pytest |
| `.mypy_cache/` | `.mypy_cache/` | Кэш mypy |
| `.ruff_cache/` | `.ruff_cache/` | Кэш ruff |

## Что НЕ удаляется

- `*.rpy` — исходные файлы игры
- `*.rpa` — архивы ресурсов
- `.git/` — директория git
- Любые другие пользовательские файлы

## Безопасность

- Скрипт **никогда** не удаляет `.rpy` файлы
- Перед удалением можно использовать `--dry-run` для предпросмотра
- Пропускается директория `.git`
- При ошибке удаления выводится предупреждение, процесс продолжается

## Типичные сценарии

### Перевод не обновляется после редактирования .rpy
```bash
python clear_cache.py --verbose
```
Удаляет `.rpyc` файлы, после чего Ren'Py перекомпилирует скрипт с актуальными переводами.

## Тестирование

```bash
python -m pytest test_clear_cache.py -v
```