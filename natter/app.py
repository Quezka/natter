"""Entry point: picks the native backend for the current platform."""
from __future__ import annotations

import argparse
import sys

from natter import APP_NAME, DEVELOPER, __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="natter", description="WhatsApp Web in a native window.")
    parser.add_argument("--debug", action="store_true", help="enable the web inspector")
    parser.add_argument("--background", action="store_true",
                        help="start hidden in the tray (used when starting on login)")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__} by {DEVELOPER}")
    args, rest = parser.parse_known_args(argv)

    if sys.platform == "win32":
        from natter import windows
        return windows.run(debug=args.debug, background=args.background)
    from natter import linux
    return linux.run(debug=args.debug, background=args.background, argv=[sys.argv[0], *rest])
