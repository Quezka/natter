"""Platform-independent settings and helpers shared by every backend."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from natter import APP_ID, APP_NAME  # noqa: F401 (re-exported for the backends)
from natter.i18n import _, plural

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


def tray_tooltip(unread: int) -> str:
    if not unread:
        return APP_NAME
    return _("{app}: {chats}").format(app=APP_NAME, chats=plural(unread, "unread chat"))


def badged_svg(svg: str) -> str:
    """The app icon with a red dot in the corner, for the tray when chats are unread."""
    dot = '<circle cx="212" cy="44" r="40" fill="#e5484d" stroke="#fff" stroke-width="10"/>'
    head, sep, tail = svg.rpartition("</svg>")
    return f"{head}{dot}\n{sep}{tail}" if sep else svg


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
