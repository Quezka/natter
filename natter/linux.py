"""Linux backend: GTK 3 + WebKitGTK (the system webview), driven directly."""
from __future__ import annotations

import os
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gio, GLib, Gtk, WebKit2  # noqa: E402

from natter import config  # noqa: E402
from natter.state import WindowState  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"
ZOOM_STEP = 0.1

# Only the things WhatsApp Web actually asks for: notifications, the microphone for
# voice notes, the camera for photos, and the clipboard for pasting images.
ALLOWED_PERMISSIONS = (
    WebKit2.NotificationPermissionRequest,
    WebKit2.UserMediaPermissionRequest,
    WebKit2.ClipboardPermissionRequest,
)


class NatterApp(Gtk.Application):
    def __init__(self, debug: bool) -> None:
        super().__init__(application_id=config.APP_ID)
        self.debug = debug
        self.window: Gtk.ApplicationWindow | None = None
        self.view: WebKit2.WebView | None = None
        self.state_path = config.data_dir() / "window.json"
        self.state = WindowState.load(self.state_path)

    # --- application lifecycle -------------------------------------------------

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        GLib.set_application_name(config.APP_NAME)
        Gtk.Window.set_default_icon_name(config.APP_ID)
        self._add_action("quit", self._quit, "<Primary>q")
        self._add_action("reload", lambda: self.view.reload(), "<Primary>r", "F5")
        self._add_action("zoom-in", lambda: self._zoom(ZOOM_STEP), "<Primary>plus", "<Primary>equal")
        self._add_action("zoom-out", lambda: self._zoom(-ZOOM_STEP), "<Primary>minus")
        self._add_action("zoom-reset", lambda: self._zoom(None), "<Primary>0")

    def do_activate(self) -> None:
        # A second launch lands here in the running instance, which brings the
        # hidden window back instead of starting another copy.
        if self.window is None:
            self._build_window()
        self.window.present()

    def _add_action(self, name, callback, *accels) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda *_: callback())
        self.add_action(action)
        self.set_accels_for_action(f"app.{name}", list(accels))

    def _quit(self) -> None:
        self._save_state()
        self.quit()

    # --- window and webview ------------------------------------------------------

    def _build_window(self) -> None:
        data, cache = config.data_dir(), config.cache_dir()
        data.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)

        manager = WebKit2.WebsiteDataManager(
            base_data_directory=str(data / "web"), base_cache_directory=str(cache)
        )
        cookies = manager.get_cookie_manager()
        cookies.set_persistent_storage(str(data / "cookies.sqlite"), WebKit2.CookiePersistentStorage.SQLITE)
        cookies.set_accept_policy(WebKit2.CookieAcceptPolicy.NO_THIRD_PARTY)

        context = WebKit2.WebContext.new_with_website_data_manager(manager)
        context.set_cache_model(WebKit2.CacheModel.WEB_BROWSER)
        context.set_spell_checking_enabled(True)
        context.set_spell_checking_languages(_spelling_languages())
        context.connect("download-started", self._on_download_started)

        view = WebKit2.WebView(web_context=context)
        settings = view.get_settings()
        settings.set_user_agent(config.LINUX_USER_AGENT)
        settings.set_hardware_acceleration_policy(
            WebKit2.HardwareAccelerationPolicy.NEVER
            if os.environ.get("NATTER_NO_GPU")
            else WebKit2.HardwareAccelerationPolicy.ALWAYS
        )
        settings.set_enable_smooth_scrolling(True)
        settings.set_enable_media_stream(True)
        settings.set_enable_webaudio(True)
        settings.set_javascript_can_access_clipboard(True)
        settings.set_enable_back_forward_navigation_gestures(False)
        settings.set_enable_developer_extras(self.debug)
        if settings.find_property("enable-webrtc"):
            settings.set_property("enable-webrtc", True)

        view.set_zoom_level(self.state.zoom)
        view.connect("decide-policy", self._on_decide_policy)
        view.connect("permission-request", self._on_permission_request)
        view.connect("show-notification", self._on_show_notification)
        view.connect("notify::title", self._on_title_changed)
        view.connect("web-process-terminated", lambda v, _reason: v.reload())
        view.connect("create", lambda *_: None)  # never open extra app windows

        window = Gtk.ApplicationWindow(application=self, title=config.APP_NAME)
        window.set_default_size(self.state.width, self.state.height)
        if self.state.maximized:
            window.maximize()
        if not Gtk.IconTheme.get_default().has_icon(config.APP_ID):
            window.set_icon_from_file(str(ASSETS / "icon.svg"))
        window.connect("delete-event", self._on_delete)
        window.connect("focus-in-event", lambda w, _e: w.set_urgency_hint(False))
        window.add(view)
        view.show()

        self.window, self.view = window, view
        view.load_uri(config.URL)

    def _on_delete(self, window, _event) -> bool:
        # Closing keeps WhatsApp running in the background so notifications still
        # arrive; launch Natter again to bring it back, or press Ctrl+Q to quit.
        self._save_state()
        window.hide()
        return True

    def _save_state(self) -> None:
        if self.window is None:
            return
        self.state.maximized = self.window.is_maximized()
        if not self.state.maximized:
            self.state.width, self.state.height = self.window.get_size()
        self.state.zoom = self.view.get_zoom_level()
        try:
            self.state.save(self.state_path)
        except OSError:
            pass

    def _zoom(self, step: float | None) -> None:
        level = 1.0 if step is None else self.view.get_zoom_level() + step
        self.view.set_zoom_level(min(max(round(level, 2), 0.5), 3.0))

    # --- webview signals -----------------------------------------------------------

    def _on_decide_policy(self, _view, decision, kind) -> bool:
        if kind not in (WebKit2.PolicyDecisionType.NAVIGATION_ACTION,
                        WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION):
            return False
        action = decision.get_navigation_action()
        uri = action.get_request().get_uri()
        opens_window = kind == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION
        clicked_away = (action.get_navigation_type() == WebKit2.NavigationType.LINK_CLICKED
                        and not config.is_internal(uri))
        if not (opens_window or clicked_away):
            return False
        if config.is_external_link(uri):
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
            except GLib.Error:
                pass
        decision.ignore()
        return True

    def _on_permission_request(self, _view, request) -> bool:
        if isinstance(request, ALLOWED_PERMISSIONS):
            request.allow()
        else:
            request.deny()
        return True

    def _on_show_notification(self, _view, notification) -> bool:
        notification.connect("clicked", lambda _n: self.activate())
        return False  # let WebKit show it through the desktop's notification service

    def _on_title_changed(self, view, _pspec) -> None:
        unread = config.unread_count(view.get_title())
        self.window.set_title(config.window_title(unread))
        if unread and not self.window.is_active():
            self.window.set_urgency_hint(True)

    def _on_download_started(self, _context, download) -> None:
        download.connect("decide-destination", self._on_decide_destination)

    def _on_decide_destination(self, download, suggested: str) -> bool:
        folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        folder = Path(folder) if folder else Path.home() / "Downloads"
        folder.mkdir(parents=True, exist_ok=True)
        target = config.unique_path(folder, suggested)
        download.set_destination(GLib.filename_to_uri(str(target), None))
        return True


def _spelling_languages() -> list[str]:
    names = [n for n in GLib.get_language_names() if "_" in n and "." not in n and "@" not in n]
    return names[:3] or ["en_US"]


def run(debug: bool, argv: list[str]) -> int:
    return NatterApp(debug).run(argv)
