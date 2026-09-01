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
  missing_voices.md            # ЗАГЛУШКИ: кто без голоса (генерится voice_status.py)
config/
  voices.yaml                  # персонаж -> реф голоса; нет записи = не озвучиваем
tools/
  voice_catalog.py             # tl/ru + script.rpy -> voices.json + label_arc.json
  voice_status.py              # отчёт готово/нет голоса -> missing_voices.md
  add_candidate.py             # MP3-кандидат -> реф (нарезка + чистка одномерным прогоном;
                               # qwen_*.mp3 ИГНОРИРУЮТСЯ — это не рефы)
  clean_refs.py                # лечение рефов: highpass+денойз+deesser+EQ+LOUDNORM+фейды
  voice_batch.py               # батч-генерация: каталог -> ai_voice/{lang}/{arc}/{uid}__{variant}.wav
                               # (модель 1 раз, resumable, автотрим; фильтры --arc/--char/--uid/--ref)
  trim_tail_burst.py           # паттерн-трим хвостовых артефактов (импортится батчем)
  voice_manage.py              # управление голосами: list/status/select
                               # (select сам перегенерирует who_variant)
  voice_runtime_map.py         # voices.yaml + каталог -> catalog/who_variant.json
  levelnorm.py                 # выравнивание реплик: -16 LUFS / TP -1.5
                               # (вызывается voice_batch'ем после сохранения;
                               #  CLI: --dir ai_voice/ru — для старых файлов)
  voice_preview.py             # 3 самых длинных фразы × каждый реф -> ревью-таблица
refs/                          # ГОТОВЫЕ рефы (нарезка 10с + чистка + loudnorm), ПЛОСКАЯ:
  {Голос}.wav                  # активный реф: сюда ссылается config/voices.yaml
  {Голос}_{variant}.wav        # варианты для A/B-тестирования
```

ВАЖНО: рабочие рефы ВСЕГДА из refs/ (вылеченные). Правила лечения
(решение 2026-09-01, актуализировано):
  1. «Подшипливание» источника клонируется CV3 — рефы чистятся ДО генерации:
     `highpass=f=60, afftdn=nr=15, deesser=i=0.5, highshelf=f=8000:g=-6`
  2. Громкость всех рефов выровнена EBU R128 loudnorm: -16 LUFS, TP -1.5
     (иначе голоса «гуляли» по уровню и генерация наследовала громкость)
  3. Фейды 30мс по краям — защита от кликов
Всё — в tools/clean_refs.py, применяется автоматически add_candidate.py
(одним прогоном: mp3 -> нарезка 10с -> чистка -> refs/{Голос}.wav).

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
#    (qwen_*.mp3 игнорируются — это VoiceDesign-кандидаты, не рефы)
# 2. Собрать реф (существующие скипаются):
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
3. Генерация ПО КАЖДОМУ варианту (файлы лежат рядом, постфикс = реф):
   voice_batch.py --char Sarah --ref refs/Sarah_1.wav --limit 5
   voice_batch.py --char Sarah --ref refs/Sarah_3.wav --limit 5
   → ai_voice/ru/{arc}/{uid}__Sarah_1.wav и {uid}__Sarah_3.wav
4. Выбор: слушаешь пары в ai_voice/ru/{arc}/ (одинаковые uid рядом)
5. Фиксация: voice_manage.py select {Name} {variant}
   → копирует refs/{Name}_{variant}.wav → refs/{Name}.wav
   → обновляет config/voices.yaml
   → перегенерирует catalog/who_variant.json
6. Генерация: voice_batch.py --char {Name} — использует активный реф
   (файлы проигравшего варианта при желании удаляются вручную)
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
  --char Sarah --ref refs/Sarah_1.wav --limit 5
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Sarah --ref refs/Sarah_3.wav --limit 5

# Управление голосами
python tools/voice_manage.py list      # все голоса, активный реф, варианты
python tools/voice_manage.py status    # кто озвучен
python tools/voice_manage.py select Sarah 3  # выбрать вариант → refs/Sarah.wav

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
  {Name}.wav           # АКТИВНЫЙ реф (вылеченный, используется voice_batch)
  {Name}_{variant}.wav # варианты для сравнения (Sarah_1, Sarah_3, ...)
```

Альтернативный реф без правки yaml: `voice_batch.py --ref refs/{Name}_{variant}.wav`
(постфикс файла генерации = имя рефа: `{uid}__{variant}.wav`).

### Тесты

```bash
python -m pytest tests/ -v  # 16 тестов: voice_manage, voice_batch, clean_refs
```

## План работ

1. **Пилот: Prologue** (241 реплика) — Sarah, Narrator, Orwell, Thomas
2. Основные пути (WarriorPath/MagePath/SailorPath) → остальные арки
3. EN-озвучка после RU

## Открытые вопросы

- EN-рефы голосов (в игре озвучки нет) — источники
- Формат аудио: WAV (~16 ГБ/язык) vs OGG в игре (тест в пилоте)
- Fallback при отсутствии RU-файла: играть EN или молчать
