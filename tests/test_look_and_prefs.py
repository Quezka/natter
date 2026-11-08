"""The Settings window's look, the shortcut list and the new preferences, without GTK."""
from natter import look
from natter.state import Preferences


def test_css_has_the_glass_wash_and_frosted_cards():
    for dark in (False, True):
        sheet = look.css(dark)
        assert "linear-gradient" in sheet and "rgba(" in sheet and ".card" in sheet


def test_the_shortcut_is_added_once_and_removed_cleanly():
    other = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"
    added = look.with_shortcut([other])
    assert added == [other, look.SHORTCUT_PATH]
    assert look.with_shortcut(added) == added
    assert look.without_shortcut(added) == [other]


def test_preferences_round_trip_with_the_new_choices(tmp_path):
    prefs = Preferences()
    assert prefs.spelling() == ["en_US", "it_IT", "ru_RU"] and prefs.memory_saver and not prefs.do_not_disturb
    prefs.set_spelling("ru_RU", False)
    prefs.set_spelling("de_DE", True)
    prefs.do_not_disturb = True
    path = tmp_path / "p.json"
    prefs.save(path)
    back = Preferences.load(path)
    assert back.spelling() == ["en_US", "it_IT", "de_DE"] and back.do_not_disturb
