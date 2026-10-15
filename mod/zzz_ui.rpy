################################################################################
## TSSR mod — аддитивный слой (внешняя папка mod/ рядом с game/).
## Подключение: environment.txt (корень установки) -> RENPY_SEARCHPATH.
## НИ ОДИН файл игры не изменяется.
##
## Содержимое:
##   1) Gui-патч: шрифт Forum + размеры + persistent-настройки шрифтов
##      (дословный порт git HEAD — наш патч, живший в game/gui.rpy до
##      апдейта 0.79; источники: tmp/mod-migration/gui.HEAD.rpy, analysis.md);
##   2) Расширяемый список языков TSSR_LANGUAGES;
##   3) Кнопка на главном меню (штатный хук label before_main_menu,
##      renpy/common/00start.rpy:308-309) -> НАШЕ меню tssr_mod_menu:
##      выбор языка + вкл/выкл озвучки;
##   4) translate ru strings для строк нашего меню.
##
## НЕ перенесено (решение владельца 2026-10-14): старая оболочка
## preferences и правки меню (хуки H11/H15/H19/H27) — официальные экраны
## 0.79 остаются как есть и не переопределяются.
##
## Правила (доказаны ресёрчем 2026-10-14, tasks/2026-10-14-update-proof-...):
##   - наш файл грузится ПОСЛЕ официальных (zzz_) и после gui.init
##     (официальный game/gui.rpy имеет init offset = -2) -> define/стили
##     позднего файла побеждают;
##   - import renpy ЗАПРЕЩЁН (перебивает алиас renpy.exports в store);
##   - default-дубли официальных ключей не использовать;
##   - label-имена придумать свои (before_main_menu в игре отсутствует —
##     проверено grep'ом 2026-10-14).
################################################################################


################################################################################
## 1. Gui-патч (дословно из gui.HEAD.rpy)
################################################################################

## The font used for in-game text.
define gui.text_font = "fonts/Forum-Regular.ttf"

## The font that is used for the names of characters.
define gui.name_text_font = "fonts/Forum-Regular.ttf"

## The font that is used for user interface text.
define gui.interface_text_font = "fonts/Forum-Regular.ttf"

## Font sizes
define gui.text_size = 32
define gui.name_text_size = 38
define gui.interface_text_size = 28
define gui.label_text_size = 36
define gui.notify_text_size = 24
define gui.title_text_size = 75

default persistent.font_text_size = 32
default persistent.font_name_size = 38
default persistent.font_interface_size = 28
default persistent.font_label_size = 36
default persistent.font_notify_size = 24
default persistent.font_title_size = 75

## Производные gui.* — переобъявляем ПОСЛЕ официального gui.rpy, иначе они
## заморожены на официальных базах (HEAD: gui.HEAD.rpy 244/247/294/295).
define gui.button_text_font = gui.interface_text_font
define gui.button_text_size = gui.interface_text_size
define gui.choice_button_text_font = gui.text_font
define gui.choice_button_text_size = gui.text_size

init python:
    FONT_DEFAULTS = {
        'font_text_size': 32,
        'font_name_size': 38,
        'font_interface_size': 28,
        'font_label_size': 36,
        'font_notify_size': 24,
        'font_title_size': 75
    }

    def set_style_size(style_name, size):
        try:
            getattr(style, style_name).size = size
        except:
            pass

    def update_font_styles():
        set_style_size('say_dialogue', persistent.font_text_size)
        set_style_size('say_label', persistent.font_name_size)
        set_style_size('nvl_dialogue', persistent.font_text_size)
        set_style_size('nvl_label', persistent.font_name_size)
        set_style_size('interface_text', persistent.font_interface_size)
        set_style_size('gui_text', persistent.font_interface_size)
        set_style_size('history_text', persistent.font_text_size)
        set_style_size('history_name', persistent.font_name_size)
        set_style_size('pref_label_text', persistent.font_label_size)
        set_style_size('slot_time_text', persistent.font_interface_size)
        set_style_size('slot_name_text', persistent.font_interface_size)
        set_style_size('game_menu_label_text', persistent.font_label_size)
        set_style_size('quick_button_text', persistent.font_interface_size)
        set_style_size('choice_button_text', persistent.font_text_size)
        set_style_size('navigation_button_text', persistent.font_interface_size)
        set_style_size('button_text', persistent.font_interface_size)
        set_style_size('label_text', persistent.font_interface_size)
        set_style_size('prompt_text', persistent.font_interface_size)
        set_style_size('main_menu_text', persistent.font_interface_size)
        set_style_size('about_text', persistent.font_interface_size)
        set_style_size('about_label_text', persistent.font_label_size)
        set_style_size('page_label_text', persistent.font_label_size)
        set_style_size('page_button_text', persistent.font_interface_size)
        set_style_size('slot_button_text', persistent.font_interface_size)
        set_style_size('radio_label_text', persistent.font_label_size)
        set_style_size('radio_button_text', persistent.font_interface_size)
        set_style_size('check_label_text', persistent.font_label_size)
        set_style_size('check_button_text', persistent.font_interface_size)
        set_style_size('slider_label_text', persistent.font_label_size)
        set_style_size('slider_button_text', persistent.font_interface_size)
        set_style_size('mute_all_button_text', persistent.font_interface_size)
        set_style_size('history_label_text', persistent.font_label_size)
        set_style_size('help_button_text', persistent.font_interface_size)
        set_style_size('help_label_text', persistent.font_label_size)
        set_style_size('help_text', persistent.font_interface_size)
        set_style_size('confirm_prompt_text', persistent.font_interface_size)
        set_style_size('confirm_button_text', persistent.font_interface_size)
        set_style_size('skip_text', persistent.font_interface_size)
        set_style_size('notify_text', persistent.font_interface_size)
        set_style_size('nvl_button_text', persistent.font_text_size)
        set_style_size('return_button_text', persistent.font_interface_size)

    def update_all():
        gui.text_size = persistent.font_text_size
        gui.name_text_size = persistent.font_name_size
        gui.interface_text_size = persistent.font_interface_size
        gui.label_text_size = persistent.font_label_size
        gui.notify_text_size = persistent.font_notify_size
        gui.title_text_size = persistent.font_title_size
        update_font_styles()
        gui.rebuild()
        renpy.save_persistent()
        renpy.utter_restart()

    def reset_font_sizes():
        persistent.font_text_size = FONT_DEFAULTS['font_text_size']
        persistent.font_name_size = FONT_DEFAULTS['font_name_size']
        persistent.font_interface_size = FONT_DEFAULTS['font_interface_size']
        persistent.font_label_size = FONT_DEFAULTS['font_label_size']
        persistent.font_notify_size = FONT_DEFAULTS['font_notify_size']
        persistent.font_title_size = FONT_DEFAULTS['font_title_size']
        update_all()

    ## Первичный прогон: применяем persistent-размеры к стилям.
    gui.text_size = persistent.font_text_size
    gui.name_text_size = persistent.font_name_size
    gui.interface_text_size = persistent.font_interface_size
    gui.label_text_size = persistent.font_label_size
    gui.notify_text_size = persistent.font_notify_size
    gui.title_text_size = persistent.font_title_size
    update_font_styles()


################################################################################
## 2. Языки — ЕДИНСТВЕННОЕ место правки при добавлении новой локализации
################################################################################

init python:

    # (код языка, отображаемое имя); None = английский (оригинал игры).
    # Добавление языка: строка сюда + translate <код> strings: (или
    # mod/tl/<код>/*.rpy) + при необходимости ai_voice/<код>/ с озвучкой.
    # Официальные файлы игры не трогаются.
    TSSR_LANGUAGES = [
        (None, "English"),
        ("ru", "Русский"),
    ]


################################################################################
## 3. Кнопка на главном меню -> наше меню
################################################################################

init python:

    def tssr_menu_marker():
        # Диагностика: факт срабатывания хука -> mod/last_menu_hook.txt
        import os
        try:
            fn = os.path.join(config.basedir, "mod", "last_menu_hook.txt")
            f = open(fn, "w")
            f.write("before_main_menu fired\n")
            f.close()
        except Exception:
            pass

# Штатный хук движка (renpy/common/00start.rpy:308-309): вызывается при каждом
# входе в главное меню. Внимание: только код и return — никаких jump (иначе
# меню скипается; лемма t=42498).
label before_main_menu:
    $ renpy.show_screen("tssr_menu_hook")
    $ tssr_menu_marker()
    return

screen tssr_menu_hook():
    # Кнопка видна ТОЛЬКО на реальном главном меню; не tag menu (иначе заменит
    # сам main_menu); zorder 50 — поверх main_menu (0), под confirm (200).
    zorder 50

    if main_menu and renpy.get_screen("main_menu"):
        frame:
            style "empty"
            xalign 0.98
            yalign 0.05

            textbutton _("TSSR Mod"):
                action ShowMenu("tssr_mod_menu")


################################################################################
## 4. Наше меню (полностью своё: не завязано на официальные экраны 0.79)
################################################################################

screen tssr_mod_menu():
    tag menu

    add gui.main_menu_background

    frame:
        style "tssr_mod_dim"

    frame:
        style "tssr_mod_card"

        vbox:
            spacing 15

            label "TSSR"

            null height 10

            text _("TSSR Languages"):
                style "tssr_mod_section"

            for code, title in TSSR_LANGUAGES:
                textbutton title:
                    action Language(code)
                    selected Language(code).get_selected()

            null height 15

            text _("TSSR Voice"):
                style "tssr_mod_section"

            if ToggleMute("voice").get_selected():
                textbutton _("TSSR Voice: OFF"):
                    action ToggleMute("voice")
                    selected True
            else:
                textbutton _("TSSR Voice: ON"):
                    action ToggleMute("voice")

            null height 15

            textbutton _("TSSR Back"):
                action Return()

    key "game_menu" action Return()


style tssr_mod_dim is empty:
    background Solid("#000000aa")
    xfill True
    yfill True

style tssr_mod_card is frame:
    xalign 0.5
    yalign 0.5
    padding (35, 30, 35, 30)

style tssr_mod_section is label_text


################################################################################
## 5. Перевод строк нашего меню (новый язык = свой translate-блок здесь или
##    в mod/tl/<код>/ — без правки официальных файлов)
################################################################################

translate ru strings:

    old "TSSR Mod"
    new "Меню TSSR"

    old "TSSR Languages"
    new "Языки"

    old "TSSR Voice"
    new "Озвучка"

    old "TSSR Voice: ON"
    new "Озвучка: ВКЛ"

    old "TSSR Voice: OFF"
    new "Озвучка: ВЫКЛ"

    old "TSSR Back"
    new "Назад"
