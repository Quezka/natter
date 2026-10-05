"""Translations for Natter's own text (tray menu, tooltip, login entry, --help).

Wrap on-screen text in `_()`; it returns the text in the chosen language, or the
English original when there's no translation. Text with values in it uses named
placeholders: `_("Open {app}").format(app=...)`. Tests check every `_()` string has
a Russian and an Italian translation.

WhatsApp Web itself isn't translated here: it follows the system language and has its
own language setting.
"""
from __future__ import annotations

import importlib
import os
import sys

# (code, name in its own language). "" follows the system.
LANGUAGES = [("", "System"), ("en", "English"), ("it", "Italiano"), ("ru", "Русский")]
SUPPORTED = {"en", "it", "ru"}

_language = "en"
_messages: dict[str, str] = {}
_plurals: dict[str, tuple[str, str, str]] = {}


def system_language() -> str:
    """The desktop's language as a two-letter code, e.g. "ru"."""
    if sys.platform == "win32":
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        return {0x19: "ru", 0x10: "it"}.get(lang_id, "en")
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "").split(":")[0]
        if value and value not in ("C", "POSIX") and not value.startswith("C."):
            return value[:2].lower()
    return "en"


def resolve(code: str) -> str:
    """What "" (system) means here: Italian and Russian systems get their language, the rest English."""
    if code in SUPPORTED:
        return code
    system = system_language()
    return system if system in SUPPORTED else "en"


def install(code: str) -> str:
    """Activate a language ("", "en", "it" or "ru") and return the one now in use."""
    global _language, _messages, _plurals
    _language = resolve(code)
    if _language == "en":
        _messages, _plurals = {}, {}
    else:
        module = importlib.import_module(f"natter.locales.{_language}")
        _messages, _plurals = module.MESSAGES, module.PLURALS
    return _language


def language() -> str:
    return _language


def _(text: str) -> str:
    return _messages.get(text, text)


def plural_form(n: int) -> int:
    """Russian: 1 чат (0), 2-4 чата (1), 5+ чатов (2), with 11-14 counting as 5+."""
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return 0
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return 1
    return 2


def _form(n: int) -> int:
    """Which plural form the active language uses: Italian has two, Russian three."""
    return (0 if n == 1 else 1) if _language == "it" else plural_form(n)


def plural(n: int, word: str) -> str:
    """"3 unread chats" / "3 chat non letti" / "3 непрочитанных чата". `word` is the English singular."""
    if word in _plurals:
        return f"{n} {_plurals[word][_form(n)]}"
    return f"{n} {word}{'' if n == 1 else 's'}"
