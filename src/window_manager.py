"""
Win32 Window and Monitor Management utilities.
Handles DPI awareness, multi-monitor enumeration, invisible drop-shadow margin detection,
and pixel-perfect window centering across screens.
"""

import ctypes
from ctypes import wintypes
import time
from typing import Optional, Dict, List, Tuple, Any

# Win32 Libraries
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
kernel32 = ctypes.windll.kernel32

# Win32 Constants
MONITOR_DEFAULTTONEAREST = 2
MONITOR_DEFAULTTOPRIMARY = 1
DWMWA_EXTENDED_FRAME_BOUNDS = 9
SW_RESTORE = 9
SW_SHOW = 5

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOREDRAW = 0x0008
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

HWND_TOP = 0

# DPI Awareness Constants
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

# Win32 Structures
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32)
    ]


# Function Signatures
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetForegroundWindow.argtypes = []

user32.GetDesktopWindow.restype = wintypes.HWND
user32.GetDesktopWindow.argtypes = []

user32.GetShellWindow.restype = wintypes.HWND
user32.GetShellWindow.argtypes = []

user32.IsWindow.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]

user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]

user32.IsIconic.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]

user32.IsZoomed.restype = wintypes.BOOL
user32.IsZoomed.argtypes = [wintypes.HWND]

user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]

user32.GetWindowRect.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]

user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT
]

user32.MonitorFromWindow.restype = wintypes.HMONITOR
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]

user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]

dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long
dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD
]

MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM
)

user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.EnumDisplayMonitors.argtypes = [
    wintypes.HDC, ctypes.c_void_p, MONITORENUMPROC, wintypes.LPARAM
]


def init_dpi_awareness():
    """Enable Per-Monitor V2 DPI awareness for pixel-perfect coordinates."""
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2))
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


# Shell and system window class names to ignore
IGNORED_WINDOW_CLASSES = {
    "progman",
    "workerw",
    "shell_traywnd",
    "shell_secondarytraywnd",
    "dv2controlhost",
    "windows.ui.core.corewindow",
}


class WindowManager:
    """Manages active window identification, multi-monitor querying, and centering."""

    def __init__(self):
        init_dpi_awareness()

    @staticmethod
    def get_window_title(hwnd: int) -> str:
        """Get window title text."""
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        return ""

    @staticmethod
    def get_window_class(hwnd: int) -> str:
        """Get window class name."""
        buff = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buff, 256)
        return buff.value.lower()

    def is_valid_user_window(self, hwnd: int) -> bool:
        """Check whether the window is a valid normal application window."""
        if not hwnd or not user32.IsWindow(hwnd):
            return False
        if not user32.IsWindowVisible(hwnd):
            return False
        if hwnd == user32.GetDesktopWindow() or hwnd == user32.GetShellWindow():
            return False
        
        cls_name = self.get_window_class(hwnd)
        if cls_name in IGNORED_WINDOW_CLASSES:
            return False
            
        return True

    def get_active_window(self) -> Optional[int]:
        """Return the current foreground window HWND if valid."""
        hwnd = user32.GetForegroundWindow()
        if self.is_valid_user_window(hwnd):
            return hwnd
        return None

    @staticmethod
    def get_window_bounds(hwnd: int) -> Tuple[RECT, RECT, Tuple[int, int, int, int]]:
        """
        Retrieve both the outer window rect and the visible frame bounds.
        Returns:
            (window_rect, frame_rect, (margin_left, margin_top, margin_right, margin_bottom))
        """
        win_rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(win_rect))

        frame_rect = RECT()
        # DWMWA_EXTENDED_FRAME_BOUNDS gets true visible bounds without invisible resize borders
        dwm_res = dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(frame_rect),
            ctypes.sizeof(RECT)
        )

        if dwm_res != 0 or frame_rect.width <= 0 or frame_rect.height <= 0:
            # Fallback to standard window rect if DWM call failed
            frame_rect = win_rect
            margins = (0, 0, 0, 0)
        else:
            margin_left = max(0, frame_rect.left - win_rect.left)
            margin_top = max(0, frame_rect.top - win_rect.top)
            margin_right = max(0, win_rect.right - frame_rect.right)
            margin_bottom = max(0, win_rect.bottom - frame_rect.bottom)
            margins = (margin_left, margin_top, margin_right, margin_bottom)

        return win_rect, frame_rect, margins

    @staticmethod
    def get_all_monitors() -> List[Dict[str, Any]]:
        """
        Enumerate all active monitors with geometry, work area, and primary flag.
        Sorted left-to-right by X coordinate.
        """
        monitors: List[Dict[str, Any]] = []

        def enum_cb(hmon, hdc, lprect, lparam):
            mi = MONITORINFOEXW()
            mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                is_primary = bool(mi.dwFlags & 1)
                monitors.append({
                    "hmon": int(hmon),
                    "device": mi.szDevice,
                    "primary": is_primary,
                    "monitor_rect": mi.rcMonitor,
                    "work_rect": mi.rcWork,
                })
            return True

        cb = MONITORENUMPROC(enum_cb)
        user32.EnumDisplayMonitors(None, None, cb, 0)

        # Sort monitors left to right, then top to bottom
        monitors.sort(key=lambda m: (m["monitor_rect"].left, m["monitor_rect"].top))
        return monitors

    def get_monitor_for_window(self, hwnd: int) -> Optional[Dict[str, Any]]:
        """Find the monitor containing the window, or nearest to it."""
        hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if not hmon:
            return None

        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return {
                "hmon": int(hmon),
                "device": mi.szDevice,
                "primary": bool(mi.dwFlags & 1),
                "monitor_rect": mi.rcMonitor,
                "work_rect": mi.rcWork,
            }
        return None

    def center_window(
        self,
        hwnd: Optional[int] = None,
        target_monitor: Optional[Dict[str, Any]] = None,
        auto_restore_maximized: bool = True,
        auto_shrink_oversized: bool = True,
        resize_factor: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Center a window on a monitor.
        If hwnd is None, uses the current foreground window.
        If target_monitor is None, centers on the monitor the window is currently on.
        
        Args:
            hwnd: Window handle to center, or None for foreground.
            target_monitor: Monitor dict to center on, or None for window's current monitor.
            auto_restore_maximized: Restore window if it is currently maximized.
            auto_shrink_oversized: Shrink window if it exceeds work area dimensions.
            resize_factor: Optional float (e.g. 0.75) to resize window to % of work area.
            
        Returns:
            Dict containing execution status and window details.
        """
        if hwnd is None:
            hwnd = self.get_active_window()

        if not hwnd or not self.is_valid_user_window(hwnd):
            return {"success": False, "error": "No valid foreground window found"}

        title = self.get_window_title(hwnd)

        # If window is minimized, restore it
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.04)

        # If window is maximized, restore it first if permitted
        if user32.IsZoomed(hwnd):
            if auto_restore_maximized:
                user32.ShowWindow(hwnd, SW_RESTORE)
                time.sleep(0.05)
            else:
                return {
                    "success": False,
                    "error": "Window is maximized (enable 'Auto-restore' in settings to center)"
                }

        # Determine target monitor
        if target_monitor is None:
            target_monitor = self.get_monitor_for_window(hwnd)

        if not target_monitor:
            return {"success": False, "error": "Could not determine target monitor"}

        work_rect: RECT = target_monitor["work_rect"]
        work_w = work_rect.width
        work_h = work_rect.height

        if work_w <= 0 or work_h <= 0:
            return {"success": False, "error": "Invalid work area dimensions"}

        # Get window bounds and DWM invisible margin offsets
        win_rect, frame_rect, (margin_l, margin_t, margin_r, margin_b) = self.get_window_bounds(hwnd)

        current_vis_w = frame_rect.width
        current_vis_h = frame_rect.height

        # Calculate new dimensions
        new_vis_w = current_vis_w
        new_vis_h = current_vis_h

        needs_resize = False

        if resize_factor and 0.1 <= resize_factor <= 1.0:
            new_vis_w = int(work_w * resize_factor)
            new_vis_h = int(work_h * resize_factor)
            needs_resize = True
        elif auto_shrink_oversized:
            if new_vis_w > work_w:
                new_vis_w = work_w
                needs_resize = True
            if new_vis_h > work_h:
                new_vis_h = work_h
                needs_resize = True

        # Compute centered coordinates within the work area
        target_vis_x = work_rect.left + (work_w - new_vis_w) // 2
        target_vis_y = work_rect.top + (work_h - new_vis_h) // 2

        # Adjust for invisible borders so visible frame lands exactly at target
        target_win_x = target_vis_x - margin_l
        target_win_y = target_vis_y - margin_t

        swp_flags = SWP_NOZORDER | SWP_NOACTIVATE
        if needs_resize:
            target_win_w = new_vis_w + margin_l + margin_r
            target_win_h = new_vis_h + margin_t + margin_b
        else:
            swp_flags |= SWP_NOSIZE
            target_win_w = 0
            target_win_h = 0

        res = user32.SetWindowPos(
            hwnd,
            HWND_TOP,
            target_win_x,
            target_win_y,
            target_win_w,
            target_win_h,
            swp_flags
        )

        if not res:
            err = kernel32.GetLastError()
            return {"success": False, "error": f"SetWindowPos failed with code {err}"}

        return {
            "success": True,
            "title": title or "(Untitled)",
            "monitor": target_monitor.get("device", "Monitor"),
            "is_primary": target_monitor.get("primary", False),
            "x": target_vis_x,
            "y": target_vis_y,
            "width": new_vis_w,
            "height": new_vis_h,
        }

    def cycle_monitor(
        self,
        hwnd: Optional[int] = None,
        direction: int = 1,
        auto_restore_maximized: bool = True,
        auto_shrink_oversized: bool = True
    ) -> Dict[str, Any]:
        """
        Move the active window to the next (direction=1) or previous (direction=-1) monitor
        and center it there.
        """
        if hwnd is None:
            hwnd = self.get_active_window()

        if not hwnd or not self.is_valid_user_window(hwnd):
            return {"success": False, "error": "No valid foreground window found"}

        all_monitors = self.get_all_monitors()
        if not all_monitors:
            return {"success": False, "error": "No monitors detected"}

        if len(all_monitors) == 1:
            # Single monitor: just center it on the existing monitor
            return self.center_window(
                hwnd=hwnd,
                target_monitor=all_monitors[0],
                auto_restore_maximized=auto_restore_maximized,
                auto_shrink_oversized=auto_shrink_oversized
            )

        current_mon = self.get_monitor_for_window(hwnd)
        current_hmon = current_mon["hmon"] if current_mon else None

        current_idx = 0
        for i, mon in enumerate(all_monitors):
            if mon["hmon"] == current_hmon:
                current_idx = i
                break

        target_idx = (current_idx + direction) % len(all_monitors)
        target_monitor = all_monitors[target_idx]

        return self.center_window(
            hwnd=hwnd,
            target_monitor=target_monitor,
            auto_restore_maximized=auto_restore_maximized,
            auto_shrink_oversized=auto_shrink_oversized
        )
