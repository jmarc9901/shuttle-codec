import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import (
    format_seconds,
    get_icon_path,
    human_size,
    open_folder,
    qtime_to_seconds,
    safe_int,
    seconds_to_qtime_components,
)


class FakeQTime:
    """Duck-typed stand-in for QTime (avoids requiring a QApplication)."""

    def __init__(self, h: int, m: int, s: int) -> None:
        self._h, self._m, self._s = h, m, s

    def hour(self) -> int:
        return self._h

    def minute(self) -> int:
        return self._m

    def second(self) -> int:
        return self._s


class TestFormatSeconds(unittest.TestCase):
    def test_under_a_minute(self):
        self.assertEqual(format_seconds(0), "0s")
        self.assertEqual(format_seconds(45), "45s")

    def test_minutes(self):
        self.assertEqual(format_seconds(60), "1m 00s")
        self.assertEqual(format_seconds(185), "3m 05s")

    def test_hours(self):
        self.assertEqual(format_seconds(3900), "1h 05m 00s")
        self.assertEqual(format_seconds(7325), "2h 02m 05s")

    def test_negative_clamps_to_zero(self):
        self.assertEqual(format_seconds(-10), "0s")


class TestSecondsToQtimeComponents(unittest.TestCase):
    def test_roundtrip_with_qtime(self):
        comps = seconds_to_qtime_components(3900)
        fake = FakeQTime(*comps)
        self.assertEqual(qtime_to_seconds(fake), 3900)

    def test_negative_clamps(self):
        self.assertEqual(seconds_to_qtime_components(-5), (0, 0, 0))


class TestHumanSize(unittest.TestCase):
    def test_one_mb(self):
        self.assertEqual(human_size(1024 * 1024), "1.0 MB")

    def test_fractional(self):
        self.assertEqual(human_size(512 * 1024), "0.5 MB")


class TestSafeInt(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(safe_int("42"), 42)
        self.assertEqual(safe_int("-7"), -7)

    def test_invalid_returns_default(self):
        self.assertIsNone(safe_int("abc"))
        self.assertEqual(safe_int("abc", 0), 0)
        self.assertIsNone(safe_int(None))


class TestIconPath(unittest.TestCase):
    def test_returns_existing_path_or_logo(self):
        # In dev runs the logo must resolve; in frozen runs _MEIPASS is used.
        path = get_icon_path()
        self.assertTrue(os.path.isabs(path))
        self.assertIn("logo.png", path)


class TestOpenFolder(unittest.TestCase):
    def test_nonexistent_folder_returns_false(self):
        self.assertFalse(open_folder(""))
        self.assertFalse(open_folder("Z:/definitely/not/a/real/path"))


if __name__ == "__main__":
    unittest.main()
