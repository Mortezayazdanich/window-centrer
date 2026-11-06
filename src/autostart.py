"""
Windows Auto-Start management.
Supports both Windows Startup Folder shortcut (.vbs script) and HKCU Registry Run key,
ensuring auto-start works across all Windows user permission levels.
"""

import os
import sys
import winreg

APP_NAME = "WindowCenterer"


def get_startup_folder_path() -> str:
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")


def get_startup_vbs_path() -> str:
    return os.path.join(get_startup_folder_path(), f"{APP_NAME}.vbs")


def is_autostart_enabled() -> bool:
    """Check if auto-start is configured via Startup folder or Registry."""
    # Check 1: Startup folder VBS
    vbs_path = get_startup_vbs_path()
    if os.path.exists(vbs_path):
        return True

    # Check 2: Registry Run key
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return bool(val)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def enable_autostart(main_py_path: str = None) -> bool:
    """
    Enable auto-start on Windows login.
    Creates a silent .vbs script in the Windows Startup folder.
    """
    if not main_py_path:
        main_py_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))

    # Determine pythonw executable (windowless python)
    python_dir = os.path.dirname(sys.executable)
    pythonw_exe = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable

    # Method 1: Create VBScript in Startup folder
    try:
        startup_dir = get_startup_folder_path()
        if os.path.exists(startup_dir):
            vbs_content = (
                'Set WshShell = CreateObject("WScript.Shell")\r\n'
                f'WshShell.Run """{pythonw_exe}"" ""{main_py_path}"" --minimized", 0, False\r\n'
                'Set WshShell = Nothing\r\n'
            )
            vbs_file = get_startup_vbs_path()
            with open(vbs_file, "w", encoding="ascii") as f:
                f.write(vbs_content)
            return True
    except Exception:
        pass

    # Method 2: Fallback to HKCU Registry Run
    try:
        cmd = f'"{pythonw_exe}" "{main_py_path}" --minimized'
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def disable_autostart() -> bool:
    """Disable auto-start on Windows login."""
    success = True

    # Remove Startup folder VBS
    vbs_path = get_startup_vbs_path()
    if os.path.exists(vbs_path):
        try:
            os.remove(vbs_path)
        except Exception:
            success = False

    # Remove Registry Run value
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass

    return success
