# Natter

WhatsApp Web in a lightweight native window for Linux and Windows.

Natter uses the webview that's already on your system instead of shipping its own copy of
Chromium the way Electron apps do. It runs the official WhatsApp Web, so your account is
linked like any browser session: no unofficial protocol, no ban risk.

| | Linux | Windows |
|---|---|---|
| Engine | WebKitGTK 4.1 (GTK 3) | Edge WebView2 (via pywebview) |
| Package | `.deb`, ~16 KB | setup `.exe` (per-user install) |

Natter is not affiliated with WhatsApp or Meta.

## Features

- Stays logged in; remembers window size and zoom
- Desktop notifications, unread count in the title, taskbar attention
- Links open in your browser; downloads go to Downloads
- Voice notes, camera, clipboard images, spell-check
- Runs in the background like Discord:
  - a tray icon with a red dot and a count in its tooltip when chats are unread;
  - closing the window hides it to the tray (quit from the tray menu, or Ctrl+Q on Linux);
  - starts hidden in the tray when you log in (untick "Start on login" in the tray menu);
  - launching it again brings the running window back instead of opening a second copy.
- Linux tray: KDE, Ubuntu (AppIndicator extension), Cinnamon, XFCE, waybar… On plain GNOME
  without a tray extension there's no icon; launch Natter again to bring the window back.

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
python scripts/build.py --installer  # on Windows: setup wizard, needs Inno Setup 6
python scripts/build.py --exe        # on Windows: single portable .exe
```

Pushing a tag `vX.Y.Z` that matches `natter.__version__` makes CI publish a GitHub release
with both packages and the matching `CHANGELOG.md` section as notes.

## Layout

- `natter/config.py`: URLs, user agent, link policy, paths (pure, tested)
- `natter/state.py`: remembered window state and preferences (pure, tested)
- `natter/autostart.py`: start on login (XDG autostart entry / Windows Run key)
- `natter/tray_linux.py`: tray icon over D-Bus (StatusNotifierItem + dbusmenu), no extra libraries
- `natter/single_instance.py`: one copy per user on Windows (Linux uses GApplication)
- `natter/linux.py`: GTK + WebKitGTK backend
- `natter/windows.py`: pywebview + WebView2 backend
