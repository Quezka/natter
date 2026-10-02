# Natter

Python 3.10+ WhatsApp Web wrapper using the system webview. Linux: GTK 3 + WebKitGTK 4.1 via
the distro's PyGObject (`natter/linux.py`). Windows: pywebview + WebView2 (`natter/windows.py`).

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
  Russian to `natter/locales/ru.py` (`tests/test_i18n.py` fails on anything missing).
- Release metadata (version, developer, homepage) lives in `natter/__init__.py`; packaging reads it.
- Release (automatic after each change): bump `__version__`, add a CHANGELOG section and a
  `<release>` at the top of the metainfo (`tests/test_packaging.py` checks both), then push
  tag `vX.Y.Z` on its own (GitHub starts no tag workflows when one push carries >3 tags).
- Updates (`natter/updates.py`, platform-independent: feed, installers, `Updater` rules; dialogs in `updates_gtk.py` and `updates_win.py`). The repo must be public for GitHub's API to answer. Asset names must stay `natter_<v>_all.deb` and `Natter-<v>-windows-x64-setup.exe`. Choices live in `Preferences` (`auto_update_check`, `update_last_check`, `update_skipped`). Tests use fakes, never GitHub.
