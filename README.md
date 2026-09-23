# Natter

WhatsApp Web in a lightweight native window for Linux and Windows.

Natter uses the webview that's already on your system instead of shipping its own copy of
Chromium the way Electron apps do. It runs the official WhatsApp Web, so your account is
linked like any browser session: no unofficial protocol, no ban risk.

| | Linux | Windows |
|---|---|---|
| Engine | WebKitGTK 4.1 (GTK 3) | Edge WebView2 (via pywebview) |
| Package | `.deb`, ~16 KB | portable `.exe` |

Natter is not affiliated with WhatsApp or Meta.

## Features

- Stays logged in; remembers window size and zoom
- Desktop notifications, unread count in the title, taskbar attention
- Links open in your browser; downloads go to Downloads
- Voice notes, camera, clipboard images, spell-check
- Linux: close to background (launch again to show, Ctrl+Q to quit), single instance

## Run from source

Linux needs the distro's PyGObject and WebKitGTK:

```sh
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e . pytest
.venv/bin/natter            # --debug enables the web inspector
.venv/bin/python -m pytest -q
```

If rendering glitches on your GPU driver, run with `NATTER_NO_GPU=1`.

On Windows: `pip install -e .` then `natter`.

## Build

```sh
python3 scripts/build.py --deb   # on Linux
python scripts/build.py --exe    # on Windows (pip install -e ".[build]" first)
```

Pushing a tag `vX.Y.Z` that matches `natter.__version__` makes CI publish a GitHub release
with both packages and the matching `CHANGELOG.md` section as notes.

## Layout

- `natter/config.py`: URLs, user agent, link policy, paths (pure, tested)
- `natter/state.py`: remembered window state (pure, tested)
- `natter/linux.py`: GTK + WebKitGTK backend
- `natter/windows.py`: pywebview + WebView2 backend
