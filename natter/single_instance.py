"""Keep one Natter per user: a second launch asks the first to show its window, then exits.

Linux gets this from GApplication; Windows uses this module over a named pipe.
"""
from __future__ import annotations

import os
import sys
import threading
from multiprocessing.connection import Client, Listener
from typing import Callable

from natter import APP_ID

SHOW = "show"
_AUTHKEY = APP_ID.encode()


def default_address() -> tuple[str, str]:
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    if sys.platform == "win32":
        return rf"\\.\pipe\{APP_ID}-{user}", "AF_PIPE"
    return f"/tmp/{APP_ID}-{user}.sock", "AF_UNIX"


def claim(on_show: Callable[[], None], address: tuple[str, str] | None = None) -> bool:
    """True if this is the first instance (it now listens for later launches).

    False if another instance is running; it has been told to show its window.
    """
    path, family = address or default_address()
    try:
        with Client(path, family=family, authkey=_AUTHKEY) as conn:
            conn.send(SHOW)
        return False
    except (FileNotFoundError, ConnectionRefusedError):
        if family == "AF_UNIX":
            try:
                os.unlink(path)  # left behind by a crash
            except FileNotFoundError:
                pass
    except OSError:
        pass  # pipe busy or unreadable: better to run a second copy than none

    listener = Listener(path, family=family, authkey=_AUTHKEY)

    def serve() -> None:
        while True:  # the listener lives as long as the app; the thread is a daemon
            try:
                with listener.accept() as conn:
                    if conn.recv() == SHOW:
                        on_show()
            except Exception:  # a bad or impatient client must not stop the listener
                continue

    threading.Thread(target=serve, name="natter-single-instance", daemon=True).start()
    return True
