"""The suite's look for Natter's own windows (Settings), as GTK CSS: the same colour tokens as suite-kit
(`quezka_ui/theme.py`). Plain backgrounds, never a gradient wash. Pure Python, no GTK, so it's tested without a display."""
from __future__ import annotations

LIGHT = {
    "bg": "#f3f2ff", "surface": "#ffffff", "raised": "#e9e8ff", "border": "#b3b6cc",
    "text": "#0b0d14", "muted": "#343b4d", "faint": "#4d5466",
    "accent": "#4f46e5", "accent_soft": "#dcdbff", "on_accent": "#ffffff", "glow": "#ec4899",
}
DARK = {
    "bg": "#0e0e19", "surface": "#1a1a2b", "raised": "#27273f", "border": "#4b4e66",
    "text": "#f6f7fb", "muted": "#cbcfdd", "faint": "#a2a8bb",
    "accent": "#a9a6ff", "accent_soft": "#3b3984", "on_accent": "#0b0b14", "glow": "#ec4899",
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
        border-radius: 18px;
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
