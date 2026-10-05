"""Every on-screen text needs a Russian and an Italian translation, with the same placeholders."""
import ast
import string
from pathlib import Path

import pytest

from natter import config, i18n
from natter.locales import it, ru

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


CATALOGUES = [pytest.param(ru, 3, id="ru"), pytest.param(it, 2, id="it")]


@pytest.mark.parametrize("catalogue, forms", CATALOGUES)
def test_every_ui_string_is_translated(catalogue, forms):
    ui = calls("_") | {name for code, name in i18n.LANGUAGES if code == ""}
    missing = sorted(ui - catalogue.MESSAGES.keys())
    assert not missing, "Missing translation for:\n" + "\n".join(missing)


@pytest.mark.parametrize("catalogue, forms", CATALOGUES)
def test_every_plural_word_has_its_forms(catalogue, forms):
    missing = sorted(calls("plural", 1) - catalogue.PLURALS.keys())
    assert not missing, "Missing plural forms for: " + ", ".join(missing)
    assert all(len(f) == forms for f in catalogue.PLURALS.values())


@pytest.mark.parametrize("catalogue, forms", CATALOGUES)
def test_translations_keep_their_placeholders(catalogue, forms):
    wrong = [k for k, v in catalogue.MESSAGES.items() if placeholders(k) != placeholders(v)]
    assert not wrong, "Placeholders differ in: " + "; ".join(wrong)


@pytest.mark.parametrize("n, form", [(1, 0), (21, 0), (2, 1), (4, 1), (22, 1), (5, 2), (11, 2),
                                     (12, 2), (14, 2), (25, 2), (0, 2), (111, 2), (101, 0)])
def test_russian_plural_rule(n, form):
    assert i18n.plural_form(n) == form


@pytest.mark.parametrize("env, expected", [
    ({"LANG": "ru_RU.UTF-8"}, "ru"),
    ({"LANG": "it_IT.UTF-8"}, "it"),
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


def test_tray_tooltip_in_italian():
    i18n.install("it")
    assert config.tray_tooltip(0) == "Natter"
    assert config.tray_tooltip(1) == "Natter: 1 chat non letta"
    assert config.tray_tooltip(3) == "Natter: 3 chat non lette"
    assert i18n._("Start on login") == "Avvia all’accesso"


def test_italian_system_gets_italian(monkeypatch):
    monkeypatch.setattr(i18n, "system_language", lambda: "it")
    assert i18n.install("") == "it"
