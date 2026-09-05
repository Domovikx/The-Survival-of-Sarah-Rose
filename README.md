# The Survival of Sarah Rose — Russian Localization + AI Voice Pack / Русификатор + AI-озвучка

[![Русский перевод](https://img.shields.io/badge/перевод-100%25-blue?style=flat-square)](game/tl/ru/)
[![Russian translation](https://img.shields.io/badge/translation-100%25-blue?style=flat-square)](game/tl/ru/)
[![Озвучка / Voice](https://img.shields.io/badge/voice-RU%2BEN-green?style=flat-square)](ai_voice/)
[![Ren'Py](https://img.shields.io/badge/engine-Ren'Py%208.5-ff69b4?style=flat-square)](https://www.renpy.org/)
[![Steam](https://img.shields.io/badge/platform-Steam-1b2838?style=flat-square)](https://store.steampowered.com/)
[![License CC BY-NC 4.0](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey?style=flat-square)](LICENSE)

**English · [Русский](#русская-версия)**

Full Russian fan translation + AI voice acting for the visual novel **The Survival of Sarah Rose** (Ren'Py, Steam).
Полный русский перевод + AI-озвучка визуальной новеллы **The Survival of Sarah Rose** (Ren'Py, Steam).

- 68 254 lines translated / 68 254 строки переведено
- AI voice pack in two languages (RU + EN) / AI-озвучка на двух языках (RU + EN)
- 75+ characters with cloned voices / 75+ персонажей с клонированными голосами
- Emotion-aware delivery / эмоциональная озвучка каждой реплики
- Free, open source, CC BY-NC 4.0 / бесплатно, открытый код

---

# English

[Download ZIP](#download) • [Installation](#installation) • [Voice pack](#voice-pack) • [Screenshots](#screenshots) • [FAQ](#faq)

## Features

| | |
|---|---|
| 🌐 **Full Russian translation** | 68 254 lines: dialogues, narration, UI, character names |
| 🎙 **AI voice acting (RU + EN)** | cloned voices for every main character — the game becomes fully voiced |
| 🎭 **Emotion-aware delivery** | every line carries the director's emotional state (anger, desire, whisper, sarcasm, ...) |
| 🗣 **75+ voices** | Sarah, Narrator, King Orwell, Kate, Thomas and dozens more |
| 🔊 **Two languages** | switch language in-game — the voice pack follows automatically |
| ⚙️ **Ren'Py 8.5** | works with the Steam version of the game |

## Download

[**⬇ Download ZIP**](https://github.com/Domovikx/The-Survival-of-Sarah-Rose/archive/refs/heads/master.zip) — latest version (translation + voice pack).

> The ZIP already contains everything: `game/` (translation + voice engine) and `ai_voice/` (voice lines). No extra downloads needed.

## Installation

1. Copy the contents of the ZIP into the game folder
   (Steam default: `C:\Program Files (x86)\Steam\steamapps\common\The Survival of Sarah Rose\`) with file replacement
2. Launch the game, in settings select **Language → Russian** (or English — voices follow the language)
3. Done — the game is voiced

> First launch after installation may be slower (Ren'Py cache rebuild).

## Voice pack

The voice pack is generated with **CosyVoice3** (voice cloning) and covers both languages:

| Language | Voice files | Status |
|---|---|---|
| **Russian (RU)** | `ai_voice/ru/...` | in active generation |
| **English (EN)** | `ai_voice/en/...` | in active generation |

- Voice lookup is automatic: `uid = md5(text)` → `ai_voice/{lang}/{arc}/{uid}__{voice}.wav`
- Every line has an emotion instruction (state of the narrator/speaker)
- Fallback: if a file is missing, the game plays silently (no crashes)

> ⚠ The voice pack is large (hundreds of MB and growing). Check disk space.

## Contents

### Translated arcs (all 19)

Prologue, StoryBeginnings, WarriorPath, MagePath, UnionKingdom, HollowWorld, BlackMonolith, HassarPath, SailorPath, SailorArc, LifeInRahayal, VargaMarionPath, Training, PrisonArc, AlfredArc, DemonArc, WarArc, HyralArc, Other — **68 254 lines total**.

### Voiced characters (75+)

Sarah, Narrator, King Orwell Rose, Kate, Thomas, Varga, Captain Belmont, Alaric, Carolyn, Marion, Kravel, Barion, Basilisk and many more — every character has a unique cloned voice with emotional delivery.

## Screenshots

![Main menu in Russian](screenshots/main_menu_russian.jpg)
![Russian dialogue](screenshots/dialogue_russian_1.jpg)
![Language settings](screenshots/language_settings_russian.jpg)
![Russian dialogue 2](screenshots/dialogue_russian_2.jpg)

## FAQ

### What is this?
An unofficial fan **Russian localization** (русификатор) for the visual novel **The Survival of Sarah Rose**, plus an **AI voice pack** that fully voices the game in Russian and English.

### How do I install the Russian translation / русификатор?
Copy the ZIP contents into the game folder, select Language → Russian in settings, clear Ren'Py cache if text is not showing.

### How does the voice acting work?
Voices are cloned from custom reference recordings with CosyVoice3 and generated for every line in both languages. The game loads `ai_voice/{lang}/{arc}/{uid}__{voice}.wav` automatically.

### Is the translation official?
No — this is an unofficial fan project, not affiliated with the developers or publishers.

### Does it contain adult content?
**Yes — 18+.** The game contains explicit adult material. Download and play only if you are **18 or older**. Keep it away from minors; you are responsible for complying with your local laws (see [LICENSE](LICENSE)).

### License?
**CC BY-NC 4.0** — free to share and adapt with attribution, non-commercial only.

### How to help?
Open an issue or submit a pull request on GitHub.

---

# Русская версия

[Скачать ZIP](#скачать) • [Установка](#установка) • [Озвучка](#озвучка) • [Скриншоты](#скриншоты-1) • [FAQ](#faq-1)

## Возможности

| | |
|---|---|
| 🌐 **Полный русский перевод** | 68 254 строки: диалоги, нарратив, интерфейс, имена персонажей |
| 🎙 **AI-озвучка (RU + EN)** | клонированные голоса всех главных героев — игра становится полностью озвученной |
| 🎭 **Эмоциональная подача** | каждая реплика несёт состояние диктора (гнев, страсть, шёпот, сарказм...) |
| 🗣 **75+ голосов** | Сара, Рассказчик, Король Орвелл, Кейт, Томас и десятки других |
| 🔊 **Два языка** | переключай язык в игре — озвучка подстраивается автоматически |
| ⚙️ **Ren'Py 8.5** | работает со Steam-версией игры |

## Скачать

[**⬇ Скачать ZIP**](https://github.com/Domovikx/The-Survival-of-Sarah-Rose/archive/refs/heads/master.zip) — последняя версия (перевод + озвучка).

> В ZIP уже всё: `game/` (перевод + голосовой движок) и `ai_voice/` (реплики). Ничего дополнительно качать не нужно.

## Установка

1. Скопируйте содержимое ZIP в папку с игрой
   (Steam: `C:\Program Files (x86)\Steam\steamapps\common\The Survival of Sarah Rose\`) с заменой файлов
2. Запустите игру, в настройках выберите **Language → Russian** (или English — озвучка подстроится)
3. Готово — игра озвучена

> Первый запуск после установки может быть медленнее (пересборка кэша Ren'Py).

## Озвучка

Озвучка создана на **CosyVoice3** (клонирование голоса) и покрывает оба языка:

| Язык | Файлы | Статус |
|---|---|---|
| **Русский (RU)** | `ai_voice/ru/...` | в активной генерации |
| **Английский (EN)** | `ai_voice/en/...` | в активной генерации |

- Поиск голоса автоматический: `uid = md5(текста)` → `ai_voice/{lang}/{arc}/{uid}__{voice}.wav`
- У каждой реплики есть эмоция — состояние диктора/рассказчика
- Если файла нет — игра просто играет без звука (без ошибок)

> ⚠ Озвучка большая (сотни МБ и растёт). Следи за местом на диске.

## Содержание

### Переведённые арки (все 19)

Prologue, StoryBeginnings, WarriorPath, MagePath, UnionKingdom, HollowWorld, BlackMonolith, HassarPath, SailorPath, SailorArc, LifeInRahayal, VargaMarionPath, Training, PrisonArc, AlfredArc, DemonArc, WarArc, HyralArc, Other — **68 254 строки**.

### Озвученные персонажи (75+)

Сара, Рассказчик, Король Орвелл, Кейт, Томас, Варга, Капитан Бельмонт, Аларик, Кэролин, Марион, Кравэл, Барион, Базилиск и многие другие — у каждого уникальный клонированный голос с эмоциональной подачей.

## Скриншоты

![Главное меню на русском](screenshots/main_menu_russian.jpg)
![Русский диалог](screenshots/dialogue_russian_1.jpg)
![Настройки языка](screenshots/language_settings_russian.jpg)
![Русский диалог 2](screenshots/dialogue_russian_2.jpg)

## FAQ

### Что это?
Неофициальный фанатский **русификатор** визуальной новеллы **The Survival of Sarah Rose**, плюс **AI-озвучка**, которая полностью озвучивает игру на русском и английском.

### Как установить русификатор?
Скопируйте содержимое ZIP в папку с игрой, выберите в настройках русский язык, при необходимости очистите кэш Ren'Py.

### Как работает озвучка?
Голоса клонированы с референсных записей через CosyVoice3 и сгенерированы для каждой реплики на обоих языках. Игра автоматически подгружает `ai_voice/{lang}/{arc}/{uid}__{voice}.wav`.

### Это официальный перевод?
Нет — неофициальный фанатский проект, не связанный с разработчиками и издателями.

### В игре есть взрослый контент?
**Да — 18+.** Игра содержит откровенные взрослые материалы. Скачивайте и играйте, только если вам **18 лет и больше**. Не допускайте к материалу несовершеннолетних; вы несёте ответственность за соблюдение законов вашей страны (см. [LICENSE](LICENSE)).

### Лицензия?
**CC BY-NC 4.0** — свободное распространение и адаптация с указанием авторства, только некоммерческое использование.

### Как помочь проекту?
Откройте issue или сделайте pull request на GitHub.

---

## О проекте / Project

- **Репозиторий / Repository:** [github.com/Domovikx/The-Survival-of-Sarah-Rose](https://github.com/Domovikx/The-Survival-of-Sarah-Rose)
- **Игра в Steam / Game on Steam:** [The Survival of Sarah Rose](https://store.steampowered.com/app/2166470/The_Survival_of_Sarah_Rose/)
- **Issues:** [github.com/Domovikx/The-Survival-of-Sarah-Rose/issues](https://github.com/Domovikx/The-Survival-of-Sarah-Rose/issues)

---

## Лицензия и отказ от ответственности / License & Disclaimer

**Файлы перевода** (`game/tl/ru/`) и **озвучка** (`ai_voice/`) распространяются под лицензией [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — свободное использование и распространение с указанием авторства, только некоммерческое. / Translation files and the voice pack are distributed under the [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) license.

**18+:** Игра содержит откровенный взрослый контент — используя проект, вы подтверждаете, что вам 18+. / The game contains explicit adult content — by using this project you confirm you are 18+.

**Отказ от ответственности:** неофициальная фанатская работа. Все права на оригинальную игру принадлежат её правообладателям. Используйте на свой страх и риск. / This is an unofficial fan work. All rights to the original game belong to its rights holders. Use at your own risk.