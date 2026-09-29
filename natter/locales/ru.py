"""Русский перевод Natter."""

# English singular -> (1, 2-4, 5+) forms.
PLURALS = {
    "unread chat": ("непрочитанный чат", "непрочитанных чата", "непрочитанных чатов"),
}

MESSAGES = {
    # ---- tray ---------------------------------------------------------------------
    "Open {app}": "Открыть {app}",
    "Start on login": "Запускать при входе в систему",
    "Language": "Язык",
    "System": "Как в системе",
    "Quit {app}": "Выйти из {app}",
    "{app}: {chats}": "{app}: {chats}",
    # ---- login entry ----------------------------------------------------------------
    "Start {app} in the background": "Запуск {app} в фоне",
    # ---- command line -----------------------------------------------------------------
    "WhatsApp Web in a native window.": "WhatsApp Web в отдельном окне.",
    "enable the web inspector": "включить веб-инспектор",
    "start hidden in the tray (used when starting on login)":
        "запуститься свёрнутым в трей (так Natter запускается при входе в систему)",
    "{app} {version} by {developer}": "{app} {version}, автор {developer}",
}
