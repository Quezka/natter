"""A system-wide keyboard shortcut on Windows (Ctrl+Alt+W shows and hides Natter), through Windows' own
RegisterHotKey. It needs a thread with its own message loop: the hotkey's messages go to the thread that registered it."""
from __future__ import annotations

import threading
from typing import Callable

MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x0001, 0x0002, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012
HOTKEY_ID = 0x4E41  # any number unique within the thread


class Hotkey:
    def __init__(self, on_press: Callable[[], None], key: str = "W") -> None:
        self.on_press = on_press
        self.key = key
        self._thread: threading.Thread | None = None
        self._thread_id = 0
        self.ok = False

    def start(self) -> bool:
        """Registers the shortcut; False if Windows refused (another app already has it)."""
        if self._thread is not None:
            return self.ok
        ready = threading.Event()
        self._thread = threading.Thread(target=self._loop, args=(ready,), name="natter-hotkey", daemon=True)
        self._thread.start()
        ready.wait(2)
        return self.ok

    def stop(self) -> None:
        if self._thread is None:
            return
        import ctypes
        ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._thread = None
        self.ok = False

    def _loop(self, ready: threading.Event) -> None:
        import ctypes
        from ctypes import wintypes

        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()
        self.ok = bool(user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, ord(self.key)))
        ready.set()
        if not self.ok:
            return
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    try:
                        self.on_press()
                    except Exception:  # never let a failed toggle end the loop
                        pass
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)
