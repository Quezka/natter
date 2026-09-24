"""Platform-independent settings and helpers shared by every backend."""
from __future__ import annotations

import os
import re
import shutil
import socket
import sys
from pathlib import Path
from urllib.parse import urlsplit

from natter import APP_ID, APP_NAME  # noqa: F401 (re-exported for the backends)

URL = "https://web.whatsapp.com/"

# WhatsApp Web refuses WebKitGTK's own user agent ("browser not supported"), so the
# Linux backend presents itself as desktop Chrome. WebView2 is Chromium already.
LINUX_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

INTERNAL_HOSTS = {"web.whatsapp.com"}
_UNREAD = re.compile(r"^\((\d+)\)")


def is_internal(uri: str) -> bool:
    """True if the URI belongs inside the app window rather than the default browser."""
    parts = urlsplit(uri)
    if parts.scheme in ("blob", "data", "about"):
        return True
    return parts.scheme == "https" and parts.hostname in INTERNAL_HOSTS


def is_external_link(uri: str) -> bool:
    return urlsplit(uri).scheme in ("http", "https", "mailto", "tel") and not is_internal(uri)


def unread_count(page_title: str | None) -> int:
    """WhatsApp Web titles the page "(3) WhatsApp" when there are unread chats."""
    match = _UNREAD.match(page_title or "")
    return int(match.group(1)) if match else 0


def window_title(unread: int) -> str:
    return f"({unread}) {APP_NAME}" if unread else APP_NAME


def data_dir() -> Path:
    """Where the session (cookies, IndexedDB) and window state live."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / APP_NAME
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "natter"


def cache_dir() -> Path:
    if sys.platform == "win32":
        return data_dir() / "cache"
    base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "natter"


def unique_path(directory: Path, filename: str) -> Path:
    """A path in `directory` for `filename` that doesn't overwrite an existing file."""
    name = Path(filename).name or "download"
    candidate = directory / name
    stem, suffix = Path(name).stem, Path(name).suffix
    n = 1
    while candidate.exists():
        candidate = directory / f"{stem} ({n}){suffix}"
        n += 1
    return candidate


# ---- Linux: WhatsApp in an installed Chromium-family browser ------------------------
#
# WhatsApp Web only offers calls in Chromium browsers, and WebKitGTK also lacks the
# WebRTC pieces calls need. So on Linux Natter opens WhatsApp as an app window of a
# Chromium browser you already have, with its own profile; WebKitGTK is the fallback.

# In order of preference; the first one installed is used.
BROWSERS = (
    "google-chrome-stable", "google-chrome", "chromium", "chromium-browser",
    "microsoft-edge-stable", "microsoft-edge", "brave-browser",
)


def find_browser(which=shutil.which, env=os.environ) -> str | None:
    """The browser to use: $NATTER_BROWSER (a name or path) or the first one installed."""
    wanted = env.get("NATTER_BROWSER", "").strip()
    if wanted:
        return which(wanted)
    return next((path for name in BROWSERS if (path := which(name))), None)


def use_browser(env=os.environ) -> bool:
    """$NATTER_ENGINE=webkit keeps the old WebKitGTK window."""
    return env.get("NATTER_ENGINE", "").strip().lower() != "webkit"


def browser_profile(browser: str, home: Path | None = None) -> Path:
    """Natter's own profile for that browser, separate from your everyday one.

    Snap browsers can't write to hidden folders in your home, so theirs lives in the
    snap's own folder.
    """
    name = Path(browser).name
    real = os.path.realpath(browser)
    if real.startswith("/snap/") or "/snap/bin/" in browser:
        return (home or Path.home()) / "snap" / name / "common" / "natter-profile"
    return data_dir() / "browser" / name


def browser_command(browser: str, profile: Path, debug: bool = False) -> list[str]:
    command = [
        browser,
        f"--user-data-dir={profile}",
        f"--class={APP_ID}",  # so the dock shows Natter's icon for the window
        "--no-first-run",
        "--no-default-browser-check",
        f"--app={URL}",
    ]
    if debug:
        command.insert(-1, "--auto-open-devtools-for-tabs")
    return command


def profile_in_use(profile: Path) -> bool:
    """True if a browser is already running with this profile (a second launch would
    open WhatsApp twice). Chromium marks a running profile with a SingletonLock link
    pointing at "<hostname>-<pid>"."""
    try:
        target = os.readlink(profile / "SingletonLock")
    except OSError:
        return False
    host, _, pid = target.rpartition("-")
    if host != socket.gethostname() or not pid.isdigit():
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
