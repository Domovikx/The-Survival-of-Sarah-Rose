# The Survival of Sarah Rose — Русская локализация (Russian Translation)

[![Русский перевод](https://img.shields.io/badge/lang-Русский-blue?style=flat-square)](game/tl/ru/)
[![Ren'Py](https://img.shields.io/badge/engine-Ren'Py%208.5-ff69b4?style=flat-square)](https://www.renpy.org/)
[![Steam](https://img.shields.io/badge/platform-Steam-1b2838?style=flat-square)](https://store.steampowered.com/)
[![Перевод](https://img.shields.io/badge/перевод-72%25-brightgreen?style=flat-square)](game/tl/ru/)

**Русификатор (русская локализация) визуальной новеллы [The Survival of Sarah Rose](https://store.steampowered.com/app/2166470/The_Survival_of_Sarah_Rose/).**

Полный перевод диалогов, интерфейса, описаний и внутриигровых текстов на русский язык. Перевод выполняется вручную, с сохранением стилистики и атмосферы оригинала. Проект в активной разработке — новые главы переводятся и публикуются регулярно.

---

## Установка русификатора

Скопируйте папку `game/tl/ru/` из репозитория в папку с игрой (`The Survival of Sarah Rose/game/tl/ru/`).

Дополнительно скопируйте файлы из репозитория в корень `game/`:

| Файл | Назначение |
|------|-----------|
| `game/screens.rpy` | Интерфейс (шрифт, переключатель языка) |
| `game/gui.rpy` | Настройки GUI |
| `game/options.rpy` | Опции игры |
| `game/language.rpy` | Языковой файл |
| `game/language_switcher.rpy` | Переключатель языка |
| `game/fonts/Forum-Regular.ttf` | Шрифт с кириллицей |

После копирования очистите кэш Ren'Py (удалите `game/*.rpyc` и `game/**/*.rpyc`).

---

## Выбор языка в игре

Запустите игру. В настройках (Settings) выберите язык **Russian**.

---

## Статус перевода

Актуальное состояние русификации на текущий момент:

| Раздел                                       | Строк    | Статус                        |
| -------------------------------------------- | -------- | ----------------------------- |
| Пролог (4 файла)                             | 241      | ✅ 100%                       |
| StoryBeginnings (10 файлов)                  | 1035     | 🟡 95% (5 файлов с 88–99%)    |
| Training (12 файлов)                         | 1546     | ✅ 100%                       |
| misc_strings.rpy (имена персонажей)          | 151      | ✅ 100%                       |
| screens.rpy (интерфейс)                      | 102      | 🟡 90%                        |
| WarriorPath (18 файлов)                      | 8646     | ✅ 100%                       |
| UnionKingdom (21 файл)                       | 5253     | ✅ 100%                       |
| HassarPath (12 файлов)                       | 2895     | ✅ 100%                       |
| BlackMonolith (19 файлов)                    | 6180     | ✅ 100%                       |
| DemonArc (3 файла)                           | 940      | ✅ 100%                       |
| PrisonArc (9 файлов)                         | 1482     | ✅ 100%                       |
| AlfredArc (9 файлов)                         | 3016     | ✅ 100%                       |
| HyralArc (5 файлов)                          | 1312     | ✅ 100%                       |
| WarArc (2 файла)                             | 710      | ✅ 100%                       |
| MagePath (20 файлов)                         | 6729     | 🟡 82% (19/20)                |
| HollowWorld (14 файлов)                      | 4485     | 🟡 77% (1 файл не тронут)      |
| Other (55 файлов)                            | 10861    | 🟡 52% (30/55)                |
| LifeInRahayal (7 файлов)                     | 2556     | ❌ 0%                         |
| SailorArc (7 файлов)                         | 2719     | ❌ 0%                         |
| SailorPath (11 файлов)                       | 3865     | ❌ 0%                         |
| VargaMarionPath (12 файлов)                  | 1740     | ❌ 0%                         |
| **Итого**                                    | **66464**| **✅ 72% (48 052 переведено)** |

---

## Содержание перевода

- **Пролог, StoryBeginnings, Training** — начало игры, выбор пути, обучение
- **WarriorPath** — полный путь Воительницы (18 файлов)
- **UnionKingdom** — полная арка Объединённого Королевства (21 файл)
- **BlackMonolith** — полная арка Чёрного Монолита (19 файлов)
- **HassarPath** — полный путь Хассара (12 файлов)
- **PrisonArc / AlfredArc / DemonArc / WarArc** — полностью переведённые арки
- **HyralArc** — арка Гиpaла (полностью, 5 файлов)
- **MagePath** — 82% (19 из 20 файлов переведены)
- **HollowWorld** — 77% (полный мир Mage и Warrior, кроме Warrior6)
- **Other** — 52% (30 из 55 файлов)
- **Интерфейс** — все кнопки, меню, настройки (90%)
- **Имена персонажей** — полный список имён

![Главное меню The Survival of Sarah Rose с русским переводом — русификатор интерфейса](screenshots/main_menu_russian.jpg)
![Диалог в русской локализации — перевод текста The Survival of Sarah Rose](screenshots/dialogue_russian_1.jpg)
![Настройки выбора языка Russian в The Survival of Sarah Rose](screenshots/language_settings_russian.jpg)
![Диалог с русским переводом — The Survival of Sarah Rose](screenshots/dialogue_russian_2.jpg)

---

## Как помочь проекту

Русификатор делается силами сообщества. Вы можете помочь:

- **Нашли ошибку в переводе?** [Откройте issue](https://github.com/Domovikx/The-Survival-of-Sarah-Rose/issues)
- **Хотите улучшить текст?** Сделайте pull request с правками в `game/tl/ru/`

---

## Лицензия и отказ от ответственности

**Файлы перевода** (`game/tl/ru/`) распространяются под лицензией [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — вы можете свободно использовать и распространять перевод с указанием авторства, но не в коммерческих целях.

**Отказ от ответственности:** Данный перевод является неофициальной фанатской работой. Авторы перевода не связаны с разработчиками и издателями оригинальной игры. Все права на игру «The Survival of Sarah Rose» принадлежат её правообладателям. Используйте перевод на свой страх и риск.
