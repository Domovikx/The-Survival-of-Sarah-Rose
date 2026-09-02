# Архитектура voice_candidates — v2 (решение по фидбэку)

> Статус: РЕШЕНИЕ (2026-09-02). Демо на примере `voice_candidates/Alaric`.
> Итоги обсуждения вариантов A/B/C (документ v1) — выбран «конвейер с
> финальной зоной»: `generated → gen_selected → refs → ref_selected`.

---

## Проблема-триггер

`voice_design.py:272` пишет `01.mp3..NN.mp3` прямо в папку персонажа, а
`add_candidate.py:55-59` исключает только `qwen_*.mp3` → всё сырьё
превращается в рефы без отбора. Разделитель `qwen_*` ушёл — «сгенерировано»
и «отобрано» неразличимы по файлам.

Пример: у Alaric сейчас 6 свежих `01..06.mp3` + старый `refs/Alaric.wav`,
и запуск add_candidate наделал бы `refs/Alaric_01..06.wav` из неотобранного.

---

## Целевая структура (папка персонажа)

```
voice_candidates/{Name}/
  {Name}.yaml              # КОНТРАКТ (+ отчёт: скрипты дописывают статус)
  generated/               # СЫРЬЁ: всё, что наплодил voice_design (01.mp3..NN.mp3)
  gen_selected/            # ОТБОР: вручную отобранные из generated
                           #   ({Name}.mp3, {Name}_1.mp3 — явное «выбрано»)
  refs/                    # РАБОЧАЯ зона: add_candidate нарезает 10с + чистит
                           #   ({Name}.wav, {Name}_1.wav — A/B-варианты;
                           #    эксперименты с фильтрами; demo/ — демо-реплики)
  ref_selected/            # ФИНАЛ: идеальный реф {Name}.wav
                           #   единственное, что видит система (voices.yaml)
```

Конвейер строго односторонний: `generated → gen_selected → refs → ref_selected`.
`ref_selected/` = единый источник истины для генерации реплик.

---

## Схема конвейера (на примере Alaric)

```
 voice_design --char Alaric
        │
        ▼
 ┌──────────────────────────────────────────────────────┐
 │ voice_candidates/Alaric/                             │
 │                                                      │
 │  generated/  01.mp3 02.mp3 03.mp3 04.mp3 05.mp3 06.mp3 │ ← сырьё (авто)
 │                    │                                 │
 │                    │  слушаешь на слух, копируешь    │
 │                    ▼  лучшие вручную                 │
 │  gen_selected/  Alaric_1.mp3  Alaric_2.mp3           │ ← отбор (вручную)
 │                    │                                 │
 │                    │  add_candidate --only Alaric    │
 │                    ▼  (нарезка 10с + чистка)         │
 │  refs/  Alaric_1.wav  Alaric_2.wav  demo/            │ ← рабочие (авто)
 │                    │                                 │
 │                    │  A/B: voice_batch --ref         │
 │                    ▼  refs/Alaric_1.wav ...          │
 │  ref_selected/  Alaric.wav                           │ ← финал (авто,
 │                                                      │    voice_manage
 │                                                      │    select Alaric 1)
 └──────────────────────┬───────────────────────────────┘
                        │  config/voices.yaml:
                        │    ref: voice_candidates/Alaric/ref_selected/Alaric.wav
                        ▼
              voice_batch --char Alaric
                        │
                        ▼
        ai_voice/ru/{arc}/{uid}__Alaric.wav
```

Роли:

| Стадия        | Папка           | Кто пишет                                | Кто читает                                                   | Правило                                                           |
| ------------- | --------------- | ---------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------- |
| Сырьё         | `generated/`    | voice_design (авто)                      | человек                                                      | резюмабельно: существующие `NN.mp3` не пересоздаются              |
| Отбор         | `gen_selected/` | человек (копия из generated)             | add_candidate                                                | только сюда смотрит add*candidate; имя = `{Name}[*{вариант}].mp3` |
| Рабочие рефы  | `refs/`         | add_candidate, clean_refs (авто)         | voice_batch `--ref`, voice_manage, voice_preview             | песочница: варианты чистки, фильтры, `demo/`                      |
| Финальный реф | `ref_selected/` | voice_manage `select` (копия победителя) | voice_batch (через voices.yaml), voice_manage, voice_preview | `voice_ready` = существует `{Name}.wav`                           |

---

## Пример: Alaric после миграции

Текущее состояние:

```
voice_candidates/Alaric/
  Alaric.yaml              # контракт
  01.mp3 .. 06.mp3         # сырьё от voice_design (2 Sep)
refs/
  Alaric.wav               # старый активный реф (1 Sep) → мигрирует
```

После миграции:

```
voice_candidates/Alaric/
  Alaric.yaml                        # контракт + отчёт
  generated/
    01.mp3 02.mp3 03.mp3 04.mp3 05.mp3 06.mp3   # как было
  gen_selected/                                # выбрал на слух 02 и 05
    Alaric_1.mp3                               # копия generated/02.mp3
    Alaric_2.mp3                               # копия generated/05.mp3
  refs/
    Alaric_1.wav                               # рабочий реф (10с, чистка)
    Alaric_2.wav                               # рабочий реф (10с, чистка)
    demo/                                      # демо-реплики для ревью
  ref_selected/
    Alaric.wav                                 # победитель A/B (финал)
```

`config/voices.yaml`:

```yaml
Alaric:
  ref: voice_candidates/Alaric/ref_selected/Alaric.wav
  who:
    - al
  gender: M
```

`voice_batch.py` менять НЕ нужно — он делает `os.path.join(ROOT, ref_cfg)`
(voice_batch.py:130).

---

## Контракт `{Name}.yaml` (контракт + отчёт)

Файл = контракт (обязательные поля, валидируются строго) + отчёт
(опциональные поля скриптов, «свои поля для своих дел», не нарушают контракт).

### Контрактные поля (обязательные)

| Поле          | Тип           | Назначение                               |
| ------------- | ------------- | ---------------------------------------- |
| `name`        | str           | имя голоса = имя папки                   |
| `gender`      | M / F         | пол (для typeaжа и инструкции)           |
| `age`         | str           | возрастной диапазон («25-30»)            |
| `who`         | str           | роль персонажа в игре (человекочитаемо)  |
| `instruct_en` | str           | англ. описание тембра для VoiceDesign    |
| `texts`       | list[str] ≥ 1 | рус. реплики-рефы с явным признаком пола |

### Отчётные поля (пишут скрипты, контракт не трогают)

`status: {generated, gen_selected, refs, ref_selected, voice_ready, last_run}`,
а также любые будущие поля (extra allowed).

### Пример Alaric.yaml

```yaml
name: Alaric
gender: M
age: "25-30"
who: >-
  «low life» из свободного города, обаятельный жулик, спутник/любовник Сары
  в MagePath.
instruct_en: >-
  Male, 25-30 years old, medium-low velvet baritone, charming rogue, cynical
  and sarcastic, smooth delivery with slight smirk in voice
texts:
  - Я пошёл через весь город, только чтобы добраться до тебя, и даже не пожалел о том, что потратил столько времени на дорогу.
  - Я делал всё, что мог, чтобы вытащить нас из этой передряги, но некоторые решения приходится принимать быстро и без лишних вопросов.

# ── отчёт (пишут скрипты) ────────────────────────────────────────
status:
  generated: 6 # voice_design: клипов в generated/
  gen_selected: [Alaric_1.mp3, Alaric_2.mp3] # add_candidate: что взял
  refs: [Alaric_1.wav, Alaric_2.wav] # add_candidate: что сделал
  ref_selected: Alaric.wav # voice_manage select: финал
  voice_ready: true
  last_run: 2026-09-02 20:11
```

### Валидация контракта (ресёрч по типизации YAML)

Варианты: pydantic v2 / JSON Schema+jsonschema / yamale / cerberus.

**Решение: pydantic v2** — код = контракт:

- `tools/cast_contract.py` (новый): модель `CastContract` с обязательными
  полями (`gender: Literal["M","F"]`, `texts: min_length=1`, ...) и
  `model_config = ConfigDict(extra="allow")` — отчёт-поля проходят свободно.
- Все скрипты читают каст через `CastContract.model_validate(yaml.safe_load(...))`
  и пишут отчёт через `model_dump()` (чужие поля сохраняются).
- `CastContract.model_json_schema()` → `voice_candidates/cast_schema.json`:
  автокомплит yaml в VS Code (redhat.vscode-yaml, `yaml.schemas` в .vscode/settings.json).
- Тест `tests/`: все 64 `{Name}.yaml` валидны по контракту.

Зависимость: pydantic есть в system python и qwen venv (2.13.4), в
cosyvoice venv отсутствует → одноразово `pip install pydantic`
(нужен только для add_candidate, остальные потребители каста уже имеют).

---

## Изменения по файлам

| Файл                             | Что                                                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `tools/cast_contract.py` (НОВЫЙ) | pydantic-модель контракта, валидация, экспорт JSON Schema                                                             |
| `tools/voice_design.py`          | dst → `{Name}/generated/{NN:02d}.mp3`; отчёт `status.generated`                                                       |
| `tools/add_candidate.py`         | вход `gen_selected/`, выход `refs/` (рабочие); сниппет → `ref_selected`                                               |
| `tools/voice_manage.py`          | select: `refs/{Name}_{v}.wav` → `ref_selected/{Name}.wav` + voices.yaml; list/status показывают обе зоны; пишет отчёт |
| `tools/voice_design_stats.py`    | status по `ref_selected/`; candidates = `generated/`; сводка + отчёт                                                  |
| `tools/voice_preview.py`         | читает `refs/` (A/B) и `ref_selected/` (активный); demo → `refs/demo/`                                                |
| `config/voices.yaml`             | 40 записей `ref:` → `voice_candidates/{Name}/ref_selected/{Name}.wav`                                                 |
| `tests/`                         | тест валидности каста по контракту                                                                                    |
| Миграция                         | см. ниже                                                                                                              |
| AGENTS.md                        | структура, контракт, команды, A/B-цикл                                                                                |

---

## Миграция (одноразово)

1. Создать 4 подпапки в каждой папке персонажа.
2. `voice_candidates/{Name}/*.mp3`:
   - `NN.mp3` (множественные, сырьё от voice_design: Alaric, Atilla, Metis,
     Naydeen, Ramsey, Samayra) → `generated/`;
   - `{Name}.mp3` (единичные, отобранные вручную: Ayaka, Kate, ...) → `gen_selected/`.
3. `refs/{Name}_{variant}.wav` (A/B-варианты) → `voice_candidates/{Name}/refs/`.
4. `refs/{Name}.wav` (активные, 40 шт.) → `voice_candidates/{Name}/ref_selected/`.
5. Пустой `refs/` удалить.
6. `config/voices.yaml`: заменить все `ref:` пути (механически, по имени).
7. `voice_candidates/voice_candidates.yaml` (сводка) — пересобрать
   `voice_design_stats.py` (status: `voice_ready` = есть `ref_selected/{Name}.wav`).

---

## Поток работ (команды после миграции)

```bash
# 1. Генерация кандидатов
"$PY" tools/voice_design.py --char Alaric --n 6          # → generated/01..06.mp3

# 2. Отбор: слушаешь generated/, копируешь лучшие
#    (хелпер: add_candidate --pick 02 05 → сам скопирует в gen_selected/ как Alaric_1.mp3...)

# 3. Рабочие рефы
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/add_candidate.py --only Alaric
#    → gen_selected/*.mp3 → refs/Alaric_1.wav, refs/Alaric_2.wav

# 4. A/B: реплики каждым рабочим рефом
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Alaric --ref voice_candidates/Alaric/refs/Alaric_1.wav --limit 5
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  --char Alaric --ref voice_candidates/Alaric/refs/Alaric_2.wav --limit 5

# 5. Фиксация победителя
python tools/voice_manage.py select Alaric 1
#    → refs/Alaric_1.wav → ref_selected/Alaric.wav, voices.yaml, отчёт в Alaric.yaml

# 6. Массовая генерация финалом
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py --char Alaric
```

---

## Открытые вопросы

- Хелпер `--pick` в add_candidate (автокопирование generated → gen_selected) —
  делать в первой итерации или вручную? -------- только вручную
- `refs/demo/` — демо-реплики voice_preview кладёт сюда или оставить --------- на дэмо пока полностью забьем не требуется
  `output/voice/` как сейчас? ---------- Это пона не будем делать
- Удалять проигравшие рабочие рефы из `refs/` автоматически после select? -------- всё сохраняем для историчности

фитбэк :
я думаю оставить ямл

нужен тул который при необходимости пройдет по ресурсам выявит НОВЫЕ голоса для озвучки, всёже игра может динамично развиваться и меняться, скорее будут новые голоса но и если тул проверит наличие или изменение старых будет не плохо,
для тула можно сделать справочный информационный скил, чтобы анент как минимум знал что есть тул и он работает, если тулы хорошо работают и без скила и анент о тулах все знает то можно не заморачиваться, но обычно с тулом быстрее.

кстати есть ли в вскоде экстеншен который будет позволять надиктовывать и голос будет переводиться в текст , а то я устаю много писать. а было бы удобнее. но это так, боковик.

итак тул будет отвечать за актуализацию и обновление, а значит первичный ямл с полями и папками мы можем ожидать от такого процесса, ямл по структуре а папки пустые могут быть ? наверное да... ну тоесть тул пробежался создал структуру что надо где надо обновил ИЛИ скипнул что не надо, главное чтобы случайно не удалял и не перетирал. тул можно тестом покрыть, лишним не будет. я чтото еще забыл ? не вроде ничего, работаем по mvp форкфлоу, тоесть получаем первичку с которой можно работать и идем дальше, не стараемся сейчас закрыть всё и вся.

и смотри если у нас уже есть
voice_candidates\Albert\Albert.mp3 - это переносим в gen_selected, я буду стараться всегда туда ложить только 1 топ файл, я бы вообще запретил работать со множеством это ОЧЕНЬ тормозит процесс ревью и прочего
voice_candidates\Albert\Albert.yaml - это актуализируем
соответственно папки можно по структуре создать НО мне кажется нет смысла делать
generated прямо сейчас, просто папку делаем и я потом решу делать или нет, может когдато на ночь процесс поставим для папок которые пустые, то точно не сейчас
refs/ я бы переименовал хз во что может in_progress или чтотоо типа того в котором мы проводим чистки подготовки обработки фильтрами и прочие активности чтобы получить в итоге идеальный файл
и вот этот файл я потом перу в единственном числе и копирую или мувлю в ref/

будет в итоге как то вот так
voice_candidates\Albert\ref\

как тебе план ?
