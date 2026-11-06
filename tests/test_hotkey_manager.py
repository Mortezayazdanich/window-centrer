"""
Unit tests for Hotkey Binding & Matching logic.
"""

import unittest
from src.hotkey_manager import HotkeyBinding


class TestHotkeyBinding(unittest.TestCase):

    def test_hotkey_matching(self):
        called = False
        def dummy_cb():
            nonlocal called
            called = True

        binding = HotkeyBinding("test_center", ["ctrl", "alt"], "C", dummy_cb)
        
        # Exact match: VK_C (0x43) with ctrl + alt
        self.assertTrue(binding.matches(0x43, {"ctrl", "alt"}))
        
        # Wrong key
        self.assertFalse(binding.matches(0x44, {"ctrl", "alt"}))
        
        # Missing Alt
        self.assertFalse(binding.matches(0x43, {"ctrl"}))
        
        # Extra Shift pressed
        self.assertFalse(binding.matches(0x43, {"ctrl", "alt", "shift"}))

    def test_arrow_keys_matching(self):
        binding = HotkeyBinding("test_next", ["ctrl", "alt"], "Right", lambda: None)
        self.assertEqual(binding.vk_code, 0x27)
        self.assertTrue(binding.matches(0x27, {"ctrl", "alt"}))


if __name__ == "__main__":
    unittest.main()
