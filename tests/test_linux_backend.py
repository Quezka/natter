"""The GTK backend imports and builds its window without touching the network."""
import pytest

gi = pytest.importorskip("gi")
try:
    gi.require_version("WebKit2", "4.1")
except ValueError:
    pytest.skip("WebKitGTK 4.1 not installed", allow_module_level=True)

from natter import linux  # noqa: E402


def test_spelling_languages_are_plain_locale_names():
    langs = linux._spelling_languages()
    assert langs
    assert all("." not in lang and "@" not in lang for lang in langs)
