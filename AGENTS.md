# The Survival of Sarah Rose — AI Voice

## Правила для AI-агента

- **НИКОГДА не коммитить без явного разрешения пользователя.**

## Архитектура озвучки

### Ключ: uid = md5(old) 

`uid = md5(old-текст реплики в UTF-8)` — полный 32-hex, язык-независимый.
`old` — оригинальный английский текст (ключ из `translate ru strings:`), он же
`_last_say_what` в рантайме. Один uid = одна реплика; одинаковые тексты дедупятся
автоматически.

### Рантайм-раскладка (наш мод-контент, не пересекается с файлами игры)

```
ai_voice/                       # КОРЕНЬ ПРОЕКТА, рядом с game/ (не внутри!)
  ru/{Arc}/{uid}.wav            # русская озвучка (текст = new)
  en/{Arc}/{uid}.wav            # английская озвучка (текст = old)
game/
  catalog/
    label_arc.json              # label -> Arc (рантайм-мапа, грузится конфигом)
  voice_config.rpy              # config.auto_voice = static_auto_voice
```

`ai_voice/` лежит ВНЕ game/, поэтому voice_config.rpy добавляет корень
проекта в `config.searchpath` — без этого Ren'Py ищет файлы только в game/.

`Arc` в рантайме берётся из label-части translation ID
(`OpeningScene_92a05bc0` → `OpeningScene`) через `catalog/label_arc.json`.
Неизвестный label → папка `_unknown`. Язык: `preferences.language or "en"`.

### Dev-сторона

```
catalog/
  voices.json                  # 68 254 записей: uid, old, new, who, arc, scene, category
  label_arc.json               # label -> Arc (рантайм-мапа для voice_config.rpy)
  missing_voices.md            # ЗАГЛУШКИ: кто без голоса (генерится voice_status.py)
config/
  voices.yaml                  # персонаж -> реф голоса; нет записи = не озвучиваем
tools/
  voice_catalog.py             # tl/ru + script.rpy -> voices.json + label_arc.json
  voice_status.py              # отчёт готово/нет голоса -> missing_voices.md
  add_candidate.py             # новый MP3-кандидат -> raw-нарезка -> вылеченный реф
  clean_refs.py                # лечение рефов: денойз+deesser+EQ+LOUDNORM (EBU R128 -16 LUFS)
  voice_batch.py               # батч-генерация: каталог -> ai_voice/{lang}/{arc}/{uid}.wav
                               # (модель 1 раз, resumable, автотрим; фильтры --arc/--char/--uid)
  trim_tail_burst.py           # паттерн-трим хвостовых артефактов (импортится батчем)
  voice_manage.py              # управление голосами: list/status/select/compare
  voice_ab_test.py             # A/B-тестирование: генерация N кандидатов → compare-папка
refs/                          # Готовые рефы (нарезка 10с + чистка + loudnorm):
  {Голос}.wav                  # RU рефы: сюда ссылается config/voices.yaml
  {Голос}_{variant}.wav        # варианты для A/B-тестирования
```

ВАЖНО: рабочие рефы ВСЕГДА из refs/ (вылеченные). Правила лечения
(решение 2026-08-31):
  1. «Подшипливание» источника клонируется CV3 — рефы чистятся ДО генерации
     (afftdn nr=15 + deesser i=0.5 + highshelf 8000Hz -6dB)
  2. Громкость всех рефов выровнена EBU R128 loudnorm: -16 LUFS, TP -1.5
     (иначе голоса «гуляли» по уровню и генерация наследовала громкость)
Оба правила — в tools/clean_refs.py, применяются автоматически add_candidate.py.

Категории (voices.json): dialogue 22 216, narration 45 051, menu 491, ui 496.
Озвучиваются только dialogue + narration, и только персонажи из config/voices.yaml
(остальные — пропуск, видны в missing_voices.md).

## Пересборка каталога

```bash
python tools/voice_catalog.py    # ТОЛЬКО при апдейте игры (тексты поменялись)
python tools/voice_status.py     # обновить отчёт-заглушки
```

## Добавление нового голоса (инкрементально, ничего не пересобирается)

```bash
# 1. Положить кандидата: voice_candidates/{Имя}/*.mp3
# 2. Собрать реф + транскрипт (существующие скипаются):
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/add_candidate.py
# 3. Вписать напечатанный фрагмент в config/voices.yaml
# 4. Обновить отчёт:
python tools/voice_status.py
# 5. Сгенерировать реплики только этого персонажа (только отсутствующие файлы):
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char "{Имя}" --limit 10
```

## Генерация кандидатов по промту (VoiceDesign)

Голоса-кандидаты можно не искать, а ГЕНЕРИРОВАТЬ: Qwen3-TTS-12Hz-1.7B-VoiceDesign
создаёт речь по текстовому описанию тембра (пол/возраст/характер).

```bash
PY="C:\pinokio\api\Qwen3-TTS-Pinokio.git\app\venv\Scripts\python.exe"
"$PY" tools/voice_design.py --list                # каст
"$PY" tools/voice_design.py --char Carolyn --n 6  # 6 кандидатов -> voice_candidates/Carolyn/qwen_NN.mp3
```

Правила: каст в tools/voice_design_cast.py (base/vars/texts; тексты с ЯВНЫМ
признаком пола «я пошёл/пошла»); клип должен быть ≥10с — тул сам добирает
длину (slow-инструкция → +вторая фраза); резюмабелен (существующие файлы
пропускает). Подробнее: .opencode/skills/tssr-voice-design/SKILL.md.
Папки-заглушки `voice_candidates/{Имя}/{Имя}.md` — типаж «что искать» для
персонажей без каста.

## Тримминг хвостов (паттерн)

`trim_tail_burst.py`: тишина ≥80мс → короткий звук ≤500мс, упирающийся в конец
файла = артефакт → режем. Запуск: `--dry-run` (отчёт), `--in-place` (применение),
`--dir` (батч).

## A/B-тестирование голосов

### Цикл: сравнение → выбор → генерация

```
1. Кандидаты: voice_candidates/{Name}/*.mp3
2. Рефы: add_candidate.py → refs/{Name}_{variant}.wav
3. Сравнение: voice_ab_test.py → output/voice/compare_{name}/
   Файлы: {uid}__{variant}.wav (постфиксы __[speaker]_[v])
4. Выбор: слушаешь compare-папку, пишешь номер победителя
5. Фиксация: voice_manage.py select {Name} {variant}
   → копирует refs/{Name}_{variant}.wav → refs/{Name}.wav
   → обновляет config/voices.yaml
6. Генерация: voice_batch.py --char {Name} — использует активный реф
```

### Инструменты

```bash
# Добавление кандидата → реф
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/add_candidate.py --only {Name}

# A/B-сравнение (генерирует N реплик × M вариантов)
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_ab_test.py \
  --name Sarah --refs 1 3 --limit 5

# Управление голосами
python tools/voice_manage.py list      # все голоса, активный реф, варианты
python tools/voice_manage.py status    # кто озвучен
python tools/voice_manage.py select Sarah 3  # выбрать вариант → refs/Sarah.wav
python tools/voice_manage.py compare Sarah   # A/B-тест через voice_ab_test.py

# Генерация (только отсутствующие файлы)
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Sarah --limit 10

# Перегенерация (все файлы, --force)
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Sarah --limit 5 --force
```

### Структура рефов

```
refs/
  raw/{Name}.wav          # грязная нарезка 10с (пересобирается)
  ready/{Name}.wav        # АКТИВНЫЙ реф (вылеченный, используется voice_batch)
  ready/{Name}_{variant}.wav  # варианты для сравнения
```

### Тесты

```bash
python -m pytest tests/ -v  # 15 тестов: voice_manage, voice_batch, clean_refs
```

## План работ

1. **Пилот: Prologue** (241 реплика) — Sarah, Narrator, Orwell, Thomas
2. Основные пути (WarriorPath/MagePath/SailorPath) → остальные арки
3. EN-озвучка после RU

## Открытые вопросы

- EN-рефы голосов (в игре озвучки нет) — источники
- Формат аудио: WAV (~16 ГБ/язык) vs OGG в игре (тест в пилоте)
- Fallback при отсутствии RU-файла: играть EN или молчать
