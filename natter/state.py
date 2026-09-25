"""Window geometry, zoom and preferences, remembered between runs."""
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

    @classmethod
    def load(cls, path: Path) -> "WindowState":
        state = _load(cls, path)
        state.width = max(state.width, 480)
        state.height = max(state.height, 400)
        state.zoom = min(max(state.zoom, 0.5), 3.0)
        return state

    def save(self, path: Path) -> None:
        _save(self, path)


@dataclass
class Preferences:
    # On by default, like Discord: Natter starts hidden in the tray when you log in.
    start_on_login: bool = True

    @classmethod
    def load(cls, path: Path) -> "Preferences":
        return _load(cls, path)

    def save(self, path: Path) -> None:
        _save(self, path)
