"""What Natter puts into web pages on Windows, where WebView2 is a web browser it can script: the Do Not Disturb
switch inside WhatsApp, and the Settings window (an HTML page, so it can use real backdrop blur for its glass).

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
/* Glass the Apple way: the page is plain and the cards solid; the header floats over them and blurs them as they
   scroll underneath. */
header {{ position: sticky; top: 0; z-index: 2; padding: 18px 22px 12px;
  background: {look.rgba(t["bg"], .55)}; backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border-bottom: 1px solid {look.rgba("#ffffff", .10) if dark else look.rgba("#000000", .08)}; }}
main {{ padding: 8px 22px 22px; display: grid; gap: 14px; }}
h1 {{ margin: 0; font-size: 26px; font-weight: 800; }}
.card {{ border-radius: 20px; padding: 14px 16px; background: {t["surface"]};
  border: 1px solid {look.rgba(t["border"], .45)}; border-top-color: {look.rgba("#ffffff", .10 if dark else .95)}; }}
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
