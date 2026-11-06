"""
Unit tests for Virtual Key Code mapping, parsing, and formatting.
"""

import unittest
from src.vk_codes import (
    vk_to_name,
    name_to_vk,
    format_hotkey,
    parse_hotkey,
    normalize_modifier,
)


class TestVKCodes(unittest.TestCase):

    def test_vk_to_name(self):
        self.assertEqual(vk_to_name(0x43), "C")
        self.assertEqual(vk_to_name(0x20), "Space")
        self.assertEqual(vk_to_name(0x1B), "Escape")
        self.assertEqual(vk_to_name(0x70), "F1")
        self.assertEqual(vk_to_name(0x7B), "F12")
        self.assertEqual(vk_to_name(0x25), "Left")
        self.assertEqual(vk_to_name(0x27), "Right")

    def test_name_to_vk(self):
        self.assertEqual(name_to_vk("C"), 0x43)
        self.assertEqual(name_to_vk("c"), 0x43)
        self.assertEqual(name_to_vk("Space"), 0x20)
        self.assertEqual(name_to_vk("esc"), 0x1B)
        self.assertEqual(name_to_vk("Escape"), 0x1B)
        self.assertEqual(name_to_vk("F12"), 0x7B)
        self.assertEqual(name_to_vk("Left"), 0x25)
        self.assertEqual(name_to_vk("Right"), 0x27)

    def test_format_hotkey(self):
        self.assertEqual(format_hotkey(["ctrl", "alt"], "C"), "Ctrl + Alt + C")
        self.assertEqual(format_hotkey(["alt", "ctrl"], "c"), "Ctrl + Alt + C")
        self.assertEqual(format_hotkey(["ctrl", "shift", "win"], "F11"), "Ctrl + Shift + Win + F11")
        self.assertEqual(format_hotkey([], "F5"), "F5")
        self.assertEqual(format_hotkey(["alt"], "Left"), "Alt + Left")

    def test_parse_hotkey(self):
        mods, key = parse_hotkey("Ctrl + Alt + C")
        self.assertEqual(set(mods), {"ctrl", "alt"})
        self.assertEqual(key, "C")

        mods, key = parse_hotkey("Win + Shift + F12")
        self.assertEqual(set(mods), {"win", "shift"})
        self.assertEqual(key, "F12")

        mods, key = parse_hotkey("Ctrl-Alt-Right")
        self.assertEqual(set(mods), {"ctrl", "alt"})
        self.assertEqual(key, "Right")


if __name__ == "__main__":
    unittest.main()
