"""
Window Centerer - Main Application Entry Point.
Center any active window across any monitor in Windows, with customizable global shortcuts.
"""

import sys
import os
import argparse
import ctypes
from ctypes import wintypes
import time

from src.window_manager import WindowManager, init_dpi_awareness, user32
from src.hotkey_manager import HotkeyManager
from src.config_manager import ConfigManager
from src.tray_icon import TrayIcon
from src.ui import WindowCentererApp
from src.vk_codes import format_hotkey

kernel32 = ctypes.windll.kernel32
ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "WindowCenterer_SingleInstance_Mutex_Global"


def acquire_single_instance_mutex():
    """Ensure only one instance of the app runs at a time."""
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    
    mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    last_err = kernel32.GetLastError()
    if last_err == ERROR_ALREADY_EXISTS:
        # Another instance is already running
        # Try finding and showing the existing window
        hwnd = user32.FindWindowW(None, "Window Centerer")
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
        return None
    return mutex


def run_one_shot_cli(action: str):
    """Support headless/instant CLI triggering for Stream Deck, scripts, or shortcuts."""
    init_dpi_awareness()
    wm = WindowManager()
    if action == "center":
        res = wm.center_window()
        if res.get("success"):
            print(f"Successfully centered '{res.get('title')}' on {res.get('monitor')}.")
            sys.exit(0)
        else:
            print(f"Failed: {res.get('error')}", file=sys.stderr)
            sys.exit(1)
    elif action == "cycle":
        res = wm.cycle_monitor(direction=1)
        if res.get("success"):
            print(f"Successfully moved '{res.get('title')}' to {res.get('monitor')}.")
            sys.exit(0)
        else:
            print(f"Failed: {res.get('error')}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Window Centerer: Center any active window across any screen with shortcuts."
    )
    parser.add_argument("--minimized", action="store_true", help="Start minimized in system tray")
    parser.add_argument("--center", action="store_true", help="One-shot: Center active window immediately and exit")
    parser.add_argument("--cycle", action="store_true", help="One-shot: Cycle active window to next monitor and exit")
    args = parser.parse_args()

    # Handle one-shot CLI commands
    if args.center:
        run_one_shot_cli("center")
        return
    if args.cycle:
        run_one_shot_cli("cycle")
        return

    # Check Single Instance Mutex
    mutex = acquire_single_instance_mutex()
    if not mutex:
        print("Window Centerer is already running in the background/system tray.")
        sys.exit(0)

    # Initialize Core Systems
    init_dpi_awareness()
    cfg = ConfigManager()
    wm = WindowManager()
    hm = HotkeyManager()

    # Icon path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "assets", "icon.ico")

    # Global references for clean teardown
    tray: Optional[TrayIcon] = None
    app: Optional[WindowCentererApp] = None

    def cleanup_and_exit():
        nonlocal tray, app, mutex
        try:
            if tray:
                tray.stop()
            if hm:
                hm.stop()
            if mutex:
                kernel32.CloseHandle(mutex)
                mutex = None
            if app and app.root:
                app.root.quit()
                app.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    # Initialize Desktop GUI
    app = WindowCentererApp(
        config_manager=cfg,
        window_manager=wm,
        hotkey_manager=hm,
        on_exit_callback=cleanup_and_exit,
    )

    # Register Hotkeys in HotkeyManager
    for action_name in ["center_current", "cycle_next", "cycle_prev", "center_resize"]:
        hk = cfg.get_hotkey(action_name)
        if hk and hk.get("enabled", True):
            mods = hk.get("modifiers", [])
            key = hk.get("key", "")
            if mods and key:
                callback = app._get_callback_for_action(action_name)
                hm.register_hotkey(action_name, mods, key, callback)

    # Start Hotkey Manager Background Hook
    hm.start()

    # Setup System Tray Icon
    c_hk = cfg.get_hotkey("center_current")
    shortcut_tip = c_hk.get("display", "Ctrl + Alt + C") if c_hk else "Ctrl + Alt + C"

    tray = TrayIcon(
        tooltip=f"Window Centerer ({shortcut_tip})",
        icon_path=icon_path,
        on_show_window=lambda: app.root.after(0, app.show_from_tray),
        on_center_now=app.trigger_center_now,
        on_toggle_enabled=lambda enabled: hm.set_enabled(enabled),
        on_exit=lambda: app.root.after(0, cleanup_and_exit),
    )
    tray.start()

    # Handle Initial Window State
    start_minimized = args.minimized or cfg.get_system("start_minimized", False)
    if start_minimized:
        app.hide_to_tray()
    else:
        app.show_from_tray()

    try:
        app.root.mainloop()
    except KeyboardInterrupt:
        cleanup_and_exit()


if __name__ == "__main__":
    main()
