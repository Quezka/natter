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
- Release metadata (version, developer, homepage) lives in `natter/__init__.py`; packaging reads it.
- Release (automatic after each change): bump `__version__`, add a CHANGELOG section and a
  `<release>` at the top of the metainfo (`tests/test_packaging.py` checks both), push tag `vX.Y.Z`.
