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
  ru/{Arc}/{uid}__{variant}.wav  # русская озвучка с постфиксом рефа
  en/{Arc}/{uid}__{variant}.wav  # английская озвучка с постфиксом рефа
game/
  catalog/
    label_arc.json              # label -> Arc (рантайм-мапа, грузится конфигом)
    who_variant.json            # кто -> активный вариант (грузится конфигом;
                                #  генерится voice_runtime_map.py при смене yaml)
  voice_config.rpy              # config.auto_voice = static_auto_voice
```

**Поиск в игре:** сначала `{uid}__{активный вариант}.wav` (кто говорит →
`_last_say_who.name` → `who_variant.json` → вариант из voices.yaml), затем
фолбэк glob `{uid}*.wav` (первый совпавший по алфавиту).

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
  missing_voices.md            # ЗАГЛУШКИ: кто без голоса (генерится voice_sync.py report)
  voice_sync_report.md         # расхождения слоёв: NEW/READY/BROKEN/FOREIGN/ORPHAN
  who_variant.json             # кто -> активный вариант (генерится voice_runtime_map.py)
config/
  voices.yaml                  # персонаж -> реф голоса; нет записи = не озвучиваем
  voice_presets.yaml           # ЕДИНАЯ карта конфигов: audio/refs/design/batch/beastify
                               #   (читается через tools/voicekit/config.py; в коде только
                               #   фолбэк-дефолты)
voice_candidates/
  {Имя}/
    {Имя}.yaml                 # КОНТРАКТ (+ отчёт-поля скриптов, extra allowed;
                               #   instruct_en — типаж для генерации, instruct_ru — его
                               #   русский перевод для быстрого ревью)
    generated/                 # СЫРЬЁ: voice_design.py пишет сюда 01.mp3..NN.mp3
    gen_selected/              # ОТБОР: вручную лучшие клипы ({Имя}.mp3, {Имя}_1.mp3)
    in_progress/               # РАБОЧИЕ рефы: add_candidate (нарезка 10с + чистка),
                               #   A/B-варианты, эксперименты с фильтрами
    ref/                       # ФИНАЛ: {Имя}.wav — сюда ссылается voices.yaml
tools/
  voicekit/                    # ЯДРО: paths (раскладка), catalog, contract (pydantic),
                               #   fs (безопасные операции), tts_env (пути моделей)
  voice_sync.py                # АКТУАЛИЗАТОР: status/update/migrate/report
                               #   (создаёт структуру новым, чинит пути, отчёты)
  voice_catalog.py             # tl/ru + script.rpy -> voices.json + label_arc.json
  voice_design.py              # VoiceDesign-генерация кандидатов -> generated/
  add_candidate.py             # gen_selected/*.mp3 -> in_progress/{Имя}[_{v}].wav
                               #   (нарезка + чистка одномерным прогоном)
  clean_refs.py                # лечение рефов: highpass+денойз+deesser+EQ+LOUDNORM+фейды
  beastify.py                  # нелюдские голоса: пресеты orc/demon/monster
                               #   (pitch+formant вниз, тёмный EQ, acrusher, гроул-субтон,
                               #   модуляция/реверб) + loudnorm -16 LUFS/TP -1.5
  voice_batch.py               # батч-генерация: каталог -> ai_voice/{lang}/{arc}/{uid}__{variant}.wav
                               #   (реф ТОЛЬКО из voices.yaml; --ref перезаписывает;
                               #    --emotion — стилевая инструкция в промпт, суффикс _em;
                               #    ДО генерации пишет манифест {wav}.txt: uid/arc/ref/emotion/
                               #    тексты/конфиг — описание того, чем сгенерировано)
  trim_tail_burst.py           # паттерн-трим хвостовых артефактов (импортится батчем)
  voice_manage.py              # list/status/select (select: in_progress -> ref/ +
                               #   voices.yaml + who_variant.json)
  voice_runtime_map.py         # voices.yaml + каталог -> catalog/who_variant.json
  levelnorm.py                 # выравнивание реплик: -16 LUFS / TP -1.5
  voice_preview.py             # 3 самых длинных фразы × каждый реф -> ревью-таблица
  emotion_tag.py               # разметка эмоций: catalog/emotions.json
                               #   (эвристика по тексту или --llm-url локальная LLM)
```

ВАЖНО: рабочие рефы ВСЕГДА из `voice_candidates/{Имя}/ref/` (вылеченные).
Правила лечения (решение 2026-09-01, актуализировано):
  1. «Подшипливание» источника клонируется CV3 — рефы чистятся ДО генерации:
     `highpass=f=60, afftdn=nr=15, deesser=i=0.5, highshelf=f=8000:g=-6`
  2. Громкость всех рефов выровнена EBU R128 loudnorm: -16 LUFS, TP -1.5
  3. Фейды 30мс по краям — защита от кликов
Всё — в tools/clean_refs.py, применяется автоматически add_candidate.py
(одним прогоном: mp3 -> ПЕРВЫЕ 10с -> чистка -> loudnorm -16/TP -1.5 ->
in_progress/{Имя}.wav). Единый уровень громкости для ВСЕХ рефов.

Категории (voices.json): dialogue 22 326, narration 44 941, menu 491, ui 496.
Озвучиваются только dialogue + narration, и только персонажи из config/voices.yaml
(остальные — пропуск, видны в missing_voices.md).

## Актуализация (voice_sync)

```bash
python tools/voice_sync.py status    # сводка слоёв + расхождения (console)
python tools/voice_sync.py update --apply   # структура+заглушки новым, сводка
python tools/voice_sync.py report   # missing_voices.md + voice_sync_report.md
python tools/voice_sync.py migrate  # переезд refs/ -> папки (одноразовый, сделан)
```

Безопасность: ничего не удаляет и не перетирает; `--apply` = реальные изменения,
по умолчанию — только план.

## Пересборка каталога

```bash
python tools/voice_catalog.py    # ТОЛЬКО при апдейте игры (тексты поменялись)
python tools/voice_sync.py report  # обновить отчёты (заглушки + расхождения)
```

## Добавление нового голоса (инкрементально, ничего не пересобирается)

```bash
# 1. Положить отобранный клип: voice_candidates/{Имя}/gen_selected/{Имя}.mp3
# 2. Собрать рабочий реф (существующие скипаются):
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/add_candidate.py --only "{Имя}"
#    -> in_progress/{Имя}.wav, в консоли фрагмент для config/voices.yaml
# 3. Вписать фрагмент в config/voices.yaml (ref: voice_candidates/{Имя}/ref/{Имя}.wav)
# 4. Зафиксировать финальный реф (копия in_progress -> ref/):
python tools/voice_manage.py select {Имя} ""    # вариант без номера = базовый
#    (или сам скопируй in_progress/{Имя}.wav -> ref/{Имя}.wav)
# 5. Обновить отчёты:
python tools/voice_sync.py report
# 6. Сгенерировать реплики только этого персонажа (только отсутствующие файлы):
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char "{Имя}" --limit 10
```

## Генерация кандидатов по промту (VoiceDesign)

Голоса-кандидаты можно не искать, а ГЕНЕРИРОВАТЬ: Qwen3-TTS-12Hz-1.7B-VoiceDesign
создаёт речь по текстовому описанию тембра (пол/возраст/характер).

```bash
PY="C:\pinokio\api\Qwen3-TTS-Pinokio.git\app\venv\Scripts\python.exe"
"$PY" tools/voice_design.py --list                # каст
"$PY" tools/voice_design.py --char Carolyn --n 6  # 6 кандидатов -> generated/01..06.mp3
python tools/voice_sync.py report                 # сводка -> voice_candidates.yaml
```

Правила: каст в `voice_candidates/{Имя}/{Имя}.yaml` (instruct_en — ФИЗИОГНОМИКА + СОЦИАЛЬНАЯ РОЛЬ для генерации:
пол, возраст с «лет», кто это (вор/генерал/король/трактирщик...),
телосложение/лицо/осанка/поступь — БЕЗ описания голоса (типаж
вырисовывается из тела), instruct_ru — русский перевод для ревью,
texts — рус. фразы с ЯВНЫМ признаком пола; файл = контракт);
**texts: каждая фраза 150–250 символов (≈10–20с речи)** — короче даёт клип
<10с (не годится в реф), длиннее — риск дрейфа голоса внутри клипа
(voice_design.py печатает WARN для коротких); клип должен быть ≥10с — тул сам добирает длину (slow-инструкция →
+вторая фраза); резюмабелен (существующие файлы пропускает). Итоги прогона и
сводка каста — в `voice_candidates/voice_candidates.yaml`
(summary/cast/generation; --char принимает ОДНО имя — повторяй флаг; параллельно
можно гнать 2 процесса по OMP_NUM_THREADS=8, ~8 ГБ RAM на процесс).
Подробнее: .opencode/skills/tssr-voice-design/SKILL.md.
Заглушки без texts (созданы voice_sync update) видны в --list с WARN — заполни
контракт перед генерацией.

## Тримминг хвостов (паттерн)

`trim_tail_burst.py`: тишина ≥80мс → короткий звук ≤500мс, упирающийся в конец
файла = артефакт → режем. Запуск: `--dry-run` (отчёт), `--in-place` (применение),
`--dir` (батч).

## A/B-тестирование голосов

### Цикл: сравнение → выбор → генерация

```
1. Кандидаты: voice_design.py → voice_candidates/{Name}/generated/*.mp3
2. Отбор: слушаешь generated/, копируешь лучшие вручную в gen_selected/
   ({Name}.mp3 — один топ-файл; A/B — {Name}_1.mp3, {Name}_2.mp3)
3. Рабочие рефы: add_candidate.py → in_progress/{Name}_{variant}.wav
4. Генерация ПО КАЖДОМУ варианту (файлы лежат рядом, постфикс = реф):
   voice_batch.py --char Sarah --ref voice_candidates/Sarah/in_progress/Sarah_1.wav --limit 5
   voice_batch.py --char Sarah --ref voice_candidates/Sarah/in_progress/Sarah_3.wav --limit 5
   → ai_voice/ru/{arc}/{uid}__Sarah_1.wav и {uid}__Sarah_3.wav
5. Выбор: слушаешь пары в ai_voice/ru/{arc}/ (одинаковые uid рядом)
6. Фиксация: voice_manage.py select {Name} {variant}
   → копирует in_progress/{Name}_{variant}.wav → ref/{Name}.wav
   → обновляет config/voices.yaml
   → перегенерирует catalog/who_variant.json
7. Генерация: voice_batch.py --char {Name} — использует активный реф
   (проигравшие варианты сохраняются в in_progress/ для истории)
```

### Переключение варианта в рантайме (yaml рулит звучанием)

Кто говорит, игра знает (`_last_say_who.name`). Приоритет резолва:
`{uid}__{активный в yaml}.wav` → любой `{uid}*.wav`. Поэтому сменил
`ref:` в voices.yaml → перегенерил `catalog/who_variant.json`
(`python tools/voice_runtime_map.py`; select делает это сам) →
в игре зазвучал новый вариант, старые файлы удалять НЕ обязательно
(они просто перестают выигрывать приоритет).

```
```

### Инструменты

```bash
# Добавление кандидата → реф
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/add_candidate.py --only {Name}

# A/B-сравнение: генерация каждым вариантом
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Sarah --ref voice_candidates/Sarah/in_progress/Sarah_1.wav --limit 5
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Sarah --ref voice_candidates/Sarah/in_progress/Sarah_3.wav --limit 5

# Управление голосами
python tools/voice_manage.py list      # все голоса, активный реф, варианты
python tools/voice_manage.py status    # кто озвучен
python tools/voice_manage.py select Sarah 3  # выбрать вариант → ref/Sarah.wav

# Генерация (только отсутствующие файлы)
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Sarah --limit 10

# Перегенерация (все файлы, --force)
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Sarah --limit 5 --force
```

### Структура рефов

```
voice_candidates/{Name}/
  in_progress/{Name}_{variant}.wav  # рабочие варианты для A/B (сохраняются)
  ref/{Name}.wav                    # АКТИВНЫЙ реф (voices.yaml ссылается сюда)
```

Альтернативный реф без правки yaml: `voice_batch.py --ref`
`voice_candidates/{Name}/in_progress/{Name}_{variant}.wav`
(постфикс файла генерации = имя рефа: `{uid}__{variant}.wav`).

### Эмоции в генерации (рецепт, проверено 2026-09-02)

`voice_batch.py --emotion "..." --emotion-tag <тег>` — instruct2-режим
(эмоция + клонированный голос). ПРАВИЛА:

1. **Писать ТОЛЬКО на английском** — русские и китайские инструкции дают
   акцент (проверено).
2. **Формат — описание состояния, а не приказ**: «In a burst of passion,
   crying out with joy and ecstasy» работает идеально; «говори злобно»
   / «Speak angrily» — хуже.
3. **Эмоция работает, когда текст ей соответствует**: агрессивный текст
   + агрессивная эмоция = результат; нейтральный текст + эмоция = вяло
   (модель берёт тон из текста, инструкция вторична).
4. Пресеты: `--emotion angry|sad|happy|fast|slow|loud|soft|whisper` —
   англ. описания состояний (китайские шаблоны убраны).
5. Конфиг генерации — ОФИЦИАЛЬНЫЕ параметры модели (FunAudioLLM):
   `--flow-temp 0.8 --cfg-rate 0.7 --top-p 0.8 --top-k 25 --tau-r 0.1`
   (flow-temp 1.2/cfg 0.9 давали звуковые артефакты — заменено 2026-09-03).
6. Пофразовые эмоции: `catalog/emotions.json` (uid -> emotion_en),
   разметка `tools/emotion_tag.py` (эвристика или --llm-url phi4-mini);
   приоритет: `--emotion` (CLI) > emotions.json[uid] > без эмоции.
   `--no-emotion` отключает пофразовую (суффикс _plain);
   `--emotion-ru` — русский перевод для манифеста/ревью.
6. Манифест {wav}.txt фиксирует ref/emotion/конфиг — всегда рядом с wav.
7. Эмоция = состояние ДИКТОРА (кто произносит), не содержание текста:
   диалог участника — «In a burst of passion, crying out with joy and ecstasy»;
   наррация-наблюдение — «Erotically and sensually»; кульминация —
   «Crying out with joy, gasping through the spasms of orgasm».
   В текст добавляй эмоциональную пунктуацию («Ещё! Ещё! Да-а-а!»).

ВЫВОД (2026-09-03): конфиг + эмоция решают всё — официальные параметры
модели (batch в voice_presets.yaml) + пофразовая эмоция из emotions.json
дают чистую генерацию без артефактов. Эмоция автоматически берётся из
catalog/emotions.json при генерации каждой фразы.

```bash
... voice_batch.py --char Sarah --emotion "In a burst of passion, crying out with joy and ecstasy" --emotion-tag passion --limit 10
```

## Вариативность vs стабильность (проверено 2026-09-03)

Требование: один голос = один стиль. ВНУТРИ клипа голос не должен
«прыгать» (в начале ≠ в конце).

- Генерация кандидатов (voice_design): ОДНА конфигурация семплирования
  на всех — `temperature 0.9`, `top_p 0.9` (честное сравнение голосов;
  в yaml можно переопределить числами `temperature:` / `top_p:`).
- Кандидаты отличаются ТОЛЬКО инструкцией: `variations` (через `{style}`
  или «; ») — разные манеры, один тембр-ядро.
- Риск дрейфа голоса ВНУТРИ клипа создают:
  - длина текста > 20-30с (архитектурный дрейф CV3) — реплики игры 5-15с
    безопасны;
  - слишком высокие температура (>1.1) и top_p (1.0);
  - flow-temp (voice_batch) — выше 1.0 тембр «гуляет» на длинных фразах.
- RAS (штраф повторов) держим — он создан для стабильности LLM.

## Ударения (проверено 2026-09-03)

Unicode-ударение **U+0301** после ударной гласной РАБОТАЕТ:
«Тра́хай» = `Тра\u0301хай`. Заглавные буквы и апостроф ударения НЕ дают.
Ставить только в проблемных словах (омографы/редкие), не в каждом.
`--text "..."` — произвольный текст для демо (uid = md5(text), arc = --arc or Demo).

### Тесты

```bash
python -m pytest tests/ -v  # 37 тестов: voicekit, voice_sync, manage, batch, pipeline
```

## План работ

1. **Пилот: Prologue** (241 реплика) — Sarah, Narrator, Orwell, Thomas
2. Основные пути (WarriorPath/MagePath/SailorPath) → остальные арки
3. EN-озвучка после RU

## Открытые вопросы

- EN-рефы голосов (в игре озвучки нет) — источники
- Формат аудио: WAV (~16 ГБ/язык) vs OGG в игре (тест в пилоте)
- Fallback при отсутствии RU-файла: играть EN или молчать
