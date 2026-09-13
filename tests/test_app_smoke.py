"""Headless smoke tests for the main window.

These guard the UI wiring (construction, language switching, presets and
derived output paths) without needing a display. When Qt cannot create an
offscreen QApplication the whole module is skipped instead of failing.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must be set before the first QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:  # pragma: no cover - depends on the host Qt plugins
    from PyQt5.QtCore import QSettings, QTime
    from PyQt5.QtGui import QDesktopServices
    from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

    from src.ffmpeg_handler import FFmpegHandler

    _APP = QApplication.instance() or QApplication([])

    # Isolate persisted QSettings in a throwaway directory so the tests are
    # independent from whatever the developer's machine has saved. The
    # two-argument `QSettings(organization, application)` constructor always
    # uses NativeFormat - the Windows *registry* - so the ini paths below only
    # take effect if the settings object is built with an explicit IniFormat.
    _SETTINGS_DIR = tempfile.mkdtemp(prefix="shuttle-codec-settings-")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, _SETTINGS_DIR)
    QSettings.setPath(QSettings.IniFormat, QSettings.SystemScope, _SETTINGS_DIR)

    def _isolated_settings(*_args: object) -> QSettings:
        return QSettings(
            QSettings.IniFormat, QSettings.UserScope, "ShuttleCodec", "ShuttleCodec"
        )

    # `src.app` builds its settings with `QSettings("ShuttleCodec", "ShuttleCodec")`;
    # redirect that call for the whole module (see setUpClass).
    _settings_patcher = patch("src.app.QSettings", _isolated_settings)

    HAS_QT = True
except Exception:  # pragma: no cover
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "Qt offscreen platform not available")
class TestMainWindowSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from src.app import MainWindow

        # Must be active *before* the window is constructed: the main window
        # reads and writes its QSettings in __init__.
        _settings_patcher.start()
        cls.addClassCleanup(_settings_patcher.stop)
        cls.addClassCleanup(shutil.rmtree, _SETTINGS_DIR, ignore_errors=True)
        cls.window = MainWindow()

    def setUp(self) -> None:
        from src.i18n import LANG_ES, set_language

        set_language(LANG_ES)
        # Reset every piece of cross-test state explicitly.
        self.window.input_file = None
        self.window._image_mode = False
        self.window._audio_mode = False
        self.window._current_summary = None
        self.window.frame_check.setChecked(False)
        self.window.target_check.setChecked(False)
        self.window.extract_audio_check.setChecked(False)
        self.window.image_format.setCurrentText("PNG")
        self.window.video_format.setCurrentText("MP4 (H.264)")
        self.window.hw_check.setChecked(False)
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

    # ─── helpers for the new modes ──────────────────────────────────────────
    def _temp_file(self, suffix: str, content: bytes = b"fake media content") -> str:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        handle.write(content)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def _temp_image(self) -> str:
        # Smallest valid PNG so ffprobe (when available) can read it.
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d4944415478da63f8ffff3f0005fe02fea7351a2b"
            "0000000049454e44ae426082"
        )
        return self._temp_file(".png", png)

    def test_image_input_switches_to_image_mode(self) -> None:
        image = self._temp_image()
        self.window.load_file(image)

        self.assertTrue(self.window._image_mode)
        mode, settings = self.window._get_settings_from_ui()
        self.assertEqual(mode, "image")
        self.assertEqual(settings["format"], "PNG")
        self.assertTrue(self.window._build_output_path(image).endswith(".png"))
        self.assertTrue(self.window.image_group.isVisibleTo(self.window))
        self.assertTrue(self.window.video_group.isHidden())
        self.assertTrue(self.window.trim_group.isHidden())

    def test_image_output_extension_follows_the_format(self) -> None:
        image = self._temp_image()
        self.window.load_file(image)
        self.window.image_format.setCurrentText("WebP")
        self.assertTrue(self.window._build_output_path(image).endswith(".webp"))

    def test_frame_export_uses_image_mode_and_the_chosen_timestamp(self) -> None:
        video = self._temp_file(".mp4")
        self.window.load_file(video)
        self.window._set_simple_mode(False)

        self.assertFalse(self.window.frame_time.isVisibleTo(self.window))
        self.window.frame_check.setChecked(True)

        mode, _settings = self.window._get_settings_from_ui()
        self.assertEqual(mode, "image")
        self.assertTrue(self.window.frame_time.isVisibleTo(self.window))
        self.assertTrue(self.window.trim_group.isHidden())
        # The video controls do not apply when exporting a frame.
        self.assertTrue(self.window.video_group.isHidden())

        self.window.frame_time.setTime(QTime(0, 0, 30))
        self.assertEqual(self.window._conversion_plan("image"), (30.0, None))

    def test_leaving_expert_mode_clears_the_expert_only_output_modes(self) -> None:
        video = self._temp_file(".mp4")
        self.window._set_simple_mode(False)
        self.window.load_file(video)
        self.window.frame_check.setChecked(True)
        self.window.extract_audio_check.setChecked(True)

        self.window._set_simple_mode(True)

        # Those switches live in expert-only groups: they must not keep
        # changing the output type where the user cannot see them.
        self.assertFalse(self.window.frame_check.isChecked())
        self.assertFalse(self.window.extract_audio_check.isChecked())
        mode, _settings = self.window._get_settings_from_ui()
        self.assertEqual(mode, "video")

    def test_extract_audio_switches_to_the_audio_track_only(self) -> None:
        video = self._temp_file(".mp4")
        self.window._set_simple_mode(False)
        self.window.load_file(video)
        self.window.audio_format.setCurrentText("MP3")
        self.window.extract_audio_check.setChecked(True)

        mode, settings = self.window._get_settings_from_ui()
        self.assertEqual(mode, "extract_audio")
        self.assertEqual(settings["audio_codec"], "libmp3lame")
        self.assertTrue(self.window._build_output_path(video).endswith(".mp3"))
        self.assertTrue(self.window.audio_group.isVisibleTo(self.window))

        cmd = self.window.ffmpeg.build_convert_command(video, "out.mp3", mode, settings)
        self.assertIn("-vn", cmd)
        self.assertNotIn("-c:v", cmd)

    def test_target_size_replaces_crf_in_the_estimate(self) -> None:
        self.window._set_simple_mode(False)
        self.window.target_size.setValue(25)
        self.window.target_check.setChecked(True)

        self.assertEqual(self.window._collect_video_settings()["target_size_mb"], 25)
        self.assertIn("25", self.window.info_estimate.text())
        self.assertFalse(self.window.video_crf.isEnabled())

    def test_estimate_is_dash_without_a_loaded_file(self) -> None:
        self.assertNotIn("MB", self.window.info_estimate.text())

    def test_batch_queue_is_persisted_and_restored(self) -> None:
        video = self._temp_file(".mp4")
        self.window._add_single_to_batch(video)

        # Simulate closing the window, then starting the app again.
        self.window._save_settings()
        self.window.batch_items.clear()
        self.window.batch_list.clear()
        self.window._restore_batch()

        self.assertEqual([path for path, _ in self.window.batch_items], [video])
        self.assertEqual(self.window.batch_list.count(), 1)

    def test_restoring_the_mode_does_not_wipe_the_persisted_queue(self) -> None:
        """Regression: refreshing the button used to save an empty queue.

        `_load_settings` restores the mode before the queue, so a save triggered
        by that refresh would erase the batch left from the previous session.
        """
        video = self._temp_file(".mp4")
        self.window._add_single_to_batch(video)
        self.window.settings.setValue("simple_mode", "true")
        self.window._save_settings()

        # Simulate the next start: the queue starts empty, settings are loaded.
        self.window.batch_items.clear()
        self.window.batch_list.clear()
        self.window._set_simple_mode(True)
        self.window._restore_batch()

        self.assertEqual([path for path, _ in self.window.batch_items], [video])

    def test_restore_batch_skips_missing_files(self) -> None:
        self.window.settings.setValue("batch/items", ["Z:/gone/missing.mp4"])
        self.window._restore_batch()
        self.assertEqual(self.window.batch_items, [])

    def test_simple_mode_does_not_offer_the_hidden_batch_queue(self) -> None:
        """Regression: a restored queue used to hijack the convert button.

        In simple mode the batch list is hidden, so the button offered to
        "convert 1 file" while pressing it went down the single-file path and
        asked for a file to be selected.
        """
        from src.i18n import tr

        video = self._temp_file(".mp4")
        self.window._set_simple_mode(True)
        self.window._add_single_to_batch(video)

        self.assertFalse(self.window.batch_list.isVisibleTo(self.window))
        self.assertEqual(self.window.convert_btn.text(), tr("btn_convert"))
        # Nothing is loaded, so there is nothing this button could convert.
        self.assertFalse(self.window.convert_btn.isEnabled())

    def test_expert_mode_offers_the_batch_queue(self) -> None:
        video = self._temp_file(".mp4")
        self.window._set_simple_mode(False)
        self.window._add_single_to_batch(video)

        self.assertIn("1", self.window.convert_btn.text())
        self.assertTrue(self.window.convert_btn.isEnabled())

    def test_cancelled_batch_does_not_report_completion(self) -> None:
        """A cancelled batch also reaches all_finished: no "done" dialog then."""
        self.window.batch_manager.cancelled = True
        try:
            with patch.object(QMessageBox, "information") as info, \
                    patch.object(self.window, "_maybe_shutdown") as shutdown:
                self.window._on_batch_all_finished(0, 2)
        finally:
            self.window.batch_manager.cancelled = False
        info.assert_not_called()
        shutdown.assert_not_called()

    def test_target_size_fallback_is_logged(self) -> None:
        """The docs promise a log line when the target size cannot be honoured."""
        video = self._temp_file(".mp4")  # 4 bytes: ffprobe can read no duration
        self.window._set_simple_mode(False)
        self.window.load_file(video)
        self.window.target_size.setValue(25)
        self.window.target_check.setChecked(True)
        self.window.log_output.clear()
        out = os.path.join(os.path.dirname(video), "out.mp4")

        with patch.object(self.window.ffmpeg, "check_ffmpeg", return_value=True), \
                patch.object(QFileDialog, "getSaveFileName", return_value=(out, "")), \
                patch("src.app.ConversionThread"):
            self.window.start_conversion()

        self.assertIn("objetivo", self.window.log_output.toPlainText().lower())

    def test_report_problem_copies_diagnostics_when_the_browser_fails(self) -> None:
        with patch.object(QDesktopServices, "openUrl", return_value=False), \
                patch.object(QMessageBox, "information"):
            self.window.log_output.setPlainText("▶ conversion")
            self.window.report_problem()
        self.assertIn("Shuttle Codec", QApplication.clipboard().text())

    def test_report_issue_url_is_prefilled(self) -> None:
        from src.diagnostics import build_issue_url

        url = build_issue_url("diagnostics here", title="[Bug] ")
        self.assertIn("github.com/jmarc9901/shuttle-codec/issues/new", url)
        self.assertIn("diagnostics", url)

    def test_output_path_uses_selected_extension(self) -> None:
        self.window._set_simple_mode(False)
        idx = self.window.video_format.findText("MKV (H.264)")
        self.window.video_format.setCurrentIndex(idx)
        self.assertTrue(self.window._build_output_path("/media/clip.mp4").endswith(".mkv"))

    def test_dialogs_use_the_dark_palette(self) -> None:
        """Regression: QMessageBox rendered light text on the light system background."""
        from PyQt5.QtGui import QPalette

        from src.theme import BASE, TEXT

        palette = QApplication.instance().palette()
        self.assertEqual(palette.color(QPalette.Window).name(), BASE)
        self.assertEqual(palette.color(QPalette.WindowText).name(), TEXT)
        self.assertEqual(palette.color(QPalette.ToolTipBase).name(), "#313244")


    # ─── conversion / dialog flows (no real encoding) ────────────────────────
    def test_start_conversion_builds_a_software_command(self) -> None:
        video = self._temp_file(".mp4")
        self.window._set_simple_mode(False)
        self.window.load_file(video)
        self.window.video_format.setCurrentText("MP4 (H.264)")
        self.window.hw_check.setChecked(False)
        out = os.path.join(os.path.dirname(video), "out.mp4")

        with patch.object(QFileDialog, "getSaveFileName", return_value=(out, "")), \
                patch("src.app.ConversionThread") as thread_cls:
            self.window.start_conversion()

        self.assertTrue(thread_cls.called)
        cmd = thread_cls.call_args[0][1]
        self.assertIn("libx264", cmd)
        # Software encoding needs no fallback command.
        self.assertIsNone(thread_cls.call_args[1]["fallback_cmd"])

    def test_start_conversion_offers_a_cpu_fallback_for_hardware_encoding(self) -> None:
        video = self._temp_file(".mp4")
        self.window._set_simple_mode(False)
        self.window.load_file(video)
        self.window.video_format.setCurrentText("MP4 (H.264)")
        self.window.hw_check.setVisible(True)
        self.window.hw_check.setChecked(True)
        out = os.path.join(os.path.dirname(video), "out.mp4")

        with patch.object(QFileDialog, "getSaveFileName", return_value=(out, "")), \
                patch.object(FFmpegHandler, "_get_hw_encoder", return_value="h264_nvenc"), \
                patch("src.app.ConversionThread") as thread_cls:
            self.window.start_conversion()

        cmd = thread_cls.call_args[0][1]
        fallback = thread_cls.call_args[1]["fallback_cmd"]
        self.assertIn("h264_nvenc", cmd)
        self.assertIsNotNone(fallback)
        self.assertIn("libx264", fallback)

    def test_start_conversion_without_a_file_warns(self) -> None:
        self.window.input_file = None
        with patch.object(QMessageBox, "warning") as warning, \
                patch.object(self.window.ffmpeg, "check_ffmpeg", return_value=True):
            self.window.start_conversion()
        warning.assert_called_once()

    def test_start_conversion_aborts_when_the_save_dialog_is_cancelled(self) -> None:
        video = self._temp_file(".mp4")
        self.window.load_file(video)
        with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")), \
                patch("src.app.ConversionThread") as thread_cls:
            self.window.start_conversion()
        self.assertFalse(thread_cls.called)

    def test_conversion_finished_enables_the_buttons_again(self) -> None:
        self.window.cancel_btn.setEnabled(True)
        with patch.object(QMessageBox, "information", return_value=QMessageBox.Ok):
            self.window._on_conversion_finished(True, "clip → out", "Z:/nope/out.mp4")
        self.assertTrue(self.window.convert_btn.isEnabled())
        self.assertFalse(self.window.cancel_btn.isEnabled())

    def test_cancel_conversion_is_logged(self) -> None:
        with patch.object(self.window.ffmpeg, "cancel_conversion") as cancel:
            self.window.cancel_conversion()
        cancel.assert_called_once()
        self.assertIn("cancelada", self.window.log_output.toPlainText().lower())

    def test_browse_file_rejects_an_invalid_selection(self) -> None:
        with patch.object(QFileDialog, "getOpenFileName", return_value=("Z:/nope/x.mp4", "")), \
                patch.object(QMessageBox, "warning") as warning:
            self.window.browse_file()
        warning.assert_called_once()

    def test_add_and_remove_batch_items(self) -> None:
        first = self._temp_file(".mp4")
        second = self._temp_file(".mp4")
        with patch.object(QFileDialog, "getOpenFileNames", return_value=([first, second], "")):
            self.window._add_to_batch()
        self.assertEqual(len(self.window.batch_items), 2)

        self.window.batch_list.setCurrentRow(0)
        self.window._remove_from_batch()
        self.assertEqual([path for path, _ in self.window.batch_items], [second])

    def test_check_ffmpeg_reports_a_missing_binary(self) -> None:
        with patch.object(self.window.ffmpeg, "check_ffmpeg", return_value=False), \
                patch.object(QMessageBox, "critical") as critical:
            self.window._check_ffmpeg()
        critical.assert_called_once()
        self.assertFalse(self.window._ffmpeg_ok)

    def test_language_change_is_applied_and_persisted(self) -> None:
        index = self.window.lang_combo.findData("en")
        self.window._on_language_change(index)
        self.assertIn("Start conversion", self.window.convert_btn.text())
        self.assertEqual(self.window.settings.value("window/language"), "en")

        self.window.lang_combo.setCurrentIndex(self.window.lang_combo.findData("es"))
        self.window.retranslate_ui()

    def test_quit_shortcut_closes_the_window(self) -> None:
        with patch.object(self.window, "close") as close:
            self.window._quit()
        close.assert_called_once()

    def test_close_event_is_ignored_while_encoding(self) -> None:
        from PyQt5.QtGui import QCloseEvent

        fake_thread = MagicMock()
        fake_thread.isRunning.return_value = True
        self.window.current_thread = fake_thread
        event = QCloseEvent()
        try:
            with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
                self.window.closeEvent(event)
            self.assertFalse(event.isAccepted())
        finally:
            self.window.current_thread = None

    def test_close_event_cancels_a_running_conversion(self) -> None:
        from PyQt5.QtGui import QCloseEvent

        fake_thread = MagicMock()
        fake_thread.isRunning.return_value = True
        self.window.current_thread = fake_thread
        event = QCloseEvent()
        try:
            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
                    patch.object(self.window.ffmpeg, "cancel_conversion"):
                self.window.closeEvent(event)
            self.assertTrue(event.isAccepted())
        finally:
            self.window.current_thread = None

    # ─── shutdown flow (never actually powers anything off) ──────────────────
    def test_shutdown_is_skipped_unless_opted_in(self) -> None:
        self.window.shutdown_check.setChecked(False)
        with patch("src.app.shutdown_command") as command:
            self.window._maybe_shutdown()
        command.assert_not_called()

    def test_shutdown_reports_when_the_platform_is_unsupported(self) -> None:
        self.window.shutdown_check.setChecked(True)
        self.window.log_output.setPlainText("")
        try:
            with patch("src.app.shutdown_command", return_value=None):
                self.window._maybe_shutdown()
            self.assertTrue(self.window.log_output.toPlainText())
        finally:
            self.window.shutdown_check.setChecked(False)

    def test_shutdown_dialog_runs_the_command_on_timeout(self) -> None:
        with patch.object(QMessageBox, "addButton", return_value=object()), \
                patch.object(QMessageBox, "exec_"), \
                patch.object(QMessageBox, "clickedButton", return_value=None), \
                patch("src.app.subprocess.Popen") as popen:
            self.window._show_shutdown_dialog(["systemctl", "poweroff"])
        popen.assert_called_once_with(["systemctl", "poweroff"])

    def test_shutdown_dialog_aborts_when_the_user_cancels(self) -> None:
        sentinel = object()
        with patch.object(QMessageBox, "addButton", return_value=sentinel), \
                patch.object(QMessageBox, "exec_"), \
                patch.object(QMessageBox, "clickedButton", return_value=sentinel), \
                patch("src.app.subprocess.Popen") as popen:
            self.window._show_shutdown_dialog(["systemctl", "poweroff"])
        popen.assert_not_called()

    # ─── log and accessibility ───────────────────────────────────────────────
    def test_log_entries_are_timestamped(self) -> None:
        self.window.log_output.clear()
        self.window._append_log("hola")
        self.assertRegex(self.window.log_output.toPlainText(), r"^\[\d{2}:\d{2}:\d{2}\] hola$")

    def test_indented_log_lines_keep_their_alignment(self) -> None:
        """Batch results and command arguments are continuations, not entries."""
        self.window.log_output.clear()
        self.window._append_log("  ✅ [1/2] out.mp4")
        self.assertTrue(self.window.log_output.toPlainText().startswith("  ✅"))

    def test_main_controls_have_accessible_names(self) -> None:
        """A screen reader announces an unnamed widget as just "button"."""
        controls = (
            self.window.convert_btn, self.window.cancel_btn, self.window.browse_btn,
            self.window.report_btn, self.window.lang_combo, self.window.expert_btn,
            self.window.video_format, self.window.video_crf, self.window.video_resolution,
            self.window.image_format, self.window.image_quality, self.window.audio_format,
            self.window.target_size, self.window.trim_start, self.window.trim_end,
            self.window.batch_list, self.window.progress_bar, self.window.log_output,
        )
        for widget in controls:
            with self.subTest(widget=type(widget).__name__):
                self.assertTrue(widget.accessibleName(), "widget has no accessible name")

    def test_accessible_names_follow_the_language(self) -> None:
        from src.i18n import LANG_EN, set_language

        set_language(LANG_EN)
        self.window.retranslate_ui()
        self.assertIn("Start", self.window.convert_btn.accessibleName())

    def test_invalid_trim_range_is_stated_in_words(self) -> None:
        """Colour alone cannot carry this: the tooltip says what is wrong."""
        from src.i18n import tr

        self.window.trim_start.setTime(QTime(0, 0, 10))
        self.window.trim_end.setTime(QTime(0, 0, 5))
        self.assertEqual(self.window.trim_duration.toolTip(), tr("trim_invalid"))
        self.assertEqual(self.window.trim_duration.accessibleDescription(), tr("trim_invalid"))

        self.window.trim_end.setTime(QTime(0, 0, 20))
        self.assertEqual(self.window.trim_duration.toolTip(), "")
        self.assertEqual(self.window.trim_duration.text(), "00:00:10")


class TestMainEntryPoint(unittest.TestCase):
    @unittest.skipUnless(HAS_QT, "Qt offscreen platform not available")
    def test_main_runs_the_application(self) -> None:
        from src.main import main

        with patch("src.main.QApplication") as app_cls, patch("src.main.MainWindow") as window_cls:
            app_cls.return_value.exec_.return_value = 0
            with self.assertRaises(SystemExit):
                main()
        window_cls.return_value.show.assert_called_once()


if __name__ == "__main__":
    unittest.main()
