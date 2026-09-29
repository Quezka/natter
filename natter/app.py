"""Entry point: picks the native backend for the current platform."""
from __future__ import annotations

import argparse
import sys

from natter import APP_NAME, DEVELOPER, __version__, config, i18n
from natter.i18n import _
from natter.state import Preferences


def main(argv: list[str] | None = None) -> int:
    i18n.install(Preferences.load(config.data_dir() / "preferences.json").language)
    parser = argparse.ArgumentParser(prog="natter", description=_("WhatsApp Web in a native window."))
    parser.add_argument("--debug", action="store_true", help=_("enable the web inspector"))
    parser.add_argument("--background", action="store_true",
                        help=_("start hidden in the tray (used when starting on login)"))
    parser.add_argument("--version", action="version", version=_("{app} {version} by {developer}").format(
        app=APP_NAME, version=__version__, developer=DEVELOPER))
    args, rest = parser.parse_known_args(argv)

    if sys.platform == "win32":
        from natter import windows
        return windows.run(debug=args.debug, background=args.background)
    from natter import linux
    return linux.run(debug=args.debug, background=args.background, argv=[sys.argv[0], *rest])
