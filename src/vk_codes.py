"""
Virtual Key Codes and formatting utilities for Windows.
Maps Win32 virtual key codes (VK_*) to human-readable strings and vice-versa.
"""

# Modifier VK Codes
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_LWIN = 0x5B
VK_RWIN = 0x5C

MODIFIERS_MAP = {
    "ctrl": VK_CONTROL,
    "control": VK_CONTROL,
    "alt": VK_MENU,
    "shift": VK_SHIFT,
    "win": VK_LWIN,
    "windows": VK_LWIN,
}

MODIFIER_NAMES = ["ctrl", "alt", "shift", "win"]

# Primary VK mapping
VK_TO_NAME = {
    # Special keys
    0x08: "Backspace",
    0x09: "Tab",
    0x0D: "Enter",
    0x1B: "Escape",
    0x20: "Space",
    0x21: "PageUp",
    0x22: "PageDown",
    0x23: "End",
    0x24: "Home",
    0x25: "Left",
    0x26: "Up",
    0x27: "Right",
    0x28: "Down",
    0x2C: "PrintScreen",
    0x2D: "Insert",
    0x2E: "Delete",
    0x5D: "Apps",
    0x90: "NumLock",
    0x91: "ScrollLock",
    0x14: "CapsLock",
    # OEM / Punctuation
    0xBA: ";",
    0xBB: "=",
    0xBC: ",",
    0xBD: "-",
    0xBE: ".",
    0xBF: "/",
    0xC0: "`",
    0xDB: "[",
    0xDC: "\\",
    0xDD: "]",
    0xDE: "'",
}

# Add 0-9
for i in range(10):
    VK_TO_NAME[0x30 + i] = str(i)

# Add A-Z
for i in range(26):
    VK_TO_NAME[0x41 + i] = chr(ord('A') + i)

# Add Numpad 0-9 and operators
for i in range(10):
    VK_TO_NAME[0x60 + i] = f"Num{i}"
VK_TO_NAME[0x6A] = "Num*"
VK_TO_NAME[0x6B] = "Num+"
VK_TO_NAME[0x6D] = "Num-"
VK_TO_NAME[0x6E] = "Num."
VK_TO_NAME[0x6F] = "Num/"

# Add Function keys F1-F24
for i in range(1, 25):
    VK_TO_NAME[0x70 + (i - 1)] = f"F{i}"

# Inverted mapping: NAME -> VK
NAME_TO_VK = {name.lower(): vk for vk, name in VK_TO_NAME.items()}
# Synonyms
NAME_TO_VK.update({
    "esc": 0x1B,
    "return": 0x0D,
    "pgup": 0x21,
    "pgdn": 0x22,
    "del": 0x2E,
    "ins": 0x2D,
    "prtscr": 0x2C,
    "arrowup": 0x26,
    "arrowdown": 0x28,
    "arrowleft": 0x25,
    "arrowright": 0x27,
    "minus": 0xBD,
    "plus": 0xBB,
    "period": 0xBE,
    "comma": 0xBC,
    "slash": 0xBF,
    "backslash": 0xDC,
    "bracketleft": 0xDB,
    "bracketright": 0xDD,
    "semicolon": 0xBA,
    "quote": 0xDE,
    "tilde": 0xC0,
    "spacebar": 0x20,
})

def vk_to_name(vk: int) -> str:
    """Return a human-readable display string for a VK code."""
    return VK_TO_NAME.get(vk, f"Key(0x{vk:02X})")

def name_to_vk(name: str) -> int:
    """Return the VK code for a key name, or 0 if unknown."""
    return NAME_TO_VK.get(name.lower().strip(), 0)

def normalize_modifier(mod: str) -> str:
    """Normalize modifier string to canonical 'ctrl', 'alt', 'shift', or 'win'."""
    m = mod.lower().strip()
    if m in ("ctrl", "control"):
        return "ctrl"
    if m in ("alt", "menu"):
        return "alt"
    if m in ("shift",):
        return "shift"
    if m in ("win", "windows", "super", "cmd"):
        return "win"
    return m

def format_hotkey(modifiers: list, key: str) -> str:
    """
    Format modifier list and key into a standard display string.
    Example: ['ctrl', 'alt'], 'C' -> 'Ctrl + Alt + C'
    """
    order = ["ctrl", "alt", "shift", "win"]
    canonical_mods = set(normalize_modifier(m) for m in modifiers if m)
    
    parts = []
    for mod in order:
        if mod in canonical_mods:
            if mod == "ctrl":
                parts.append("Ctrl")
            elif mod == "alt":
                parts.append("Alt")
            elif mod == "shift":
                parts.append("Shift")
            elif mod == "win":
                parts.append("Win")
                
    if key:
        # Standardize key display
        k_upper = key.strip()
        if len(k_upper) == 1:
            parts.append(k_upper.upper())
        else:
            # Capitalize key names (e.g., Home, Left, F12)
            parts.append(k_upper.capitalize())
            
    return " + ".join(parts)

def parse_hotkey(hotkey_str: str) -> tuple[list[str], str]:
    """
    Parse a hotkey string like 'Ctrl + Alt + C' into (modifiers, key).
    Returns (['ctrl', 'alt'], 'C').
    """
    if not hotkey_str or not hotkey_str.strip():
        return [], ""
        
    raw_parts = [p.strip() for p in hotkey_str.replace("-", "+").split("+") if p.strip()]
    modifiers = []
    key = ""
    
    for part in raw_parts:
        norm = normalize_modifier(part)
        if norm in MODIFIER_NAMES:
            if norm not in modifiers:
                modifiers.append(norm)
        else:
            key = part
            
    return modifiers, key
