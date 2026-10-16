################################################################################
## TSSR mod — аддитивный слой (внешняя папка mod/ рядом с game/).
## Подключение: environment.txt (корень установки) -> RENPY_SEARCHPATH.
## НИ ОДИН файл игры не изменяется.
##
## Содержимое:
##   1) Gui-патч: шрифт Literata (кастинг 2026-10-15, выбор владельца —
##      tmp/font_casting/index.html; прежний Forum) + размеры +
##      persistent-настройки шрифтов (порт git HEAD — наш патч, живший
##      в game/gui.rpy до апдейта 0.79; источники: tmp/mod-migration/...);
##   2) Расширяемый список языков TSSR_LANGUAGES;
##   2.1) Размеры шрифтов: числовые поля в меню (стейджинг: черновик ->
##      Применить; см. UX-решение в секции 2.1);
##   3) Кнопка-бейдж (штатный хук label before_main_menu,
##      renpy/common/00start.rpy:308-309, + config.overlay_screens в игре)
##      -> страница настроек tssr_mod_menu: язык, озвучка, размеры шрифтов,
##      ссылки (GitHub/Boosty);
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
## 1. Gui-патч (порт gui.HEAD.rpy; ШРИФТ заменён на Literata — кастинг
##    2026-10-15, победитель tmp/font_casting/index.html, файл лежит в
##    mod/fonts/ и резолвится тем же "fonts/..."-путём через RENPY_SEARCHPATH)
################################################################################

## The font used for in-game text.
define gui.text_font = "fonts/Literata-Regular.ttf"

## The font that is used for the names of characters.
define gui.name_text_font = "fonts/Literata-Regular.ttf"

## The font that is used for user interface text.
define gui.interface_text_font = "fonts/Literata-Regular.ttf"

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

    # Короткие коды для КНОПКИ (подпись = текущий язык; ENG/RUS — привычные
    # для игр 3-буквенные формы, не спутать с флагом/регионом). Новый язык =
    # добавить строку в TSSR_LANGUAGES + сюда.
    TSSR_LANG_SHORT = {
        None: "ENG",
        "ru": "RUS",
    }

    def tssr_current_short():
        # Текущий язык -> короткий код кнопки ("RUS"/"ENG"/...).
        for code, title in TSSR_LANGUAGES:
            if Language(code).get_selected():
                return TSSR_LANG_SHORT.get(code, (code or "en").upper())
        return "ENG"


################################################################################
## 2.1 Размеры шрифтов: числовые поля со «стейджингом» (черновик -> Применить)
##
##     Поля ввода пишут в store-переменные tssr_fs_* (НЕ в persistent) — это
##     черновик. При открытии страницы черновик снапшотится из persistent
##     (on "show" -> tssr_fs_snapshot). «Применить» клонирует черновик в
##     persistent и зовёт update_all() (перезапуск); «Закрыть» черновик просто
##     отбрасывает.
##     UX-паттерн (ресёрч 2026-10-15): мгновенные настройки (язык/голос) — без
##     кнопки сохранения; тяжёлые, требующие рестарта (шрифты) — явный Apply;
##     в подвале страницы — динамическая кнопка: «Применить и перезапустить»
##     видна ТОЛЬКО при неприменённых изменениях (паттерн «save disabled,
##     когда изменений нет» / «unsaved changes prompt»).
################################################################################

default tssr_fs_text = 32
default tssr_fs_name = 38
default tssr_fs_interface = 28
default tssr_fs_label = 36
default tssr_fs_notify = 24
default tssr_fs_title = 75

init python:

    # (persistent-поле, store-черновик, original-заголовок строки) —
    # ЕДИНСТВЕННОЕ место правки при добавлении нового размера шрифта.
    TSSR_FS_ROWS = [
        ("font_text_size", "tssr_fs_text", "TSSR Dialogue"),
        ("font_name_size", "tssr_fs_name", "TSSR Names"),
        ("font_interface_size", "tssr_fs_interface", "TSSR Interface"),
        ("font_label_size", "tssr_fs_label", "TSSR Headers"),
        ("font_notify_size", "tssr_fs_notify", "TSSR Notifications"),
        ("font_title_size", "tssr_fs_title", "TSSR Game Title"),
    ]

    class TssrFsInput(VariableInputValue):
        # Инпут для INT-черновиков tssr_fs_*: в 7.4.11 input_post_per_interact
        # берёт get_text() сырым и делает len() — VariableInputValue отдаёт
        # переменную как есть -> «TypeError: object of type 'int' has no len()».
        # Наследник отдаёт строкой, set_text() пишет обратно int (пусто при
        # стирании = черновик не трогаем); нормализация и кламп — в _tssr_fs_norm.
        def get_text(self):
            return str(globals()[self.variable])

        def set_text(self, s):
            try:
                globals()[self.variable] = int(str(s).strip())
            except Exception:
                pass
            renpy.restart_interaction()

    def _tssr_fs_norm(attr, value):
        # Поле ввода -> строка, persistent -> int. Валидное целое зажимается
        # в 10..160; мусор/пусто = оставить текущее persistent-значение.
        try:
            v = int(str(value).strip())
        except Exception:
            return int(getattr(persistent, attr))
        return max(10, min(160, v))

    def tssr_fs_snapshot():
        # Черновик <- persistent (on "show" страницы настроек).
        st = globals()
        for attr, var, _title in TSSR_FS_ROWS:
            st[var] = getattr(persistent, attr)

    def tssr_fs_dirty():
        # Есть ли неприменённые изменения (динамическая кнопка подвала).
        st = globals()
        for attr, var, _title in TSSR_FS_ROWS:
            if _tssr_fs_norm(attr, st[var]) != getattr(persistent, attr):
                return True
        return False

    def tssr_fs_apply():
        # Черновик -> persistent + стили + gui.rebuild + перезапуск.
        st = globals()
        for attr, var, _title in TSSR_FS_ROWS:
            setattr(persistent, attr, _tssr_fs_norm(attr, st[var]))
        update_all()

    def tssr_fs_reset_draft():
        # Сброс ЧЕРНОВИКА до дефолтов (persistent не трогаем: подвал станет
        # «грязным», игрок применит осознанно кнопкой Применить).
        st = globals()
        for attr, var, _title in TSSR_FS_ROWS:
            st[var] = FONT_DEFAULTS[attr]

    def tssr_fs_preview_size(var):
        # Кегль preview-строки: clamp 8..48 — большие значения не раздувают
        # строку (страница с фиксированной сеткой, без прыжков).
        try:
            v = int(str(globals()[var]).strip())
        except Exception:
            v = 24
        return max(8, min(v, 48))


################################################################################
## 3. Кнопка: главное меню + процесс игры -> наше меню
################################################################################

init python:

    def tssr_menu_marker(where="label"):
        # Диагностика: какой хук сработал -> mod/last_menu_hook.txt
        import os
        try:
            fn = os.path.join(config.basedir, "mod", "last_menu_hook.txt")
            f = open(fn, "w")
            f.write("hook: %s, button=%s\n" % (where, tssr_current_short()))
            f.close()
        except Exception:
            pass

    # Кнопка В ПРОЦЕССЕ ИГРЫ: второй hook-экран в overlay-списке — движок
    # показывает его в игре и прячет в меню (так же работает quick_menu:
    # game/screens.rpy:269). Список в меню подавлен (display/screen.py:1407-1411),
    # поэтому ГЛАВНОЕ МЕНЮ обслуживает ОТДЕЛЬНЫЙ экран tssr_menu_hook через
    # label ниже — их нельзя объединять в один экран: движок прятал бы и его.
    if "tssr_game_hook" not in config.overlay_screens:
        config.overlay_screens.append("tssr_game_hook")

# Штатный хук движка (renpy/common/00start.rpy:308-309): вызывается при каждом
# входе в главное меню. Внимание: только код и return — никаких jump (иначе
# меню скипается; лемма t=42498).
label before_main_menu:
    $ renpy.show_screen("tssr_menu_hook")
    $ tssr_menu_marker("before_main_menu")
    return

screen tssr_button():
    # Общая кнопка-бейдж (подпись = текущий язык: RUS/ENG), правый верхний
    # угол. Скрываем, пока открыта страница настроек (она сама содержит языки).
    if not renpy.get_screen("tssr_mod_menu"):
        frame:
            style "empty"
            xalign 0.98
            yalign 0.05

            textbutton tssr_current_short():
                # Снапшот черновика ДО открытия (порядок гарантирован).
                action [Function(tssr_fs_snapshot), ShowMenu("tssr_mod_menu")]
                style "tssr_badge"

screen tssr_menu_hook():
    # ГЛАВНОЕ МЕНЮ: показывается label'ом before_main_menu; в overlay-списке
    # НЕ состоит — движок его в меню не прячет (в отличие от game_hook).
    zorder 50
    on "show" action Function(tssr_menu_marker, "menu_hook")
    use tssr_button

screen tssr_game_hook():
    # ПРОЦЕСС ИГРЫ: в config.overlay_screens (см. init python выше) — видна
    # всю игру; в меню и на сплэше движок прячет её автоматически.
    zorder 50
    on "show" action Function(tssr_menu_marker, "game_hook")
    use tssr_button


################################################################################
## 4. Страница настроек TSSR — НА ВЕСЬ ЭКРАН (полупрозрачный тёмный фон,
##    главный план слегка виден; колонка фиксированной ширины -> контент не
##    «прыгает» за счёт строк). Своя: не завязана на официальные экраны 0.79.
##    Расширение: новая секция = блок внутри tssr_mod_menu (+ helper в
##    секции 2.1 и пара строк old/new в translate ниже).
################################################################################

screen tssr_mod_menu():
    tag menu

    # Снапшот черновика (persistent -> tssr_fs_*) делает КНОПКА-БЕЙДЖ ДО
    # ShowMenu (см. tssr_button): порядок «снапшот -> execute экрана»
    # гарантирован, инпуты сразу получают актуальные значения. on "show"
    # здесь не используется: событие show приходит после сборки детей и
    # перезапускало бы интеракшен (а Function на rebuild мог бы затирать
    # то, что игрок уже напечатал).

    add gui.main_menu_background

    frame:
        style "tssr_mod_page"

        vbox:
            style "tssr_mod_column"

            ## Шапка
            text "TSSR":
                style "tssr_mod_title"

            text _("TSSR Settings page: language, voice, fonts, links."):
                style "tssr_mod_hint"

            ## Язык + Озвучка — применяются МГНОВЕННО (без кнопки сохранения)
            hbox:
                spacing 40

                vbox:
                    xsize 530
                    spacing 10

                    text _("TSSR Language"):
                        style "tssr_mod_section"

                    hbox:
                        spacing 15

                        for code, title in TSSR_LANGUAGES:
                            textbutton title:
                                action Language(code)
                                selected Language(code).get_selected()
                                style "radio_button"

                vbox:
                    xsize 530
                    spacing 10

                    text _("TSSR Voice"):
                        style "tssr_mod_section"

                    hbox:
                        spacing 15

                        textbutton _("TSSR On"):
                            action SetMute("voice", False)
                            selected (not ToggleMute("voice").get_selected())
                            style "radio_button"

                        textbutton _("TSSR Off"):
                            action SetMute("voice", True)
                            selected ToggleMute("voice").get_selected()
                            style "radio_button"

            ## Размеры шрифтов — целые числа; стейджинг -> Apply (секция 2.1)
            text _("TSSR Font Sizes"):
                style "tssr_mod_section"

            text _("TSSR Font hint: whole numbers 10-160, applied on game restart."):
                style "tssr_mod_hint"

            for attr, var, title in TSSR_FS_ROWS:
                hbox:
                    spacing 15

                    text _(title):
                        style "tssr_mod_row"

                    frame:
                        style "tssr_mod_input_box"

                        input value TssrFsInput(var):
                            allow "0123456789"
                            length 3
                            style "tssr_mod_input"

                    text _("TSSR Preview text"):
                        style "tssr_mod_preview"
                        size tssr_fs_preview_size(var)

            textbutton _("TSSR Reset to defaults"):
                action [Function(tssr_fs_reset_draft), Function(renpy.restart_interaction)]
                style "tssr_secondary"

            ## Ссылки (сейчас GitHub; Boosty — когда будет постоянная ссылка)
            text _("TSSR Links"):
                style "tssr_mod_section"

            textbutton _("TSSR GitHub star"):
                action OpenURL("https://github.com/Domovikx/The-Survival-of-Sarah-Rose")
                style "tssr_link"

            # TODO(Boosty): раскомментировать, когда будет постоянный адрес:
            # textbutton _("TSSR Boosty"):
            #     action OpenURL("https://boosty.to/<slug>")

            ## Подвал — динамический (UX-формулировка владельца: «назад, если
            ## ничего не менял, иначе — сохранить/применить»):
            ##   чисто   -> [Закрыть];
            ##   «грязно» -> [Отменить правки] + [Применить и перезапустить]
            ##             (безмолвного закрытия с изменениями НЕТ: паттерн
            ##             unsaved-changes из ресёрча; отмена = явная кнопка).
            hbox:
                spacing 15
                xalign 1.0

                if tssr_fs_dirty():
                    textbutton _("TSSR Revert changes"):
                        action [Function(tssr_fs_snapshot), Function(renpy.restart_interaction)]
                        style "tssr_secondary"

                    textbutton _("TSSR Apply and restart"):
                        action Function(tssr_fs_apply)
                        style "tssr_primary"
                else:
                    textbutton _("TSSR Close"):
                        action Return()
                        style "tssr_secondary"

    # Esc = зеркало подвала: при изменениях — Применить, иначе — Закрыть.
    key "game_menu" action (Function(tssr_fs_apply) if tssr_fs_dirty() else Return())


## Фон: вся страница, тёмный полупрозрачный — фон меню слегка виден (UX-просьба
## владельца: «тёмный фон с небольшой прозрачностью, чтобы заднюю часть видеть»).
style tssr_mod_page is frame:
    xfill True
    yfill True
    background Solid("#0b0e14c7")
    padding (60, 40, 60, 40)

## Колонка контента: ФИКСИРОВАННАЯ ширина — контент не меняет геометрию.
style tssr_mod_column is vbox:
    xalign 0.5
    yalign 0.5
    xsize 1100
    spacing 10

style tssr_mod_title is gui_text:
    size 44
    color "#ffffff"

style tssr_mod_hint is gui_text:
    size 22
    color "#9aa4b2"

style tssr_mod_section is gui_text:
    size 30
    color gui.accent_color

style tssr_mod_row is gui_text:
    size 26
    color "#e6e6e6"
    xsize 300
    yalign 0.5

style tssr_mod_input_box is frame:
    background Solid("#ffffff1a")
    padding (12, 9, 12, 9)
    xsize 130
    yalign 0.5

style tssr_mod_input is gui_text:
    color "#ffffff"

style tssr_mod_preview is gui_text:
    color "#9aa4b2"
    yalign 0.5

## Кнопка-бейдж (правый верх): подпись = текущий язык.
style tssr_badge is button:
    background Solid("#00000066")
    hover_background Solid("#99ccff40")
    padding (14, 7, 14, 7)

style tssr_badge_text is gui_text:
    size 26
    color "#ffffff"
    hover_color gui.accent_color

## Кнопки страницы: primary (акцент) / secondary (призрачная) / ссылка.
style tssr_primary is button:
    background Solid(gui.accent_color)
    hover_background Solid("#ffffff")
    padding (22, 10, 22, 10)

style tssr_primary_text is gui_text:
    size 26
    color "#0b0e14"
    hover_color "#0b0e14"

style tssr_secondary is button:
    background Solid("#ffffff1f")
    hover_background Solid("#ffffff33")
    padding (22, 10, 22, 10)

style tssr_secondary_text is gui_text:
    size 26
    color "#e6e6e6"
    hover_color "#ffffff"

style tssr_link is button:
    background Solid("#ffffff14")
    hover_background Solid("#99ccff33")
    padding (16, 8, 16, 8)

style tssr_link_text is gui_text:
    size 26
    color gui.accent_color
    hover_color "#ffffff"


################################################################################
## 5. Перевод строк нашего меню (новый язык = свой translate-блок здесь или
##    в mod/tl/<код>/ — без правки официальных файлов)
################################################################################

translate ru strings:

    old "TSSR Settings page: language, voice, fonts, links."
    new "Настройки TSSR: язык, голос, шрифты, ссылки."

    old "TSSR Language"
    new "Язык"

    old "TSSR Voice"
    new "Озвучка"

    old "TSSR On"
    new "Вкл"

    old "TSSR Off"
    new "Выкл"

    old "TSSR Font Sizes"
    new "Размеры шрифтов"

    old "TSSR Font hint: whole numbers 10-160, applied on game restart."
    new "Целые числа 10–160. Применяются при перезапуске игры."

    old "TSSR Dialogue"
    new "Диалоги"

    old "TSSR Names"
    new "Имена"

    old "TSSR Interface"
    new "Интерфейс"

    old "TSSR Headers"
    new "Заголовки"

    old "TSSR Notifications"
    new "Уведомления"

    old "TSSR Game Title"
    new "Название игры"

    old "TSSR Preview text"
    new "Пример строки"

    old "TSSR Reset to defaults"
    new "К стандартным"

    old "TSSR Revert changes"
    new "Отменить правки"

    old "TSSR Links"
    new "Ссылки и поддержка"

    old "TSSR GitHub star"
    new "GitHub — поставить звезду ★"

    old "TSSR Apply and restart"
    new "Применить и перезапустить"

    old "TSSR Close"
    new "Закрыть"
