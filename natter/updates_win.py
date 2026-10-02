"""Update prompts for the Windows backend: plain system message boxes on a worker thread,
so nothing blocks WebView2 or the tray."""
from __future__ import annotations

import threading
from typing import Callable

from natter import config
from natter.i18n import _
from natter.updates import AvailableUpdate, UpdateError, Updater

FIRST_CHECK_SECONDS = 30
TICK_SECONDS = 3600  # the check itself only happens about once a day
NOTES_SHOWN = 700  # characters of release notes in the prompt

MB_OK, MB_YESNO, MB_YESNOCANCEL = 0x0, 0x4, 0x3
MB_ICONINFORMATION, MB_ICONQUESTION, MB_TOPMOST = 0x40, 0x20, 0x40000
IDCANCEL, IDYES = 2, 6


def _box(text: str, flags: int) -> int:
    import ctypes
    return ctypes.windll.user32.MessageBoxW(0, text, config.APP_NAME, flags | MB_TOPMOST)


def _message(error: Exception) -> str:
    return str(error) if isinstance(error, UpdateError) else _(
        "Something went wrong: {error}").format(error=error)


class WindowsUpdateUI:
    def __init__(self, updater: Updater, open_url: Callable[[str], None],
                 quit_app: Callable[[], None]) -> None:
        self.updater = updater
        self._open_url = open_url
        self._quit = quit_app
        self._busy = False

    def start(self) -> None:
        threading.Timer(FIRST_CHECK_SECONDS, self._tick, args=(True,)).start()

    def _tick(self, first: bool = False) -> None:
        if self.updater.due():
            self.check(interactive=False)
        timer = threading.Timer(TICK_SECONDS, self._tick)
        timer.daemon = True
        timer.start()

    def check(self, interactive: bool = True) -> None:
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._run, args=(interactive,), name="natter-update",
                         daemon=True).start()

    def _run(self, interactive: bool) -> None:
        try:
            try:
                update = self.updater.check()
            except Exception as e:
                if interactive:
                    _box(_message(e), MB_OK | MB_ICONINFORMATION)
                return
            self.updater.mark_checked()
            if update is None:
                if interactive:
                    _box(_("You have the latest version of Natter ({version}).").format(
                        version=self.updater.current_version), MB_OK | MB_ICONINFORMATION)
            elif interactive or not self.updater.skipped(update.version):
                self._offer(update)
        finally:
            self._busy = False

    def _offer(self, update: AvailableUpdate) -> None:
        notes = update.notes.strip()
        if len(notes) > NOTES_SHOWN:
            notes = notes[:NOTES_SHOWN].rstrip() + "…"
        head = _("{app} {version} is available").format(app=config.APP_NAME,
                                                        version=update.version)
        whats_new = _("You have {current}. Here's what's new:").format(current=update.current)
        text = f"{head}\n\n{whats_new}\n{notes or _('No release notes.')}\n\n"
        if not update.can_install:
            if _box(text + _("Open the download page?"), MB_YESNO | MB_ICONQUESTION) == IDYES:
                self._open_url(update.page_url)
            return
        answer = _box(text + _("Yes: update now. No: later. Cancel: skip this version."),
                      MB_YESNOCANCEL | MB_ICONQUESTION)
        if answer == IDCANCEL:
            self.updater.skip(update.version)
        elif answer == IDYES:
            self._install(update)

    def _install(self, update: AvailableUpdate) -> None:
        try:
            path = self.updater.download(update, lambda done, total: None)
            if self.updater.install(path):  # setup takes over: quit so it can replace the files
                self._quit()
        except Exception as e:
            _box(_message(e), MB_OK | MB_ICONINFORMATION)
