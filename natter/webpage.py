"""What Natter puts into web pages on Windows, where WebView2 is a web browser it can script: the Do Not Disturb
switch inside WhatsApp, and the Settings window (an HTML page).

Pure Python (strings only), so it's tested here without Windows."""
from __future__ import annotations

import html
import json

from natter import __version__, config, i18n, look
from natter.i18n import _
from natter.state import Preferences

# Runs in WhatsApp's page before its own code. While `window.__natterQuiet` is true, notifications are made but
# never shown: WhatsApp carries on as usual and the unread count in the title (and the tray) still updates.
QUIET_SCRIPT = """
(() => {
  if (window.__natterWrapped) return;
  window.__natterWrapped = true;
  window.__natterQuiet = false;
  const Real = window.Notification;
  if (!Real) return;
  function Quiet(title, options) {
    if (window.__natterQuiet) {
      const silent = new EventTarget();
      silent.close = () => {};
      silent.title = title;
      silent.onclick = null;
      return silent;
    }
    return new Real(title, options);
  }
  Quiet.prototype = Real.prototype;
  Object.defineProperty(Quiet, "permission", { get: () => Real.permission });
  Quiet.requestPermission = (...args) => Real.requestPermission(...args);
  window.Notification = Quiet;
})();
"""


# Linux: WebKitGTK forgets the notification permission on every start, so WhatsApp asked again each time
# ("Turn on desktop notifications"). The page's Notification is replaced: always granted, and each one is
# handed to Natter (script message `natterNotify`), which shows it as the app's own desktop notification.
LINUX_NOTIFY_SCRIPT = """
(() => {
  if (window.__natterNotify || !window.webkit || !window.webkit.messageHandlers.natterNotify) return;
  window.__natterNotify = true;
  const post = (m) => window.webkit.messageHandlers.natterNotify.postMessage(JSON.stringify(m));
  let next = 1;
  const live = new Map();
  class NatterNotification extends EventTarget {
    constructor(title, options) {
      super();
      options = options || {};
      this.title = String(title);
      this.body = String(options.body || "");
      this.tag = String(options.tag || "");
      this.icon = String(options.icon || "");
      this.data = options.data;
      this.onclick = this.onclose = this.onshow = this.onerror = null;
      this._id = next++;
      live.set(this._id, this);
      post({kind: "show", id: this._id, title: this.title, body: this.body, tag: this.tag});
      setTimeout(() => { const e = new Event("show"); this.dispatchEvent(e); if (this.onshow) this.onshow(e); }, 0);
    }
    close() {
      if (!live.delete(this._id)) return;
      post({kind: "close", id: this._id, tag: this.tag});
      const e = new Event("close"); this.dispatchEvent(e); if (this.onclose) this.onclose(e);
    }
    static get permission() { return "granted"; }
    static requestPermission(callback) { if (callback) callback("granted"); return Promise.resolve("granted"); }
  }
  NatterNotification.maxActions = 0;
  window.__natterClicked = (id) => {
    const n = live.get(id);
    if (!n) return;
    const e = new Event("click", {cancelable: true});
    n.dispatchEvent(e);
    if (n.onclick) n.onclick(e);
  };
  window.Notification = NatterNotification;
  if (navigator.permissions && navigator.permissions.query) {
    const query = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (d) => d && d.name === "notifications"
      ? Promise.resolve({state: "granted", status: "granted", onchange: null, addEventListener() {}, removeEventListener() {}})
      : query(d);
  }
})();
"""


def notify_message(raw: str) -> dict | None:
    """A message from LINUX_NOTIFY_SCRIPT, checked: {"kind": "show"|"close", "id": int, ...}; None if it's not one."""
    try:
        m = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(m, dict) or m.get("kind") not in ("show", "close") or not isinstance(m.get("id"), int):
        return None
    return {"kind": m["kind"], "id": m["id"], "title": str(m.get("title", ""))[:200],
            "body": str(m.get("body", ""))[:1000], "tag": str(m.get("tag", ""))[:100]}


def notification_key(message: dict) -> str:
    """One desktop notification per WhatsApp tag (a new message in the same chat replaces the last one)."""
    return f"wa-{message['tag']}" if message["tag"] else f"wa-{message['id']}"


def quiet_switch(on: bool) -> str:
    """The script that turns Do Not Disturb on or off in the running page."""
    return f"window.__natterQuiet = {json.dumps(bool(on))};"


def settings_page(prefs: Preferences, auto_update: bool, dark: bool) -> str:
    """The Settings window as one HTML page. Switches call `pywebview.api.<name>(value)` on the Windows backend."""
    t = look.DARK if dark else look.LIGHT
    esc = html.escape

    def switch(name: str, title: str, hint: str, on: bool) -> str:
        checked = " checked" if on else ""
        return (f'<label class="row"><span><b>{esc(title)}</b><small>{esc(hint)}</small></span>'
                f'<input type="checkbox" role="switch" onchange="pywebview.api.{name}(this.checked)"{checked}></label>')

    languages = "".join(
        f'<option value="{esc(code)}"{" selected" if code == prefs.language else ""}>'
        f'{esc(_(name) if code == "" else name)}</option>'
        for code, name in i18n.LANGUAGES)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
:root {{ color-scheme: {"dark" if dark else "light"}; }}
body {{ margin: 0; font: 15px "Segoe UI Variable", "Segoe UI", sans-serif; color: {t["text"]};
  background: {t["bg"]}; min-height: 100vh; overflow-x: hidden; }}
/* Material 3 tonal: a plain page, solid cards, a solid header. */
header {{ position: sticky; top: 0; z-index: 2; padding: 16px 20px; background: {t["bg"]}; }}
main {{ padding: 10px; display: grid; gap: 10px; }}
h1 {{ margin: 0; font-size: 26px; font-weight: 800; }}
.card {{ border-radius: 28px; padding: 16px 20px; background: {t["surface"]}; border: none; }}
.card h2 {{ margin: 0 0 6px; font-size: 13px; color: {t["accent"]}; letter-spacing: .3px; }}
.row {{ display: flex; gap: 16px; align-items: center; justify-content: space-between; padding: 8px 0; }}
.row span {{ display: grid; gap: 2px; }}
small, .hint {{ color: {t["faint"]}; font-size: 13px; }}
input[role=switch] {{ appearance: none; width: 50px; height: 28px; border-radius: 14px; flex: none; cursor: pointer;
  background: {look.rgba(t["text"], .18)}; position: relative; transition: background .15s; }}
input[role=switch]::after {{ content: ""; position: absolute; top: 3px; left: 3px; width: 22px; height: 22px;
  border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.35); transition: left .15s; }}
input[role=switch]:checked {{ background: {t["accent"]}; }}
input[role=switch]:checked::after {{ left: 25px; }}
select, button {{ font: inherit; border-radius: 12px; padding: 7px 14px; color: {t["text"]};
  border: 1px solid {look.rgba(t["border"], .6)}; background: {t["raised"] if "raised" in t else t["surface"]}; }}
button {{ cursor: pointer; }}
</style></head><body>
<header><h1>{esc(_("Settings"))}</h1></header>
<main>
<section class="card"><h2>{esc(_("Notifications"))}</h2>
{switch("set_dnd", _("Do Not Disturb"), _("Messages arrive without a pop-up or a sound; the unread count on the tray icon still shows."), prefs.do_not_disturb)}
</section>
<section class="card"><h2>{esc(_("Starting"))}</h2>
{switch("set_start_on_login", _("Start on login"), _("Natter waits in the tray, so messages arrive from the start."), prefs.start_on_login)}
{switch("set_shortcut", _("Show and hide with Ctrl+Alt+W"), _("A keyboard shortcut for the whole desktop."), bool(prefs.shortcut))}
</section>
<section class="card"><h2>{esc(_("Spelling"))}</h2>
<p class="hint">{esc(_("On Windows, spelling follows the typing languages set in Windows' own settings."))}</p>
</section>
<section class="card"><h2>{esc(_("Speed and memory"))}</h2>
{switch("set_memory", _("Save memory"), _("Uses less memory while Natter waits in the tray."), prefs.memory_saver)}
</section>
<section class="card"><h2>{esc(_("Language and updates"))}</h2>
<label class="row"><b>{esc(_("Language"))}</b><select onchange="pywebview.api.set_language(this.value)">{languages}</select></label>
{switch("set_auto_update", _("Check for updates automatically"), "", auto_update)}
<button onclick="pywebview.api.check_updates()">{esc(_("Check for updates…"))}</button>
</section>
<p class="hint">{esc(_("{app} {version}").format(app=config.APP_NAME, version=__version__))}</p>
</main></body></html>"""
