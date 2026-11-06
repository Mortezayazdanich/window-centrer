"""
Unit tests for Window Centering Geometry & Multi-Monitor calculation algorithms.
"""

import unittest
from src.window_manager import RECT


def compute_target_coordinates(
    work_rect: RECT,
    win_w: int,
    win_h: int,
    margin_l: int = 0,
    margin_t: int = 0,
    auto_shrink: bool = True,
    resize_factor: float = None
) -> tuple[int, int, int, int]:
    """Pure algorithm simulating WindowManager coordinate calculation."""
    work_w = work_rect.width
    work_h = work_rect.height

    target_w = win_w
    target_h = win_h

    if resize_factor and 0.1 <= resize_factor <= 1.0:
        target_w = int(work_w * resize_factor)
        target_h = int(work_h * resize_factor)
    elif auto_shrink:
        if target_w > work_w:
            target_w = work_w
        if target_h > work_h:
            target_h = work_h

    vis_x = work_rect.left + (work_w - target_w) // 2
    vis_y = work_rect.top + (work_h - target_h) // 2

    actual_win_x = vis_x - margin_l
    actual_win_y = vis_y - margin_t

    return actual_win_x, actual_win_y, target_w, target_h


class TestWindowGeometry(unittest.TestCase):

    def test_primary_monitor_centering(self):
        # Primary 1080p screen, taskbar height = 40px at bottom
        work = RECT(0, 0, 1920, 1040)
        # Window size 800x600, no shadow margin
        x, y, w, h = compute_target_coordinates(work, 800, 600)
        
        # Center x: 0 + (1920 - 800) // 2 = 560
        # Center y: 0 + (1040 - 600) // 2 = 220
        self.assertEqual(x, 560)
        self.assertEqual(y, 220)
        self.assertEqual(w, 800)
        self.assertEqual(h, 600)

    def test_dwm_shadow_margin_compensation(self):
        # Windows 10/11 7px invisible resize border on left, 0 on top
        work = RECT(0, 0, 1920, 1080)
        x, y, w, h = compute_target_coordinates(work, 1000, 800, margin_l=7, margin_t=0)
        
        # Visible target: x = (1920 - 1000) // 2 = 460
        # Outer win x should be 460 - 7 = 453 so visible frame starts exactly at 460!
        self.assertEqual(x, 453)
        self.assertEqual(y, 140)

    def test_secondary_monitor_left_negative_coordinates(self):
        # Secondary monitor placed to the left: -1920 to 0
        work = RECT(-1920, 0, 0, 1080)
        x, y, w, h = compute_target_coordinates(work, 1000, 700)
        
        # Center x: -1920 + (1920 - 1000) // 2 = -1920 + 460 = -1460
        # Center y: 0 + (1080 - 700) // 2 = 190
        self.assertEqual(x, -1460)
        self.assertEqual(y, 190)

    def test_secondary_monitor_stacked_above(self):
        # Secondary monitor placed above primary: y: -1080 to 0
        work = RECT(0, -1080, 1920, 0)
        x, y, w, h = compute_target_coordinates(work, 1200, 800)
        
        # Center x: 0 + (1920 - 1200) // 2 = 360
        # Center y: -1080 + (1080 - 800) // 2 = -1080 + 140 = -940
        self.assertEqual(x, 360)
        self.assertEqual(y, -940)

    def test_oversized_window_auto_shrink(self):
        work = RECT(0, 0, 1920, 1080)
        # Window larger than screen (e.g. 2560x1440)
        x, y, w, h = compute_target_coordinates(work, 2560, 1440, auto_shrink=True)
        self.assertEqual(w, 1920)
        self.assertEqual(h, 1080)
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)

    def test_resize_factor(self):
        work = RECT(0, 0, 1920, 1000)
        x, y, w, h = compute_target_coordinates(work, 500, 500, resize_factor=0.5)
        self.assertEqual(w, 960)
        self.assertEqual(h, 500)
        self.assertEqual(x, (1920 - 960) // 2)
        self.assertEqual(y, (1000 - 500) // 2)


if __name__ == "__main__":
    unittest.main()
