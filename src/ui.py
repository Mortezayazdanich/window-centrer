"""
Windows 11 Settings Desktop GUI for Window Centerer.
Pure standard-library implementation (Tkinter + ctypes) matching 100% of the
Windows 11 Settings (Fluent 2 / WinUI 3) design system:
- Immersive DWM dark mode, Mica backdrop, caption color matching (#1F1F1F), rounded window corners.
- Left Navigation Rail with search ("Find a setting"), app banner, and active selection pill indicators.
- Responsive right content pane with strictly locked horizontal bounds and smooth vertical scrolling.
- Right-anchored controls (keycaps, change/reset buttons, WinUI toggle switches) guaranteed 100% visible.
- Dynamic description text wrapping so rows adapt cleanly to any DPI scale or window resize.
- Individual Keyboard Keycap Badges ([Ctrl] + [Alt] + [C]).
- Interactive Display Layout Arranger mirroring Windows 11 System > Display.
- Segmented Scale Pills (50%, 67%, 75%, 80%, 90%) for window resize factor.
- WinUI 3 pill Toggle Switches.
- Native Segoe Fluent Icons and Segoe UI Variable typography.
- Zero external dependencies.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
import winsound
import threading
import time
import os
import ctypes
from ctypes import wintypes
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

# Authentic Windows 11 Settings Dark Mode Palette
COLORS = {
    "bg": "#1F1F1F",                  # Windows 11 Settings background (Mica base)
    "sidebar_bg": "#181818",          # Left navigation pane surface
    "sidebar_hover": "#242424",       # Nav item hover
    "sidebar_active": "#2B2B2B",      # Selected nav item background
    "search_bg": "#242424",           # Search input background
    "search_border": "#363636",       # Search input border
    "hero_bg": "#262626",             # Hero card background
    "hero_border": "#363636",         # Hero card 1px border
    "card": "#2B2B2B",                # Elevated Card background
    "card_hover": "#303030",          # Card row hover highlight
    "card_border": "#363636",         # 1px card outline
    "divider": "#353535",             # Inner card horizontal divider
    "icon_box_bg": "#333333",         # Icon slot background
    "accent": "#0078D4",              # Windows 11 Accent Blue
    "accent_hover": "#1E88E5",        # Accent hover
    "accent_active": "#0067C6",       # Accent pressed
    "text": "#FFFFFF",                # Primary high-contrast text
    "text_muted": "#A0A0A0",          # Secondary description text
    "text_dim": "#707070",            # Breadcrumb / tertiary text
    "keycap_bg": "#1E1E1E",           # Keycap pill background
    "keycap_border": "#484848",       # Keycap subtle border
    "keycap_text": "#FFFFFF",         # Keycap character text
    "keycap_sep": "#7C7C7C",          # "+" symbol between keycaps
    "success": "#6CCB5F",             # Windows 11 Green
    "danger": "#FF6B6B",              # Error / Red
    "warning": "#FFB900",             # Windows 11 Amber / Gold
    "switch_off": "#383838",          # Toggle track off
    "switch_border_off": "#686868",   # Toggle border off
    "infobar_bg": "#242424",          # Footer info bar
}

# Authentic Segoe Fluent Icon Glyphs (Windows 11 Built-in Font)
ICONS = {
    "search": "\uE721",
    "keyboard": "\uE765",
    "display": "\uE7F4",
    "snap": "\uE74C",                 # Windows 11 official Snap / Multitasking glyph
    "system": "\uE713",               # Settings gear
    "about": "\uE946",                # Info circle
    "refresh": "\uE72C",
    "check": "\uE73E",
    "sound": "\uE767",                # Speaker / Volume
    "restore": "\uE923",              # Restore window
    "shrink": "\uE740",               # Resize / Fit
    "next": "\uE72A",                 # Chevron right / forward
    "prev": "\uE72B",                 # Chevron left / back
    "resize": "\uE740",
    "star": "\uE734",
    "autostart": "\uE777",            # Power / Startup
    "tray": "\uE819",                 # Notification / Taskbar tray
    "window": "\uE737",               # Single application window
}


def apply_dwm_styling(root: tk.Tk):
    """Apply native Windows 11 DWM (Desktop Window Manager) attributes."""
    root.update_idletasks()
    try:
        hwnd = user32.GetParent(root.winfo_id())
        if not hwnd:
            wm_frame = root.wm_frame()
            if wm_frame:
                hwnd = int(wm_frame, 16)
        if not hwnd:
            hwnd = root.winfo_id()

        dwmapi = ctypes.windll.dwmapi

        # 1. Immersive Dark Mode (DWMWA_USE_IMMERSIVE_DARK_MODE = 20)
        dark = ctypes.c_int(2)
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))

        # 2. Window Corner Rounding (DWMWA_WINDOW_CORNER_PREFERENCE = 33 -> DWMWCP_ROUND = 2)
        corners = ctypes.c_int(2)
        dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corners), ctypes.sizeof(corners))

        # 3. Caption Color (DWMWA_CAPTION_COLOR = 35 -> 0x001F1F1F in 0x00BBGGRR format)
        caption = ctypes.c_int(0x001F1F1F)
        dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))

        # 4. Text Color (DWMWA_TEXT_COLOR = 36 -> White)
        text_color = ctypes.c_int(0x00FFFFFF)
        dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))

        # 5. System Backdrop Mica (DWMWA_SYSTEMBACKDROP_TYPE = 38 -> 2 = Mica)
        backdrop = ctypes.c_int(2)
        dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop))
    except Exception:
        pass


class WinUIToggle(tk.Canvas):
    """Authentic Windows 11 pill toggle switch (WinUI 3 ToggleSwitch)."""

    def __init__(
        self,
        parent: tk.Widget,
        is_on: bool = False,
        command: Optional[Callable[[bool], None]] = None,
        bg: str = COLORS["card"],
        accent: str = COLORS["accent"],
    ):
        super().__init__(
            parent,
            width=44,
            height=22,
            bg=bg,
            highlightthickness=0,
            cursor="hand2",
        )
        self.is_on = is_on
        self.command = command
        self.bg_color = bg
        self.accent_color = accent

        self.bind("<Button-1>", self._on_click)
        self.draw()

    def set(self, value: bool):
        self.is_on = bool(value)
        self.draw()

    def get(self) -> bool:
        return self.is_on

    def draw(self):
        self.delete("all")
        if self.is_on:
            fill_track = self.accent_color
            border_track = self.accent_color
            thumb_x0, thumb_x1 = 25, 39
        else:
            fill_track = COLORS["switch_off"]
            border_track = COLORS["switch_border_off"]
            thumb_x0, thumb_x1 = 5, 19

        # Draw smooth pill track (caps + rectangle)
        self.create_oval(1, 1, 21, 21, fill=fill_track, outline=border_track, width=1)
        self.create_oval(23, 1, 43, 21, fill=fill_track, outline=border_track, width=1)
        self.create_rectangle(11, 1, 33, 21, fill=fill_track, outline=border_track, width=1)
        # Cover inner seams
        self.create_rectangle(11, 2, 33, 20, fill=fill_track, outline=fill_track)
        # White circular thumb
        self.create_oval(thumb_x0, 4, thumb_x1, 18, fill="#FFFFFF", outline="#FFFFFF")

    def _on_click(self, event=None):
        self.is_on = not self.is_on
        self.draw()
        if self.command:
            self.command(self.is_on)


def render_keycaps(parent: tk.Widget, shortcut_str: str, font_body: str, bg_color: str) -> tk.Frame:
    """
    Renders shortcuts as authentic individual Windows 11 keycaps:
    [ Ctrl ]  +  [ Alt ]  +  [ C ]
    """
    container = tk.Frame(parent, bg=bg_color)
    if not shortcut_str or shortcut_str == "(None)":
        lbl = tk.Label(
            container,
            text="(Disabled)",
            font=(font_body, 8, "italic"),
            fg=COLORS["text_dim"],
            bg=bg_color,
        )
        lbl.pack(side=tk.LEFT)
        return container

    parts = [p.strip() for p in shortcut_str.split("+")]
    for idx, part in enumerate(parts):
        key_box = tk.Frame(
            container,
            bg=COLORS["keycap_bg"],
            highlightbackground=COLORS["keycap_border"],
            highlightthickness=1,
            padx=7,
            pady=2,
        )
        key_box.pack(side=tk.LEFT)

        lbl = tk.Label(
            key_box,
            text=part,
            font=(font_body, 8, "bold"),
            fg=COLORS["keycap_text"],
            bg=COLORS["keycap_bg"],
        )
        lbl.pack()

        if idx < len(parts) - 1:
            sep = tk.Label(
                container,
                text="+",
                font=(font_body, 8),
                fg=COLORS["keycap_sep"],
                bg=bg_color,
            )
            sep.pack(side=tk.LEFT, padx=4)

    return container


class HotkeyRecorderRow:
    """A row inside a Windows 11 Settings Card Group with guaranteed visible right controls."""

    def __init__(
        self,
        parent: tk.Widget,
        action_name: str,
        icon_glyph: str,
        title: str,
        description: str,
        current_modifiers: List[str],
        current_key: str,
        on_change_callback: Callable[[str, List[str], str, str], None],
        on_reset_callback: Callable[[str], None],
        allow_toggle: bool = False,
        is_enabled: bool = True,
        on_toggle_callback: Optional[Callable[[str, bool], None]] = None,
        font_body: str = "Segoe UI Variable Text",
        font_icon: str = "Segoe Fluent Icons",
        is_last_in_group: bool = False,
    ):
        self.action_name = action_name
        self.icon_glyph = icon_glyph
        self.title = title
        self.description = description
        self.modifiers = current_modifiers
        self.key = current_key
        self.on_change_callback = on_change_callback
        self.on_reset_callback = on_reset_callback
        self.allow_toggle = allow_toggle
        self.is_enabled = is_enabled
        self.on_toggle_callback = on_toggle_callback
        self.font_body = font_body
        self.font_icon = font_icon
        self.is_last_in_group = is_last_in_group
        self.is_recording = False

        # Outer Row Container
        self.wrapper = tk.Frame(parent, bg=COLORS["card"])
        self.wrapper.pack(fill=tk.X)

        self.row = tk.Frame(self.wrapper, bg=COLORS["card"], padx=18, pady=12)
        self.row.pack(fill=tk.X)

        # 1. Left Icon Slot (32x32 rounded)
        self.icon_box = tk.Frame(
            self.row,
            bg=COLORS["icon_box_bg"],
            width=32,
            height=32,
        )
        self.icon_box.pack(side=tk.LEFT, padx=(0, 14))
        self.icon_box.pack_propagate(False)

        lbl_icon = tk.Label(
            self.icon_box,
            text=self.icon_glyph,
            font=(self.font_icon, 11),
            fg=COLORS["accent"],
            bg=COLORS["icon_box_bg"],
        )
        lbl_icon.pack(expand=True)

        # 2. Right Controls Box (PACKED TO THE RIGHT FIRST so it is NEVER pushed off screen!)
        self.ctrl_box = tk.Frame(self.row, bg=COLORS["card"])
        self.ctrl_box.pack(side=tk.RIGHT, padx=(10, 0))

        # Keycaps
        self.keycaps_holder = tk.Frame(self.ctrl_box, bg=COLORS["card"])
        self.keycaps_holder.pack(side=tk.LEFT, padx=(0, 10))
        self._refresh_keycaps_display()

        # Change Button (Windows 11 Accent Blue Pill)
        self.btn_record = tk.Button(
            self.ctrl_box,
            text="Change",
            font=(self.font_body, 8, "bold"),
            fg="#FFFFFF",
            bg=COLORS["accent"],
            activebackground=COLORS["accent_active"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            bd=0,
            command=self.start_recording,
        )
        self.btn_record.pack(side=tk.LEFT, padx=(0, 6))

        # Reset Button (Subtle border button)
        self.btn_reset = tk.Button(
            self.ctrl_box,
            text="Reset",
            font=(self.font_body, 8),
            fg=COLORS["text_muted"],
            bg="#363636",
            activebackground="#444444",
            activeforeground=COLORS["text"],
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            bd=0,
            command=self._on_reset,
        )
        self.btn_reset.pack(side=tk.LEFT, padx=(0, 10 if self.allow_toggle else 0))

        # Optional Toggle Switch
        if self.allow_toggle:
            self.toggle = WinUIToggle(
                self.ctrl_box,
                is_on=self.is_enabled,
                command=self._on_toggle,
                bg=COLORS["card"],
                accent=COLORS["accent"],
            )
            self.toggle.pack(side=tk.LEFT)

        # 3. Middle Text Box (Fills remaining space, with dynamic description wrapping)
        self.text_box = tk.Frame(self.row, bg=COLORS["card"])
        self.text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        lbl_title = tk.Label(
            self.text_box,
            text=self.title,
            font=(self.font_body, 9, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        lbl_title.pack(anchor="w")

        self.lbl_desc = tk.Label(
            self.text_box,
            text=self.description,
            font=(self.font_body, 8),
            fg=COLORS["text_muted"],
            bg=COLORS["card"],
            justify=tk.LEFT,
        )
        self.lbl_desc.pack(anchor="w", pady=(2, 0))

        # Dynamic wrap binding: guarantees text never forces card beyond window boundary
        self.text_box.bind(
            "<Configure>",
            lambda e: self.lbl_desc.config(wraplength=max(100, e.width - 10))
        )

        # Subtle 1px Divider Line (if not last in group)
        if not self.is_last_in_group:
            self.divider = tk.Frame(self.wrapper, bg=COLORS["divider"], height=1)
            self.divider.pack(fill=tk.X, padx=(64, 16))

        # Row hover illumination
        self._bind_hover(self.row)

    def _bind_hover(self, widget: tk.Widget):
        widget.bind("<Enter>", lambda e: self._on_hover(True))
        widget.bind("<Leave>", lambda e: self._on_hover(False))

    def _on_hover(self, entering: bool):
        bg = COLORS["card_hover"] if entering else COLORS["card"]
        self.row.config(bg=bg)
        self.ctrl_box.config(bg=bg)
        self.text_box.config(bg=bg)

    def _refresh_keycaps_display(self):
        for w in self.keycaps_holder.winfo_children():
            w.destroy()
        display_str = self.get_display_text()
        kc = render_keycaps(self.keycaps_holder, display_str, self.font_body, COLORS["card"])
        kc.pack()

    def get_display_text(self) -> str:
        if not self.key:
            return "(None)"
        return format_hotkey(self.modifiers, self.key)

    def _on_toggle(self, is_on: bool):
        self.is_enabled = is_on
        if self.on_toggle_callback:
            self.on_toggle_callback(self.action_name, is_on)

    def _on_reset(self):
        self.on_reset_callback(self.action_name)

    def start_recording(self):
        if self.is_recording:
            self.stop_recording(cancelled=True)
            return

        self.is_recording = True
        self.btn_record.config(
            text="Press Keys (Esc to cancel)",
            bg=COLORS["warning"],
            fg="#000000",
        )
        for w in self.keycaps_holder.winfo_children():
            w.destroy()
        lbl_rec = tk.Label(
            self.keycaps_holder,
            text="Listening for input...",
            font=(self.font_body, 8, "bold"),
            fg=COLORS["warning"],
            bg=COLORS["card"],
        )
        lbl_rec.pack()

        top = self.wrapper.winfo_toplevel()
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
        if vk == 0x1B:  # Escape
            self.stop_recording(cancelled=True)
            return "break"

        if vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5):
            mods = self._detect_active_modifiers()
            display_preview = " + ".join([m.capitalize() for m in mods]) + " + ..."
            for w in self.keycaps_holder.winfo_children():
                w.destroy()
            lbl = tk.Label(
                self.keycaps_holder,
                text=display_preview,
                font=(self.font_body, 8, "bold"),
                fg=COLORS["warning"],
                bg=COLORS["card"],
            )
            lbl.pack()
            return "break"

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
        top = self.wrapper.winfo_toplevel()
        top.unbind("<KeyPress>")

        self.btn_record.config(
            text="Change",
            bg=COLORS["accent"],
            fg="#FFFFFF",
        )
        self._refresh_keycaps_display()

    def update_values(self, modifiers: List[str], key: str):
        self.modifiers = modifiers
        self.key = key
        self._refresh_keycaps_display()


class WindowCentererApp:
    """Windows 11 Settings Desktop Application."""

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
        self.root.geometry("880x640")
        self.root.minsize(780, 560)
        self.root.configure(bg=COLORS["bg"])

        self._init_fonts()

        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"))
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self._hotkey_rows: Dict[str, HotkeyRecorderRow] = {}
        self.nav_buttons: Dict[str, tk.Frame] = {}
        self.nav_indicators: Dict[str, tk.Frame] = {}
        self.nav_labels: Dict[str, tk.Label] = {}
        self.nav_icons: Dict[str, tk.Label] = {}
        self.page_frames: Dict[str, tk.Frame] = {}
        self._current_search_query = ""

        self._build_ui()
        self.refresh_monitors_list()

        # DWM dark theme & mica
        self.root.after(10, lambda: apply_dwm_styling(self.root))

    def _init_fonts(self):
        families = set(tkfont.families())
        self.font_body = "Segoe UI Variable Text" if "Segoe UI Variable Text" in families else "Segoe UI"
        self.font_display = "Segoe UI Variable Display" if "Segoe UI Variable Display" in families else self.font_body
        self.font_icon = "Segoe Fluent Icons" if "Segoe Fluent Icons" in families else ("Segoe MDL2 Assets" if "Segoe MDL2 Assets" in families else "Segoe UI")

    def _build_ui(self):
        main_box = tk.Frame(self.root, bg=COLORS["bg"])
        main_box.pack(fill=tk.BOTH, expand=True)

        # =========================================================================
        # 1. LEFT NAVIGATION PANE (Windows 11 Settings Sidebar - 250px)
        # =========================================================================
        self.sidebar = tk.Frame(main_box, bg=COLORS["sidebar_bg"], width=250)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Top App Identity Banner (Logo + Title + Subtitle)
        brand_card = tk.Frame(self.sidebar, bg=COLORS["sidebar_bg"], padx=18, pady=18)
        brand_card.pack(fill=tk.X)

        logo_box = tk.Frame(brand_card, bg=COLORS["accent"], width=34, height=34)
        logo_box.pack(side=tk.LEFT, padx=(0, 12))
        logo_box.pack_propagate(False)

        lbl_logo = tk.Label(
            logo_box,
            text=ICONS["snap"],
            font=(self.font_icon, 13),
            fg="#FFFFFF",
            bg=COLORS["accent"],
        )
        lbl_logo.pack(expand=True)

        brand_info = tk.Frame(brand_card, bg=COLORS["sidebar_bg"])
        brand_info.pack(side=tk.LEFT, fill=tk.X, expand=True)

        lbl_brand_name = tk.Label(
            brand_info,
            text="Window Centerer",
            font=(self.font_display, 11, "bold"),
            fg=COLORS["text"],
            bg=COLORS["sidebar_bg"],
        )
        lbl_brand_name.pack(anchor="w")

        lbl_brand_sub = tk.Label(
            brand_info,
            text="Precision Window Snapper",
            font=(self.font_body, 8),
            fg=COLORS["text_dim"],
            bg=COLORS["sidebar_bg"],
        )
        lbl_brand_sub.pack(anchor="w")

        # Windows 11 Settings Search Box ("Find a setting")
        search_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar_bg"], padx=14)
        search_frame.pack(fill=tk.X, pady=(0, 12))

        search_box = tk.Frame(
            search_frame,
            bg=COLORS["search_bg"],
            highlightbackground=COLORS["search_border"],
            highlightthickness=1,
            padx=8,
            pady=4,
        )
        search_box.pack(fill=tk.X)

        lbl_mag = tk.Label(
            search_box,
            text=ICONS["search"],
            font=(self.font_icon, 10),
            fg=COLORS["text_muted"],
            bg=COLORS["search_bg"],
        )
        lbl_mag.pack(side=tk.LEFT, padx=(0, 6))

        self.search_entry = tk.Entry(
            search_box,
            font=(self.font_body, 9),
            fg=COLORS["text_muted"],
            bg=COLORS["search_bg"],
            insertbackground="#FFFFFF",
            bd=0,
            relief=tk.FLAT,
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.insert(0, "Find a setting")
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self.search_entry.bind("<KeyRelease>", self._on_search_query_changed)

        # Navigation Category Items
        self.nav_items_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar_bg"], padx=10)
        self.nav_items_frame.pack(fill=tk.BOTH, expand=True)

        nav_tabs = [
            ("shortcuts", ICONS["keyboard"], "Shortcuts"),
            ("display", ICONS["display"], "Display & Layout"),
            ("behavior", ICONS["snap"], "Centering Behavior"),
            ("system", ICONS["system"], "System & Startup"),
            ("about", ICONS["about"], "About & Support"),
        ]

        for tab_id, icon_char, label_text in nav_tabs:
            self._create_nav_item(tab_id, icon_char, label_text)

        # Bottom Sidebar Divider & Status
        sidebar_bottom = tk.Frame(self.sidebar, bg=COLORS["sidebar_bg"], padx=14, pady=14)
        sidebar_bottom.pack(fill=tk.X, side=tk.BOTTOM)

        divider_side = tk.Frame(sidebar_bottom, bg=COLORS["divider"], height=1)
        divider_side.pack(fill=tk.X, pady=(0, 10))

        # Status Pill
        status_box = tk.Frame(sidebar_bottom, bg=COLORS["sidebar_bg"])
        status_box.pack(fill=tk.X, pady=(0, 10))

        self.lbl_status_icon = tk.Label(
            status_box,
            text=ICONS["check"],
            font=(self.font_icon, 9),
            fg=COLORS["success"],
            bg=COLORS["sidebar_bg"],
        )
        self.lbl_status_icon.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_status_text = tk.Label(
            status_box,
            text="Hotkeys Active & Listening",
            font=(self.font_body, 8, "bold"),
            fg=COLORS["text"],
            bg=COLORS["sidebar_bg"],
        )
        self.lbl_status_text.pack(side=tk.LEFT)

        btn_min = tk.Button(
            sidebar_bottom,
            text="Minimize to Tray",
            font=(self.font_body, 8),
            fg=COLORS["text"],
            bg="#262626",
            activebackground="#333333",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            pady=6,
            cursor="hand2",
            command=self.hide_to_tray,
        )
        btn_min.pack(fill=tk.X, pady=(0, 6))

        btn_exit = tk.Button(
            sidebar_bottom,
            text="Exit App",
            font=(self.font_body, 8),
            fg=COLORS["danger"],
            bg="#262626",
            activebackground=COLORS["danger"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            pady=6,
            cursor="hand2",
            command=self.exit_application,
        )
        btn_exit.pack(fill=tk.X)

        # =========================================================================
        # 2. RIGHT CONTENT PANE
        # =========================================================================
        self.right_container = tk.Frame(main_box, bg=COLORS["bg"])
        self.right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 2.1 Fixed Header Bar (Breadcrumbs & Title)
        self.page_header = tk.Frame(self.right_container, bg=COLORS["bg"], padx=32)
        self.page_header.pack(fill=tk.X, pady=(20, 12))

        self.lbl_breadcrumb = tk.Label(
            self.page_header,
            text="Window Centerer  >  Keyboard Shortcuts",
            font=(self.font_body, 8),
            fg=COLORS["text_dim"],
            bg=COLORS["bg"],
        )
        self.lbl_breadcrumb.pack(anchor="w")

        title_row = tk.Frame(self.page_header, bg=COLORS["bg"])
        title_row.pack(fill=tk.X, pady=(2, 0))

        self.lbl_page_title = tk.Label(
            title_row,
            text="Keyboard Shortcuts",
            font=(self.font_display, 20, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        self.lbl_page_title.pack(side=tk.LEFT, anchor="w")

        # 2.2 Bottom Feedback Infobar (Packed to BOTTOM FIRST so it is NEVER covered!)
        self.footer_bar = tk.Frame(self.right_container, bg=COLORS["infobar_bg"], padx=20, pady=8)
        self.footer_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_feedback = tk.Label(
            self.footer_bar,
            text="Ready. Press your configured shortcuts anytime across any application.",
            font=(self.font_body, 8),
            fg=COLORS["text_muted"],
            bg=COLORS["infobar_bg"],
        )
        self.lbl_feedback.pack(side=tk.LEFT)

        # 2.3 Scrollable Viewport (Canvas locked strictly to horizontal width)
        self.content_canvas = tk.Canvas(
            self.right_container,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.content_canvas.pack(fill=tk.BOTH, expand=True)

        self.scroll_window = tk.Frame(self.content_canvas, bg=COLORS["bg"], padx=32, pady=6)
        self.canvas_window_id = self.content_canvas.create_window(
            (0, 0),
            window=self.scroll_window,
            anchor="nw",
        )

        self.scroll_window.bind("<Configure>", self._on_scroll_configure)
        self.content_canvas.bind("<Configure>", self._on_canvas_configure)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        # Instantiate Content Pages
        for tab_id, _, _ in nav_tabs:
            frame = tk.Frame(self.scroll_window, bg=COLORS["bg"])
            self.page_frames[tab_id] = frame

        self._build_shortcuts_page(self.page_frames["shortcuts"])
        self._build_display_page(self.page_frames["display"])
        self._build_behavior_page(self.page_frames["behavior"])
        self._build_system_page(self.page_frames["system"])
        self._build_about_page(self.page_frames["about"])

        # Activate initial tab
        self.switch_tab("shortcuts")

    def _create_nav_item(self, tab_id: str, icon_char: str, label_text: str):
        row = tk.Frame(self.nav_items_frame, bg=COLORS["sidebar_bg"], cursor="hand2")
        row.pack(fill=tk.X, pady=2)

        indicator = tk.Frame(row, bg=COLORS["sidebar_bg"], width=3, height=20)
        indicator.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))

        lbl_icon = tk.Label(
            row,
            text=icon_char,
            font=(self.font_icon, 11),
            fg=COLORS["text_muted"],
            bg=COLORS["sidebar_bg"],
            width=2,
            anchor="center",
        )
        lbl_icon.pack(side=tk.LEFT, padx=(0, 8))

        lbl_text = tk.Label(
            row,
            text=label_text,
            font=(self.font_body, 9, "bold"),
            fg=COLORS["text_muted"],
            bg=COLORS["sidebar_bg"],
            anchor="w",
        )
        lbl_text.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=8)

        widgets = (row, indicator, lbl_icon, lbl_text)
        for w in widgets:
            w.bind("<Button-1>", lambda e, tid=tab_id: self.switch_tab(tid))
            w.bind("<Enter>", lambda e, tid=tab_id: self._on_nav_hover(tid, True))
            w.bind("<Leave>", lambda e, tid=tab_id: self._on_nav_hover(tid, False))

        self.nav_buttons[tab_id] = row
        self.nav_indicators[tab_id] = indicator
        self.nav_labels[tab_id] = lbl_text
        self.nav_icons[tab_id] = lbl_icon

    def _on_nav_hover(self, tab_id: str, entering: bool):
        if getattr(self, "_active_tab", None) == tab_id:
            return
        bg = COLORS["sidebar_hover"] if entering else COLORS["sidebar_bg"]
        self.nav_buttons[tab_id].config(bg=bg)
        self.nav_icons[tab_id].config(bg=bg)
        self.nav_labels[tab_id].config(bg=bg)

    def switch_tab(self, tab_id: str):
        self._active_tab = tab_id
        meta = {
            "shortcuts": ("Keyboard Shortcuts", "Window Centerer  >  Keyboard Shortcuts"),
            "display": ("Display & Layout", "Window Centerer  >  Display"),
            "behavior": ("Centering Behavior", "Window Centerer  >  Centering Behavior"),
            "system": ("System & Startup", "Window Centerer  >  System & Startup"),
            "about": ("About & Support", "Window Centerer  >  About"),
        }
        title, breadcrumb = meta.get(tab_id, ("Window Centerer", "Settings"))
        self.lbl_page_title.config(text=title)
        self.lbl_breadcrumb.config(text=breadcrumb)

        for tid, frame in self.page_frames.items():
            if tid == tab_id:
                frame.pack(fill=tk.BOTH, expand=True)
                self.nav_buttons[tid].config(bg=COLORS["sidebar_active"])
                self.nav_indicators[tid].config(bg=COLORS["accent"])
                self.nav_labels[tid].config(fg=COLORS["text"], bg=COLORS["sidebar_active"])
                self.nav_icons[tid].config(fg=COLORS["accent"], bg=COLORS["sidebar_active"])
            else:
                frame.pack_forget()
                self.nav_buttons[tid].config(bg=COLORS["sidebar_bg"])
                self.nav_indicators[tid].config(bg=COLORS["sidebar_bg"])
                self.nav_labels[tid].config(fg=COLORS["text_muted"], bg=COLORS["sidebar_bg"])
                self.nav_icons[tid].config(fg=COLORS["text_muted"], bg=COLORS["sidebar_bg"])

        self.content_canvas.yview_moveto(0)

    # ----------------- SEARCH FILTERING -----------------

    def _on_search_focus_in(self, event):
        if self.search_entry.get() == "Find a setting":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=COLORS["text"])

    def _on_search_focus_out(self, event):
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, "Find a setting")
            self.search_entry.config(fg=COLORS["text_muted"])

    def _on_search_query_changed(self, event):
        query = self.search_entry.get().strip().lower()
        if query == "find a setting":
            query = ""
        self._current_search_query = query

        if query in ("shortcut", "shortcuts", "hotkey", "key"):
            self.switch_tab("shortcuts")
        elif query in ("display", "monitor", "screen", "displays", "resolution"):
            self.switch_tab("display")
        elif query in ("sound", "shrink", "restore", "resize", "chime", "behavior"):
            self.switch_tab("behavior")
        elif query in ("startup", "autostart", "tray", "minimize", "windows"):
            self.switch_tab("system")
        elif query in ("about", "cli", "stream deck", "docs"):
            self.switch_tab("about")

    # ----------------- CANVAS SCROLL MATH -----------------

    def _on_scroll_configure(self, event):
        # Strict horizontal lock: scrollregion only allows vertical motion
        req_h = self.scroll_window.winfo_reqheight()
        c_w = self.content_canvas.winfo_width()
        self.content_canvas.configure(scrollregion=(0, 0, c_w, req_h))

    def _on_canvas_configure(self, event):
        # Force scroll_window width to match canvas exactly
        self.content_canvas.itemconfig(self.canvas_window_id, width=event.width)

    def _on_mousewheel(self, event):
        self.content_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # =========================================================================
    # PAGE 1: KEYBOARD SHORTCUTS
    # =========================================================================
    def _build_shortcuts_page(self, parent: tk.Frame):
        # 1. Hero Card (Action Button packed RIGHT FIRST so it's guaranteed visible!)
        hero = tk.Frame(
            parent,
            bg=COLORS["hero_bg"],
            highlightbackground=COLORS["hero_border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        hero.pack(fill=tk.X, pady=(0, 16))

        # Action Button packed RIGHT FIRST
        btn_hero_test = tk.Button(
            hero,
            text=f"{ICONS['snap']}  Center Active Window",
            font=(self.font_body, 9, "bold"),
            fg="#FFFFFF",
            bg=COLORS["accent"],
            activebackground=COLORS["accent_active"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=16,
            pady=7,
            cursor="hand2",
            bd=0,
            command=self.trigger_center_now,
        )
        btn_hero_test.pack(side=tk.RIGHT, padx=(14, 0))

        # Hero Left content
        hero_left = tk.Frame(hero, bg=COLORS["hero_bg"])
        hero_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hero_icon_box = tk.Frame(hero_left, bg=COLORS["accent"], width=38, height=38)
        hero_icon_box.pack(side=tk.LEFT, padx=(0, 14))
        hero_icon_box.pack_propagate(False)

        lbl_hero_icon = tk.Label(
            hero_icon_box,
            text=ICONS["snap"],
            font=(self.font_icon, 14),
            fg="#FFFFFF",
            bg=COLORS["accent"],
        )
        lbl_hero_icon.pack(expand=True)

        hero_text_box = tk.Frame(hero_left, bg=COLORS["hero_bg"])
        hero_text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        lbl_h_title = tk.Label(
            hero_text_box,
            text="Active Window Snapper",
            font=(self.font_body, 11, "bold"),
            fg=COLORS["text"],
            bg=COLORS["hero_bg"],
        )
        lbl_h_title.pack(anchor="w")

        lbl_h_sub = tk.Label(
            hero_text_box,
            text="Press hotkeys anytime to snap the active foreground window down to the exact pixel.",
            font=(self.font_body, 8),
            fg=COLORS["text_muted"],
            bg=COLORS["hero_bg"],
        )
        lbl_h_sub.pack(anchor="w", pady=(2, 0))

        # 2. Section Header
        lbl_sec1 = tk.Label(
            parent,
            text="Global Window Centerer Hotkeys",
            font=(self.font_body, 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        lbl_sec1.pack(anchor="w", pady=(0, 8))

        # 3. Unified Card Group for Shortcuts
        card_group = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
        )
        card_group.pack(fill=tk.X, pady=(0, 16))

        # Row 1: Center on Current Screen
        c_hotkey = self.cfg.get_hotkey("center_current")
        row_center = HotkeyRecorderRow(
            parent=card_group,
            action_name="center_current",
            icon_glyph=ICONS["snap"],
            title="Center on Current Screen",
            description="Centers the active window on its screen, compensating for invisible DWM border margins.",
            current_modifiers=c_hotkey.get("modifiers", ["ctrl", "alt"]),
            current_key=c_hotkey.get("key", "C"),
            on_change_callback=self.on_hotkey_changed,
            on_reset_callback=self.on_hotkey_reset,
            font_body=self.font_body,
            font_icon=self.font_icon,
            is_last_in_group=False,
        )
        self._hotkey_rows["center_current"] = row_center

        # Row 2: Move to Next Screen & Center
        next_hotkey = self.cfg.get_hotkey("cycle_next")
        row_next = HotkeyRecorderRow(
            parent=card_group,
            action_name="cycle_next",
            icon_glyph=ICONS["next"],
            title="Move to Next Screen & Center",
            description="Moves the active window to the next monitor in sequence and auto-centers it.",
            current_modifiers=next_hotkey.get("modifiers", ["ctrl", "alt"]),
            current_key=next_hotkey.get("key", "Right"),
            on_change_callback=self.on_hotkey_changed,
            on_reset_callback=self.on_hotkey_reset,
            allow_toggle=True,
            is_enabled=next_hotkey.get("enabled", True),
            on_toggle_callback=self.on_hotkey_toggle,
            font_body=self.font_body,
            font_icon=self.font_icon,
            is_last_in_group=False,
        )
        self._hotkey_rows["cycle_next"] = row_next

        # Row 3: Move to Previous Screen & Center
        prev_hotkey = self.cfg.get_hotkey("cycle_prev")
        row_prev = HotkeyRecorderRow(
            parent=card_group,
            action_name="cycle_prev",
            icon_glyph=ICONS["prev"],
            title="Move to Previous Screen & Center",
            description="Moves the active window to the previous monitor in sequence and auto-centers it.",
            current_modifiers=prev_hotkey.get("modifiers", ["ctrl", "alt"]),
            current_key=prev_hotkey.get("key", "Left"),
            on_change_callback=self.on_hotkey_changed,
            on_reset_callback=self.on_hotkey_reset,
            allow_toggle=True,
            is_enabled=prev_hotkey.get("enabled", True),
            on_toggle_callback=self.on_hotkey_toggle,
            font_body=self.font_body,
            font_icon=self.font_icon,
            is_last_in_group=False,
        )
        self._hotkey_rows["cycle_prev"] = row_prev

        # Row 4: Center & Resize Window
        resize_hotkey = self.cfg.get_hotkey("center_resize")
        row_resize = HotkeyRecorderRow(
            parent=card_group,
            action_name="center_resize",
            icon_glyph=ICONS["resize"],
            title="Center & Resize Window",
            description="Resizes the window to a proportion of the display and centers it.",
            current_modifiers=resize_hotkey.get("modifiers", ["ctrl", "alt"]),
            current_key=resize_hotkey.get("key", "R"),
            on_change_callback=self.on_hotkey_changed,
            on_reset_callback=self.on_hotkey_reset,
            allow_toggle=True,
            is_enabled=resize_hotkey.get("enabled", False),
            on_toggle_callback=self.on_hotkey_toggle,
            font_body=self.font_body,
            font_icon=self.font_icon,
            is_last_in_group=True,
        )
        self._hotkey_rows["center_resize"] = row_resize

        # 4. Resize Scale Selector Card (Segmented Pills packed RIGHT FIRST!)
        lbl_sec2 = tk.Label(
            parent,
            text="Resize Proportion",
            font=(self.font_body, 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        lbl_sec2.pack(anchor="w", pady=(0, 8))

        scale_card = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=18,
            pady=14,
        )
        scale_card.pack(fill=tk.X, pady=(0, 16))

        # Segmented Pills packed RIGHT FIRST
        pills_box = tk.Frame(scale_card, bg=COLORS["card"])
        pills_box.pack(side=tk.RIGHT, padx=(10, 0))

        self.scale_pills: Dict[float, tk.Button] = {}
        current_factor = float(self.cfg.get_behavior("resize_factor", 0.75))

        for factor, label in [(0.50, "50%"), (0.67, "67%"), (0.75, "75%"), (0.80, "80%"), (0.90, "90%")]:
            btn = tk.Button(
                pills_box,
                text=label,
                font=(self.font_body, 8, "bold"),
                fg="#FFFFFF" if abs(current_factor - factor) < 0.02 else COLORS["text_muted"],
                bg=COLORS["accent"] if abs(current_factor - factor) < 0.02 else "#343434",
                activebackground=COLORS["accent_active"],
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                bd=0,
                padx=10,
                pady=4,
                cursor="hand2",
                command=lambda f=factor: self._set_resize_factor(f),
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.scale_pills[factor] = btn

        scale_left = tk.Frame(scale_card, bg=COLORS["card"])
        scale_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        lbl_sc_title = tk.Label(
            scale_left,
            text="Window Resize Scale",
            font=(self.font_body, 9, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        lbl_sc_title.pack(anchor="w")

        lbl_sc_sub = tk.Label(
            scale_left,
            text="Target size ratio applied when triggering the 'Center & Resize' shortcut.",
            font=(self.font_body, 8),
            fg=COLORS["text_muted"],
            bg=COLORS["card"],
        )
        lbl_sc_sub.pack(anchor="w", pady=(2, 0))

    def _set_resize_factor(self, factor: float):
        self.cfg.set_behavior("resize_factor", factor)
        for f, btn in self.scale_pills.items():
            if abs(f - factor) < 0.02:
                btn.config(bg=COLORS["accent"], fg="#FFFFFF")
            else:
                btn.config(bg="#343434", fg=COLORS["text_muted"])
        self.set_feedback(f"Resize factor updated to {int(factor * 100)}% of work area.")

    # =========================================================================
    # PAGE 2: DISPLAY & LAYOUT (Visual Screen Arranger)
    # =========================================================================
    def _build_display_page(self, parent: tk.Frame):
        arranger_card = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        arranger_card.pack(fill=tk.X, pady=(0, 16))

        top_row = tk.Frame(arranger_card, bg=COLORS["card"])
        top_row.pack(fill=tk.X, pady=(0, 10))

        btn_ref = tk.Button(
            top_row,
            text=f"{ICONS['refresh']}  Detect & Refresh",
            font=(self.font_body, 8, "bold"),
            fg=COLORS["text"],
            bg="#363636",
            activebackground="#444444",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.refresh_monitors_list,
        )
        btn_ref.pack(side=tk.RIGHT)

        lbl_arr_title = tk.Label(
            top_row,
            text="Display Arrangement",
            font=(self.font_body, 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        lbl_arr_title.pack(side=tk.LEFT)

        # Monitor Canvas Graphic
        self.arranger_canvas = tk.Canvas(
            arranger_card,
            bg="#222222",
            height=130,
            highlightbackground=COLORS["divider"],
            highlightthickness=1,
            cursor="hand2",
        )
        self.arranger_canvas.pack(fill=tk.X, pady=(0, 8))

        lbl_help = tk.Label(
            arranger_card,
            text="Click on any monitor box above to center the active foreground window directly on that screen.",
            font=(self.font_body, 8),
            fg=COLORS["text_dim"],
            bg=COLORS["card"],
        )
        lbl_help.pack(anchor="w")

        lbl_sec = tk.Label(
            parent,
            text="Connected Monitors & Usable Work Areas",
            font=(self.font_body, 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        lbl_sec.pack(anchor="w", pady=(0, 8))

        self.monitors_container = tk.Frame(parent, bg=COLORS["bg"])
        self.monitors_container.pack(fill=tk.BOTH, expand=True)

    def refresh_monitors_list(self):
        for widget in self.monitors_container.winfo_children():
            widget.destroy()

        monitors = self.wm.get_all_monitors()
        if not monitors:
            lbl_none = tk.Label(
                self.monitors_container,
                text="No active monitors detected.",
                font=(self.font_body, 10),
                fg=COLORS["text_muted"],
                bg=COLORS["bg"],
            )
            lbl_none.pack(pady=20)
            return

        if hasattr(self, "arranger_canvas"):
            self._draw_arranger_canvas(monitors)

        monitor_group = tk.Frame(
            self.monitors_container,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
        )
        monitor_group.pack(fill=tk.X, pady=(0, 16))

        for idx, mon in enumerate(monitors):
            is_last = (idx == len(monitors) - 1)
            wrapper = tk.Frame(monitor_group, bg=COLORS["card"])
            wrapper.pack(fill=tk.X)

            row = tk.Frame(wrapper, bg=COLORS["card"], padx=18, pady=12)
            row.pack(fill=tk.X)

            # Left Icon
            icon_box = tk.Frame(row, bg=COLORS["icon_box_bg"], width=32, height=32)
            icon_box.pack(side=tk.LEFT, padx=(0, 14))
            icon_box.pack_propagate(False)

            lbl_ico = tk.Label(
                icon_box,
                text=ICONS["display"],
                font=(self.font_icon, 11),
                fg=COLORS["accent"],
                bg=COLORS["icon_box_bg"],
            )
            lbl_ico.pack(expand=True)

            # Right Button PACKED RIGHT FIRST
            btn_center = tk.Button(
                row,
                text=f"{ICONS['snap']}  Center Here",
                font=(self.font_body, 8, "bold"),
                fg="#FFFFFF",
                bg="#3A3A3A",
                activebackground=COLORS["accent"],
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                bd=0,
                padx=12,
                pady=4,
                cursor="hand2",
                command=lambda m=mon: self._test_center_on_screen(m),
            )
            btn_center.pack(side=tk.RIGHT, padx=(10, 0))

            # Info Text
            text_box = tk.Frame(row, bg=COLORS["card"])
            text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            title_row = tk.Frame(text_box, bg=COLORS["card"])
            title_row.pack(anchor="w", fill=tk.X)

            lbl_title = tk.Label(
                title_row,
                text=f"Display {idx + 1}: {mon['device']}",
                font=(self.font_body, 9, "bold"),
                fg=COLORS["text"],
                bg=COLORS["card"],
            )
            lbl_title.pack(side=tk.LEFT)

            if mon["primary"]:
                lbl_badge = tk.Label(
                    title_row,
                    text="PRIMARY DISPLAY",
                    font=(self.font_body, 7, "bold"),
                    fg="#FFFFFF",
                    bg=COLORS["accent"],
                    padx=6,
                    pady=1,
                )
                lbl_badge.pack(side=tk.LEFT, padx=(8, 0))

            m_rect = mon["monitor_rect"]
            w_rect = mon["work_rect"]
            lbl_res = tk.Label(
                text_box,
                text=f"Resolution: {m_rect.width}×{m_rect.height}  |  Usable Work Area: {w_rect.width}×{w_rect.height} at ({w_rect.left}, {w_rect.top})",
                font=(self.font_body, 8),
                fg=COLORS["text_muted"],
                bg=COLORS["card"],
                justify=tk.LEFT,
            )
            lbl_res.pack(anchor="w", pady=(2, 0))

            text_box.bind(
                "<Configure>",
                lambda e, l=lbl_res: l.config(wraplength=max(100, e.width - 10))
            )

            if not is_last:
                div = tk.Frame(wrapper, bg=COLORS["divider"], height=1)
                div.pack(fill=tk.X, padx=(64, 16))

    def _draw_arranger_canvas(self, monitors: List[Dict[str, Any]]):
        self.arranger_canvas.delete("all")
        if not monitors:
            return

        min_x = min(m["monitor_rect"].left for m in monitors)
        min_y = min(m["monitor_rect"].top for m in monitors)
        max_x = max(m["monitor_rect"].right for m in monitors)
        max_y = max(m["monitor_rect"].bottom for m in monitors)

        total_w = max(1, max_x - min_x)
        total_h = max(1, max_y - min_y)

        c_w = self.arranger_canvas.winfo_width()
        if c_w < 50:
            c_w = 480
        c_h = 130

        scale = min((c_w - 60) / total_w, (c_h - 40) / total_h)
        offset_x = (c_w - (total_w * scale)) / 2
        offset_y = (c_h - (total_h * scale)) / 2

        for idx, mon in enumerate(monitors):
            mr = mon["monitor_rect"]
            x1 = offset_x + (mr.left - min_x) * scale
            y1 = offset_y + (mr.top - min_y) * scale
            x2 = x1 + mr.width * scale
            y2 = y1 + mr.height * scale

            is_primary = mon["primary"]
            fill_color = "#2E3B4E" if is_primary else "#2A2A2A"
            outline_color = COLORS["accent"] if is_primary else "#4A4A4A"

            rect_id = self.arranger_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=fill_color,
                outline=outline_color,
                width=2,
            )

            self.arranger_canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2 - 8,
                text=str(idx + 1),
                fill="#FFFFFF",
                font=(self.font_display, 13, "bold"),
            )

            sub_label = "Primary" if is_primary else f"{mr.width}×{mr.height}"
            self.arranger_canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2 + 10,
                text=sub_label,
                fill=COLORS["accent"] if is_primary else COLORS["text_muted"],
                font=(self.font_body, 7, "bold"),
            )

            self.arranger_canvas.tag_bind(rect_id, "<Button-1>", lambda e, m=mon: self._test_center_on_screen(m))

    def _test_center_on_screen(self, mon: Dict[str, Any]):
        self.root.iconify()
        time.sleep(0.1)
        res = self.wm.center_window(target_monitor=mon)
        self.root.deiconify()
        self.root.lift()
        if res.get("success"):
            self.set_feedback(f"Centered '{res.get('title')}' on {mon.get('device')}")
        else:
            self.set_feedback(f"Note: {res.get('error')}", is_error=True)

    # =========================================================================
    # PAGE 3: CENTERING BEHAVIOR
    # =========================================================================
    def _build_behavior_page(self, parent: tk.Frame):
        lbl_sec = tk.Label(
            parent,
            text="Window Adaptation & Audio Options",
            font=(self.font_body, 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        lbl_sec.pack(anchor="w", pady=(0, 8))

        card = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
        )
        card.pack(fill=tk.X, pady=(0, 16))

        # Row 1: Auto-restore
        self._add_settings_row(
            card_parent=card,
            icon_glyph=ICONS["restore"],
            title="Auto-restore maximized windows",
            description="Automatically un-maximizes foreground windows before snapping them to the center of the screen.",
            initial_val=self.cfg.get_behavior("auto_restore_maximized", True),
            on_change=lambda val: self._update_behavior("auto_restore_maximized", val),
            is_last=False,
        )

        # Row 2: Auto-shrink
        self._add_settings_row(
            card_parent=card,
            icon_glyph=ICONS["shrink"],
            title="Auto-shrink oversized windows",
            description="Constrains windows that exceed current screen dimensions to fit comfortably within the work area.",
            initial_val=self.cfg.get_behavior("auto_shrink_oversized", True),
            on_change=lambda val: self._update_behavior("auto_shrink_oversized", val),
            is_last=False,
        )

        # Row 3: Sound chime
        self._add_settings_row(
            card_parent=card,
            icon_glyph=ICONS["sound"],
            title="Play subtle audio chime on center",
            description="Plays an instant audible feedback tone when a window is centered.",
            initial_val=self.cfg.get_behavior("play_sound", True),
            on_change=lambda val: self._update_behavior("play_sound", val),
            is_last=True,
        )

    # =========================================================================
    # PAGE 4: SYSTEM & STARTUP
    # =========================================================================
    def _build_system_page(self, parent: tk.Frame):
        lbl_sec = tk.Label(
            parent,
            text="Windows Startup & Background Tray Presence",
            font=(self.font_body, 10, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        lbl_sec.pack(anchor="w", pady=(0, 8))

        card = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
        )
        card.pack(fill=tk.X, pady=(0, 16))

        # Row 1: Start with Windows
        self._add_settings_row(
            card_parent=card,
            icon_glyph=ICONS["autostart"],
            title="Start Window Centerer automatically with Windows",
            description="Runs silently in the system notification tray upon login so global hotkeys are always active.",
            initial_val=is_autostart_enabled(),
            on_change=self._on_autostart_toggled,
            is_last=False,
        )

        # Row 2: Minimize to Tray on Close
        self._add_settings_row(
            card_parent=card,
            icon_glyph=ICONS["tray"],
            title="Minimize to system tray on window close (X)",
            description="Closing this settings dashboard keeps the background hotkey listener active in the tray.",
            initial_val=self.cfg.get_system("minimize_to_tray_on_close", True),
            on_change=lambda val: self._update_system("minimize_to_tray_on_close", val),
            is_last=True,
        )

    def _add_settings_row(
        self,
        card_parent: tk.Frame,
        icon_glyph: str,
        title: str,
        description: str,
        initial_val: bool,
        on_change: Callable[[bool], None],
        is_last: bool = False,
    ):
        wrapper = tk.Frame(card_parent, bg=COLORS["card"])
        wrapper.pack(fill=tk.X)

        row = tk.Frame(wrapper, bg=COLORS["card"], padx=18, pady=12)
        row.pack(fill=tk.X)

        icon_box = tk.Frame(row, bg=COLORS["icon_box_bg"], width=32, height=32)
        icon_box.pack(side=tk.LEFT, padx=(0, 14))
        icon_box.pack_propagate(False)

        lbl_ico = tk.Label(
            icon_box,
            text=icon_glyph,
            font=(self.font_icon, 11),
            fg=COLORS["accent"],
            bg=COLORS["icon_box_bg"],
        )
        lbl_ico.pack(expand=True)

        # Right Switch PACKED RIGHT FIRST
        switch = WinUIToggle(
            row,
            is_on=initial_val,
            command=on_change,
            bg=COLORS["card"],
            accent=COLORS["accent"],
        )
        switch.pack(side=tk.RIGHT, padx=(10, 0))

        text_box = tk.Frame(row, bg=COLORS["card"])
        text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        lbl_title = tk.Label(
            text_box,
            text=title,
            font=(self.font_body, 9, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            text_box,
            text=description,
            font=(self.font_body, 8),
            fg=COLORS["text_muted"],
            bg=COLORS["card"],
            justify=tk.LEFT,
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        text_box.bind(
            "<Configure>",
            lambda e, l=lbl_desc: l.config(wraplength=max(100, e.width - 10))
        )

        if not is_last:
            div = tk.Frame(wrapper, bg=COLORS["divider"], height=1)
            div.pack(fill=tk.X, padx=(64, 16))

        # Hover state
        row.bind("<Enter>", lambda e: row.config(bg=COLORS["card_hover"]))
        row.bind("<Leave>", lambda e: row.config(bg=COLORS["card"]))

    # =========================================================================
    # PAGE 5: ABOUT & DOCUMENTATION
    # =========================================================================
    def _build_about_page(self, parent: tk.Frame):
        card = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=20,
            pady=18,
        )
        card.pack(fill=tk.X, pady=(0, 16))

        lbl_app = tk.Label(
            card,
            text="🎯 Window Centerer",
            font=(self.font_display, 13, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        )
        lbl_app.pack(anchor="w")

        lbl_desc = tk.Label(
            card,
            text="Precision active window centering across any display configuration on Windows 10 & 11.\n"
                 "Utilizes DWMWA_EXTENDED_FRAME_BOUNDS to compensate for invisible drop-shadow margins down to the exact pixel.",
            font=(self.font_body, 8),
            fg=COLORS["text_muted"],
            bg=COLORS["card"],
            justify=tk.LEFT,
        )
        lbl_desc.pack(anchor="w", pady=(4, 14))

        specs = [
            ("Zero External Dependencies", "Built strictly with Python standard library (ctypes, tkinter, winsound, json)."),
            ("CLI & Hardware Triggers", "Execute 'python main.py --center' or '--cycle' from Elgato Stream Deck or scripts."),
            ("Multi-DPI & Mixed Layouts", "Supports mixed scaling factors (100%, 150%, 200%) and vertical displays."),
            ("Single Instance Mutex", "Win32 named mutex ensures hotkeys are never registered twice."),
        ]

        for heading, detail in specs:
            box = tk.Frame(card, bg=COLORS["card"], pady=4)
            box.pack(fill=tk.X)
            lbl_h = tk.Label(
                box,
                text=f"• {heading}: ",
                font=(self.font_body, 8, "bold"),
                fg=COLORS["accent"],
                bg=COLORS["card"],
            )
            lbl_h.pack(side=tk.LEFT)
            lbl_d = tk.Label(
                box,
                text=detail,
                font=(self.font_body, 8),
                fg=COLORS["text_muted"],
                bg=COLORS["card"],
            )
            lbl_d.pack(side=tk.LEFT)

    # =========================================================================
    # CORE LOGIC & CALLBACKS
    # =========================================================================
    def on_hotkey_changed(self, action: str, modifiers: List[str], key: str, display: str):
        self.cfg.set_hotkey(action, modifiers, key, display, enabled=True)
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
            enabled=enabled,
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
        auto_restore = self.cfg.get_behavior("auto_restore_maximized", True)
        auto_shrink = self.cfg.get_behavior("auto_shrink_oversized", True)

        res = self.wm.center_window(
            auto_restore_maximized=auto_restore,
            auto_shrink_oversized=auto_shrink,
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
        auto_restore = self.cfg.get_behavior("auto_restore_maximized", True)
        auto_shrink = self.cfg.get_behavior("auto_shrink_oversized", True)

        res = self.wm.cycle_monitor(
            direction=direction,
            auto_restore_maximized=auto_restore,
            auto_shrink_oversized=auto_shrink,
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
        factor = float(self.cfg.get_behavior("resize_factor", 0.75))
        auto_restore = self.cfg.get_behavior("auto_restore_maximized", True)

        res = self.wm.center_window(
            auto_restore_maximized=auto_restore,
            resize_factor=factor,
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

    def _update_behavior(self, key: str, value: bool):
        self.cfg.set_behavior(key, value)
        self.set_feedback("Centering behavior saved.")

    def _update_system(self, key: str, value: bool):
        self.cfg.set_system(key, value)
        self.set_feedback("System settings saved.")

    def _on_autostart_toggled(self, enabled: bool):
        if enabled:
            ok = enable_autostart()
            if ok:
                self.cfg.set_system("start_with_windows", True)
                self.set_feedback("Auto-start with Windows enabled.")
            else:
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
