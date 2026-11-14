"""The suite's look for Natter's own windows (Settings), as GTK CSS: the same colour tokens as suite-kit
(`quezka_ui/theme.py`). Plain backgrounds, never a gradient wash. Pure Python, no GTK, so it's tested without a display."""
from __future__ import annotations

# material 3 tonal = suite tokens 2026-11-14 (suite-rs/design/tokens.json)
LIGHT = {
    "bg": "#f7f7fb", "surface": "#ffffff", "raised": "#eaeaf2", "border": "#b6b6c4",
    "text": "#111116", "muted": "#3d3d46", "faint": "#5b5b66",
    "accent": "#4f46e5", "accent_soft": "#e3e2fb", "on_accent": "#ffffff", "glow": "#4f46e5",
}
DARK = {
    "bg": "#121218", "surface": "#1d1d24", "raised": "#2a2a33", "border": "#4a4a56",
    "text": "#f8f7fc", "muted": "#cfcfd9", "faint": "#a8a8b4",
    "accent": "#a9a6ff", "accent_soft": "#37356e", "on_accent": "#0b0b14", "glow": "#a9a6ff",
}


def _rgb(colour: str) -> tuple[int, int, int]:
    colour = colour.lstrip("#")
    return int(colour[0:2], 16), int(colour[2:4], 16), int(colour[4:6], 16)


def mix(a: str, b: str, amount: float) -> str:
    (ra, ga, ba), (rb, gb, bb) = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * amount) for x, y in ((ra, rb), (ga, gb), (ba, bb)))


def rgba(colour: str, alpha: float) -> str:
    r, g, b = _rgb(colour)
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"


def css(dark: bool) -> str:
    """The style sheet for the Settings window: plain background, solid cards with a light top edge, big clear
    text. (GTK 3 can't blur what's behind a widget, so there's no glass here; never a gradient wash instead.)"""
    t = DARK if dark else LIGHT
    edge = rgba("#ffffff", 0.10 if dark else 0.95)
    return f"""
    window.natter-settings {{ background-color: {t["bg"]}; color: {t["text"]}; }}
    .natter-settings .title {{ font-size: 20pt; font-weight: 800; }}
    .natter-settings .card {{
        background-color: {t["surface"]};
        border: 1px solid {rgba(t["border"], 0.45)};
        border-top-color: {edge};
        border-radius: 28px;
        padding: 14px 16px;
    }}
    .natter-settings .card-title {{ color: {t["accent"]}; font-weight: 700; }}
    .natter-settings .row-title {{ font-weight: 600; font-size: 11.5pt; }}
    .natter-settings .hint {{ color: {t["faint"]}; }}
    .natter-settings button {{ border-radius: 12px; padding: 6px 14px; }}
    .natter-settings button.suggested-action {{ background: {t["accent"]}; color: {t["on_accent"]}; }}
    .natter-settings switch:checked {{ background: {t["accent"]}; }}
    """


SHORTCUT = "<Control><Alt>w"
SHORTCUT_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/natter-toggle/"


def with_shortcut(paths: list[str]) -> list[str]:
    """GNOME's list of custom shortcuts, with Natter's added once."""
    return paths if SHORTCUT_PATH in paths else [*paths, SHORTCUT_PATH]


def without_shortcut(paths: list[str]) -> list[str]:
    return [p for p in paths if p != SHORTCUT_PATH]
