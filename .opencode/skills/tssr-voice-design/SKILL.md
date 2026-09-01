---
name: tssr-voice-design
description: Генерация голосов-кандидатов для TSSR по текстовому описанию (Qwen3-TTS VoiceDesign) — промт-дизайн тембра, генерация реплик-рефов ≥10с с автодобором длины, постобработка. Используй, когда нужно создать/дополнить голос персонажа, добавить новых кандидатов в voice_candidates/ или найти голос по типажу из cast.md.
---

# Skill: tssr-voice-design — Генерация голосов по промту

Генерация кандидатов-голосов для The Survival of Sarah Rose через
**Qwen3-TTS-12Hz-1.7B-VoiceDesign** (модель дизайна голоса по текстовому
описанию). Архитектура озвучки проекта — в `AGENTS.md` (читать обязательно).

## Где что лежит

```
tools/
  voice_design.py          # тул генерации (резюмабельный)
  voice_design_cast.py     # КАСТ: описание каждого голоса (base/vars/texts)
  voice_design.log         # лог прогонов
voice_candidates/{Имя}/    # сюда падают qwen_NN.mp3 (+ .md-заглушки для
                           # персонажей без каста — что искать)
```

## Запуск

**Важно:** нужен python с пакетом `qwen_tts` — это venv pinokio-приложения
Qwen3-TTS (`C:\pinokio\api\Qwen3-TTS-Pinokio.git\app\venv`). В cosyvoice-venv
пакета нет (там transformers 4.51, а qwen-tts требует 4.57+).

```bash
PY="C:\pinokio\api\Qwen3-TTS-Pinokio.git\app\venv\Scripts\python.exe"
"$PY" tools/voice_design.py --list                    # каст
"$PY" tools/voice_design.py --char Carolyn --n 6      # один персонаж, 6 шт
"$PY" tools/voice_design.py --n 3                     # весь каст по 3 шт
"$PY" tools/voice_design.py --char Narrator --n 5 --force  # перегенерить
```

Модель VoiceDesign (~4.3 ГБ) должна лежать в HF-кэше
`~/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign`.

CPU (torch+cpu): ~1-2 мин/клип. Весь каст — часы: запускай частями, тул
пропускает существующие файлы (резюм).

## Правила каста (voice_design_cast.py)

1. **Явный пол в тексте** — каждая фраза первого лица с маркером рода:
   «я пошёл/пошла», «я делал/делала», «я была/был». Иначе TTS путает пол.
2. **base** — всегда «Отчётливо женский/мужской голос, N лет, тембр, характер».
3. **vars** — 3 стиля подачи (циклятся по индексу кандидата).
4. **texts** — 100+ знаков каждая; один текст = один кандидат.
5. **≥10с** — рефы CosyVoice3 режутся до 10с (`add_candidate.py` берёт
   min(10, dur)), поэтому тул сам добирает длину: try2 «говори медленно,
   растягивая слова», try3 текст + следующая фраза. Короче 10с после трёх
   попыток — GIVE UP в логе.
6. Постобработка: срез ведущей тишины (silenceremove), mp3 24 kHz mono 96k.
   Большие паузы — брак; лечится промтом «паузы короткие».

## Как добавить новый голос

1. Если персонаж в `catalog/missing_voices.md` — проверь пол/возраст по игре
   (морфология RU-реплик + нарратив; каст может врать — Xanthippe мужчина,
   Kim/Dio женщины, Marion в игре мужчина).
2. Добавь блок в `tools/voice_design_cast.py` (base/vars/texts с маркерами пола).
3. Сгенерируй: `"$PY" tools/voice_design.py --char "{Имя}" --n 6`.
4. Отдай пользователю слушать; он сам отберёт и переименует победителя в
   `{Имя}.mp3` (add_candidate.py берёт первый mp3 по алфавиту).
5. Готовый голос — дальше обычный пайплайн: `add_candidate.py` → voices.yaml
   → `voice_status.py` → `voice_batch.py`.

## Папки-заглушки

`voice_candidates/{Имя}/{Имя}.md` — описание типажа: кто, пол, возраст,
характер, реплики, «что искать» (для охоты на fish.audio/YouTube). Папка без
.mp3 не участвует в add_candidate.py. После генерации qwen-кандидатов .md
можно оставить как справку.
