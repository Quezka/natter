"""Natter's Settings window (Linux), in the suite's look: a colour wash, frosted cards, switches, big clear text.

It only shows and changes `Preferences`; the backend (`linux.py`) passes in what to do when something changes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from natter import __version__, config, i18n, look  # noqa: E402
from natter.i18n import _  # noqa: E402
from natter.state import Preferences  # noqa: E402

SPELLING = (("en_US", "English"), ("it_IT", "Italiano"), ("ru_RU", "Русский"))


@dataclass
class Actions:
    """What the window can ask the backend to do."""
    changed: Callable[[], None]  # a preference changed: save it and apply what can be applied now
    language: Callable[[str], None]
    start_on_login: Callable[[bool], None]
    check_updates: Callable[[], None]
    shortcut: Callable[[bool], bool]  # turn the desktop shortcut on/off; False when the desktop can't
    shortcut_possible: bool


def _apply_css(window: Gtk.Window) -> None:
    settings = Gtk.Settings.get_default()
    dark = bool(settings and settings.get_property("gtk-application-prefer-dark-theme"))
    theme = (settings.get_property("gtk-theme-name") or "").lower() if settings else ""
    dark = dark or "dark" in theme
    provider = Gtk.CssProvider()
    provider.load_from_data(look.css(dark).encode())
    Gtk.StyleContext.add_provider_for_screen(window.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window.get_style_context().add_class("natter-settings")


def _label(text: str, css: str, wrap: bool = False) -> Gtk.Label:
    label = Gtk.Label(label=text, xalign=0)
    label.get_style_context().add_class(css)
    if wrap:
        label.set_line_wrap(True)
        label.set_max_width_chars(46)
    return label


def _card(title: str) -> tuple[Gtk.Box, Gtk.Box]:
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    card.get_style_context().add_class("card")
    card.pack_start(_label(title, "card-title"), False, False, 0)
    return card, card


def _switch_row(box: Gtk.Box, title: str, hint: str | None, on: bool, toggled: Callable[[bool], None]) -> Gtk.Switch:
    row = Gtk.Box(spacing=16)
    words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    words.pack_start(_label(title, "row-title", wrap=True), False, False, 0)
    if hint:
        words.pack_start(_label(hint, "hint", wrap=True), False, False, 0)
    row.pack_start(words, True, True, 0)
    switch = Gtk.Switch(active=on, valign=Gtk.Align.CENTER)
    switch.connect("notify::active", lambda s, _p: toggled(s.get_active()))
    row.pack_end(switch, False, False, 0)
    box.pack_start(row, False, False, 0)
    return switch


class SettingsWindow(Gtk.Window):
    def __init__(self, parent: Gtk.Window | None, prefs: Preferences, actions: Actions, auto_update: bool,
                 set_auto_update: Callable[[bool], None]) -> None:
        super().__init__(title=_("{app} settings").format(app=config.APP_NAME))
        self.prefs, self.actions = prefs, actions
        if parent is not None:
            self.set_transient_for(parent)
        self.set_default_size(560, 640)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        _apply_css(self)

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=22)
        column.pack_start(_label(_("Settings"), "title"), False, False, 0)

        box, card = _card(_("Notifications"))
        _switch_row(box, _("Do Not Disturb"), _("Messages arrive without a pop-up or a sound; the unread count on "
                                                "the tray icon still shows."),
                    prefs.do_not_disturb, self._dnd)
        column.pack_start(card, False, False, 0)

        box, card = _card(_("Starting"))
        _switch_row(box, _("Start on login"), _("Natter waits in the tray, so messages arrive from the start."),
                    prefs.start_on_login, actions.start_on_login)
        if actions.shortcut_possible:
            _switch_row(box, _("Show and hide with Ctrl+Alt+W"), _("A keyboard shortcut for the whole desktop."),
                        bool(prefs.shortcut), self._shortcut)
        column.pack_start(card, False, False, 0)

        box, card = _card(_("Spelling"))
        box.pack_start(_label(_("Underlines mistakes in these languages while you type."), "hint", wrap=True),
                       False, False, 0)
        chosen = prefs.spelling()
        row = Gtk.Box(spacing=18)
        for code, name in SPELLING:
            check = Gtk.CheckButton(label=name, active=code in chosen)
            check.connect("toggled", lambda b, code=code: self._spelling(code, b.get_active()))
            row.pack_start(check, False, False, 0)
        box.pack_start(row, False, False, 0)
        column.pack_start(card, False, False, 0)

        box, card = _card(_("Speed and memory"))
        _switch_row(box, _("Save memory"), _("Keeps WhatsApp under a memory limit and its cache small. Applies "
                                             "after a restart."), prefs.memory_saver, self._memory)
        column.pack_start(card, False, False, 0)

        box, card = _card(_("Language and updates"))
        language = Gtk.ComboBoxText()
        for code, name in i18n.LANGUAGES:
            language.append(code, _(name) if code == "" else name)
        language.set_active_id(prefs.language)
        language.connect("changed", lambda c: actions.language(c.get_active_id() or ""))
        row = Gtk.Box(spacing=16)
        row.pack_start(_label(_("Language"), "row-title"), True, True, 0)
        row.pack_end(language, False, False, 0)
        box.pack_start(row, False, False, 0)
        _switch_row(box, _("Check for updates automatically"), None, auto_update, set_auto_update)
        check = Gtk.Button(label=_("Check for updates…"), halign=Gtk.Align.START)
        check.connect("clicked", lambda _b: actions.check_updates())
        box.pack_start(check, False, False, 0)
        column.pack_start(card, False, False, 0)

        column.pack_start(_label(_("{app} {version}").format(app=config.APP_NAME, version=__version__), "hint"),
                          False, False, 0)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.add(column)
        self.add(scroller)

    def _dnd(self, on: bool) -> None:
        self.prefs.do_not_disturb = on
        self.actions.changed()

    def _spelling(self, code: str, on: bool) -> None:
        self.prefs.set_spelling(code, on)
        self.actions.changed()

    def _memory(self, on: bool) -> None:
        self.prefs.memory_saver = on
        self.actions.changed()

    def _shortcut(self, on: bool) -> None:
        if self.actions.shortcut(on):
            self.prefs.shortcut = look.SHORTCUT if on else ""
            self.actions.changed()
