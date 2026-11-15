"""The update dialogs and timers for the Linux Qt WebEngine backend (same flow as updates_gtk.py)."""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QMessageBox, QProgressBar, QPushButton,
                               QTextEdit, QVBoxLayout)

from natter import config
from natter.i18n import _
from natter.updates import AvailableUpdate, UpdateError, Updater

FIRST_CHECK_MS = 30_000
TICK_MS = 3_600_000  # the check itself only happens about once a day


def _message(error: Exception) -> str:
    return str(error) if isinstance(error, UpdateError) else _(
        "Something went wrong: {error}").format(error=error)


class UpdateUI(QObject):
    # worker threads -> UI thread
    _checked_sig = Signal(object, object, bool)
    _progress_sig = Signal(int, int)
    _installing_sig = Signal()
    _installed_sig = Signal(bool, object)

    def __init__(self, updater: Updater, window, restart, open_url) -> None:
        super().__init__()
        self.updater = updater
        self._window = window  # a callable: the main window, or None while it isn't built
        self._restart = restart
        self._open_url = open_url
        self._busy = False
        self._progress: QDialog | None = None
        self._bar: QProgressBar | None = None
        self._status: QLabel | None = None
        self._checked_sig.connect(self._checked)
        self._progress_sig.connect(self._set_progress)
        self._installing_sig.connect(self._set_installing)
        self._installed_sig.connect(self._installed)
        self._timers: list[QTimer] = []

    def start(self) -> None:
        """Check shortly after start-up, then now and then while Natter sits in the tray."""
        QTimer.singleShot(FIRST_CHECK_MS, self._tick)
        timer = QTimer(self, interval=TICK_MS)
        timer.timeout.connect(self._tick)
        timer.start()
        self._timers.append(timer)

    def _tick(self) -> None:
        if self.updater.due():
            self.check(interactive=False)

    def check(self, interactive: bool = True) -> None:
        if self._busy:
            return
        self._busy = True

        def work() -> None:
            try:
                update, error = self.updater.check(), None
            except Exception as e:  # shown on the UI thread; never crash the app
                update, error = None, _message(e)
            self._checked_sig.emit(update, error, interactive)

        threading.Thread(target=work, name="natter-update-check", daemon=True).start()

    def _checked(self, update: AvailableUpdate | None, error: str | None, interactive: bool) -> None:
        self._busy = False
        if error is None:
            self.updater.mark_checked()
        if error:
            if interactive:
                self._tell(_("Couldn't check for updates"), error)
        elif update is None:
            if interactive:
                self._tell(_("No updates"), _("You have the latest version of Natter ({version}).").format(
                    version=self.updater.current_version))
        elif interactive or not self.updater.skipped(update.version):
            self._offer(update)

    def _parent(self):
        window = self._window()
        return window if window is not None and window.isVisible() else None

    def _tell(self, title: str, text: str) -> None:
        box = QMessageBox(QMessageBox.Information, title, text, QMessageBox.Ok, self._parent())
        box.setAttribute(Qt.WA_DeleteOnClose)
        box.show()

    def _offer(self, update: AvailableUpdate) -> None:
        dialog = QDialog(self._parent())
        dialog.setWindowTitle(_("Update available"))
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.resize(480, 340)
        layout = QVBoxLayout(dialog)
        heading = QLabel(_("{app} {version} is available").format(app=config.APP_NAME, version=update.version))
        font = heading.font()
        font.setPointSizeF(font.pointSizeF() * 1.3)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)
        layout.addWidget(QLabel(_("You have {current}. Here's what's new:").format(current=update.current)))
        notes = QTextEdit(readOnly=True)
        notes.setPlainText(update.notes.strip() or _("No release notes."))
        layout.addWidget(notes, 1)
        box = QDialogButtonBox()
        skip = box.addButton(_("Skip this version"), QDialogButtonBox.ResetRole)
        later = box.addButton(_("Later"), QDialogButtonBox.RejectRole)
        go = box.addButton(_("Update now") if update.can_install else _("Open download page"),
                           QDialogButtonBox.AcceptRole)
        go.setDefault(True)
        layout.addWidget(box)

        def clicked(button: QPushButton) -> None:
            dialog.close()
            if button is skip:
                self.updater.skip(update.version)
            elif button is go:
                if update.can_install:
                    self._download(update)
                else:
                    self._open_url(update.page_url)

        box.clicked.connect(clicked)
        later.setAutoDefault(False)
        dialog.show()

    def _show_progress(self, text: str) -> None:
        dialog = QDialog(self._parent())
        dialog.setWindowTitle(config.APP_NAME)
        dialog.setWindowFlag(Qt.WindowCloseButtonHint, False)  # no closing it halfway
        layout = QVBoxLayout(dialog)
        self._status = QLabel(text)
        self._bar = QProgressBar()
        layout.addWidget(self._status)
        layout.addWidget(self._bar)
        dialog.resize(380, dialog.sizeHint().height())
        dialog.show()
        self._progress = dialog

    def _close_progress(self) -> None:
        if self._progress is not None:
            self._progress.close()
            self._progress.deleteLater()
            self._progress = self._bar = self._status = None

    def _download(self, update: AvailableUpdate) -> None:
        self._show_progress(_("Downloading…"))
        self._busy = True

        def work() -> None:
            try:
                path = self.updater.download(update, lambda done, total: self._progress_sig.emit(done, total))
                self._installing_sig.emit()
                restart = not self.updater.install(path)
                self._installed_sig.emit(restart, None)
            except Exception as e:
                self._installed_sig.emit(False, _message(e))

        threading.Thread(target=work, name="natter-update", daemon=True).start()

    def _set_progress(self, done: int, total: int) -> None:
        if self._bar is not None and total:
            self._bar.setRange(0, 1000)
            self._bar.setValue(int(min(done / total, 1.0) * 1000))
            self._status.setText(_("Downloading… {done} of {total} MB").format(
                done=f"{done / 1e6:.1f}", total=f"{total / 1e6:.1f}"))

    def _set_installing(self) -> None:
        if self._bar is not None:
            self._bar.setRange(0, 0)  # busy
            self._status.setText(_("Installing… your system may ask for your password."))

    def _installed(self, restart: bool, error: str | None) -> None:
        self._busy = False
        self._close_progress()
        if error:
            self._tell(_("Update available"), error)
        elif restart:
            self._restart()
