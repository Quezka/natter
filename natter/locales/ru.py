"""Русский перевод Natter."""

# English singular -> (1, 2-4, 5+) forms.
PLURALS = {
    "unread chat": ("непрочитанный чат", "непрочитанных чата", "непрочитанных чатов"),
}

MESSAGES = {
    # ---- updates --------------------------------------------------------------------
    "Can't reach GitHub to check for updates. Check your internet connection.": 'Не удаётся связаться с GitHub, чтобы проверить обновления. Проверьте подключение к интернету.',
    'Check for updates automatically': 'Проверять обновления автоматически',
    'Check for updates…': 'Проверить обновления…',
    "Couldn't check for updates": 'Не удалось проверить обновления',
    "Couldn't start the installer.": 'Не удалось запустить установщик.',
    'Downloading…': 'Загрузка…',
    'Downloading… {done} of {total} MB': 'Загрузка… {done} из {total} МБ',
    'GitHub answered with an error ({code}).': 'GitHub ответил ошибкой ({code}).',
    'GitHub is limiting update checks right now: try again in an hour.': 'GitHub сейчас ограничивает проверки обновлений: попробуйте через час.',
    "GitHub sent an answer Natter doesn't understand.": 'GitHub прислал ответ, который Natter не понимает.',
    'Installing the update failed: {detail}': 'Не удалось установить обновление: {detail}',
    'Installing was cancelled.': 'Установка отменена.',
    'Installing… your system may ask for your password.': 'Установка… система может запросить пароль.',
    'Later': 'Позже',
    'No release notes.': 'Описания изменений нет.',
    'No updates': 'Обновлений нет',
    'Open download page': 'Открыть страницу загрузки',
    'Open the download page?': 'Открыть страницу загрузки?',
    'Skip this version': 'Пропустить эту версию',
    'Something went wrong: {error}': 'Что-то пошло не так: {error}',
    "The download didn't finish. Check your internet connection and try again.": 'Загрузка не завершилась. Проверьте подключение к интернету и попробуйте ещё раз.',
    "The download was damaged (its checksum doesn't match), so it wasn't installed. Try again.": 'Загруженный файл повреждён (контрольная сумма не совпадает), поэтому он не был установлен. Попробуйте ещё раз.',
    "There's no download for this computer in that release.": 'Для этого компьютера в этом выпуске нет файла.',
    "This copy of Natter can't update itself.": 'Эта копия Natter не может обновлять себя.',
    'Update available': 'Доступно обновление',
    'Update now': 'Обновить сейчас',
    'Yes: update now. No: later. Cancel: skip this version.': 'Да: обновить сейчас. Нет: позже. Отмена: пропустить эту версию.',
    'You have the latest version of Natter ({version}).': 'У вас последняя версия Natter ({version}).',
    "You have {current}. Here's what's new:": 'У вас {current}. Что нового:',
    '{app} {version} is available': 'Доступна версия {version} приложения {app}',
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
