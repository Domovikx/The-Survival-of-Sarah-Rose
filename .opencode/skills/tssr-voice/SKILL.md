---
name: tssr-voice
description: Generate voice lines for The Survival of Sarah Rose using CosyVoice3 voice cloning. Supports batch generation, auto_voice ID mapping, and language switching.
---

# Skill: tssr-voice — Озвучка TSSR

Генерация WAV для The Survival of Sarah Rose через Fun-CosyVoice3-0.5B (zero-shot voice clone).

## Структура

```
game/
  voice/                    # Английский (default)
    {id}.wav
  tl/
    ru/
      voice/                # Русский
        {id}.wav
```

## Конфигурация

### auto_voice (config.auto_voice)

В `game/voice_test.rpy` или `game/options.rpy`:

```renpy
define config.auto_voice = "voice/{id}.wav"
```

### Translation ID

Ren'Py генерирует ID автоматически для каждого блока диалога:
- Формат: `{label}_{hash}` (например `start_636ae3f5`)
- ID логируется в `voice_debug.log` через debug hook

## Генерация голосов

### Запуск (простой wrapper)

```bash
# ОБЯЗАТЕЛЬНО через venv CosyVoice
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_gen_simple.py \
  --text "Фраза" \
  --ref refs/samples_ru_cosy/Speaker.wav \
  --out game/tl/ru/voice/{id}.wav
```

### Параметры

| Параметр | Описание |
|----------|----------|
| `--text` | Текст фразы |
| `--ref` | Путь к референсу голоса (.wav) |
| `--out` | Выходной файл (.wav) |
| `--id` | Translation ID (опционально) |
| `--seed` | Seed (default: 42) |
| `--no-trim` | Отключить тримминг |

### Настройки (победный конфиг)

| Параметр | Значение | Описание |
|----------|----------|----------|
| `--mode` | `cross_lingual` | Режим генерации |
| `--lang-token` | `ru` | Языковой токен |
| `--seed` | `42` | Seed для воспроизводимости |
| `--sampling` | `0.5,10,0.15` | RAS: top_p, top_k, tau_r |
| `--cfg` | `0.9` | inference_cfg_rate |
| `--flow-temp` | `1.2` | Temperature flow-диффузии |
| `--rl` | (default) | Использовать RL веса |
| `--tail-trim` | (default ON) | Обрезка хвоста + fade |
| `--s16` | (default ON) | PCM 16-bit encoding |

### Референсы голосов

`refs/samples_ru_cosy/`:
- `Sarah.wav` + `Sarah.txt` — Сара (17-19 принцесса)
- `Narrator.wav` + `Narrator.txt` — Рассказчик (женский)
- `Kate.wav` + `Kate.txt` — Кейт
- `Marion.wav` + `Marion.txt` — Марион

## Тримминг

### Паттерн-трим (`trim_tail_burst.py`) — ОСНОВНОЙ

Обрезает хвостовые артефакты TTS по **форме паттерна**, без учёта громкости:

**Паттерн:** глубокая тишина (≥80мс) → короткий звук (≤500мс), упирающийся в конец файла = вздох/шум-артефакт, НЕ слово.

```bash
# Один файл (in-place)
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/trim_tail_burst.py file.wav --in-place

# Пакетный dry-run (только отчёт)
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/trim_tail_burst.py --dir game/tl/ru/voice/ --dry-run

# Пакетный in-place
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/trim_tail_burst.py --dir game/tl/ru/voice/ --in-place
```

### Логика тримминга

1. **Найти последний не-тихий кадр** — от конца файла назад
2. **Проверить примыкание к EOF** — всплеск должен заканчиваться в пределах 100мс от конца файла
3. **Измерить всплеск** — если длительность ≤ 500мс → кандидат в артефакт
4. **Проверить тишину перед всплеском** — ≥ 80мс непрерывной тишины → это артефакт
5. **Обрезать** — файл режется до начала всплеска (тишина остаётся как естественный хвост)
6. **Итерировать** — повторять, пока паттерн находится (до 5 раз)

### Параметры

| Параметр | Default | Описание |
|----------|---------|----------|
| `--noise-floor` | -50 dB | Порог тишины |
| `--max-burst` | 500 ms | Макс. длина артефакта |
| `--min-gap` | 80 ms | Мин. тишина перед артефактом |
| `--eof-tol` | 100 ms | Допуск до конца файла |
| `--max-tail-silence` | off | Доп. ограничение хвостовой тишины, мс |

## Тестирование

### Debug hook

В `game/voice_test.rpy`:
```renpy
define config.auto_voice = "voice/{id}.wav"
```

При запуске игры логирует ID в `voice_debug.log`.

### Ручной тест

В игре **Ctrl+V** — проигрывает тестовый голос.

## Известные проблемы

1. **Стресс в русском языке** — cross_lingual режим может ставить неверное ударение (отЭц вместо отЕц). Решение: попробовать zero_shot или instruct2 режим.

2. **Хвостовые артефакты** — вздохи/всхлипы в конце фразы. Решение: `trim_tail_burst.py` (паттерн-трим, применяется автоматически в voice_gen_simple.py).

3. **FFmpeg конвертация** — если нужен OGG, конвертировать отдельно:
   ```bash
   ffmpeg -i input.wav -c:a libvorbis -q:a 6 output.ogg
   ```

## Workflow

1. **Получить translation ID** — запустить игру, проверить `voice_debug.log`
2. **Сгенерировать голос** — `python tools/voice_gen_simple.py --text "..." --ref refs/samples_ru_cosy/Speaker.wav --out game/tl/ru/voice/{id}.wav`
3. **Протестировать** — запустить игру, проверить проигрывание
4. **Повторить** для следующей фразы
