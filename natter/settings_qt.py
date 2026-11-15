"""Settings for the Linux Qt WebEngine backend: plain Qt widgets (no second web view: that would start another
Chromium renderer, and Natter stays light). Same choices and words as the Windows HTML page (webpage.settings_page)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from natter import __version__, config, i18n
from natter.i18n import _
from natter.state import Preferences


@dataclass
class Actions:
    changed: Callable[[], None]  # a preference changed: save it
    language: Callable[[str], None]
    start_on_login: Callable[[bool], None]
    dnd: Callable[[bool], None]
    shortcut: Callable[[bool], bool]  # False if the desktop can't set one
    shortcut_possible: bool
    auto_update: Callable[[bool], None]
    check_updates: Callable[[], None]


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame(objectName="card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 14, 18, 14)
    heading = QLabel(title, objectName="cardTitle")
    layout.addWidget(heading)
    return card, layout


def _switch(layout: QVBoxLayout, title: str, hint: str, on: bool, toggled) -> QCheckBox:
    box = QCheckBox(title)
    box.setChecked(on)
    box.toggled.connect(toggled)
    layout.addWidget(box)
    if hint:
        small = QLabel(hint, wordWrap=True, objectName="hint")
        small.setIndent(26)
        layout.addWidget(small)
    return box


class SettingsWindow(QDialog):
    def __init__(self, parent, prefs: Preferences, actions: Actions, auto_update: bool) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Settings"))
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(520, 600)
        self.setStyleSheet("""
            QFrame#card { border-radius: 20px; background: palette(base); }
            QLabel#cardTitle { color: palette(highlight); font-weight: bold; }
            QLabel#hint { color: palette(placeholder-text); }
            QLabel#title { font-size: 22pt; font-weight: 800; }
            QCheckBox { padding: 6px 0; font-weight: 600; }
        """)
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setSpacing(10)
        col.addWidget(QLabel(_("Settings"), objectName="title"))

        card, lay = _card(_("Notifications"))
        _switch(lay, _("Do Not Disturb"),
                _("Messages arrive without a pop-up or a sound; the unread count on the tray icon still shows."),
                prefs.do_not_disturb, actions.dnd)
        col.addWidget(card)

        card, lay = _card(_("Starting"))
        _switch(lay, _("Start on login"), _("Natter waits in the tray, so messages arrive from the start."),
                prefs.start_on_login, actions.start_on_login)
        if actions.shortcut_possible:
            box = _switch(lay, _("Show and hide with Ctrl+Alt+W"), _("A keyboard shortcut for the whole desktop."),
                          bool(prefs.shortcut), lambda on: None)
            box.toggled.connect(lambda on, b=box: b.setChecked(False) if not actions.shortcut(on) and on else None)
        col.addWidget(card)

        card, lay = _card(_("Speed and memory"))

        def memory(on: bool) -> None:
            prefs.memory_saver = on
            actions.changed()

        _switch(lay, _("Save memory"), _("Uses less memory while Natter waits in the tray."),
                prefs.memory_saver, memory)
        col.addWidget(card)

        card, lay = _card(_("Language and updates"))
        row = QHBoxLayout()
        row.addWidget(QLabel(_("Language")))
        languages = QComboBox()
        for code, name in i18n.LANGUAGES:
            languages.addItem(_(name) if code == "" else name, code)
        languages.setCurrentIndex(max(0, languages.findData(prefs.language)))
        languages.currentIndexChanged.connect(lambda _i: actions.language(languages.currentData()))
        row.addWidget(languages, 1)
        lay.addLayout(row)
        _switch(lay, _("Check for updates automatically"), "", auto_update, actions.auto_update)
        check = QPushButton(_("Check for updates…"))
        check.clicked.connect(actions.check_updates)
        lay.addWidget(check, 0, Qt.AlignLeft)
        col.addWidget(card)

        col.addWidget(QLabel(_("{app} {version}").format(app=config.APP_NAME, version=__version__),
                             objectName="hint"))
        col.addStretch(1)
        scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addWidget(scroll)
