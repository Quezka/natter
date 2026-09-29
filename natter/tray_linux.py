"""Tray icon for Linux, spoken directly over D-Bus.

Implements the StatusNotifierItem protocol (what KDE, Ubuntu's AppIndicator extension,
Cinnamon, XFCE and waybar show as tray icons) plus its com.canonical.dbusmenu menu, so no
extra library such as libayatana-appindicator is needed. If no tray host is running (plain
GNOME without the extension), the icon simply doesn't appear.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio, GLib  # noqa: E402

from natter import APP_ID, APP_NAME, config  # noqa: E402

WATCHER = "org.kde.StatusNotifierWatcher"
ITEM_PATH = "/StatusNotifierItem"
MENU_PATH = "/MenuBar"
ICON_SIZES = (22, 32, 48, 64)

NODE_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <method name="Activate"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
    <method name="SecondaryActivate"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
    <method name="ContextMenu"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
    <method name="Scroll"><arg name="delta" type="i" direction="in"/><arg name="orientation" type="s" direction="in"/></method>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewToolTip"/>
    <signal name="NewStatus"><arg name="status" type="s"/></signal>
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
  </interface>
  <interface name="com.canonical.dbusmenu">
    <method name="GetLayout">
      <arg name="parentId" type="i" direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision" type="u" direction="out"/>
      <arg name="layout" type="(ia{sv}av)" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties" type="a(ia{sv})" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg name="id" type="i" direction="in"/>
      <arg name="name" type="s" direction="in"/>
      <arg name="value" type="v" direction="out"/>
    </method>
    <method name="Event">
      <arg name="id" type="i" direction="in"/>
      <arg name="eventId" type="s" direction="in"/>
      <arg name="data" type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg name="events" type="a(isvu)" direction="in"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg name="id" type="i" direction="in"/>
      <arg name="needUpdate" type="b" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="updatesNeeded" type="ai" direction="out"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <signal name="ItemsPropertiesUpdated">
      <arg name="updatedProps" type="a(ia{sv})"/>
      <arg name="removedProps" type="a(ias)"/>
    </signal>
    <signal name="LayoutUpdated">
      <arg name="revision" type="u"/>
      <arg name="parent" type="i"/>
    </signal>
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
  </interface>
</node>
"""


@dataclass
class MenuItem:
    id: int
    label: str = ""
    on_click: Callable[[], None] | None = None
    separator: bool = False
    checked: bool | None = None  # None: not a checkbox
    radio: bool = False  # shown as a radio button rather than a checkmark
    children: list[MenuItem] = field(default_factory=list)  # non-empty: a submenu

    def properties(self) -> dict[str, GLib.Variant]:
        if self.separator:
            return {"type": GLib.Variant("s", "separator")}
        props = {"label": GLib.Variant("s", self.label), "enabled": GLib.Variant("b", True)}
        if self.checked is not None:
            props["toggle-type"] = GLib.Variant("s", "radio" if self.radio else "checkmark")
            props["toggle-state"] = GLib.Variant("i", int(self.checked))
        if self.children:
            props["children-display"] = GLib.Variant("s", "submenu")
        return props

    def layout(self) -> tuple:
        """This item as dbusmenu's (ia{sv}av), with its submenu."""
        return (self.id, self.properties(),
                [GLib.Variant("(ia{sv}av)", child.layout()) for child in self.children])


def all_items(items: list[MenuItem]) -> list[MenuItem]:
    """The items and, depth first, everything in their submenus."""
    return [found for item in items for found in (item, *all_items(item.children))]


def _later(callback: Callable[[], object]) -> None:
    """Run `callback` once on the main loop, after the D-Bus call has been answered."""
    GLib.idle_add(lambda: callback() and False)


def argb_pixmap(pixels: bytes, width: int, height: int, rowstride: int, channels: int) -> bytes:
    """GdkPixbuf RGB(A) rows to the packed big-endian ARGB32 that StatusNotifierItem wants."""
    rows = b"".join(pixels[y * rowstride:y * rowstride + width * channels] for y in range(height))
    out = bytearray(width * height * 4)
    out[0::4] = rows[3::4] if channels == 4 else b"\xff" * (width * height)
    out[1::4] = rows[0::channels]
    out[2::4] = rows[1::channels]
    out[3::4] = rows[2::channels]
    return bytes(out)


def pixmap_variant(pixmaps: list[tuple[int, int, bytes]]) -> GLib.Variant:
    """An `a(iiay)` variant built in bulk.

    GLib.Variant("a(iiay)", ...) converts every byte to its own variant in Python, which
    takes most of a second for the tray icon and freezes the main loop (and WebKit with it).
    """
    return GLib.Variant.new_array(GLib.VariantType("(iiay)"), [
        GLib.Variant.new_tuple(
            GLib.Variant("i", width),
            GLib.Variant("i", height),
            GLib.Variant.new_from_bytes(GLib.VariantType("ay"), GLib.Bytes.new(data), True),
        )
        for width, height, data in pixmaps
    ])


def render_pixmaps(svg: str) -> list[tuple[int, int, bytes]]:
    pixmaps = []
    for size in ICON_SIZES:
        loader = GdkPixbuf.PixbufLoader()
        loader.set_size(size, size)
        loader.write(svg.encode())
        loader.close()
        pix = loader.get_pixbuf()
        data = pix.get_pixels()
        pixmaps.append((pix.get_width(), pix.get_height(),
                        argb_pixmap(data, pix.get_width(), pix.get_height(),
                                    pix.get_rowstride(), pix.get_n_channels())))
    return pixmaps


class Tray:
    """A tray icon with a menu. Call `set_unread` when the unread count changes."""

    def __init__(self, svg: str, on_activate: Callable[[], None], items: list[MenuItem]) -> None:
        self.on_activate = on_activate
        self.items = items
        self.unread = 0
        self.revision = 1
        self._icons = {False: pixmap_variant(render_pixmaps(svg)),
                       True: pixmap_variant(render_pixmaps(config.badged_svg(svg)))}
        self._bus: Gio.DBusConnection | None = None
        self._name = f"org.kde.StatusNotifierItem-{os.getpid()}-1"
        self._node = Gio.DBusNodeInfo.new_for_xml(NODE_XML)

    def start(self) -> None:
        Gio.bus_own_name(Gio.BusType.SESSION, self._name, Gio.BusNameOwnerFlags.NONE,
                         self._on_bus_acquired, None, None)

    # --- state changes ------------------------------------------------------------

    def set_unread(self, unread: int) -> None:
        if unread == self.unread:
            return
        self.unread = unread
        for signal in ("NewIcon", "NewToolTip", "NewTitle"):
            self._emit(ITEM_PATH, "org.kde.StatusNotifierItem", signal, None)

    def set_items(self, items: list[MenuItem]) -> None:
        """Replace the whole menu, e.g. after the language changed; the tooltip follows too."""
        self.items = items
        self.revision += 1
        self._emit(MENU_PATH, "com.canonical.dbusmenu", "LayoutUpdated",
                   GLib.Variant("(ui)", (self.revision, 0)))
        for signal in ("NewToolTip", "NewTitle"):
            self._emit(ITEM_PATH, "org.kde.StatusNotifierItem", signal, None)

    def set_checked(self, item_id: int, checked: bool) -> None:
        item = self._item(item_id)
        if item is None or item.checked is None:
            return
        item.checked = checked
        self.revision += 1
        self._emit(MENU_PATH, "com.canonical.dbusmenu", "ItemsPropertiesUpdated",
                   GLib.Variant("(a(ia{sv})a(ias))",
                                ([(item.id, item.properties())], [])))
        self._emit(MENU_PATH, "com.canonical.dbusmenu", "LayoutUpdated",
                   GLib.Variant("(ui)", (self.revision, 0)))

    # --- D-Bus plumbing -------------------------------------------------------------

    def _on_bus_acquired(self, bus: Gio.DBusConnection, _name: str) -> None:
        self._bus = bus
        for path, iface in ((ITEM_PATH, self._node.interfaces[0]),
                            (MENU_PATH, self._node.interfaces[1])):
            bus.register_object(path, iface, self._on_method, self._on_get_property, None)
        # Register now, and again whenever a tray host (re)starts, e.g. after a shell restart.
        Gio.bus_watch_name_on_connection(bus, WATCHER, Gio.BusNameWatcherFlags.NONE,
                                         lambda *_: self._register(), None)

    def _register(self) -> None:
        self._bus.call(WATCHER, "/StatusNotifierWatcher", WATCHER, "RegisterStatusNotifierItem",
                       GLib.Variant("(s)", (self._name,)), None, Gio.DBusCallFlags.NONE, -1,
                       None, None)

    def _emit(self, path: str, iface: str, signal: str, params) -> None:
        if self._bus is not None:
            self._bus.emit_signal(None, path, iface, signal, params)

    def _on_get_property(self, _bus, _sender, _path, iface, prop):
        # Build only the property asked for: the tray host reads them one at a time.
        if iface == "com.canonical.dbusmenu":
            return {
                "Version": lambda: GLib.Variant("u", 3),
                "TextDirection": lambda: GLib.Variant("s", "ltr"),
                "Status": lambda: GLib.Variant("s", "normal"),
                "IconThemePath": lambda: GLib.Variant("as", []),
            }.get(prop, lambda: None)()
        title = config.tray_tooltip(self.unread)
        no_pixmap = lambda: GLib.Variant("a(iiay)", [])  # noqa: E731
        return {
            "Category": lambda: GLib.Variant("s", "Communications"),
            "Id": lambda: GLib.Variant("s", APP_ID),
            "Title": lambda: GLib.Variant("s", title),
            "Status": lambda: GLib.Variant("s", "Active"),
            "WindowId": lambda: GLib.Variant("i", 0),
            "IconName": lambda: GLib.Variant("s", ""),
            "IconPixmap": lambda: self._icons[self.unread > 0],
            "AttentionIconName": lambda: GLib.Variant("s", ""),
            "AttentionIconPixmap": no_pixmap,
            "OverlayIconName": lambda: GLib.Variant("s", ""),
            "OverlayIconPixmap": no_pixmap,
            "ToolTip": lambda: GLib.Variant("(sa(iiay)ss)", ("", [], APP_NAME, title)),
            "ItemIsMenu": lambda: GLib.Variant("b", False),
            "Menu": lambda: GLib.Variant("o", MENU_PATH),
        }.get(prop, lambda: None)()

    def _on_method(self, _bus, _sender, _path, _iface, method, params, invocation) -> None:
        reply = None
        if method in ("Activate", "SecondaryActivate"):
            _later(self.on_activate)
        elif method == "GetLayout":
            parent = params.unpack()[0]  # hosts ask for a submenu by its id
            item = self._item(parent)
            layout = item.layout() if parent and item else self._layout()
            reply = GLib.Variant("(u(ia{sv}av))", (self.revision, layout))
        elif method == "GetGroupProperties":
            ids = params.unpack()[0]
            found = [(i.id, i.properties()) for i in all_items(self.items) if not ids or i.id in ids]
            if not ids or 0 in ids:
                found.insert(0, (0, self._root_properties()))
            reply = GLib.Variant("(a(ia{sv}))", (found,))
        elif method == "GetProperty":
            item_id, name = params.unpack()
            props = self._root_properties() if item_id == 0 else (self._item(item_id).properties()
                                                                 if self._item(item_id) else {})
            value = props.get(name)
            if value is None:
                invocation.return_dbus_error("org.freedesktop.DBus.Error.InvalidArgs",
                                             f"no property {name} on item {item_id}")
                return
            reply = GLib.Variant("(v)", (value,))
        elif method == "Event":
            item_id, event, _data, _time = params.unpack()
            self._clicked(item_id, event)
        elif method == "EventGroup":
            errors = []
            for item_id, event, _data, _time in params.unpack()[0]:
                if not self._clicked(item_id, event):
                    errors.append(item_id)
            reply = GLib.Variant("(ai)", (errors,))
        elif method == "AboutToShow":
            reply = GLib.Variant("(b)", (False,))
        elif method == "AboutToShowGroup":
            reply = GLib.Variant("(aiai)", ([], []))
        invocation.return_value(reply)

    def _clicked(self, item_id: int, event: str) -> bool:
        item = self._item(item_id)
        if item is None:
            return item_id == 0
        if event == "clicked" and item.on_click is not None:
            _later(item.on_click)
        return True

    def _item(self, item_id: int) -> MenuItem | None:
        return next((i for i in all_items(self.items) if i.id == item_id), None)

    @staticmethod
    def _root_properties() -> dict[str, GLib.Variant]:
        return {"children-display": GLib.Variant("s", "submenu")}

    def _layout(self):
        return (0, self._root_properties(),
                [GLib.Variant("(ia{sv}av)", i.layout()) for i in self.items])
