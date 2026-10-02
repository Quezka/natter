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


def test_the_tray_menu_offers_update_checks():
    app = linux.NatterApp(debug=False, background=False)
    items = {item.id: item for item in app._menu()}
    assert items[linux.MENU_CHECK_UPDATES].label == "Check for updates…"
    auto = items[linux.MENU_AUTO_UPDATE]
    assert auto.label == "Check for updates automatically" and auto.checked is True


def test_the_update_dialogs_module_builds_without_a_window():
    from natter.updates_gtk import UpdateUI, _message
    from natter.updates import UpdateError
    ui = UpdateUI(updater=None, window=lambda: None, restart=lambda: None,
                  open_url=lambda url: None)
    assert ui._window() is None
    assert _message(UpdateError("plain")) == "plain"
    assert "boom" in _message(RuntimeError("boom"))
