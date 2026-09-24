"""Linux backend: WhatsApp Web as an app window of an installed Chromium browser.

Natter hands over to the browser (exec), so nothing of Natter keeps running.
"""
from __future__ import annotations

import os
import sys

from natter import config


def run(browser: str, debug: bool) -> int:
    profile = config.browser_profile(browser)
    if config.profile_in_use(profile):
        # Launching again would open WhatsApp a second time ("Use here?"). The dock
        # focuses the open window; from a terminal, just say so.
        print(f"{config.APP_NAME} is already open.", file=sys.stderr)
        return 0
    profile.mkdir(parents=True, exist_ok=True)
    command = config.browser_command(browser, profile, debug)
    os.execv(command[0], command)
    return 1  # not reached
