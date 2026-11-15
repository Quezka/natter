"""Linux backend on Qt WebEngine (Chromium, the distro's build): WhatsApp's calls work here, which they don't in
WebKitGTK (see chromium.py for what WhatsApp checks). Same behaviour as linux.py: hides to the tray on close,
one copy per user (a second launch shows it; `--toggle` shows or hides it), notifications as the app's own.
Light on purpose (user 2026-11-15): one renderer, no second web view, a capped disk cache."""
from __future__ import annotations

import getpass
import os
import subprocess
from pathlib import Path

from natter import autostart, chromium, config, i18n, look
from natter.i18n import _
from natter.state import Preferences, WindowState, fit_size, starting_zoom
from natter.updates import default_updater

ASSETS = Path(__file__).resolve().parent / "assets"
ZOOM_STEP = 0.1
MENU_SHOW, MENU_START_ON_LOGIN, MENU_QUIT, MENU_LANGUAGE = 1, 3, 5, 6
MENU_CHECK_UPDATES, MENU_AUTO_UPDATE = 7, 8
MENU_SETTINGS, MENU_DND = 20, 21
MENU_FIRST_LANGUAGE = 10


def available() -> bool:
    """Whether Qt WebEngine is installed (python3-pyside6.qtwebenginewidgets); otherwise linux.py (WebKitGTK)."""
    try:
        import PySide6.QtWebEngineWidgets  # noqa: F401
        return True
    except ImportError:
        return False


def _server_name() -> str:
    return f"{config.APP_ID}-{getpass.getuser()}"


def _ask_running(message: bytes) -> bool:
    """Hand `message` to a Natter that's already running. True if there was one."""
    from PySide6.QtNetwork import QLocalSocket
    sock = QLocalSocket()
    sock.connectToServer(_server_name())
    if not sock.waitForConnected(500):
        return False
    sock.write(message)
    sock.flush()
    sock.waitForBytesWritten(500)
    sock.disconnectFromServer()
    return True


class _Notifier:
    """Desktop notifications over D-Bus (org.freedesktop.Notifications), clickable, as Natter's own."""

    def __init__(self, on_click) -> None:
        from gi.repository import Gio
        self._live: dict[int, object] = {}  # notification id -> QWebEngineNotification
        self._on_click = on_click
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._bus.signal_subscribe("org.freedesktop.Notifications", "org.freedesktop.Notifications",
                                       None, "/org/freedesktop/Notifications", None, Gio.DBusSignalFlags.NONE,
                                       self._signal)
        except Exception:
            self._bus = None

    def show(self, note) -> None:
        if self._bus is None:
            return
        from gi.repository import GLib
        args = GLib.Variant("(susssasa{sv}i)", (
            config.APP_NAME, 0, config.APP_ID, note.title() or config.APP_NAME, note.message(),
            ["default", _("Open {app}").format(app=config.APP_NAME)],
            {"desktop-entry": GLib.Variant("s", config.APP_ID), "urgency": GLib.Variant("y", 1)}, -1))
        try:
            reply = self._bus.call_sync("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                                        "org.freedesktop.Notifications", "Notify", args, None, 0, 2000, None)
        except Exception:
            return
        nid = reply.unpack()[0]
        self._live[nid] = note
        note.show()
        note.closed.connect(lambda nid=nid: self._withdraw(nid))

    def _withdraw(self, nid: int) -> None:
        if self._live.pop(nid, None) is not None and self._bus is not None:
            from gi.repository import GLib
            try:
                self._bus.call("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                               "org.freedesktop.Notifications", "CloseNotification", GLib.Variant("(u)", (nid,)),
                               None, 0, -1, None, None, None)
            except Exception:
                pass

    def _signal(self, _conn, _sender, _path, _iface, name, params) -> None:
        values = params.unpack()
        nid = values[0]
        note = self._live.get(nid)
        if name == "ActionInvoked" and note is not None:
            note.click()
            self._on_click()
        elif name == "NotificationClosed":
            self._live.pop(nid, None)


def _gnome_shortcuts():
    """GNOME's shortcut settings, or None on a desktop without them."""
    from gi.repository import Gio
    source = Gio.SettingsSchemaSource.get_default()
    if source is None or source.lookup("org.gnome.settings-daemon.plugins.media-keys", True) is None:
        return None
    if source.lookup("org.gnome.settings-daemon.plugins.media-keys.custom-keybinding", True) is None:
        return None
    return Gio.Settings.new("org.gnome.settings-daemon.plugins.media-keys")


def run(debug: bool, background: bool, argv: list[str], toggle: bool = False) -> int:
    # one copy per user: hand the request to the running one
    if _ask_running(b"toggle" if toggle else b"show"):
        return 0
    if toggle:
        background = False  # nothing was running: start and show

    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = chromium.flags(os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", ""))
    if debug:
        os.environ.setdefault("QTWEBENGINE_REMOTE_DEBUGGING", "127.0.0.1:9333")

    from PySide6.QtCore import QTimer, QUrl, Qt
    from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QKeySequence, QShortcut
    from PySide6.QtNetwork import QLocalServer
    from PySide6.QtWebEngineCore import (QWebEngineDownloadRequest, QWebEnginePage, QWebEnginePermission,
                                         QWebEngineProfile, QWebEngineScript)
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication, QMainWindow

    QGuiApplication.setDesktopFileName(config.APP_ID)
    app = QApplication(argv)
    app.setApplicationName(config.APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # closing hides to the tray
    icon = QIcon.fromTheme(config.APP_ID, QIcon(str(ASSETS / "icon.svg")))
    app.setWindowIcon(icon)

    state_path = config.data_dir() / "window.json"
    prefs_path = config.data_dir() / "preferences.json"
    state = WindowState.load(state_path)
    prefs = Preferences.load(prefs_path)

    def save_prefs() -> None:
        try:
            prefs.save(prefs_path)
        except OSError:
            pass

    if not prefs_path.exists():
        save_prefs()
    autostart.set_enabled(prefs.start_on_login)

    # --- the engine -----------------------------------------------------------------------
    data, cache = config.data_dir() / "chromium", config.cache_dir() / "chromium"
    data.mkdir(parents=True, exist_ok=True)
    profile = QWebEngineProfile("natter", app)
    profile.setPersistentStoragePath(str(data))
    profile.setCachePath(str(cache))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
    if prefs.memory_saver:
        profile.setHttpCacheMaximumSize(chromium.CACHE_MB * 1024 * 1024)
    profile.setSpellCheckEnabled(False)  # Qt needs its own dictionaries (.bdic): none installed, so no cost
    default_ua = profile.httpUserAgent()
    profile.setHttpUserAgent(chromium.user_agent(default_ua))
    version = chromium.chrome_version(default_ua)
    try:
        hints = profile.clientHints()
        hints.setFullVersionList(chromium.brands(version))
        hints.setFullVersion(version)
    except AttributeError:
        pass  # Qt < 6.8: the page script below still says Chrome
    shim = QWebEngineScript()
    shim.setName("natter-chrome")
    shim.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    shim.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    shim.setRunsOnSubFrames(True)
    shim.setSourceCode(chromium.chrome_shim(version.split(".")[0]))
    profile.scripts().insert(shim)

    window = QMainWindow()
    holder: dict = {"quitting": False}

    def show_window() -> None:
        window.show()
        window.raise_()
        window.activateWindow()

    def toggle_window() -> None:
        if window.isVisible() and window.isActiveWindow():
            hide_window()
        else:
            show_window()

    notifier = _Notifier(show_window)

    def present(note) -> None:
        if not prefs.do_not_disturb:  # quiet: nothing pops up; the tray still counts what's unread
            notifier.show(note)

    profile.setNotificationPresenter(present)

    def downloaded(request: QWebEngineDownloadRequest) -> None:
        folder = Path(QDesktopServicesDir.downloads())
        folder.mkdir(parents=True, exist_ok=True)
        target = config.unique_path(folder, request.downloadFileName())
        request.setDownloadDirectory(str(target.parent))
        request.setDownloadFileName(target.name)
        request.accept()

    profile.downloadRequested.connect(downloaded)

    def open_outside(url: QUrl) -> None:
        uri = url.toString()
        if config.is_external_link(uri):
            QDesktopServices.openUrl(url)

    class Popup(QWebEnginePage):
        """A page WhatsApp opens with window.open / target=_blank: a link goes to the browser; WhatsApp's own
        (blank or internal, e.g. a call's pop-out) gets a small window of its own."""

        def __init__(self) -> None:
            super().__init__(profile, window)
            self.view: QWebEngineView | None = None
            self.decided = False
            QTimer.singleShot(400, self._maybe_show)

        def acceptNavigationRequest(self, url, kind, main_frame):
            uri = url.toString()
            if main_frame and not self.decided and uri not in ("", "about:blank") and not config.is_internal(uri):
                self.decided = True
                open_outside(url)
                QTimer.singleShot(0, self.deleteLater)
                return False
            return super().acceptNavigationRequest(url, kind, main_frame)

        def _maybe_show(self) -> None:
            if self.decided:
                return
            self.decided = True
            self.view = QWebEngineView()
            self.view.setPage(self)
            self.view.setAttribute(Qt.WA_DeleteOnClose)
            self.windowCloseRequested.connect(self.view.close)
            self.view.resize(480, 640)
            self.view.show()

    class Page(QWebEnginePage):
        def acceptNavigationRequest(self, url, kind, main_frame):
            uri = url.toString()
            if (kind == QWebEnginePage.NavigationType.NavigationTypeLinkClicked and main_frame
                    and not config.is_internal(uri)):
                open_outside(url)
                return False
            return super().acceptNavigationRequest(url, kind, main_frame)

        def createWindow(self, _kind):
            return Popup()

    page = Page(profile, window)

    def permission(p: QWebEnginePermission) -> None:
        if chromium.allowed(p.permissionType().name, p.origin().host()):
            p.grant()
        else:
            p.deny()

    page.permissionRequested.connect(permission)
    page.renderProcessTerminated.connect(lambda *_: QTimer.singleShot(1000, lambda: page.triggerAction(QWebEnginePage.Reload)))

    view = QWebEngineView()
    view.setPage(page)
    window.setCentralWidget(view)
    window.setWindowTitle(config.APP_NAME)
    screen = app.primaryScreen()
    area = (screen.availableGeometry().width(), screen.availableGeometry().height()) if screen else None
    window.resize(*(fit_size(state.width, state.height, *area) if area else (state.width, state.height)))
    if state.maximized:
        window.setWindowState(Qt.WindowMaximized)
    view.setZoomFactor(starting_zoom(state, area[1] if area else None))

    def save_state() -> None:
        state.maximized = window.isMaximized()
        if not state.maximized:
            state.width, state.height = window.width(), window.height()
        state.zoom = view.zoomFactor()
        try:
            state.save(state_path)
        except OSError:
            pass

    def hide_window() -> None:
        save_state()
        window.hide()  # chromium throttles a hidden page by itself: timers slow, nothing drawn

    def close_event(event) -> None:
        if holder["quitting"]:
            event.accept()
            return
        event.ignore()  # closing keeps WhatsApp running in the tray so notifications still arrive
        hide_window()

    window.closeEvent = close_event

    def quit_app() -> None:
        save_state()
        holder["quitting"] = True
        app.quit()

    def title_changed(title: str) -> None:
        unread = config.unread_count(title)
        window.setWindowTitle(config.window_title(unread))
        if tray is not None:
            tray.set_unread(unread)
        if unread and not window.isActiveWindow():
            app.alert(window)

    page.titleChanged.connect(title_changed)

    def zoom(step: float | None) -> None:
        state.zoom_chosen = True
        level = 1.0 if step is None else view.zoomFactor() + step
        view.setZoomFactor(min(max(round(level, 2), 0.5), 3.0))

    for keys, action in (("Ctrl+Q", quit_app), ("Ctrl+R", lambda: page.triggerAction(QWebEnginePage.Reload)),
                         ("F5", lambda: page.triggerAction(QWebEnginePage.Reload)),
                         ("Ctrl++", lambda: zoom(ZOOM_STEP)), ("Ctrl+=", lambda: zoom(ZOOM_STEP)),
                         ("Ctrl+-", lambda: zoom(-ZOOM_STEP)), ("Ctrl+0", lambda: zoom(None)),
                         ("Ctrl+,", lambda: open_settings())):
        QShortcut(QKeySequence(keys), window, activated=action)

    # --- tray, settings, updates -----------------------------------------------------------
    from natter.updates_qt import UpdateUI

    def restart_after_update() -> None:
        try:
            subprocess.Popen(["sh", "-c", "sleep 1; exec natter"], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
        quit_app()

    updater = default_updater(prefs, save_prefs)
    update_ui = UpdateUI(updater, lambda: window, restart_after_update, lambda url: QDesktopServices.openUrl(QUrl(url)))

    tray = None

    def menu() -> list:
        from natter.tray_linux import MenuItem
        languages = [MenuItem(MENU_FIRST_LANGUAGE + n, _(name) if code == "" else name,
                              lambda code=code: set_language(code), checked=code == prefs.language, radio=True)
                     for n, (code, name) in enumerate(i18n.LANGUAGES)]
        return [
            MenuItem(MENU_SHOW, _("Open {app}").format(app=config.APP_NAME), show_window),
            MenuItem(MENU_DND, _("Do Not Disturb"), lambda: set_dnd(not prefs.do_not_disturb),
                     checked=prefs.do_not_disturb),
            MenuItem(MENU_SETTINGS, _("Settings…"), lambda: open_settings()),
            MenuItem(2, separator=True),
            MenuItem(MENU_START_ON_LOGIN, _("Start on login"), lambda: set_login(not prefs.start_on_login),
                     checked=prefs.start_on_login),
            MenuItem(MENU_LANGUAGE, _("Language"), children=languages),
            MenuItem(MENU_CHECK_UPDATES, _("Check for updates…"), lambda: update_ui.check(interactive=True)),
            MenuItem(MENU_AUTO_UPDATE, _("Check for updates automatically"),
                     lambda: set_auto(not updater.auto_check()), checked=updater.auto_check()),
            MenuItem(4, separator=True),
            MenuItem(MENU_QUIT, _("Quit {app}").format(app=config.APP_NAME), quit_app),
        ]

    def refresh_tray() -> None:
        if tray is not None:
            tray.set_items(menu())

    def set_language(code: str) -> None:
        prefs.language = code
        save_prefs()
        i18n.install(code)
        autostart.set_enabled(prefs.start_on_login)
        refresh_tray()

    def set_dnd(on: bool) -> None:
        prefs.do_not_disturb = on
        save_prefs()
        refresh_tray()

    def set_login(on: bool) -> None:
        prefs.start_on_login = on
        save_prefs()
        autostart.set_enabled(on)
        refresh_tray()

    def set_auto(on: bool) -> None:
        updater.set_auto_check(on)
        refresh_tray()

    def set_shortcut(on: bool) -> bool:
        from gi.repository import Gio
        media = _gnome_shortcuts()
        if media is None:
            return False
        paths = list(media.get_strv("custom-keybindings"))
        if on:
            binding = Gio.Settings.new_with_path(
                "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding", look.SHORTCUT_PATH)
            binding.set_string("name", config.APP_NAME)
            binding.set_string("command", "natter --toggle")
            binding.set_string("binding", look.SHORTCUT)
            media.set_strv("custom-keybindings", look.with_shortcut(paths))
            prefs.shortcut = look.SHORTCUT
        else:
            media.set_strv("custom-keybindings", look.without_shortcut(paths))
            prefs.shortcut = ""
        save_prefs()
        return True

    def open_settings() -> None:
        from natter.settings_qt import Actions, SettingsWindow
        actions = Actions(changed=save_prefs, language=set_language, start_on_login=set_login, dnd=set_dnd,
                          shortcut=set_shortcut, shortcut_possible=_gnome_shortcuts() is not None,
                          auto_update=set_auto, check_updates=lambda: update_ui.check(interactive=True))
        SettingsWindow(window if window.isVisible() else None, prefs, actions, updater.auto_check()).show()

    try:
        from natter.tray_linux import Tray
        tray = Tray((ASSETS / "icon.svg").read_text(encoding="utf-8"), toggle_window, menu())
        tray.start()
    except Exception:
        tray = None  # no tray: closing still hides, and relaunching shows

    # --- one copy per user ------------------------------------------------------------------
    server = QLocalServer(app)
    QLocalServer.removeServer(_server_name())  # a stale socket from a crash
    server.listen(_server_name())

    def incoming() -> None:
        sock = server.nextPendingConnection()
        if sock is None:
            return

        def read() -> None:
            what = bytes(sock.readAll()).strip()
            (toggle_window if what == b"toggle" else show_window)()
            sock.disconnectFromServer()

        sock.readyRead.connect(read)

    server.newConnection.connect(incoming)

    update_ui.start()
    page.load(QUrl(config.URL))
    if not background:
        show_window()
    return app.exec()


class QDesktopServicesDir:
    @staticmethod
    def downloads() -> str:
        from PySide6.QtCore import QStandardPaths
        return QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or str(Path.home() / "Downloads")
