import re
import unittest

from src.theme import (
    ACCENT,
    BASE,
    CRUST,
    DANGER,
    MANTLE,
    OVERLAY0,
    PANEL_BG,
    RED,
    SAPPHIRE,
    SECONDARY_TEXT,
    SUCCESS,
    SURFACE0,
    SURFACE1,
    SURFACE2,
    TEXT,
    WARNING,
    build_stylesheet,
    color_map,
)

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class TestTheme(unittest.TestCase):
    def test_all_colors_are_valid_hex(self):
        for name, value in color_map().items():
            self.assertRegex(value, HEX_RE, f"{name} is not a valid hex color: {value}")

    def test_semantic_aliases(self):
        self.assertEqual(ACCENT, SAPPHIRE)
        self.assertEqual(SUCCESS, "#a6e3a1")
        self.assertEqual(DANGER, RED)
        self.assertEqual(WARNING, "#f9e2af")
        self.assertEqual(SECONDARY_TEXT, OVERLAY0.replace("#6c7086", OVERLAY0[1:]) if False else SECONDARY_TEXT)
        self.assertEqual(SECONDARY_TEXT, "#a6adc8")
        self.assertEqual(PANEL_BG, BASE)

    def test_surfaces_distinct(self):
        # The Catppuccin surface ramp must use distinct colors
        order = [CRUST, MANTLE, BASE, SURFACE0, SURFACE1, SURFACE2]
        self.assertEqual(len(set(order)), len(order))

    def test_stylesheet_contains_core_widgets(self):
        css = build_stylesheet()
        for widget in ("QMainWindow", "QPushButton", "QComboBox", "QGroupBox",
                       "QProgressBar", "QCheckBox", "QTextEdit", "QLineEdit",
                       "QListWidget", "QTimeEdit", "QScrollBar"):
            self.assertIn(widget, css)

    def test_stylesheet_contains_object_names(self):
        css = build_stylesheet()
        self.assertIn("QPushButton#btnConvert", css)
        self.assertIn("QPushButton#btnCancel", css)
        self.assertIn("QPushButton#btnExpert", css)
        self.assertIn("QFrame#infoPanel", css)

    def test_stylesheet_contains_palette_colors(self):
        css = build_stylesheet()
        for color in (BASE, SURFACE0, SURFACE1, ACCENT, SUCCESS, DANGER):
            self.assertIn(color, css)

    def test_dialog_rules_keep_text_readable(self):
        # Regression: the "conversion finished" message box inherited the light
        # QLabel text but kept the platform's light dialog background.
        css = build_stylesheet()
        self.assertIn("QMessageBox", css)
        self.assertIn(f"QMessageBox {{ background-color: {MANTLE}; }}", css)
        self.assertIn(f"QDialog {{ background-color: {BASE}; }}", css)

        label_block = re.search(r"QMessageBox QLabel \{(.*?)\}", css, re.DOTALL)
        self.assertIsNotNone(label_block)
        self.assertIn(f"color: {TEXT}", label_block.group(1))

    def test_stylesheet_is_deterministic(self):
        self.assertEqual(build_stylesheet(), build_stylesheet())


if __name__ == "__main__":
    unittest.main()
