"""The Settings window's look, the shortcut list and the new preferences, without GTK."""
from natter import look
from natter.state import Preferences


def test_css_is_plain_with_no_gradient_wash():
    for dark in (False, True):
        sheet = look.css(dark)
        assert "gradient" not in sheet and ".card" in sheet


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


def test_page_notifications_are_checked_and_keyed_by_chat():
    from natter import webpage
    m = webpage.notify_message('{"kind": "show", "id": 3, "title": "Sam", "body": "hi", "tag": "chat1"}')
    assert m["title"] == "Sam" and webpage.notification_key(m) == "wa-chat1"
    assert webpage.notification_key(webpage.notify_message('{"kind": "close", "id": 4}')) == "wa-4"
    for bad in ("nope", '{"kind": "run", "id": 1}', '{"kind": "show", "id": "1"}', "[]"):
        assert webpage.notify_message(bad) is None
    assert "requestPermission" in webpage.LINUX_NOTIFY_SCRIPT and "natterNotify" in webpage.LINUX_NOTIFY_SCRIPT
