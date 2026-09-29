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


def test_pixmap_variant_keeps_sizes_and_bytes():
    pixmaps = [(1, 1, bytes([1, 2, 3, 4])), (2, 1, bytes(range(8)))]
    unpacked = [(w, h, bytes(data)) for w, h, data in tray_linux.pixmap_variant(pixmaps).unpack()]
    assert unpacked == pixmaps


def test_tray_answers_property_reads_quickly():
    # Regression: building the icon variant per read froze the main loop for ~10s at startup.
    import time

    tray = tray_linux.Tray(ICON, lambda: None, [tray_linux.MenuItem(1, "Open")])
    iface = "org.kde.StatusNotifierItem"
    props = ["Category", "Id", "Title", "Status", "WindowId", "IconName", "IconPixmap",
             "AttentionIconName", "AttentionIconPixmap", "OverlayIconName",
             "OverlayIconPixmap", "ToolTip", "ItemIsMenu", "Menu"]
    start = time.monotonic()
    values = {p: tray._on_get_property(None, None, None, iface, p) for p in props}
    assert time.monotonic() - start < 0.1
    assert all(v is not None for v in values.values())
    assert values["IconPixmap"].get_type_string() == "a(iiay)"
    assert len(values["IconPixmap"].unpack()) == len(tray_linux.ICON_SIZES)
    assert tray._on_get_property(None, None, None, iface, "Nope") is None


def test_unread_switches_to_the_badged_icon():
    tray = tray_linux.Tray(ICON, lambda: None, [])
    get = lambda p: tray._on_get_property(None, None, None, "org.kde.StatusNotifierItem", p)  # noqa: E731
    plain = get("IconPixmap").unpack()
    tray.set_unread(2)
    assert get("IconPixmap").unpack() != plain
    assert get("ToolTip").unpack()[3] == "Natter: 2 unread chats"


def test_submenus_and_radio_items_for_dbusmenu():
    english = tray_linux.MenuItem(11, "English", checked=True, radio=True)
    menu = tray_linux.MenuItem(6, "Language", children=[
        tray_linux.MenuItem(10, "System", checked=False, radio=True), english])
    assert english.properties()["toggle-type"].unpack() == "radio"
    assert menu.properties()["children-display"].unpack() == "submenu"
    item_id, _props, children = menu.layout()
    assert item_id == 6 and [c.unpack()[0] for c in children] == [10, 11]
    assert [i.id for i in tray_linux.all_items([tray_linux.MenuItem(1, "Open"), menu])] == [1, 6, 10, 11]
