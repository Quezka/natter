"""The update dialogs and timers for the Linux (GTK) backend."""
from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from natter import config  # noqa: E402
from natter.i18n import _  # noqa: E402
from natter.updates import AvailableUpdate, UpdateError, Updater  # noqa: E402

FIRST_CHECK_SECONDS = 30
TICK_SECONDS = 3600  # the check itself only happens about once a day


def _message(error: Exception) -> str:
    return str(error) if isinstance(error, UpdateError) else _(
        "Something went wrong: {error}").format(error=error)


class UpdateUI:
    def __init__(self, updater: Updater, window, restart, open_url) -> None:
        self.updater = updater
        self._window = window  # a callable: the main window, or None while it isn't built
        self._restart = restart  # called after a successful install: start Natter again
        self._open_url = open_url
        self._busy = False
        self._progress: Gtk.Dialog | None = None
        self._bar: Gtk.ProgressBar | None = None
        self._status: Gtk.Label | None = None

    def start(self) -> None:
        """Check shortly after start-up, then now and then while Natter sits in the tray."""
        GLib.timeout_add_seconds(FIRST_CHECK_SECONDS, self._tick, True)
        GLib.timeout_add_seconds(TICK_SECONDS, self._tick, False)

    def _tick(self, once: bool) -> bool:
        if self.updater.due():
            self.check(interactive=False)
        return not once

    # --- checking ----------------------------------------------------------------------

    def check(self, interactive: bool = True) -> None:
        if self._busy:
            return
        self._busy = True

        def work() -> None:
            try:
                update, error = self.updater.check(), None
            except Exception as e:  # shown on the UI thread; never crash the app
                update, error = None, _message(e)
            GLib.idle_add(self._checked, update, error, interactive)

        threading.Thread(target=work, name="natter-update-check", daemon=True).start()

    def _checked(self, update: AvailableUpdate | None, error: str | None,
                 interactive: bool) -> bool:
        self._busy = False
        if error is None:
            self.updater.mark_checked()
        if error:
            if interactive:
                self._tell(_("Couldn't check for updates"), error)
        elif update is None:
            if interactive:
                self._tell(_("No updates"), _("You have the latest version of Natter "
                                              "({version}).").format(
                                                  version=self.updater.current_version))
        elif interactive or not self.updater.skipped(update.version):
            self._offer(update)
        return False

    # --- dialogs ------------------------------------------------------------------------

    def _parent(self):
        window = self._window()
        return window if window is not None and window.is_visible() else None

    def _tell(self, title: str, text: str) -> None:
        dialog = Gtk.MessageDialog(transient_for=self._parent(), modal=True,
                                   message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK, text=title)
        dialog.format_secondary_text(text)
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.show()

    def _offer(self, update: AvailableUpdate) -> None:
        dialog = Gtk.Dialog(title=_("Update available"), transient_for=self._parent(),
                            modal=True)
        dialog.set_default_size(460, 320)
        area = dialog.get_content_area()
        area.set_spacing(10)
        area.set_border_width(16)
        heading = Gtk.Label(xalign=0)
        heading.set_markup("<big><b>{}</b></big>".format(GLib.markup_escape_text(
            _("{app} {version} is available").format(app=config.APP_NAME,
                                                     version=update.version))))
        area.pack_start(heading, False, False, 0)
        area.pack_start(Gtk.Label(label=_("You have {current}. Here's what's new:").format(
            current=update.current), xalign=0), False, False, 0)
        notes = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD, left_margin=8,
                             right_margin=8, top_margin=6, bottom_margin=6)
        notes.get_buffer().set_text(update.notes.strip() or _("No release notes."))
        scroll = Gtk.ScrolledWindow()
        scroll.add(notes)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        area.pack_start(scroll, True, True, 0)
        dialog.add_button(_("Skip this version"), 1)
        dialog.add_button(_("Later"), Gtk.ResponseType.CANCEL)
        go = dialog.add_button(_("Update now") if update.can_install
                               else _("Open download page"), Gtk.ResponseType.ACCEPT)
        go.get_style_context().add_class("suggested-action")
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)

        def answered(d, response) -> None:
            d.destroy()
            if response == 1:
                self.updater.skip(update.version)
            elif response == Gtk.ResponseType.ACCEPT:
                if update.can_install:
                    self._download(update)
                else:
                    self._open_url(update.page_url)

        dialog.connect("response", answered)
        dialog.show_all()

    # --- downloading and installing ---------------------------------------------------------

    def _show_progress(self, text: str) -> None:
        dialog = Gtk.Dialog(title=config.APP_NAME, transient_for=self._parent(), modal=True,
                            deletable=False)
        area = dialog.get_content_area()
        area.set_spacing(10)
        area.set_border_width(18)
        self._status = Gtk.Label(label=text, xalign=0)
        self._bar = Gtk.ProgressBar()
        area.pack_start(self._status, False, False, 0)
        area.pack_start(self._bar, False, False, 0)
        dialog.set_default_size(380, -1)
        dialog.connect("delete-event", lambda *_a: True)  # no closing it halfway
        dialog.show_all()
        self._progress = dialog

    def _close_progress(self) -> None:
        if self._progress is not None:
            self._progress.destroy()
            self._progress = self._bar = self._status = None

    def _download(self, update: AvailableUpdate) -> None:
        self._show_progress(_("Downloading…"))
        self._busy = True

        def progress(done: int, total: int) -> None:
            GLib.idle_add(self._set_progress, done, total)

        def work() -> None:
            try:
                path = self.updater.download(update, progress)
                GLib.idle_add(self._set_installing)
                restart = not self.updater.install(path)
                GLib.idle_add(self._installed, restart, None)
            except Exception as e:
                GLib.idle_add(self._installed, False, _message(e))

        threading.Thread(target=work, name="natter-update", daemon=True).start()

    def _set_progress(self, done: int, total: int) -> bool:
        if self._bar is not None and total:
            self._bar.set_fraction(min(done / total, 1.0))
            self._status.set_text(_("Downloading… {done} of {total} MB").format(
                done=f"{done / 1e6:.1f}", total=f"{total / 1e6:.1f}"))
        return False

    def _set_installing(self) -> bool:
        if self._bar is not None:
            self._bar.pulse()
            self._bar.set_fraction(1.0)
            self._status.set_text(_("Installing… your system may ask for your password."))
        return False

    def _installed(self, restart: bool, error: str | None) -> bool:
        self._busy = False
        self._close_progress()
        if error:
            self._tell(_("Update available"), error)
        elif restart:
            self._restart()
        return False
