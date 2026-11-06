"""
Unit tests for Configuration Manager.
"""

import unittest
import os
import tempfile
from src.config_manager import ConfigManager, DEFAULT_CONFIG


class TestConfigManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config.json")
        self.cfg = ConfigManager(custom_path=self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_values(self):
        hk = self.cfg.get_hotkey("center_current")
        self.assertEqual(hk.get("key"), "C")
        self.assertEqual(set(hk.get("modifiers")), {"ctrl", "alt"})
        self.assertTrue(self.cfg.get_behavior("auto_restore_maximized"))

    def test_update_and_persist_hotkey(self):
        self.cfg.set_hotkey("center_current", ["ctrl", "shift"], "Space", "Ctrl + Shift + Space")
        
        # Create a new ConfigManager reading the same file
        cfg2 = ConfigManager(custom_path=self.config_path)
        hk = cfg2.get_hotkey("center_current")
        self.assertEqual(hk.get("key"), "Space")
        self.assertEqual(set(hk.get("modifiers")), {"ctrl", "shift"})
        self.assertEqual(hk.get("display"), "Ctrl + Shift + Space")

    def test_update_behavior(self):
        self.cfg.set_behavior("play_sound", False)
        cfg2 = ConfigManager(custom_path=self.config_path)
        self.assertFalse(cfg2.get_behavior("play_sound"))

    def test_reset_defaults(self):
        self.cfg.set_hotkey("center_current", ["win"], "X", "Win + X")
        self.cfg.reset_to_defaults()
        hk = self.cfg.get_hotkey("center_current")
        self.assertEqual(hk.get("key"), "C")


if __name__ == "__main__":
    unittest.main()
