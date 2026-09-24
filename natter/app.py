"""Entry point: picks the native backend for the current platform."""
from __future__ import annotations

import argparse
import sys

from natter import APP_NAME, DEVELOPER, __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="natter", description="WhatsApp Web in a native window.")
    parser.add_argument("--debug", action="store_true", help="enable the web inspector")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__} by {DEVELOPER}")
    args, rest = parser.parse_known_args(argv)

    if sys.platform == "win32":
        from natter import windows
        return windows.run(debug=args.debug)
    from natter import config
    browser = config.find_browser() if config.use_browser() else None
    if browser:
        from natter import chromium
        return chromium.run(browser, debug=args.debug)
    from natter import linux  # no Chromium browser installed: WebKitGTK (no calls)
    return linux.run(debug=args.debug, argv=[sys.argv[0], *rest])
