---
name: tssr-voice
description: Generate voice lines for The Survival of Sarah Rose using CosyVoice3 voice cloning. Batch generation, uid mapping, language switching, ref cleaning and loudness normalization.
---

# Skill: tssr-voice — Озвучка TSSR

Генерация WAV для The Survival of Sarah Rose через Fun-CosyVoice3-0.5B (voice clone).
Архитектура, решения и тулы — в `AGENTS.md` проекта (обязательно читать).

## Ключевая идея: uid = md5(old)

`uid = md5(old-текста, UTF-8)` — полный 32-hex, язык-независимый ключ реплики.
`old` — исходный EN-текст из `translate ru strings:` (в рантайме = `_last_say_what`).

## Рантайм-раскладка

```
ai_voice/                    # КОРЕНЬ ПРОЕКТА (рядом с game/), не внутри game/
  ru/{Arc}/{uid}.wav         # русская озвучка (текст = new)
  en/{Arc}/{uid}.wav         # английская озвучка (текст = old)
game/
  catalog/label_arc.json     # label -> Arc (грузится voice_config.rpy)
  voice_config.rpy           # config.auto_voice = static_auto_voice (callable)
```

Arc в рантайме = label-часть translation ID (`OpeningScene_92a05bc0` → `OpeningScene`)
через `label_arc.json`. Папка вне game/ работает благодаря
`config.searchpath.append("")` в voice_config.rpy.

## Dev-структура refs (ТРИ папки, без дублей)

```
refs/raw/{Голос}.wav(+txt)   # грязная нарезка 10с + whisper-транскрипт
refs/voices/{Голос}.wav      # РАБОЧИЕ: вылечены + loudnorm (voices.yaml ссылается сюда)
refs/voices_en/{Голос}.wav   # EN-рефы (сейчас временные копии RU)
```

ПРАВИЛА ЛЕЧЕНИЯ РЕФОВ (2026-08-31, зафиксированы):
1. «Подшипливание» источника клонируется CV3 → чистим ДО генерации:
   `afftdn=nr=15, deesser=i=0.5, highshelf=f=8000:g=-6`
2. Громкость всех рефов выровнена: EBU R128 loudnorm, **-16 LUFS, TP -1.5**
   (иначе голоса «гуляли» и генерация наследовала уровень)
Оба — в `tools/clean_refs.py` (loudnorm двухпроходный).

## Тулы

| Тул | Назначение |
|---|---|
| `voice_catalog.py` | tl/ru + script.rpy → catalog/voices.json + label_arc.json (только при апдейте игры) |
| `voice_status.py` | отчёт готово/нет голоса → catalog/missing_voices.md (заглушки) |
| `add_candidate.py` | кандидат MP3 → raw-нарезка + txt + вылеченный реф (инкрементально) |
| `clean_refs.py` | лечение+громкость: refs/raw → refs/voices |
| `voice_batch.py` | батч-генерация в ai_voice/{lang}/{arc}/{uid}.wav |
| `trim_tail_burst.py` | паттерн-трим хвостов (импортится батчем) |

## Генерация

```bash
# ОБЯЗАТЕЛЬНО через venv CosyVoice
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py \
  [--arc Prologue] [--char Sarah] [--uid uid1 uid2 ...] [--limit N]
  [--force] [--lang ru|en] [--dry-run]
```

- Модель грузится 1 раз; resumable (существующие скипаются)
- Победный конфиг: cross_lingual + RL, flow-temp 1.2, cfg 0.9, RAS 0.5/10/0.15, seed 42, silent-trim
- Озвучиваются только dialogue+наррация и только персонажи из config/voices.yaml
- Автотрим хвостов (паттерн: тишина ≥80мс → всплеск ≤500мс у конца файла)

## Добавление нового голоса

```bash
# 1. Положить кандидата: voice_candidates/{Имя}/*.mp3
# 2. Собрать нарезку + транскрипт + вылеченный реф:
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/add_candidate.py
# 3. Вписать напечатанный фрагмент в config/voices.yaml (ref → refs/voices/)
# 4. Обновить отчёт заглушек:
python tools/voice_status.py
# 5. Сгенерировать реплики этого персонажа:
C:\tools\cosyvoice3\.venv\Scripts\python.exe tools/voice_batch.py --char "{Имя}" --limit 10
```

## Диагностика

- `voice_debug.log` (корень проекта) — каждая попытка резолва:
  `CALL tlid=... text=... lang=... path=... loadable=...`
- `output/voice/batch.log` — лог генерации
- Тишина в игре → проверить: (1) нет ли стейловых `.rpyc` рядом с `voice_config.rpy`,
  (2) `loadable=True` в debug-логе, (3) громкость Voice в настройках игры

## Известные проблемы

1. **Стресс в русском** — cross_lingual может ставить неверное ударение. Решение: пробовать zero_shot / instruct2.
2. **Хвостовые артефакты** — вздохи у конца фразы → `trim_tail_burst.py` (автоматически в батче).
3. **Забытый .rpyc** — Ren'Py грузит `.rpyc` даже без `.rpy`; старые кэши затирают конфиг (случай 2026-08-31: voice_test.rpyc переопределял auto_voice).
