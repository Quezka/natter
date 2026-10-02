"""Window geometry, zoom and preferences (start on login, language), remembered between runs."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path


def _load(cls, path: Path):
    """An instance of the dataclass `cls` from JSON, keeping defaults for bad or missing values."""
    state = cls()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return state
    if not isinstance(raw, dict):
        return state
    for field in fields(cls):
        value, default = raw.get(field.name), getattr(state, field.name)
        if isinstance(default, bool):
            if isinstance(value, bool):
                setattr(state, field.name, value)
        elif isinstance(default, str):
            if isinstance(value, str):
                setattr(state, field.name, value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            setattr(state, field.name, type(default)(value))
    return state


def _save(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(obj), indent=2), encoding="utf-8")


@dataclass
class WindowState:
    width: int = 1100
    height: int = 760
    maximized: bool = False
    zoom: float = 1.0
    zoom_chosen: bool = False  # until you zoom yourself, small screens get a smaller default

    @classmethod
    def load(cls, path: Path) -> "WindowState":
        state = _load(cls, path)
        state.width = max(state.width, 480)
        state.height = max(state.height, 400)
        state.zoom = min(max(state.zoom, 0.5), 3.0)
        return state

    def save(self, path: Path) -> None:
        _save(self, path)


SMALL_SCREEN = 800  # screens up to this tall (like 1366x768) start a little zoomed out
SMALL_SCREEN_ZOOM = 0.85
SCREEN_MARGIN = 40  # room for the title bar and panels


def fit_size(width: int, height: int, area_width: int, area_height: int) -> tuple[int, int]:
    """A window size that fits in the free part of the screen."""
    return (min(width, max(area_width - SCREEN_MARGIN, 480)),
            min(height, max(area_height - SCREEN_MARGIN, 400)))


def starting_zoom(state: "WindowState", screen_height: int | None) -> float:
    """What you chose, or on a small screen a little smaller than usual."""
    if state.zoom_chosen or not screen_height:
        return state.zoom
    return SMALL_SCREEN_ZOOM if screen_height <= SMALL_SCREEN else state.zoom


@dataclass
class Preferences:
    # On by default, like Discord: Natter starts hidden in the tray when you log in.
    start_on_login: bool = True
    language: str = ""  # "" follows the system; otherwise a code from i18n.LANGUAGES

    @classmethod
    def load(cls, path: Path) -> "Preferences":
        return _load(cls, path)

    def save(self, path: Path) -> None:
        _save(self, path)
