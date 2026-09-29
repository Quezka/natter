"""Every on-screen text needs a Russian translation, with the same placeholders."""
import ast
import string
from pathlib import Path

import pytest

from natter import config, i18n
from natter.locales import ru

ROOT = Path(__file__).resolve().parent.parent / "natter"


@pytest.fixture(autouse=True)
def english_afterwards():
    yield
    i18n.install("en")


def _literal(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def calls(name: str, arg: int = 0) -> set[str]:
    found = set()
    for path in ROOT.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == name
                    and len(node.args) > arg):
                text = _literal(node.args[arg])
                if text:
                    found.add(text)
    return found


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_ui_string_is_translated():
    ui = calls("_") | {name for code, name in i18n.LANGUAGES if code == ""}
    missing = sorted(ui - ru.MESSAGES.keys())
    assert not missing, "Missing Russian for:\n" + "\n".join(missing)


def test_every_plural_word_has_three_forms():
    missing = sorted(calls("plural", 1) - ru.PLURALS.keys())
    assert not missing, "Missing Russian plural forms for: " + ", ".join(missing)
    assert all(len(forms) == 3 for forms in ru.PLURALS.values())


def test_translations_keep_their_placeholders():
    wrong = [k for k, v in ru.MESSAGES.items() if placeholders(k) != placeholders(v)]
    assert not wrong, "Placeholders differ in: " + "; ".join(wrong)


@pytest.mark.parametrize("n, form", [(1, 0), (21, 0), (2, 1), (4, 1), (22, 1), (5, 2), (11, 2),
                                     (12, 2), (14, 2), (25, 2), (0, 2), (111, 2), (101, 0)])
def test_russian_plural_rule(n, form):
    assert i18n.plural_form(n) == form


@pytest.mark.parametrize("env, expected", [
    ({"LANG": "ru_RU.UTF-8"}, "ru"),
    ({"LANGUAGE": "ru_RU:en", "LANG": "en_GB.UTF-8"}, "ru"),
    ({"LANGUAGE": "", "LANG": "en_GB.UTF-8"}, "en"),
    ({"LC_ALL": "C.UTF-8", "LANG": "ru_RU.UTF-8"}, "ru"),
    ({}, "en"),
])
def test_system_language_comes_from_the_locale(monkeypatch, env, expected):
    monkeypatch.setattr(i18n.sys, "platform", "linux")
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    assert i18n.system_language() == expected


def test_system_choice_follows_the_desktop(monkeypatch):
    monkeypatch.setattr(i18n, "system_language", lambda: "ru")
    assert i18n.install("") == "ru"
    assert i18n.install("en") == "en"
    monkeypatch.setattr(i18n, "system_language", lambda: "de")
    assert i18n.install("") == "en"
    assert i18n.install("xx") == "en"


def test_tray_tooltip_in_russian():
    i18n.install("ru")
    assert config.tray_tooltip(0) == "Natter"
    assert config.tray_tooltip(1) == "Natter: 1 непрочитанный чат"
    assert config.tray_tooltip(3) == "Natter: 3 непрочитанных чата"
    assert config.tray_tooltip(11) == "Natter: 11 непрочитанных чатов"
    assert i18n._("Start on login") == "Запускать при входе в систему"
