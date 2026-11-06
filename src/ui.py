"""
Modern Desktop GUI for Window Centerer.
Built with Tkinter and ttk with a sleek, polished dark theme,
real-time interactive hotkey recorder, monitor inspector, and tray integration.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import winsound
import threading
import time
import os
from typing import Callable, Optional, Dict, Any, List

from src.vk_codes import (
    vk_to_name,
    name_to_vk,
    format_hotkey,
    parse_hotkey,
    VK_SHIFT,
    VK_CONTROL,
    VK_MENU,
    VK_LWIN,
    VK_RWIN,
)
from src.window_manager import WindowManager, user32
from src.config_manager import ConfigManager
from src.hotkey_manager import HotkeyManager
from src.autostart import is_autostart_enabled, enable_autostart, disable_autostart


# Color Theme (Modern Zinc / Windows 11 Dark)
COLORS = {
    "bg": "#121214",
    "surface": "#1E1E24",
    "card": "#26262F",
    "card_border": "#3A3A48",
    "accent": "#2563EB",         # Windows Royal Blue
    "accent_hover": "#3B82F6",
    "accent_active": "#1D4ED8",
    "success": "#10B981",        # Emerald green
    "danger": "#EF4444",         # Red
    "warning": "#F59E0B",        # Amber
    "text": "#F3F4F6",           # White / Light gray
    "text_muted": "#9CA3AF",     # Muted gray
    "badge_bg": "#333342",
    "badge_text": "#E5E7EB",
    "input_bg": "#1E1E24",
    "recording_bg": "#7C2D12",   # Dark amber/orange when recording
    "recording_border": "#F97316",
}


class HotkeyRecorderRow:
    """A row in the UI for configuring a single shortcut with recording button."""

    def __init__(
        self,
        parent: tk.Widget,
        action_name: str,
        title: str,
        description: str,
        current_modifiers: List[str],
        current_key: str,
        on_change_callback: Callable[[str, List[str], str, str], None],
        on_reset_callback: Callable[[str], None],
        allow_toggle: bool = False,
        is_enabled: bool = True,
        on_toggle_callback: Optional[Callable[[str, bool], None]] = None,
    ):
        self.action_name = action_name
        self.title = title
        self.description = description
        self.modifiers = current_modifiers
        self.key = current_key
        self.on_change_callback = on_change_callback
        self.on_reset_callback = on_reset_callback
        self.allow_toggle = allow_toggle
        self.is_enabled = is_enabled
        self.on_toggle_callback = on_toggle_callback

        self.is_recording = False

        # Container Card Frame
        self.frame = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=16,
            pady=12,
        )

        # Left Column: Titles & Description
        left_box = tk.Frame(self.frame, bg=COLORS["card"])
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header_box = tk.Frame(left_box, bg=COLORS["card"])
        header_box.pack(anchor="w", fill=tk.X)

        if self.allow_toggle:
            self.enable_var = tk.BooleanVar(value=self.is_enabled)
            self.chk = tk.Checkbutton(
                header_box,
                variable=self.enable_var,
                command=self._on_toggle,
                bg=COLORS["card"],
                activebackground=COLORS["card"],
                selectcolor=COLORS["input_bg"],
                highlightthickness=0,
                bd=0,
            )
            self.chk.pack(side=tk.LEFT, padx=(0, 6))

        lbl_title = tk.Label(
            header_box,
            text=self.title,
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        lbl_title.pack(side=tk.LEFT, anchor="w")

        lbl_desc = tk.Label(
            left_box,
            text=self.description,
            font=("Segoe UI", 8),
            fg=COLORS["text_muted"],
            bg=COLORS["card"],
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # Right Column: Shortcut Badge & Record Button
        right_box = tk.Frame(self.frame, bg=COLORS["card"])
        right_box.pack(side=tk.RIGHT, fill=tk.Y)

        self.badge = tk.Label(
            right_box,
            text=self.get_display_text(),
            font=("Consolas", 10, "bold"),
            fg=COLORS["badge_text"],
            bg=COLORS["badge_bg"],
            padx=12,
            pady=4,
            relief=tk.FLAT,
        )
        self.badge.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_record = tk.Button(
            right_box,
            text="Change Shortcut",
            font=("Segoe UI", 8, "bold"),
            fg="#FFFFFF",
            bg=COLORS["accent"],
            activebackground=COLORS["accent_active"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            bd=0,
            command=self.start_recording,
        )
        self.btn_record.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_reset = tk.Button(
            right_box,
            text="Reset",
            font=("Segoe UI", 8),
            fg=COLORS["text_muted"],
            bg=COLORS["card_border"],
            activebackground=COLORS["badge_bg"],
            activeforeground=COLORS["text"],
            relief=tk.FLAT,
            padx=8,
            pady=4,
            cursor="hand2",
            bd=0,
            command=self._on_reset,
        )
        self.btn_reset.pack(side=tk.LEFT)

    def get_display_text(self) -> str:
        if not self.key:
            return "(None)"
        return format_hotkey(self.modifiers, self.key)

    def _on_toggle(self):
        new_val = self.enable_var.get()
        self.is_enabled = new_val
        if self.on_toggle_callback:
            self.on_toggle_callback(self.action_name, new_val)

    def _on_reset(self):
        self.on_reset_callback(self.action_name)

    def start_recording(self):
        if self.is_recording:
            self.stop_recording(cancelled=True)
            return

        self.is_recording = True
        self.btn_record.config(
            text="Press Keys... (Esc to cancel)",
            bg=COLORS["warning"],
            fg="#000000",
        )
        self.badge.config(
            text="Listening...",
            bg=COLORS["recording_bg"],
            fg="#FFA500",
        )

        top = self.frame.winfo_toplevel()
        top.bind("<KeyPress>", self._on_key_press)
        top.focus_set()

    def _detect_active_modifiers(self) -> List[str]:
        mods = []
        if (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0:
            mods.append("ctrl")
        if (user32.GetAsyncKeyState(VK_MENU) & 0x8000) != 0:
            mods.append("alt")
        if (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0:
            mods.append("shift")
        if (user32.GetAsyncKeyState(VK_LWIN) & 0x8000) != 0 or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000) != 0:
            mods.append("win")
        return mods

    def _on_key_press(self, event: tk.Event):
        if not self.is_recording:
            return

        vk = event.keycode

        # Cancel on Escape
        if vk == 0x1B:  # Escape
            self.stop_recording(cancelled=True)
            return "break"

        # Check if it's a modifier key
        if vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5):
            mods = self._detect_active_modifiers()
            display_preview = " + ".join([m.capitalize() for m in mods]) + " + ..."
            self.badge.config(text=display_preview)
            return "break"

        # Non-modifier key pressed -> finalize shortcut
        mods = self._detect_active_modifiers()
        key_name = vk_to_name(vk)

        self.modifiers = mods
        self.key = key_name
        display_str = format_hotkey(mods, key_name)

        self.stop_recording(cancelled=False)
        self.on_change_callback(self.action_name, mods, key_name, display_str)
        return "break"

    def stop_recording(self, cancelled: bool = False):
        self.is_recording = False
        top = self.frame.winfo_toplevel()
        top.unbind("<KeyPress>")

        self.btn_record.config(
            text="Change Shortcut",
            bg=COLORS["accent"],
            fg="#FFFFFF",
        )
        self.badge.config(
            text=self.get_display_text(),
            bg=COLORS["badge_bg"],
            fg=COLORS["badge_text"],
        )

    def update_values(self, modifiers: List[str], key: str):
        self.modifiers = modifiers
        self.key = key
        self.badge.config(text=self.get_display_text())


class WindowCentererApp:
    """Main Application GUI."""

    def __init__(
        self,
        config_manager: ConfigManager,
        window_manager: WindowManager,
        hotkey_manager: HotkeyManager,
        on_exit_callback: Optional[Callable[[], None]] = None,
    ):
        self.cfg = config_manager
        self.wm = window_manager
        self.hm = hotkey_manager
        self.on_exit_callback = on_exit_callback

        self.root = tk.Tk()
        self.root.title("Window Centerer")
        self.root.geometry("680x640")
        self.root.minsize(580, 520)
        self.root.configure(bg=COLORS["bg"])

        # Try setting window icon
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"))
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Handle close button (minimize to tray if configured)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        self._hotkey_rows: Dict[str, HotkeyRecorderRow] = {}

        self._build_ui()
        self.refresh_monitors_list()

    def _build_ui(self):
        # 1. Header Bar
        header = tk.Frame(self.root, bg=COLORS["surface"], padx=20, pady=16)
        header.pack(fill=tk.X)

        title_box = tk.Frame(header, bg=COLORS["surface"])
        title_box.pack(side=tk.LEFT)

        lbl_app_name = tk.Label(
            title_box,
            text="🎯 Window Centerer",
            font=("Segoe UI", 16, "bold"),
            fg=COLORS["text"],
            bg=COLORS["surface"],
        )
        lbl_app_name.pack(anchor="w")

        lbl_app_sub = tk.Label(
            title_box,
            text="Center foreground windows instantly across any screen with global hotkeys",
            font=("Segoe UI", 9),
            fg=COLORS["text_muted"],
            bg=COLORS["surface"],
        )
        lbl_app_sub.pack(anchor="w", pady=(2, 0))

        # Status & Manual Trigger on Right
        actions_box = tk.Frame(header, bg=COLORS["surface"])
        actions_box.pack(side=tk.RIGHT)

        self.lbl_status = tk.Label(
            actions_box,
            text="🟢 Active",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS["success"],
            bg=COLORS["surface"],
            padx=8,
            pady=4,
        )
        self.lbl_status.pack(side=tk.LEFT, padx=(0, 10))

        btn_test = tk.Button(
            actions_box,
            text="🎯 Center Active Window Now",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg=COLORS["accent"],
            activebackground=COLORS["accent_active"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            bd=0,
            command=self.trigger_center_now,
        )
        btn_test.pack(side=tk.LEFT)

        # 2. Main Tabbed or Scrollable Content
        notebook_frame = tk.Frame(self.root, bg=COLORS["bg"], padx=18, pady=12)
        notebook_frame.pack(fill=tk.BOTH, expand=True)

        # Custom Tab Buttons Header
        tabs_header = tk.Frame(notebook_frame, bg=COLORS["bg"])
        tabs_header.pack(fill=tk.X, pady=(0, 10))

        self.tab_buttons: Dict[str, tk.Button] = {}
        self.tab_frames: Dict[str, tk.Frame] = {}

        tabs = [
            ("shortcuts", "⌨️ Shortcuts"),
            ("monitors", "🖥️ Displays & Layout"),
            ("behavior", "⚙️ Options & Startup"),
        ]

        for tab_id, tab_label in tabs:
            btn = tk.Button(
                tabs_header,
                text=tab_label,
                font=("Segoe UI", 10, "bold"),
                fg=COLORS["text_muted"],
                bg=COLORS["surface"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["text"],
                relief=tk.FLAT,
                bd=0,
                padx=16,
                pady=8,
                cursor="hand2",
                command=lambda tid=tab_id: self.switch_tab(tid),
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self.tab_buttons[tab_id] = btn

            # Body Frame
            frame = tk.Frame(notebook_frame, bg=COLORS["bg"])
            self.tab_frames[tab_id] = frame

        # Populate Tab 1: Shortcuts
        self._build_shortcuts_tab(self.tab_frames["shortcuts"])

        # Populate Tab 2: Monitors
        self._build_monitors_tab(self.tab_frames["monitors"])

        # Populate Tab 3: Behavior & Preferences
        self._build_behavior_tab(self.tab_frames["behavior"])

        # Activate First Tab
        self.switch_tab("shortcuts")

        # 3. Footer Bar
        footer = tk.Frame(self.root, bg=COLORS["surface"], padx=18, pady=10)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_feedback = tk.Label(
            footer,
            text="Ready. Press your configured shortcut anytime to center the active window.",
            font=("Segoe UI", 8),
            fg=COLORS["text_muted"],
            bg=COLORS["surface"],
        )
        self.lbl_feedback.pack(side=tk.LEFT)

        btn_min = tk.Button(
            footer,
            text="Hide to Tray",
            font=("Segoe UI", 8),
            fg=COLORS["text"],
            bg=COLORS["card_border"],
            activebackground=COLORS["badge_bg"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.hide_to_tray,
        )
        btn_min.pack(side=tk.RIGHT, padx=(8, 0))

        btn_exit = tk.Button(
            footer,
            text="Exit App",
            font=("Segoe UI", 8),
            fg=COLORS["danger"],
            bg=COLORS["card_border"],
            activebackground=COLORS["danger"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.exit_application,
        )
        btn_exit.pack(side=tk.RIGHT)

    def switch_tab(self, tab_id: str):
        for tid, frame in self.tab_frames.items():
            if tid == tab_id:
                frame.pack(fill=tk.BOTH, expand=True)
                self.tab_buttons[tid].config(
                    bg=COLORS["accent"],
                    fg="#FFFFFF",
                )
            else:
                frame.pack_forget()
                self.tab_buttons[tid].config(
                    bg=COLORS["surface"],
                    fg=COLORS["text_muted"],
                )

    def _build_shortcuts_tab(self, parent: tk.Frame):
        lbl_info = tk.Label(
            parent,
            text="Click 'Change Shortcut' on any action below, then press your desired key combination.",
            font=("Segoe UI", 9),
            fg=COLORS["text_muted"],
            bg=COLORS["bg"],
        )
        lbl_info.pack(anchor="w", pady=(0, 10))

        # 1. Center on Current Screen
        c_hotkey = self.cfg.get_hotkey("center_current")
        row_center = HotkeyRecorderRow(
            parent=parent,
            action_name="center_current",
            title="Center on Current Screen",
            description="Centers the active window inside the screen it currently resides on.",
            current_modifiers=c_hotkey.get("modifiers", ["ctrl", "alt"]),
            current_key=c_hotkey.get("key", "C"),
            on_change_callback=self.on_hotkey_changed,
            on_reset_callback=self.on_hotkey_reset,
        )
        row_center.frame.pack(fill=tk.X, pady=(0, 8))
        self._hotkey_rows["center_current"] = row_center

        # 2. Cycle to Next Screen
        next_hotkey = self.cfg.get_hotkey("cycle_next")
        row_next = HotkeyRecorderRow(
            parent=parent,
            action_name="cycle_next",
            title="Move to Next Screen & Center",
            description="Moves the active window to the next monitor in sequence and centers it.",
            current_modifiers=next_hotkey.get("modifiers", ["ctrl", "alt"]),
            current_key=next_hotkey.get("key", "Right"),
            on_change_callback=self.on_hotkey_changed,
            on_reset_callback=self.on_hotkey_reset,
            allow_toggle=True,
            is_enabled=next_hotkey.get("enabled", True),
            on_toggle_callback=self.on_hotkey_toggle,
        )
        row_next.frame.pack(fill=tk.X, pady=(0, 8))
        self._hotkey_rows["cycle_next"] = row_next

        # 3. Cycle to Previous Screen
        prev_hotkey = self.cfg.get_hotkey("cycle_prev")
        row_prev = HotkeyRecorderRow(
            parent=parent,
            action_name="cycle_prev",
            title="Move to Previous Screen & Center",
            description="Moves the active window to the previous monitor and centers it.",
            current_modifiers=prev_hotkey.get("modifiers", ["ctrl", "alt"]),
            current_key=prev_hotkey.get("key", "Left"),
            on_change_callback=self.on_hotkey_changed,
            on_reset_callback=self.on_hotkey_reset,
            allow_toggle=True,
            is_enabled=prev_hotkey.get("enabled", True),
            on_toggle_callback=self.on_hotkey_toggle,
        )
        row_prev.frame.pack(fill=tk.X, pady=(0, 8))
        self._hotkey_rows["cycle_prev"] = row_prev

        # 4. Center & Resize Window
        resize_hotkey = self.cfg.get_hotkey("center_resize")
        row_resize = HotkeyRecorderRow(
            parent=parent,
            action_name="center_resize",
            title="Center & Resize Window (e.g. 75%)",
            description="Resizes the window to a percentage of the screen and centers it.",
            current_modifiers=resize_hotkey.get("modifiers", ["ctrl", "alt"]),
            current_key=resize_hotkey.get("key", "R"),
            on_change_callback=self.on_hotkey_changed,
            on_reset_callback=self.on_hotkey_reset,
            allow_toggle=True,
            is_enabled=resize_hotkey.get("enabled", False),
            on_toggle_callback=self.on_hotkey_toggle,
        )
        row_resize.frame.pack(fill=tk.X, pady=(0, 8))
        self._hotkey_rows["center_resize"] = row_resize

    def _build_monitors_tab(self, parent: tk.Frame):
        top_bar = tk.Frame(parent, bg=COLORS["bg"])
        top_bar.pack(fill=tk.X, pady=(0, 10))

        lbl_info = tk.Label(
            top_bar,
            text="Detected displays on this computer. Coordinates exclude taskbar docks.",
            font=("Segoe UI", 9),
            fg=COLORS["text_muted"],
            bg=COLORS["bg"],
        )
        lbl_info.pack(side=tk.LEFT)

        btn_refresh = tk.Button(
            top_bar,
            text="🔄 Refresh",
            font=("Segoe UI", 8, "bold"),
            fg=COLORS["text"],
            bg=COLORS["surface"],
            activebackground=COLORS["card_border"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.refresh_monitors_list,
        )
        btn_refresh.pack(side=tk.RIGHT)

        self.monitors_container = tk.Frame(parent, bg=COLORS["bg"])
        self.monitors_container.pack(fill=tk.BOTH, expand=True)

    def _build_behavior_tab(self, parent: tk.Frame):
        # Card 1: Centering Behavior
        card_beh = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        card_beh.pack(fill=tk.X, pady=(0, 10))

        lbl_sec1 = tk.Label(
            card_beh,
            text="Centering Behavior",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        lbl_sec1.pack(anchor="w", pady=(0, 8))

        # Auto-restore maximized windows
        self.var_auto_restore = tk.BooleanVar(
            value=self.cfg.get_behavior("auto_restore_maximized", True)
        )
        chk_restore = tk.Checkbutton(
            card_beh,
            text="Auto-restore maximized windows before centering (recommended)",
            variable=self.var_auto_restore,
            command=self._on_behavior_changed,
            font=("Segoe UI", 9),
            fg=COLORS["text"],
            bg=COLORS["card"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["input_bg"],
            bd=0,
        )
        chk_restore.pack(anchor="w", pady=2)

        # Auto-shrink oversized windows
        self.var_auto_shrink = tk.BooleanVar(
            value=self.cfg.get_behavior("auto_shrink_oversized", True)
        )
        chk_shrink = tk.Checkbutton(
            card_beh,
            text="Auto-shrink windows that exceed the monitor's work area",
            variable=self.var_auto_shrink,
            command=self._on_behavior_changed,
            font=("Segoe UI", 9),
            fg=COLORS["text"],
            bg=COLORS["card"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["input_bg"],
            bd=0,
        )
        chk_shrink.pack(anchor="w", pady=2)

        # Sound chime on center
        self.var_sound = tk.BooleanVar(
            value=self.cfg.get_behavior("play_sound", True)
        )
        chk_sound = tk.Checkbutton(
            card_beh,
            text="Play subtle audio chime when centering window",
            variable=self.var_sound,
            command=self._on_behavior_changed,
            font=("Segoe UI", 9),
            fg=COLORS["text"],
            bg=COLORS["card"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["input_bg"],
            bd=0,
        )
        chk_sound.pack(anchor="w", pady=2)

        # Card 2: System Integration
        card_sys = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        card_sys.pack(fill=tk.X, pady=(0, 10))

        lbl_sec2 = tk.Label(
            card_sys,
            text="System & Startup",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        lbl_sec2.pack(anchor="w", pady=(0, 8))

        # Start with Windows
        self.var_autostart = tk.BooleanVar(value=is_autostart_enabled())
        chk_autostart = tk.Checkbutton(
            card_sys,
            text="Start Window Centerer automatically with Windows",
            variable=self.var_autostart,
            command=self._on_autostart_toggled,
            font=("Segoe UI", 9),
            fg=COLORS["text"],
            bg=COLORS["card"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["input_bg"],
            bd=0,
        )
        chk_autostart.pack(anchor="w", pady=2)

        # Minimize to Tray on Close
        self.var_min_on_close = tk.BooleanVar(
            value=self.cfg.get_system("minimize_to_tray_on_close", True)
        )
        chk_min_close = tk.Checkbutton(
            card_sys,
            text="Minimize to system notification tray when clicking close (X)",
            variable=self.var_min_on_close,
            command=self._on_system_changed,
            font=("Segoe UI", 9),
            fg=COLORS["text"],
            bg=COLORS["card"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["input_bg"],
            bd=0,
        )
        chk_min_close.pack(anchor="w", pady=2)

    def refresh_monitors_list(self):
        # Clear existing
        for widget in self.monitors_container.winfo_children():
            widget.destroy()

        monitors = self.wm.get_all_monitors()
        if not monitors:
            lbl_none = tk.Label(
                self.monitors_container,
                text="No active monitors detected.",
                font=("Segoe UI", 10),
                fg=COLORS["text_muted"],
                bg=COLORS["bg"],
            )
            lbl_none.pack(pady=20)
            return

        for idx, mon in enumerate(monitors):
            card = tk.Frame(
                self.monitors_container,
                bg=COLORS["card"],
                highlightbackground=COLORS["card_border"],
                highlightthickness=1,
                padx=16,
                pady=10,
            )
            card.pack(fill=tk.X, pady=(0, 6))

            left = tk.Frame(card, bg=COLORS["card"])
            left.pack(side=tk.LEFT)

            tag = " ⭐ PRIMARY DISPLAY" if mon["primary"] else ""
            lbl_title = tk.Label(
                left,
                text=f"Screen {idx + 1}: {mon['device']}{tag}",
                font=("Segoe UI", 10, "bold"),
                fg=COLORS["text"],
                bg=COLORS["card"],
            )
            lbl_title.pack(anchor="w")

            m_rect = mon["monitor_rect"]
            w_rect = mon["work_rect"]
            lbl_res = tk.Label(
                left,
                text=f"Full Resolution: {m_rect.width}x{m_rect.height} | Usable Work Area: {w_rect.width}x{w_rect.height} at ({w_rect.left}, {w_rect.top})",
                font=("Segoe UI", 8),
                fg=COLORS["text_muted"],
                bg=COLORS["card"],
            )
            lbl_res.pack(anchor="w", pady=(2, 0))

            btn_center_this = tk.Button(
                card,
                text=f"Center Here",
                font=("Segoe UI", 8, "bold"),
                fg="#FFFFFF",
                bg=COLORS["accent"],
                activebackground=COLORS["accent_active"],
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                bd=0,
                padx=10,
                pady=4,
                cursor="hand2",
                command=lambda m=mon: self._test_center_on_screen(m),
            )
            btn_center_this.pack(side=tk.RIGHT)

    def _test_center_on_screen(self, mon: Dict[str, Any]):
        """Center the active window on a specific monitor."""
        # Yield focus to last active window
        self.root.iconify()
        time.sleep(0.1)
        res = self.wm.center_window(target_monitor=mon)
        self.root.deiconify()
        self.root.lift()
        if res.get("success"):
            self.set_feedback(f"Centered '{res.get('title')}' on {mon.get('device')}")
        else:
            self.set_feedback(f"Note: {res.get('error')}", is_error=True)

    def on_hotkey_changed(self, action: str, modifiers: List[str], key: str, display: str):
        self.cfg.set_hotkey(action, modifiers, key, display, enabled=True)
        # Update hotkey manager
        callback = self._get_callback_for_action(action)
        self.hm.register_hotkey(action, modifiers, key, callback)
        self.set_feedback(f"Updated shortcut for '{action}' to {display}")

    def on_hotkey_toggle(self, action: str, enabled: bool):
        hk = self.cfg.get_hotkey(action)
        self.cfg.set_hotkey(
            action,
            hk.get("modifiers", []),
            hk.get("key", ""),
            hk.get("display", ""),
            enabled=enabled
        )
        if enabled:
            callback = self._get_callback_for_action(action)
            self.hm.register_hotkey(action, hk.get("modifiers", []), hk.get("key", ""), callback)
            self.set_feedback(f"Enabled '{action}' shortcut")
        else:
            self.hm.unregister_hotkey(action)
            self.set_feedback(f"Disabled '{action}' shortcut")

    def on_hotkey_reset(self, action: str):
        defaults = {
            "center_current": (["ctrl", "alt"], "C", "Ctrl + Alt + C"),
            "cycle_next": (["ctrl", "alt"], "Right", "Ctrl + Alt + Right"),
            "cycle_prev": (["ctrl", "alt"], "Left", "Ctrl + Alt + Left"),
            "center_resize": (["ctrl", "alt"], "R", "Ctrl + Alt + R"),
        }
        if action in defaults:
            mods, key, disp = defaults[action]
            self.on_hotkey_changed(action, mods, key, disp)
            if action in self._hotkey_rows:
                self._hotkey_rows[action].update_values(mods, key)

    def _get_callback_for_action(self, action: str) -> Callable[[], None]:
        if action == "center_current":
            return self.trigger_center_now
        elif action == "cycle_next":
            return lambda: self.trigger_cycle_monitor(+1)
        elif action == "cycle_prev":
            return lambda: self.trigger_cycle_monitor(-1)
        elif action == "center_resize":
            return self.trigger_center_resize
        return lambda: None

    def trigger_center_now(self):
        """Action handler to center active window."""
        auto_restore = self.cfg.get_behavior("auto_restore_maximized", True)
        auto_shrink = self.cfg.get_behavior("auto_shrink_oversized", True)

        res = self.wm.center_window(
            auto_restore_maximized=auto_restore,
            auto_shrink_oversized=auto_shrink
        )

        if res.get("success"):
            if self.cfg.get_behavior("play_sound", True):
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except Exception:
                    pass
            self.set_feedback(f"Centered: '{res.get('title')}' on {res.get('monitor')}")
        else:
            self.set_feedback(res.get("error", "Failed to center"), is_error=True)

    def trigger_cycle_monitor(self, direction: int = 1):
        """Action handler to cycle active window to next/prev monitor."""
        auto_restore = self.cfg.get_behavior("auto_restore_maximized", True)
        auto_shrink = self.cfg.get_behavior("auto_shrink_oversized", True)

        res = self.wm.cycle_monitor(
            direction=direction,
            auto_restore_maximized=auto_restore,
            auto_shrink_oversized=auto_shrink
        )

        if res.get("success"):
            if self.cfg.get_behavior("play_sound", True):
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except Exception:
                    pass
            self.set_feedback(f"Moved: '{res.get('title')}' to {res.get('monitor')}")
        else:
            self.set_feedback(res.get("error", "Failed to move monitor"), is_error=True)

    def trigger_center_resize(self):
        """Action handler to center and resize window."""
        factor = float(self.cfg.get_behavior("resize_factor", 0.75))
        auto_restore = self.cfg.get_behavior("auto_restore_maximized", True)

        res = self.wm.center_window(
            auto_restore_maximized=auto_restore,
            resize_factor=factor
        )

        if res.get("success"):
            if self.cfg.get_behavior("play_sound", True):
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except Exception:
                    pass
            self.set_feedback(f"Centered & Resized ({int(factor*100)}%): '{res.get('title')}'")
        else:
            self.set_feedback(res.get("error", "Failed to center and resize"), is_error=True)

    def _on_behavior_changed(self):
        self.cfg.set_behavior("auto_restore_maximized", self.var_auto_restore.get())
        self.cfg.set_behavior("auto_shrink_oversized", self.var_auto_shrink.get())
        self.cfg.set_behavior("play_sound", self.var_sound.get())
        self.set_feedback("Behavior options saved.")

    def _on_system_changed(self):
        self.cfg.set_system("minimize_to_tray_on_close", self.var_min_on_close.get())
        self.set_feedback("System settings saved.")

    def _on_autostart_toggled(self):
        enabled = self.var_autostart.get()
        if enabled:
            ok = enable_autostart()
            if ok:
                self.cfg.set_system("start_with_windows", True)
                self.set_feedback("Auto-start with Windows enabled.")
            else:
                self.var_autostart.set(False)
                self.set_feedback("Failed to configure auto-start.", is_error=True)
        else:
            disable_autostart()
            self.cfg.set_system("start_with_windows", False)
            self.set_feedback("Auto-start with Windows disabled.")

    def set_feedback(self, text: str, is_error: bool = False):
        color = COLORS["danger"] if is_error else COLORS["text"]
        self.root.after(0, lambda: self.lbl_feedback.config(text=text, fg=color))

    def on_window_close(self):
        if self.cfg.get_system("minimize_to_tray_on_close", True):
            self.hide_to_tray()
        else:
            self.exit_application()

    def hide_to_tray(self):
        self.root.withdraw()

    def show_from_tray(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def exit_application(self):
        if self.on_exit_callback:
            self.on_exit_callback()
        else:
            self.root.quit()
            self.root.destroy()
