"""The scripts and the Settings page Natter puts into WebView2 on Windows."""
from natter import webpage
from natter.state import Preferences


def test_the_quiet_script_wraps_notifications_once_and_switches():
    assert "window.Notification = Quiet" in webpage.QUIET_SCRIPT
    assert "__natterWrapped" in webpage.QUIET_SCRIPT
    assert webpage.quiet_switch(True) == "window.__natterQuiet = true;"
    assert webpage.quiet_switch(False) == "window.__natterQuiet = false;"


def test_the_settings_page_has_real_glass_and_every_switch():
    prefs = Preferences(do_not_disturb=True, language="it")
    page = webpage.settings_page(prefs, auto_update=False, dark=True)
    assert "backdrop-filter: blur(" in page and "position: sticky" in page  # a real glass header
    assert "gradient" not in page and "blob" not in page
    for name in ("set_dnd", "set_start_on_login", "set_shortcut", "set_memory", "set_language", "set_auto_update",
                 "check_updates"):
        assert f"pywebview.api.{name}(" in page
    assert 'onchange="pywebview.api.set_dnd(this.checked)" checked' in page
    assert '<option value="it" selected>' in page
    assert "<script" not in page.lower()  # nothing runs but the switches' calls
