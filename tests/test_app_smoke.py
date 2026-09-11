"""Headless smoke tests for the main window.

These guard the UI wiring (construction, language switching, presets and
derived output paths) without needing a display. When Qt cannot create an
offscreen QApplication the whole module is skipped instead of failing.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must be set before the first QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:  # pragma: no cover - depends on the host Qt plugins
    from PyQt5.QtCore import QSettings
    from PyQt5.QtWidgets import QApplication

    _APP = QApplication.instance() or QApplication([])

    # Isolate persisted QSettings in a throwaway directory so the tests are
    # independent from whatever the developer's machine has saved.
    _SETTINGS_DIR = tempfile.mkdtemp(prefix="shuttle-codec-settings-")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, _SETTINGS_DIR)
    QSettings.setPath(QSettings.IniFormat, QSettings.SystemScope, _SETTINGS_DIR)

    HAS_QT = True
except Exception:  # pragma: no cover
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "Qt offscreen platform not available")
class TestMainWindowSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from src.app import MainWindow

        cls.window = MainWindow()

    def setUp(self) -> None:
        from src.i18n import LANG_ES, set_language

        set_language(LANG_ES)
        self.window.input_file = None
        self.window._set_simple_mode(True)
        self.window._clear_batch()
        self.window.retranslate_ui()

    def test_window_and_presets_construct(self) -> None:
        self.assertEqual(self.window.preset_combo.count(), 8)
        self.assertTrue(self.window.simple_mode)
        # Nothing selected yet, so conversion must not be offered.
        self.assertFalse(self.window.convert_btn.isEnabled())

    def test_convert_enabled_once_a_file_is_loaded(self) -> None:
        self.window.input_file = "/media/clip.mp4"
        self.window._update_batch_ui()
        self.assertTrue(self.window.convert_btn.isEnabled())

        self.window.clear_file()
        self.assertFalse(self.window.convert_btn.isEnabled())

    def test_language_switch_updates_labels(self) -> None:
        from src.i18n import LANG_EN, LANG_ES, set_language

        set_language(LANG_EN)
        self.window.retranslate_ui()
        self.assertIn("Start conversion", self.window.convert_btn.text())

        set_language(LANG_ES)
        self.window.retranslate_ui()
        self.assertIn("Iniciar", self.window.convert_btn.text())

    def test_hardware_label_reflects_backend(self) -> None:
        self.window._hw_info = "NVENC (NVIDIA)"
        self.window._update_hw_label()
        self.assertIn("NVENC", self.window.hw_check.text())

        self.window._hw_info = ""
        self.window._update_hw_label()
        self.assertNotIn("NVENC", self.window.hw_check.text())

    def test_ffmpeg_status_tracks_availability(self) -> None:
        for available in (False, True):
            with self.subTest(available=available):
                self.window._ffmpeg_ok = available
                self.window._update_ffmpeg_status()
                self.assertNotEqual(self.window.ffmpeg_status.text(), "")

    def test_mode_toggle(self) -> None:
        self.window.expert_btn.setChecked(True)
        self.window._toggle_mode()
        self.assertFalse(self.window.simple_mode)

        self.window.expert_btn.setChecked(False)
        self.window._toggle_mode()
        self.assertTrue(self.window.simple_mode)

    def test_every_preset_produces_video_settings(self) -> None:
        from src.presets import get_preset_ids

        for preset_id in get_preset_ids():
            with self.subTest(preset=preset_id):
                self.window.preset_combo.setCurrentIndex(
                    self.window.preset_combo.findData(preset_id)
                )
                mode, settings = self.window._get_settings_from_ui()
                self.assertEqual(mode, "video")
                self.assertTrue(settings["format"])

    def test_output_path_uses_selected_extension(self) -> None:
        self.window._set_simple_mode(False)
        idx = self.window.video_format.findText("MKV (H.264)")
        self.window.video_format.setCurrentIndex(idx)
        self.assertTrue(self.window._build_output_path("/media/clip.mp4").endswith(".mkv"))


if __name__ == "__main__":
    unittest.main()
