"""
Global Keyboard Hook and Hotkey Manager for Windows.
Uses Win32 WH_KEYBOARD_LL to listen for global hotkeys across all applications
without requiring administrator privileges or third-party dependencies.
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import Callable, Dict, List, Set, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from src.vk_codes import (
    name_to_vk,
    vk_to_name,
    normalize_modifier,
    MODIFIER_NAMES,
    VK_SHIFT,
    VK_CONTROL,
    VK_MENU,
    VK_LWIN,
    VK_RWIN,
)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_longlong
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012

WH_KEYBOARD_LL = 13


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


# Win32 function types
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK

user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT

user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT

user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = wintypes.SHORT


class HotkeyBinding:
    """Represents a registered global hotkey."""

    def __init__(
        self,
        action_name: str,
        modifiers: List[str],
        key_name: str,
        callback: Callable[[], None],
        suppress: bool = False,
        debounce_secs: float = 0.25
    ):
        self.action_name = action_name
        self.modifiers = set(normalize_modifier(m) for m in modifiers if m)
        self.key_name = key_name.strip()
        self.vk_code = name_to_vk(self.key_name)
        self.callback = callback
        self.suppress = suppress
        self.debounce_secs = debounce_secs
        self.last_trigger_time = 0.0

    def matches(self, pressed_vk: int, active_mods: Set[str]) -> bool:
        if self.vk_code != pressed_vk:
            return False
        return self.modifiers == active_mods


class HotkeyManager:
    """
    Manages global keyboard hook in a background thread and triggers
    callbacks when configured key combinations are pressed.
    """

    def __init__(self):
        self._bindings: Dict[str, HotkeyBinding] = {}
        self._lock = threading.Lock()
        self._enabled = True
        self._hook_handle: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._ready_event = threading.Event()
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="HotkeyWorker")
        self._hook_proc_ref: Optional[HOOKPROC] = None

    def register_hotkey(
        self,
        action_name: str,
        modifiers: List[str],
        key_name: str,
        callback: Callable[[], None],
        suppress: bool = False
    ) -> bool:
        """Register or update a hotkey binding."""
        with self._lock:
            binding = HotkeyBinding(action_name, modifiers, key_name, callback, suppress)
            if binding.vk_code == 0:
                return False
            self._bindings[action_name] = binding
            return True

    def unregister_hotkey(self, action_name: str):
        """Remove a hotkey binding."""
        with self._lock:
            if action_name in self._bindings:
                del self._bindings[action_name]

    def set_enabled(self, enabled: bool):
        """Pause or resume hotkey processing."""
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def get_binding(self, action_name: str) -> Optional[HotkeyBinding]:
        with self._lock:
            return self._bindings.get(action_name)

    def _get_active_modifiers(self) -> Set[str]:
        """Detect currently pressed modifier keys."""
        mods = set()
        if (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0:
            mods.add("ctrl")
        if (user32.GetAsyncKeyState(VK_MENU) & 0x8000) != 0:
            mods.add("alt")
        if (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0:
            mods.add("shift")
        if (user32.GetAsyncKeyState(VK_LWIN) & 0x8000) != 0 or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000) != 0:
            mods.add("win")
        return mods

    def _hook_callback(self, nCode: int, wParam: int, lParam: int) -> int:
        """Win32 WH_KEYBOARD_LL hook callback."""
        if nCode >= 0 and self._enabled and (wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN):
            try:
                kbd = KBDLLHOOKSTRUCT.from_address(lParam)
                vk = kbd.vkCode

                # Skip standalone modifier key presses
                if vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5):
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                active_mods = self._get_active_modifiers()
                now = time.time()

                suppress_key = False
                matched_binding = None

                with self._lock:
                    for binding in self._bindings.values():
                        if binding.matches(vk, active_mods):
                            if (now - binding.last_trigger_time) >= binding.debounce_secs:
                                binding.last_trigger_time = now
                                matched_binding = binding
                                if binding.suppress:
                                    suppress_key = True
                            break

                if matched_binding:
                    # Execute callback on worker thread to avoid blocking the OS keyboard hook
                    self._executor.submit(matched_binding.callback)

                if suppress_key:
                    return 1

            except Exception:
                pass

        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _thread_worker(self):
        """Worker thread running the Windows message loop for the hook."""
        self._thread_id = kernel32.GetCurrentThreadId()

        # Initialize message queue for this thread
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        # Retain reference to callback function to prevent garbage collection
        self._hook_proc_ref = HOOKPROC(self._hook_callback)
        self._hook_handle = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            None,
            0
        )

        self._ready_event.set()

        # Message loop
        while not self._stop_event.is_set():
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:  # WM_QUIT or error
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup hook
        if self._hook_handle:
            user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None

    def start(self):
        """Start global keyboard hook in background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._ready_event.clear()
        self._thread = threading.Thread(target=self._thread_worker, daemon=True, name="HotkeyThread")
        self._thread.start()
        self._ready_event.wait(timeout=3.0)

    def stop(self):
        """Stop global keyboard hook."""
        self._stop_event.set()
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._executor.shutdown(wait=False)
