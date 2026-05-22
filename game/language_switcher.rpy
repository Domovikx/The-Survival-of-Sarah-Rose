# Language switcher
init python:
    config.game_menu = config.game_menu + [("language", "Language", "language_chooser", "True")]

screen language_chooser():
    frame:
        xalign 0.5
        yalign 0.5
        
        vbox:
            textbutton "English" action Language(None)
            textbutton "Русский" action Language("ru")
            null height 10
            textbutton "Return" action Return()