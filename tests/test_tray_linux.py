import pytest

gi = pytest.importorskip("gi")
try:
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf  # noqa: F401
except (ValueError, ImportError):
    pytest.skip("GdkPixbuf not installed", allow_module_level=True)

from pathlib import Path  # noqa: E402

from natter import tray_linux  # noqa: E402

ICON = (Path(tray_linux.__file__).parent / "assets" / "icon.svg").read_text()


def test_rgba_rows_become_packed_argb():
    # 2x1 RGBA with a padded rowstride of 12
    pixels = bytes([10, 20, 30, 40, 50, 60, 70, 80, 0, 0, 0, 0])
    assert tray_linux.argb_pixmap(pixels, 2, 1, 12, 4) == bytes([40, 10, 20, 30, 80, 50, 60, 70])


def test_rgb_without_alpha_is_opaque():
    assert tray_linux.argb_pixmap(bytes([1, 2, 3]), 1, 1, 3, 3) == bytes([255, 1, 2, 3])


def test_icon_renders_at_every_tray_size():
    pixmaps = tray_linux.render_pixmaps(ICON)
    assert [(w, h) for w, h, _ in pixmaps] == [(s, s) for s in tray_linux.ICON_SIZES]
    assert all(len(data) == w * h * 4 for w, h, data in pixmaps)


def test_menu_items_describe_themselves_for_dbusmenu():
    check = tray_linux.MenuItem(3, "Start on login", checked=True).properties()
    assert check["toggle-type"].unpack() == "checkmark"
    assert check["toggle-state"].unpack() == 1
    assert tray_linux.MenuItem(2, separator=True).properties()["type"].unpack() == "separator"
    assert "toggle-type" not in tray_linux.MenuItem(1, "Open").properties()


def test_layout_lists_every_item_in_order():
    tray = tray_linux.Tray(ICON, lambda: None, [
        tray_linux.MenuItem(1, "Open"),
        tray_linux.MenuItem(2, separator=True),
        tray_linux.MenuItem(5, "Quit"),
    ])
    root_id, _props, children = tray._layout()
    assert root_id == 0
    assert [c.unpack()[0] for c in children] == [1, 2, 5]
