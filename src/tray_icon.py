"""
Native Windows System Tray Icon implementation using pure ctypes and Win32 APIs.
No external dependencies required (no Pillow, no pystray).
"""

import ctypes
from ctypes import wintypes
import os
import threading
from typing import Callable, Optional

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

# Win32 Messages & Constants
WM_USER = 0x0400
WM_TRAY_CALLBACK = WM_USER + 20
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002
WM_QUIT = 0x0012
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010

NIIF_INFO = 0x00000001

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
MF_CHECKED = 0x00000008
MF_UNCHECKED = 0x00000000

TPM_BOTTOMALIGN = 0x0020
TPM_RIGHTALIGN = 0x0008
TPM_RETURNCMD = 0x0100

IDI_APPLICATION = ctypes.c_void_p(32512)
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HICON),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


# Setup function prototypes
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_longlong

user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM

user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.UnregisterClassW.restype = wintypes.BOOL

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL

shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL

user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.CreatePopupMenu.argtypes = []
user32.CreatePopupMenu.restype = wintypes.HMENU

user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_uint64, wintypes.LPCWSTR]
user32.AppendMenuW.restype = wintypes.BOOL

user32.TrackPopupMenuEx.argtypes = [
    wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p
]
user32.TrackPopupMenuEx.restype = wintypes.BOOL

user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL

user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL


# Context Menu Command IDs
CMD_CENTER_NOW = 2001
CMD_SHOW_WINDOW = 2002
CMD_TOGGLE_ENABLED = 2003
CMD_EXIT = 2004


class TrayIcon:
    """
    Win32 System Tray Icon with native context menu, tooltip, and event callbacks.
    Runs on its own lightweight thread.
    """

    def __init__(
        self,
        tooltip: str = "Window Centerer",
        icon_path: Optional[str] = None,
        on_show_window: Optional[Callable[[], None]] = None,
        on_center_now: Optional[Callable[[], None]] = None,
        on_toggle_enabled: Optional[Callable[[bool], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ):
        self.tooltip = tooltip
        self.icon_path = icon_path
        self.on_show_window = on_show_window
        self.on_center_now = on_center_now
        self.on_toggle_enabled = on_toggle_enabled
        self.on_exit = on_exit

        self.is_enabled = True
        self._hwnd: Optional[int] = None
        self._hicon: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._wnd_proc_ref: Optional[WNDPROC] = None
        self._class_atom = 0
        self._class_name = f"WindowCentererTray_{id(self)}"
        self._hinstance = kernel32.GetModuleHandleW(None)
        self._ready_event = threading.Event()

    def _load_icon(self) -> int:
        """Load icon from .ico file or fallback to default system icon."""
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                hicon = user32.LoadImageW(
                    None,
                    self.icon_path,
                    IMAGE_ICON,
                    0,
                    0,
                    LR_LOADFROMFILE
                )
                if hicon:
                    return hicon
            except Exception:
                pass
        return user32.LoadIconW(None, IDI_APPLICATION)

    def _show_context_menu(self):
        """Display native Windows popup context menu at current cursor location."""
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        hmenu = user32.CreatePopupMenu()
        if not hmenu:
            return

        user32.AppendMenuW(hmenu, MF_STRING, CMD_CENTER_NOW, "Center Active Window")
        user32.AppendMenuW(hmenu, MF_STRING, CMD_SHOW_WINDOW, "Open Settings Dashboard")
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, "")

        state = MF_CHECKED if self.is_enabled else MF_UNCHECKED
        user32.AppendMenuW(hmenu, MF_STRING | state, CMD_TOGGLE_ENABLED, "Hotkeys Active")
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, "")

        user32.AppendMenuW(hmenu, MF_STRING, CMD_EXIT, "Exit")

        # Required before and after TrackPopupMenu to handle focus correctly
        user32.SetForegroundWindow(self._hwnd)
        cmd = user32.TrackPopupMenuEx(
            hmenu,
            TPM_RETURNCMD | TPM_BOTTOMALIGN | TPM_RIGHTALIGN,
            pt.x,
            pt.y,
            self._hwnd,
            None
        )
        user32.PostMessageW(self._hwnd, 0, 0, 0)
        user32.DestroyMenu(hmenu)

        if cmd == CMD_CENTER_NOW:
            if self.on_center_now:
                threading.Thread(target=self.on_center_now, daemon=True).start()
        elif cmd == CMD_SHOW_WINDOW:
            if self.on_show_window:
                self.on_show_window()
        elif cmd == CMD_TOGGLE_ENABLED:
            self.is_enabled = not self.is_enabled
            if self.on_toggle_enabled:
                self.on_toggle_enabled(self.is_enabled)
            self.update_tooltip()
        elif cmd == CMD_EXIT:
            if self.on_exit:
                self.on_exit()

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_TRAY_CALLBACK:
            if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                if self.on_show_window:
                    self.on_show_window()
                return 0
            elif lparam == WM_RBUTTONUP:
                self._show_context_menu()
                return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _thread_worker(self):
        self._thread_id = kernel32.GetCurrentThreadId()

        # Register window class
        self._wnd_proc_ref = WNDPROC(self._wnd_proc)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wnd_proc_ref
        wc.lpszClassName = self._class_name
        wc.hInstance = self._hinstance

        self._class_atom = user32.RegisterClassExW(ctypes.byref(wc))

        self._hwnd = user32.CreateWindowExW(
            0,
            self._class_name,
            "WindowCentererTrayWindow",
            0,
            0, 0, 0, 0,
            0,
            None,
            self._hinstance,
            None
        )

        self._hicon = self._load_icon()

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY_CALLBACK
        nid.hIcon = self._hicon
        nid.szTip = self.tooltip[:127]

        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        self._ready_event.set()

        # Message loop
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup
        nid_del = NOTIFYICONDATAW()
        nid_del.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid_del.hWnd = self._hwnd
        nid_del.uID = 1
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid_del))

        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None

        if self._class_atom:
            user32.UnregisterClassW(self._class_name, self._hinstance)

    def start(self):
        """Start tray icon background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._ready_event.clear()
        self._thread = threading.Thread(target=self._thread_worker, daemon=True, name="TrayThread")
        self._thread.start()
        self._ready_event.wait(timeout=2.0)

    def stop(self):
        """Remove tray icon and stop thread."""
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None

    def update_tooltip(self, text: Optional[str] = None):
        """Update tray hover tooltip."""
        if text:
            self.tooltip = text
        if not self._hwnd:
            return

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_TIP
        status = "Active" if self.is_enabled else "Paused"
        tip_text = f"{self.tooltip} [{status}]"
        nid.szTip = tip_text[:127]
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

    def show_notification(self, title: str, message: str):
        """Show balloon notification from tray icon."""
        if not self._hwnd:
            return

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_INFO
        nid.szInfoTitle = title[:63]
        nid.szInfo = message[:255]
        nid.dwInfoFlags = NIIF_INFO
        nid.uTimeoutOrVersion = 2000
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
