"""Traduzione italiana di Natter."""

# English singular -> (one, other) forms.
PLURALS = {
    "unread chat": ("chat non letta", "chat non lette"),
}

MESSAGES = {
    # ---- updates --------------------------------------------------------------------
    "Can't reach GitHub to check for updates. Check your internet connection.": 'Impossibile contattare GitHub per cercare aggiornamenti. Controlla la connessione a Internet.',
    'Check for updates automatically': 'Cerca aggiornamenti automaticamente',
    'Check for updates…': 'Cerca aggiornamenti…',
    "Couldn't check for updates": 'Impossibile cercare aggiornamenti',
    "Couldn't start the installer.": "Impossibile avviare l'installazione.",
    'Downloading…': 'Download in corso…',
    'Downloading… {done} of {total} MB': 'Download in corso… {done} di {total} MB',
    'GitHub answered with an error ({code}).': 'GitHub ha risposto con un errore ({code}).',
    'GitHub is limiting update checks right now: try again in an hour.': 'GitHub sta limitando la ricerca di aggiornamenti: riprova tra un’ora.',
    "GitHub sent an answer Natter doesn't understand.": 'GitHub ha inviato una risposta che Natter non comprende.',
    'Installing the update failed: {detail}': 'Installazione dell’aggiornamento non riuscita: {detail}',
    'Installing was cancelled.': 'Installazione annullata.',
    'Installing… your system may ask for your password.': 'Installazione… il sistema potrebbe chiederti la password.',
    'Later': 'Più tardi',
    'No release notes.': 'Nessuna nota di rilascio.',
    'No updates': 'Nessun aggiornamento',
    'Open download page': 'Apri la pagina di download',
    'Open the download page?': 'Aprire la pagina di download?',
    'Skip this version': 'Salta questa versione',
    'Something went wrong: {error}': 'Qualcosa è andato storto: {error}',
    "The download didn't finish. Check your internet connection and try again.": 'Il download non è terminato. Controlla la connessione a Internet e riprova.',
    "The download was damaged (its checksum doesn't match), so it wasn't installed. Try again.": 'Il file scaricato è danneggiato (il checksum non corrisponde), quindi non è stato installato. Riprova.',
    "There's no download for this computer in that release.": 'Questa versione non contiene un file per questo computer.',
    "This copy of Natter can't update itself.": 'Questa copia di Natter non può aggiornarsi da sola.',
    'Update available': 'Aggiornamento disponibile',
    'Update now': 'Aggiorna ora',
    'Yes: update now. No: later. Cancel: skip this version.': 'Sì: aggiorna ora. No: più tardi. Annulla: salta questa versione.',
    'You have the latest version of Natter ({version}).': 'Hai l’ultima versione di Natter ({version}).',
    "You have {current}. Here's what's new:": 'Hai la {current}. Ecco le novità:',
    '{app} {version} is available': '{app} {version} è disponibile',
    # ---- tray ---------------------------------------------------------------------
    "Open {app}": "Apri {app}",
    "Start on login": "Avvia all’accesso",
    "Language": "Lingua",
    "System": "Come il sistema",
    "Quit {app}": "Esci da {app}",
    "{app}: {chats}": "{app}: {chats}",
    # ---- login entry ----------------------------------------------------------------
    "Start {app} in the background": "Avvia {app} in background",
    # ---- command line -----------------------------------------------------------------
    "WhatsApp Web in a native window.": "WhatsApp Web in una finestra dedicata.",
    "enable the web inspector": "attiva l’ispettore web",
    "start hidden in the tray (used when starting on login)":
        "avvia nascosto nell’area di notifica (usato all’avvio con l’accesso)",
    "{app} {version} by {developer}": "{app} {version}, di {developer}",
}
