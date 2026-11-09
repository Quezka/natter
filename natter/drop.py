"""Dropping files from the file manager onto WhatsApp.

WebKitGTK doesn't hand files dragged in from another app (Files, the desktop) to the page reliably, so WhatsApp
never sees them. The Linux backend takes the drop itself, serves each file to the page under a one-time address
(`natter-file://<token>/<n>`), and this script turns them into a real drop on the chat under the pointer, as if the
page had received them itself. Platform-independent, so it's tested without a display.
"""
from __future__ import annotations

import json
import mimetypes
import secrets
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

SCHEME = "natter-file"


@dataclass(frozen=True)
class Dropped:
    path: Path
    name: str
    mime: str


def files_from_uris(uris: list[str]) -> list[Dropped]:
    """The local files among dropped URIs (folders and anything not on this computer are left out)."""
    out = []
    for uri in uris:
        uri = uri.strip()
        if not uri or uri.startswith("#"):
            continue
        parsed = urlparse(uri)
        if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
            continue
        path = Path(unquote(parsed.path))
        if not path.is_file():
            continue
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        out.append(Dropped(path, path.name, mime))
    return out


class DropShelf:
    """The files of the latest drop, each reachable once by its token and number. A new drop replaces the old one,
    so the page can never read anything but what was just dropped on it."""

    def __init__(self):
        self.token = ""
        self.files: list[Dropped] = []

    def put(self, files: list[Dropped]) -> str:
        self.token = secrets.token_hex(16)
        self.files = list(files)
        return self.token

    def take(self, uri: str) -> Dropped | None:
        """The file an address asks for, if it belongs to the current drop."""
        parsed = urlparse(uri)
        if parsed.scheme != SCHEME or not self.token or parsed.netloc != self.token:
            return None
        try:
            index = int(parsed.path.strip("/"))
        except ValueError:
            return None
        return self.files[index] if 0 <= index < len(self.files) else None


def drop_script(token: str, files: list[Dropped], x: float, y: float) -> str:
    """Fetches the dropped files into the page and drops them where the pointer was (x, y in CSS pixels)."""
    meta = json.dumps([{"name": f.name, "type": f.mime} for f in files])
    return f"""
(async () => {{
  const meta = {meta};
  const files = [];
  for (let i = 0; i < meta.length; i++) {{
    const blob = await (await fetch("{SCHEME}://{token}/" + i)).blob();
    files.push(new File([blob], meta[i].name, {{ type: meta[i].type }}));
  }}
  const data = new DataTransfer();
  files.forEach(f => data.items.add(f));
  const target = document.elementFromPoint({x}, {y}) || document.body;
  for (const type of ["dragenter", "dragover", "drop"]) {{
    const event = new Event(type, {{ bubbles: true, cancelable: true }});
    Object.defineProperty(event, "dataTransfer", {{ value: data }});
    Object.defineProperty(event, "clientX", {{ value: {x} }});
    Object.defineProperty(event, "clientY", {{ value: {y} }});
    target.dispatchEvent(event);
  }}
  return files.length;
}})();
"""
