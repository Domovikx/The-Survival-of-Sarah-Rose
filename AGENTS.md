# The Survival of Sarah Rose — Voice Generation

## Правила для AI-агента

- **НИКОГДА не коммитить без явного разрешения пользователя.**
- По умолчанию все изменения остаются в рабочем дереве.

## Структура проекта

```
The Survival of Sarah Rose/
├── game/
│   ├── voice/                    # Английский (default)
│   │   └── {id}.wav
│   ├── tl/
│   │   └── ru/
│   │       └── voice/            # Русский
│   │           └── {id}.wav
│   ├── voice_test.rpy            # Debug hook + manual test
│   └── options.rpy               # config.has_voice = True
├── tools/
│   └── voice_gen.py              # Генератор голосов
├── refs/
│   └── samples_ru_cosy/          # Референсы голосов (WAV + TXT)
│       ├── Sarah.wav
│       ├── Narrator.wav
│       ├── Kate.wav
│       └── Marion.wav
└── voice_candidates/             # Кандидаты голосов (MP3)
```

## Как это работает

### auto_voice

```renpy
define config.auto_voice = "voice/{id}.wav"
```

Ren'Py генерирует translation ID для каждого блока диалога и ищет файл `{id}.wav` в:
1. `game/tl/{lang}/voice/` (текущий язык)
2. `game/voice/` (default)

### Translation ID

- Формат: `{label}_{hash}` (например `start_636ae3f5`)
- Генерируется автоматически из bytecode блока
- Логируется через debug hook в `voice_debug.log`

## Генерация голосов

### Запуск

```bash
# ОБЯЗАТЕЛЬНО через venv CosyVoice
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_gen.py --text "Фраза" --id {id} --ref refs/samples_ru_cosy/Speaker.wav
```

### Победный конфиг

- `cross_lingual + RL`
- `--flow-temp 1.2 --cfg 0.9 --sampling 0.5,10,0.15`
- `--tail-trim --s16 --seed 42`

## Персонажи и голоса

| Персонаж | Голос | Описание |
|----------|-------|----------|
| Сара | Sarah | 17-19 принцесса, blonde, blue eyes |
| Рассказчик | Narrator | Женский, для наррации |
| Кейт | Kate | Подруга Сары |
| Марион | Marion | Мать Сары |

## Debug

### voice_debug.log

Логирует translation ID при каждом диалоге:
```
ID=start_XXXXXX lang=ru ru_exists=False en_exists=False
```

### Ручной тест

**Ctrl+V** в игре — проигрывает тестовый голос.

## Известные проблемы

1. **Стресс** — cross_lingual может ставить неверное ударение
2. **Хвосты** — вздохи в конце фразы. Лечится паттерн-тримом `tools/trim_tail_burst.py`:
   паттерн «тишина ≥80мс → короткий звук ≤500мс, упирающийся в конец файла» = артефакт.
   Запуск: `python tools/trim_tail_burst.py --dir game/tl/ru/voice/ --dry-run` (отчёт)
   или `--in-place` (применение). voice_gen_simple.py делает это автоматически.
3. **OGG** — Ren'Py не поддерживает OGG Vorbis, конвертировать через FFmpeg
