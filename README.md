# The Survival of Sarah Rose — Русская локализация (Russian Translation)

[![Русский перевод](https://img.shields.io/badge/lang-Русский-blue?style=flat-square)](game/tl/ru/)
[![Ren'Py](https://img.shields.io/badge/engine-Ren'Py%208.5-ff69b4?style=flat-square)](https://www.renpy.org/)
[![Steam](https://img.shields.io/badge/platform-Steam-1b2838?style=flat-square)](https://store.steampowered.com/)

**Полный русский перевод визуальной новеллы [The Survival of Sarah Rose](https://store.steampowered.com/app/2166470/The_Survival_of_Sarah_Rose/).**  

Переведены диалоги, интерфейс, описания и внутриигровые тексты. Перевод выполняется вручную, с сохранением стилистики и атмосферы оригинала.

---

## Установка

Откройте терминал в папке с игрой и выполните одну команду:

```bash
# Windows (PowerShell)
iwr https://raw.githubusercontent.com/Domovikx/The-Survival-of-Sarah-Rose/master/install.mjs -OutFile "$env:TEMP\install.mjs"; node "$env:TEMP\install.mjs"
```

```bash
# macOS / Linux
curl -sL https://raw.githubusercontent.com/Domovikx/The-Survival-of-Sarah-Rose/master/install.mjs > /tmp/install.mjs && node /tmp/install.mjs
```

Скрипт сам найдёт игру, скачает перевод и очистит кэш Ren'Py.

**Требуется [Node.js](https://nodejs.org/) — скачать и установить.**

---

## Выбор языка в игре

После установки запустите игру. В настройках (Settings) выберите язык **Russian**.

---

## Содержание перевода

- Пролог (OpeningScene, OpeningSceneEvening, OpeningSceneFirstMorning, OpeningSceneSequence2)
- Ветки сценария: MagePath, WarriorPath, SailorPath, DemonArc, HollowWorld, BlackMonolith
- Взаимодействия: HassarPath, JaeidPath, PrisonArc, AlfredArc, HyralArc
- Политические линии: UnionKingdom, VargaMarionPath, Training, StoryBeginnings
- Все строки интерфейса

<!-- TODO: Add screenshots with alt text for SEO
![Главное меню с русским переводом - The Survival of Sarah Rose](screenshots/main_menu_ru.png)
![Диалог в русской локализации - The Survival of Sarah Rose](screenshots/dialogue_ru.png)
![Настройки языка - Russian translation](screenshots/language_settings_ru.png)
-->

---

## Как помочь

- **Нашли ошибку в переводе?** [Откройте issue](https://github.com/Domovikx/The-Survival-of-Sarah-Rose/issues)
- **Хотите улучшить текст?** Сделайте pull request с правками в `game/tl/ru/`
- **Есть вопросы?** [Discussions](https://github.com/Domovikx/The-Survival-of-Sarah-Rose/discussions)

---

## Лицензия

Перевод распространяется на тех же условиях, что и оригинальная игра.
