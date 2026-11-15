"""What the Linux Qt WebEngine (Chromium) backend needs so WhatsApp Web treats it as desktop Chrome, calls included.

Pure Python (strings only), so it's tested without Qt. Found 2026-11-15 by asking WhatsApp's own code
(`require("WAWebVoipGatingUtils").getUnsupportedBrowserReason()`) through the engine's devtools."""
from __future__ import annotations

import re

# Chromium switches, set before the engine starts (QTWEBENGINE_CHROMIUM_FLAGS).
# SharedArrayBuffer: WhatsApp's calls need it (reason "missing_shared_array_buffer"), and Chromium only gives it
# to cross-origin-isolated pages, which WhatsApp isn't inside Qt WebEngine. PipeWire: screen sharing on Wayland.
ENABLE = "SharedArrayBuffer,SharedArrayBufferOnDesktop,WebRTCPipeWireCapturer"
# light as possible (user 2026-11-15): one page -> one renderer; browser extras nobody uses here -> off
DISABLE = "Translate,OptimizationHints,MediaRouter,BackForwardCache,DialMediaRouteProvider,AutofillServerCommunication"
LIGHT = ("--renderer-process-limit=1", "--disable-background-networking", "--disable-component-update",
         "--disable-breakpad", "--disable-sync")
CACHE_MB = 64  # disk cache cap with the memory saver on (Chromium's default grows to hundreds of MB)


def flags(existing: str = "") -> str:
    """The switches for QTWEBENGINE_CHROMIUM_FLAGS, keeping any the user set."""
    ours = [f"--enable-features={ENABLE}", f"--disable-features={DISABLE}", *LIGHT]
    return " ".join([existing.strip(), *ours]).strip()

# Permissions WhatsApp Web asks for, granted for web.whatsapp.com only (everything else is refused):
# notifications, microphone and camera (calls, voice notes, photos), the clipboard (pasting pictures).
ALLOWED_PERMISSIONS = ("Notifications", "MediaAudioCapture", "MediaVideoCapture", "MediaAudioVideoCapture",
                       "ClipboardReadWrite")
WHATSAPP_HOST = "web.whatsapp.com"


def user_agent(default: str) -> str:
    """Qt's own user agent without the `QtWebEngine/x.y.z` part: plain desktop Chrome."""
    return re.sub(r"QtWebEngine/\S+\s*", "", default).strip()


def chrome_version(default_user_agent: str) -> str:
    """The Chrome version in the user agent ("134.0.6998.208" or "134.0.0.0"), or "" if there's none."""
    m = re.search(r"Chrome/([\d.]+)", default_user_agent)
    return m[1] if m else ""


def brands(full_version: str) -> dict[str, str]:
    """Client hints (Sec-CH-UA, navigator.userAgentData) as Google Chrome's, not QtWebEngine's."""
    return {"Chromium": full_version, "Google Chrome": full_version, "Not=A?Brand": "24.0.0.0"}


def allowed(permission_name: str, host: str) -> bool:
    return host == WHATSAPP_HOST and permission_name in ALLOWED_PERMISSIONS


def chrome_shim(major: str) -> str:
    """Runs before WhatsApp's code: the bits real Chrome has and Qt WebEngine lacks (`window.chrome`, Chrome brands)."""
    return """
(() => {
  if (window.__natterChrome) return;
  window.__natterChrome = true;
  const b = [{brand: 'Chromium', version: '%(v)s'}, {brand: 'Google Chrome', version: '%(v)s'},
             {brand: 'Not=A?Brand', version: '24'}];
  try { const d = navigator.userAgentData; if (d) Object.defineProperty(d, 'brands', {get: () => b}); } catch (e) {}
  if (!window.chrome) {
    const now = () => Date.now() / 1000;
    window.chrome = { app: { isInstalled: false, InstallState: {}, RunningState: {} }, runtime: {},
      loadTimes: () => ({ requestTime: now(), startLoadTime: now(), commitLoadTime: now(),
        finishDocumentLoadTime: now(), finishLoadTime: now(), firstPaintTime: now(), navigationType: 'Other',
        wasFetchedViaSpdy: true, wasNpnNegotiated: true, npnNegotiatedProtocol: 'h2', connectionInfo: 'h2' }),
      csi: () => ({ startE: Date.now(), onloadT: Date.now(), pageT: 1, tran: 15 }) };
  }
  try { Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'}); } catch (e) {}
})();
""" % {"v": major or "134"}
