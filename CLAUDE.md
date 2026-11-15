# Natter

Python 3.10+ WhatsApp Web wrapper. Linux (0.11+): Qt WebEngine = Chromium from Ubuntu's `python3-pyside6.qtwebenginewidgets` (`natter/linux_qt.py`); WebKitGTK `natter/linux.py` = fallback only (no calls). Windows: pywebview + WebView2 (`natter/windows.py`).

- Keep platform-independent logic in `natter/config.py` / `natter/state.py` and test it there;
  the backends stay thin.
- venv must use `--system-site-packages` (PyGObject isn't pip-installed). Test:
  `.venv/bin/python -m pytest -q`. Run: `.venv/bin/natter`.
- Never use an unofficial WhatsApp protocol client (ban risk); only the official WhatsApp Web.
- The Linux user agent must look like desktop Chrome or WhatsApp Web refuses to load.
- `windows.py` can't be run here; WebView2 calls must go through `form.Invoke` (UI thread).
- Background mode: `linux.py` hides on close and shows a tray from `tray_linux.py` (raw
  StatusNotifierItem + dbusmenu over Gio, no AppIndicator lib); `windows.py` uses pystray and
  `single_instance.py`. `--background` starts hidden; `autostart.py` writes the login entry.
- Live-testing Linux while the user's installed Natter runs: set `linux.config.APP_ID` to a test
  id first, or GApplication hands off to their copy (and shows their window).
- On-screen text goes through `_()` from `natter/i18n.py` with named placeholders; add the
  Russian and Italian to `natter/locales/ru.py` and `it.py` (`tests/test_i18n.py` fails on anything missing).
- Release metadata (version, developer, homepage) lives in `natter/__init__.py`; packaging reads it.
- Release (automatic after each change): bump `__version__`, add a CHANGELOG section and a
  `<release>` at the top of the metainfo (`tests/test_packaging.py` checks both), then push
  tag `vX.Y.Z` on its own (GitHub starts no tag workflows when one push carries >3 tags).
- Updates (`natter/updates.py`, platform-independent: feed, installers, `Updater` rules; dialogs in `updates_gtk.py` and `updates_win.py`). The repo must be public for GitHub's API to answer. Asset names must stay `natter_<v>_all.deb` and `Natter-<v>-windows-x64-setup.exe`. Choices live in `Preferences` (`auto_update_check`, `update_last_check`, `update_skipped`). Tests use fakes, never GitHub.
- Windows features (0.9.0): Do Not Disturb is a script in WhatsApp's page (`webpage.QUIET_SCRIPT`, switched with `quiet_switch`), the Settings window is an HTML page (`webpage.settings_page`, calls `_SettingsApi` through pywebview's js_api) with a sticky glass header, Ctrl+Alt+W is `hotkey_win.Hotkey` (RegisterHotKey on its own thread), memory saving sets `CoreWebView2.MemoryUsageTargetLevel` while hidden. None of it has been run on real Windows by Claude: ask the user how it went.
- Looks: Material 3 tonal (suite 2026-11-14), no glass, no blur; never a gradient wash or colour blobs.
- Linux notifications (0.10): WhatsApp's `Notification` is replaced by `webpage.LINUX_NOTIFY_SCRIPT` (always granted) and shown via `Gio.Notification` (`_on_page_notification`, action `app.open-chat`). WebKitGTK 2.52 `initialize_notification_permissions` did not work (tested).

## linux qt engine (0.11, 2026-11-15)
calls need chromium; webkitgtk = no calls (tested, even w/ gstreamer webrtc)
gate = WhatsApp `require("WAWebVoipGatingUtils").getUnsupportedBrowserReason()` -> must be `null`; was `missing_shared_array_buffer` => chromium flag `SharedArrayBuffer` (`chromium.py`)
also: UA w/o `QtWebEngine/`, client hints = Google Chrome, js shim `window.chrome` + `navigator.vendor`
! ubuntu qt webengine has H264; pip PySide6 wheel = no H264 => test w/ `/usr/bin/python3`, not a pip venv
light (user ask): 1 renderer, cache `64 MB` w/ memory saver, settings = native qt (`settings_qt.py`), no 2nd web view; ~`280 MB` PSS vs gtk ~`1156 MB`
single instance + `--toggle` = `QLocalServer` `io.github.quezka.Natter-<user>`; notif = d-bus `org.freedesktop.Notifications` (`_Notifier`); tray = `tray_linux.py` (gio, runs in qt glib loop)
data: `~/.local/share/natter/chromium`; `--debug` -> devtools `127.0.0.1:9333`
