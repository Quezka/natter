"""Window geometry and zoom, remembered between runs."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass
class WindowState:
    width: int = 1100
    height: int = 760
    maximized: bool = False
    zoom: float = 1.0

    @classmethod
    def load(cls, path: Path) -> "WindowState":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        state = cls()
        for field in fields(cls):
            value, default = raw.get(field.name), getattr(state, field.name)
            if isinstance(default, bool):
                if isinstance(value, bool):
                    setattr(state, field.name, value)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                setattr(state, field.name, type(default)(value))
        state.width = max(state.width, 480)
        state.height = max(state.height, 400)
        state.zoom = min(max(state.zoom, 0.5), 3.0)
        return state

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
