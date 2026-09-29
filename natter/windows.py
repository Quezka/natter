"""Windows backend: pywebview on Edge WebView2 (the system webview), with a tray icon."""
from __future__ import annotations

import threading
from pathlib import Path

import webview

from natter import autostart, config, i18n, single_instance
from natter.i18n import _
from natter.state import Preferences, WindowState

ASSETS = Path(__file__).resolve().parent / "assets"


def run(debug: bool, background: bool) -> int:
    holder: dict = {}
    # A second launch (Start menu, autostart while running) just shows this one.
    if not single_instance.claim(lambda: holder["show"]() if "show" in holder else None):
        return 0

    state_path = config.data_dir() / "window.json"
    state = WindowState.load(state_path)
    prefs_path = config.data_dir() / "preferences.json"
    prefs = Preferences.load(prefs_path)
    if not prefs_path.exists():
        _save(prefs, prefs_path)
    autostart.set_enabled(prefs.start_on_login)  # also follows the .exe if it moved

    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True

    window = webview.create_window(
        config.APP_NAME,
        config.URL,
        width=state.width,
        height=state.height,
        maximized=state.maximized,
        min_size=(480, 400),
        text_select=True,
        zoomable=True,
        hidden=background,
    )
    quitting = False

    def show() -> None:
        window.show()
        window.restore()

    def quit_app() -> None:
        nonlocal quitting
        quitting = True
        tray.stop()
        window.destroy()

    def toggle_start_on_login() -> None:
        prefs.start_on_login = not prefs.start_on_login
        _save(prefs, prefs_path)
        autostart.set_enabled(prefs.start_on_login)

    def set_language(code: str) -> None:
        prefs.language = code
        _save(prefs, prefs_path)
        i18n.install(code)
        autostart.set_enabled(prefs.start_on_login)
        tray.relabel()

    tray = _Tray(show, quit_app, toggle_start_on_login, lambda: prefs.start_on_login,
                 set_language, lambda: prefs.language)
    holder["show"] = show
    tuned = False

    def on_loaded() -> None:
        nonlocal tuned
        if not tuned:
            tuned = True
            _tune_webview2(window, tray.set_unread)

    def on_closing():
        state.width, state.height = window.width, window.height
        _save(state, state_path)
        if quitting:
            return None
        # Closing hides to the tray, like Discord; WhatsApp keeps running for notifications.
        threading.Thread(target=window.hide, daemon=True).start()
        return False  # cancels the close

    window.events.loaded += on_loaded
    window.events.closing += on_closing
    tray.start()
    webview.start(
        gui="edgechromium",
        debug=debug,
        private_mode=False,
        storage_path=str(config.data_dir() / "web"),
    )
    tray.stop()
    return 0


def _save(obj, path: Path) -> None:
    try:
        obj.save(path)
    except OSError:
        pass


class _Tray:
    """pystray icon with Open / Start on login / Language / Quit and an unread badge.

    Labels are callables, so the menu follows a language change after `relabel()`.
    """

    def __init__(self, on_open, on_quit, on_toggle_login, login_checked, on_language,
                 chosen_language) -> None:
        import pystray
        from PIL import Image

        self._base = Image.open(ASSETS / "icon.png").convert("RGBA")
        self._badged = _badge(self._base)
        self.unread = 0
        def choose(code):  # pystray counts an action's arguments, so no default args
            return lambda: on_language(code)

        languages = pystray.Menu(*(
            pystray.MenuItem((lambda _item, name=name: _(name)) if code == "" else name,
                             choose(code),
                             checked=lambda _item, code=code: chosen_language() == code,
                             radio=True)
            for code, name in i18n.LANGUAGES
        ))
        menu = pystray.Menu(
            pystray.MenuItem(lambda _item: _("Open {app}").format(app=config.APP_NAME),
                             lambda: on_open(), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _item: _("Start on login"), lambda: on_toggle_login(),
                             checked=lambda _item: login_checked()),
            pystray.MenuItem(lambda _item: _("Language"), languages),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _item: _("Quit {app}").format(app=config.APP_NAME),
                             lambda: on_quit()),
        )
        self.icon = pystray.Icon(config.APP_ID, self._base, config.APP_NAME, menu)

    def start(self) -> None:
        threading.Thread(target=self.icon.run, name="natter-tray", daemon=True).start()

    def stop(self) -> None:
        try:
            self.icon.stop()
        except Exception:
            pass

    def relabel(self) -> None:
        self.icon.title = config.tray_tooltip(self.unread)
        self.icon.update_menu()

    def set_unread(self, unread: int) -> None:
        if unread == self.unread:
            return
        self.unread = unread
        self.icon.icon = self._badged if unread else self._base
        self.icon.title = config.tray_tooltip(unread)


def _badge(image):
    """The icon with a red dot in the corner (same geometry as config.badged_svg)."""
    from PIL import ImageDraw

    badged = image.copy()
    scale = badged.width / 256
    cx, cy, r = 212 * scale, 44 * scale, 40 * scale
    ImageDraw.Draw(badged).ellipse((cx - r, cy - r, cx + r, cy + r), fill="#e5484d",
                                   outline="white", width=max(2, round(10 * scale)))
    return badged


def _tune_webview2(window, on_unread) -> None:
    """Undo pywebview's kiosk-style defaults and wire up what a chat app needs."""
    from Microsoft.Web.WebView2.Core import CoreWebView2PermissionKind, CoreWebView2PermissionState
    from System import Action

    form = window.native
    allowed = {
        CoreWebView2PermissionKind.Notifications,
        CoreWebView2PermissionKind.Microphone,
        CoreWebView2PermissionKind.Camera,
        CoreWebView2PermissionKind.ClipboardRead,
    }

    def on_permission(_sender, args) -> None:
        if args.PermissionKind in allowed:
            args.State = CoreWebView2PermissionState.Allow

    def on_title(sender, _args) -> None:
        unread = config.unread_count(sender.DocumentTitle)
        form.Text = config.window_title(unread)
        on_unread(unread)

    def tune() -> None:
        core = form.browser.webview.CoreWebView2
        settings = core.Settings
        settings.AreDefaultContextMenusEnabled = True  # copy/paste and spell-check suggestions
        settings.AreBrowserAcceleratorKeysEnabled = True  # Ctrl+F, Ctrl+R, zoom keys
        core.PermissionRequested += on_permission
        core.DocumentTitleChanged += on_title

    form.Invoke(Action(tune))
