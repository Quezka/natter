"""Windows backend: pywebview on Edge WebView2 (the system webview)."""
from __future__ import annotations

import webview

from natter import config
from natter.state import WindowState


def run(debug: bool) -> int:
    state_path = config.data_dir() / "window.json"
    state = WindowState.load(state_path)

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
    )
    tuned = False

    def on_loaded() -> None:
        nonlocal tuned
        if not tuned:
            tuned = True
            _tune_webview2(window)

    def on_closing() -> None:
        state.width, state.height = window.width, window.height
        try:
            state.save(state_path)
        except OSError:
            pass

    window.events.loaded += on_loaded
    window.events.closing += on_closing
    webview.start(
        gui="edgechromium",
        debug=debug,
        private_mode=False,
        storage_path=str(config.data_dir() / "web"),
    )
    return 0


def _tune_webview2(window) -> None:
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
        form.Text = config.window_title(config.unread_count(sender.DocumentTitle))

    def tune() -> None:
        core = form.browser.webview.CoreWebView2
        settings = core.Settings
        settings.AreDefaultContextMenusEnabled = True  # copy/paste and spell-check suggestions
        settings.AreBrowserAcceleratorKeysEnabled = True  # Ctrl+F, Ctrl+R, zoom keys
        core.PermissionRequested += on_permission
        core.DocumentTitleChanged += on_title

    form.Invoke(Action(tune))
