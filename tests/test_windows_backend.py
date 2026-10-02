import pytest

pytest.importorskip("webview")
PIL = pytest.importorskip("PIL.Image")

from natter import windows  # noqa: E402


def test_badge_draws_a_red_dot_top_right_and_keeps_the_original():
    base = PIL.new("RGBA", (256, 256), (0, 128, 0, 255))
    badged = windows._badge(base)
    assert badged.getpixel((212, 44))[:3] == (0xE5, 0x48, 0x4D)
    assert badged.getpixel((40, 200)) == (0, 128, 0, 255)
    assert base.getpixel((212, 44)) == (0, 128, 0, 255)


@pytest.mark.skipif("sys.platform != 'win32'")
def test_tray_builds_its_menu_on_windows():
    tray = windows._Tray(lambda: None, lambda: None, lambda: None, lambda: True,
                         lambda _code: None, lambda: "")
    import pystray

    labels = [item.text for item in tray.icon.menu.items if item is not pystray.Menu.SEPARATOR]
    assert labels == ["Open Natter", "Start on login", "Language", "Check for updates…",
                      "Check for updates automatically", "Quit Natter"]
    tray.set_unread(3)
    assert tray.icon.title == "Natter: 3 unread chats"
