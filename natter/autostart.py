"""Start Natter hidden in the tray when the user logs in.

Linux: an XDG autostart entry in ~/.config/autostart. Windows: the per-user Run key.
Both are rewritten on every launch, so they follow the app if it moves.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from natter import APP_ID, APP_NAME
from natter.i18n import _

BACKGROUND_FLAG = "--background"
DEB_PREFIX = Path("/usr/lib/natter")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_command() -> list[str]:
    """The command that starts this copy of Natter in the background."""
    if getattr(sys, "frozen", False):  # PyInstaller .exe
        return [sys.executable, BACKGROUND_FLAG]
    if Path(__file__).resolve().is_relative_to(DEB_PREFIX):  # installed from the .deb
        return ["natter", BACKGROUND_FLAG]
    python = sys.executable
    if sys.platform == "win32":  # no console window at login
        python = str(Path(python).with_name("pythonw.exe"))
    return [python, "-m", "natter", BACKGROUND_FLAG]


def desktop_exec(args: list[str]) -> str:
    """Quote arguments for a .desktop Exec= line (Desktop Entry spec, "Exec key")."""
    def quote(arg: str) -> str:
        if arg and not any(c in arg for c in ' \t\n"\'\\><~|&;$*?#()`'):
            return arg
        escaped = "".join("\\" + c if c in '"`$\\' else c for c in arg)
        return f'"{escaped}"'
    return " ".join(quote(a) for a in args)


def desktop_entry(args: list[str]) -> str:
    comment = _("Start {app} in the background").format(app=APP_NAME)
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Comment={comment}\n"
        f"Exec={desktop_exec(args)}\n"
        f"Icon={APP_ID}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def linux_entry_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "autostart" / f"{APP_ID}.desktop"


def set_enabled(enabled: bool) -> None:
    """Add or remove the login entry. Failures are ignored: autostart is a convenience."""
    try:
        if sys.platform == "win32":
            _set_windows(enabled)
        else:
            _set_linux(enabled)
    except OSError:
        pass


def _set_linux(enabled: bool) -> None:
    path = linux_entry_path()
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(desktop_entry(launch_command()), encoding="utf-8")
    else:
        path.unlink(missing_ok=True)


def _set_windows(enabled: bool) -> None:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                              subprocess.list2cmdline(launch_command()))
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
