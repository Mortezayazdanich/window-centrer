# 🎯 Window Centerer for Windows

> A lightweight, zero-dependency Windows desktop application that centers active/foreground windows on any screen with customizable global keyboard shortcuts.

---

## ✨ Features

- **Any Screen, Any Layout**: Automatically detects the exact monitor the active window is currently on, whether in a single-display, dual-display, triple-monitor, ultrawide, vertical, or mixed-DPI configuration.
- **Pixel-Perfect Alignment (DWM Extended Frame Bounds)**: Accurately compensates for Windows 10 & Windows 11 invisible window resize drop-shadow borders (7-8px margins) so windows are centered down to the exact pixel.
- **Work Area Aware**: Centers within the usable screen area, correctly avoiding taskbars docked at the bottom, top, left, or right, as well as secondary taskbars.
- **Customizable Global Hotkeys**:
  - Interactive **Hotkey Recorder** in the settings dashboard: click **Change Shortcut**, press your keys (e.g., `Ctrl + Alt + C`, `Win + Alt + C`, `F12`), and it saves instantly.
  - Intercepts keystrokes across all applications using low-level Win32 hooks with zero lag.
- **Multi-Monitor Superpowers**:
  - `Center on Current Screen` (Default: <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>C</kbd>)
  - `Move to Next Screen & Center` (Default: <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>Right</kbd>)
  - `Move to Previous Screen & Center` (Default: <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>Left</kbd>)
  - `Center & Resize Window (e.g. 75% of screen)` (Default: <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>R</kbd>)
- **Smart Window Handling**:
  - **Auto-Restore Maximized**: Windows does not normally move maximized windows; Window Centerer smoothly un-maximizes and centers them.
  - **Auto-Shrink Oversized**: Automatically resizes windows that exceed the display boundaries.
  - **Shell Safety Filter**: Automatically ignores the taskbar, desktop background (`Progman`/`WorkerW`), and start menus.
- **System Tray Integration**:
  - Minimizes silently to the Windows notification area (System Tray).
  - Native right-click context menu: quick trigger, pause/resume hotkeys, settings dashboard, and exit.
  - Hover tooltip displaying current hotkey and status.
  - Optional subtle sound chime feedback upon centering.
- **Windows Startup**: Optional 1-click toggle to automatically start silently in the background on login.
- **CLI / Stream Deck Support**: Run `python main.py --center` or `python main.py --cycle` to trigger centering from scripts, macros, or external hardware!
- **Zero Third-Party Dependencies**: Built exclusively with Python standard libraries (`ctypes`, `tkinter`, `json`, `winsound`).

---

## 🚀 Quick Start

### 1. Run Directly

Double-click either launcher in the folder:

- **`WindowCenterer.vbs`** *(Recommended)*: Runs silently in the background without popping up any command prompt window.
- **`WindowCenterer.bat`**: Standard batch launcher.

Or from PowerShell / Command Prompt:

```powershell
pythonw main.py
```

### 2. How to Use

1. Click into any application window you want to center (browser, text editor, file explorer, etc.).
2. Press <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>C</kbd>.
3. The window instantly snaps to the center of the screen it's currently on!

---

## ⌨️ Changing the Shortcut

1. Open the **Window Centerer** dashboard (double-click the tray icon or run the app).
2. Go to the **⌨️ Shortcuts** tab.
3. Click the **Change Shortcut** button next to *Center on Current Screen*.
4. Press the key combination you want to use (for example: `Ctrl + Shift + Space` or `Win + Alt + C` or `F11`).
5. The shortcut is updated and active immediately!
6. Click **Reset** at any time to revert back to default (`Ctrl + Alt + C`).

---

## 🖥️ Multi-Monitor Features

If you use multiple displays:

| Action | Default Shortcut | Description |
| :--- | :--- | :--- |
| **Center on Current Screen** | <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>C</kbd> | Centers window within its current screen. |
| **Move to Next Screen & Center** | <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>Right</kbd> | Moves window to the next monitor in sequence and centers it. |
| **Move to Previous Screen & Center**| <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>Left</kbd> | Moves window to the previous monitor in sequence and centers it. |
| **Center & Resize** | <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>R</kbd> | Resizes window to 75% of monitor and centers it. |

Open the **🖥️ Displays & Layout** tab to view all connected screens, their resolutions, work areas (excluding taskbars), and test centering directly on each screen.

---

## ⚙️ Configuration & Options

In the **⚙️ Options & Startup** tab:

- **Auto-restore maximized windows**: Restores maximized windows before centering.
- **Auto-shrink oversized windows**: Constrains windows that exceed monitor dimensions.
- **Play subtle audio chime**: Provides instant audible feedback when centering.
- **Start Window Centerer automatically with Windows**: Adds a silent startup entry to start in the system tray upon login.
- **Minimize to system notification tray when clicking close (X)**: Keeps the hotkey listener active while hiding the main window.

Settings are stored in `%APPDATA%\WindowCenterer\config.json`.

---

## 🛠️ Project Structure

```text
window-centring-tool/
├── assets/
│   └── icon.ico               # Multi-resolution 32-bit RGBA app icon
├── src/
│   ├── __init__.py
│   ├── autostart.py           # Windows Startup folder & registry manager
│   ├── config_manager.py      # JSON settings persistence & migration
│   ├── hotkey_manager.py      # Win32 WH_KEYBOARD_LL global hook thread
│   ├── tray_icon.py           # Native Win32 Shell_NotifyIconW & context menu
│   ├── ui.py                  # Tkinter modern dark theme dashboard & recorder
│   ├── vk_codes.py            # Win32 virtual key codes mapping & parser
│   └── window_manager.py      # DPI-aware Win32 DWM bounds, monitors & centering
├── tests/
│   ├── test_config_manager.py # Config unit tests
│   ├── test_hotkey_manager.py # Hotkey binding & matching unit tests
│   ├── test_vk_codes.py       # VK code mapping & formatting unit tests
│   └── test_window_geometry.py# Centering math & multi-monitor tests
├── build_exe.py               # Optional PyInstaller standalone .exe builder
├── main.py                    # Main application entry point & CLI handler
├── WindowCenterer.bat         # Batch launcher
├── WindowCenterer.vbs         # Silent background launcher
└── README.md                  # Documentation
```

---

## 🧪 Running Automated Tests

To run the automated test suite:

```powershell
python -m unittest discover tests
```

---

## 📦 Building a Standalone Executable (.exe)

If you'd like to bundle the application into a single `.exe` that runs without requiring Python to be visible:

```powershell
pip install pyinstaller
python build_exe.py
```

The resulting `WindowCenterer.exe` will be located in the `dist/` directory.
