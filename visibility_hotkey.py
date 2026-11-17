import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QAbstractNativeEventFilter


class VisibilityHotkey(QAbstractNativeEventFilter):
    """A window-bound Windows hotkey that continues working while the island is hidden."""

    ID = 0x4921
    WM_HOTKEY = 0x0312
    MOD_CONTROL = 0x0002
    MOD_NOREPEAT = 0x4000

    def __init__(self, app, window_handle, callback):
        super().__init__()
        self.app = app
        self.callback = callback
        self.window_handle = window_handle
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.RegisterHotKey.argtypes = [
            wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT
        ]
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.registered = bool(self.user32.RegisterHotKey(
            self.window_handle, self.ID, self.MOD_CONTROL | self.MOD_NOREPEAT, ord("H")
        ))
        if self.registered:
            self.app.installNativeEventFilter(self)

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == self.WM_HOTKEY and msg.wParam == self.ID:
                self.callback()
                return True, 0
        return False, 0

    def close(self):
        if self.registered:
            self.app.removeNativeEventFilter(self)
            self.user32.UnregisterHotKey(self.window_handle, self.ID)
            self.registered = False
