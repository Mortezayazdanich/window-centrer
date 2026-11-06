"""
Configuration Manager for Window Centerer.
Handles loading, saving, validating, and migrating user configuration settings in JSON.
"""

import json
import os
from typing import Dict, Any, List

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "hotkeys": {
        "center_current": {
            "modifiers": ["ctrl", "alt"],
            "key": "C",
            "enabled": True,
            "display": "Ctrl + Alt + C",
        },
        "cycle_next": {
            "modifiers": ["ctrl", "alt"],
            "key": "Right",
            "enabled": True,
            "display": "Ctrl + Alt + Right",
        },
        "cycle_prev": {
            "modifiers": ["ctrl", "alt"],
            "key": "Left",
            "enabled": True,
            "display": "Ctrl + Alt + Left",
        },
        "center_resize": {
            "modifiers": ["ctrl", "alt"],
            "key": "R",
            "enabled": False,
            "display": "Ctrl + Alt + R",
        },
    },
    "behavior": {
        "auto_restore_maximized": True,
        "auto_shrink_oversized": True,
        "resize_factor": 0.75,
        "play_sound": True,
        "show_notifications": False,
    },
    "system": {
        "start_minimized": False,
        "minimize_to_tray_on_close": True,
        "start_with_windows": False,
    },
}


class ConfigManager:
    """Manages application configuration in %APPDATA%/WindowCenterer/config.json."""

    def __init__(self, custom_path: str = None):
        if custom_path:
            self.config_path = custom_path
        else:
            appdata = os.environ.get("APPDATA")
            if appdata:
                config_dir = os.path.join(appdata, "WindowCenterer")
            else:
                config_dir = os.path.join(os.path.expanduser("~"), ".window_centerer")

            try:
                os.makedirs(config_dir, exist_ok=True)
                self.config_path = os.path.join(config_dir, "config.json")
            except Exception:
                self.config_path = "config.json"

        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Load configuration from disk or populate with defaults."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = self._merge_defaults(data, DEFAULT_CONFIG)
                    return self.config
            except Exception:
                pass

        # Use defaults if file missing or corrupted
        self.config = json.loads(json.dumps(DEFAULT_CONFIG))
        self.save()
        return self.config

    def _merge_defaults(self, loaded: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge loaded configuration with defaults to ensure all keys exist."""
        result = dict(defaults)
        for k, v in loaded.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge_defaults(v, result[k])
            else:
                result[k] = v
        return result

    def save(self) -> bool:
        """Persist current configuration to disk."""
        try:
            parent_dir = os.path.dirname(self.config_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            tmp_path = self.config_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)

            if os.path.exists(self.config_path):
                os.replace(tmp_path, self.config_path)
            else:
                os.rename(tmp_path, self.config_path)
            return True
        except Exception:
            return False

    def reset_to_defaults(self):
        """Reset configuration back to default values."""
        self.config = json.loads(json.dumps(DEFAULT_CONFIG))
        self.save()

    def get_hotkey(self, action: str) -> Dict[str, Any]:
        return self.config.get("hotkeys", {}).get(action, {})

    def set_hotkey(self, action: str, modifiers: List[str], key: str, display: str, enabled: bool = True):
        if "hotkeys" not in self.config:
            self.config["hotkeys"] = {}
        self.config["hotkeys"][action] = {
            "modifiers": modifiers,
            "key": key,
            "display": display,
            "enabled": enabled,
        }
        self.save()

    def get_behavior(self, key: str, default: Any = None) -> Any:
        return self.config.get("behavior", {}).get(key, default)

    def set_behavior(self, key: str, value: Any):
        if "behavior" not in self.config:
            self.config["behavior"] = {}
        self.config["behavior"][key] = value
        self.save()

    def get_system(self, key: str, default: Any = None) -> Any:
        return self.config.get("system", {}).get(key, default)

    def set_system(self, key: str, value: Any):
        if "system" not in self.config:
            self.config["system"] = {}
        self.config["system"][key] = value
        self.save()
