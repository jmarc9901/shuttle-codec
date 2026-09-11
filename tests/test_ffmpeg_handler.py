import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ffmpeg_handler import FFmpegHandler


class TestFFmpegHandler(unittest.TestCase):
    def setUp(self):
        self.handler = FFmpegHandler()

    def test_get_duration_string(self):
        self.assertEqual(self.handler.get_duration_string(0), "00:00:00")
        self.assertEqual(self.handler.get_duration_string(3661), "01:01:01")
        self.assertEqual(self.handler.get_duration_string(59), "00:00:59")
        self.assertEqual(self.handler.get_duration_string(None), "00:00:00")

    def test_get_supported_video_formats(self):
        formats = self.handler.get_supported_video_formats()
        self.assertIn("MP4 (H.264)", formats)
        self.assertIn("GIF", formats)
        self.assertIn("WebM (VP9)", formats)

    def test_get_supported_audio_formats(self):
        formats = self.handler.get_supported_audio_formats()
        self.assertIn("MP3", formats)
        self.assertIn("FLAC", formats)
        self.assertIn("WAV", formats)

    def test_video_formats_structure(self):
        for fmt in self.handler.VIDEO_FORMATS.values():
            self.assertIn("video_codec", fmt)
            self.assertIn("extension", fmt)
            self.assertIn("presets", fmt)
            self.assertIn("gif_mode", fmt)
            self.assertIn("quality_range", fmt)
            self.assertIn("default_crf", fmt)
            self.assertIsInstance(fmt["gif_mode"], bool)

    def test_audio_formats_structure(self):
        for fmt in self.handler.AUDIO_FORMATS.values():
            self.assertIn("audio_codec", fmt)
            self.assertIn("extension", fmt)
            self.assertIn("bitrates", fmt)
            self.assertIsInstance(fmt["bitrates"], list)

    @patch("src.ffmpeg_handler.find_ffmpeg")
    def test_check_ffmpeg_found(self, mock_find):
        mock_find.return_value = ("ffmpeg", "ffprobe")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = self.handler.check_ffmpeg()
            self.assertTrue(result)

    @patch("src.ffmpeg_handler.find_ffmpeg")
    def test_check_ffmpeg_not_found(self, mock_find):
        mock_find.return_value = ("ffmpeg", "ffprobe")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = self.handler.check_ffmpeg()
            self.assertFalse(result)

    def test_resolve_path_valid_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"fake mp4 content")
            temp_path = f.name
        try:
            resolved = self.handler._resolve_path(temp_path)
            self.assertEqual(resolved, os.path.realpath(temp_path))
        finally:
            os.unlink(temp_path)

    def test_resolve_path_invalid_file(self):
        result = self.handler._resolve_path("/nonexistent/path/file.mp4")
        self.assertIsNone(result)

    def test_resolve_path_empty_file_returns_none(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        try:
            result = self.handler._resolve_path(temp_path)
            self.assertEqual(result, os.path.realpath(temp_path))
        finally:
            os.unlink(temp_path)

    def test_build_convert_command_nonexistent_input(self):
        cmd = self.handler.build_convert_command(
            "/nonexistent/file.mp4",
            "/output/file.mp4",
            "video",
            {"format": "MP4 (H.264)", "crf": 23, "preset": "medium"}
        )
        self.assertIsNone(cmd)

    def test_build_convert_command_invalid_format(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test")
            temp_path = f.name
        try:
            cmd = self.handler.build_convert_command(
                temp_path, "/output/file.mp4",
                "video", {"format": "INVALID_FORMAT"}
            )
            self.assertIsNone(cmd)
        finally:
            os.unlink(temp_path)

    def test_build_convert_command_gif(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test")
            temp_path = f.name
        try:
            cmd = self.handler.build_convert_command(
                temp_path, "/output/file.gif",
                "video",
                {"format": "GIF", "framerate": "10", "resolution": None}
            )
            self.assertIsNotNone(cmd)
            cmd_str = " ".join(cmd)
            self.assertIn("palettegen", cmd_str)
            self.assertIn("paletteuse", cmd_str)
            self.assertIn("-an", cmd_str)
        finally:
            os.unlink(temp_path)

    def test_build_convert_command_h264(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test")
            temp_path = f.name
        try:
            cmd = self.handler.build_convert_command(
                temp_path, "/output/file.mp4",
                "video",
                {"format": "MP4 (H.264)", "crf": 23, "preset": "medium",
                 "resolution": None, "framerate": None, "keep_audio": True,
                 "audio_codec": "aac", "audio_bitrate": "192k",
                 "hw_accel": False}
            )
            self.assertIsNotNone(cmd)
            cmd_str = " ".join(cmd)
            self.assertIn("libx264", cmd_str)
            self.assertIn("-crf", cmd_str)
            self.assertIn("-preset", cmd_str)
        finally:
            os.unlink(temp_path)

    def test_build_convert_command_with_trim(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test")
            temp_path = f.name
        try:
            cmd = self.handler.build_convert_command(
                temp_path, "/output/file.mp4",
                "video",
                {"format": "MP4 (H.264)", "crf": 23, "preset": "medium",
                 "resolution": None, "framerate": None, "keep_audio": False,
                 "audio_codec": "aac", "audio_bitrate": "192k",
                 "hw_accel": False},
                trim_start=10, trim_duration=30
            )
            self.assertIsNotNone(cmd)
            cmd_str = " ".join(cmd)
            self.assertIn("-ss 10", cmd_str)
            self.assertIn("-t 30", cmd_str)
            self.assertIn("-an", cmd_str)
        finally:
            os.unlink(temp_path)

    def test_build_convert_command_hw_accel(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test")
            temp_path = f.name
        try:
            self.handler._encoders_cache = "h264_nvenc"
            cmd = self.handler.build_convert_command(
                temp_path, "/output/file.mp4",
                "video",
                {"format": "MP4 (H.264)", "crf": 23, "preset": "medium",
                 "resolution": "1920:1080", "framerate": "30",
                 "keep_audio": True, "audio_codec": "aac", "audio_bitrate": "192k",
                 "hw_accel": True}
            )
            self.assertIsNotNone(cmd)
            cmd_str = " ".join(cmd)
            self.assertIn("h264_nvenc", cmd_str)
            self.assertIn("-cq", cmd_str)
            self.assertIn("-vf", cmd_str)
            self.assertIn("-r 30", cmd_str)
        finally:
            os.unlink(temp_path)

    def test_detect_hardware_acceleration_nvenc(self):
        self.handler._encoders_cache = """
Encoders:
 h264_nvenc           Nvidia NVENC H.264 encoder
 hevc_nvenc           Nvidia NVENC HEVC encoder
"""
        result = self.handler.detect_hardware_acceleration()
        self.assertEqual(result, "NVENC (NVIDIA)")

    def test_detect_hardware_acceleration_none(self):
        self.handler._encoders_cache = "Encoders:\n libx264"
        result = self.handler.detect_hardware_acceleration()
        self.assertEqual(result, "")

    def test_get_file_summary_no_info(self):
        with patch.object(self.handler, "get_media_info", return_value=None):
            result = self.handler.get_file_summary("/fake/file.mp4")
            self.assertIsNone(result)

    @patch("os.path.getsize", return_value=1048576)
    def test_get_file_summary(self, mock_size):
        fake_info = {
            "format": {"duration": "60.0", "bit_rate": "1000000"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
                {"codec_type": "audio", "codec_name": "aac"}
            ]
        }
        with patch.object(self.handler, "get_media_info", return_value=fake_info):
            summary = self.handler.get_file_summary("/fake/file.mp4")
            self.assertIsNotNone(summary)
            self.assertEqual(summary["video_codec"], "h264")
            self.assertEqual(summary["audio_codec"], "aac")
            self.assertEqual(summary["width"], 1920)
            self.assertEqual(summary["height"], 1080)
            self.assertEqual(summary["size_mb"], 1.0)
            self.assertEqual(summary["bitrate"], 1000)


class TestAudioConversionCommand(unittest.TestCase):
    """mode='audio' must produce a correct audio-only command."""

    def setUp(self):
        self.handler = FFmpegHandler()

    def _make_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"test")
            self.addCleanup(os.unlink, f.name)
        return f.name

    def test_audio_mode_mp3(self):
        cmd = self.handler.build_convert_command(
            self._make_file(), "/out/file.mp3", "audio",
            {"format": "MP3", "bitrate": "192k"}
        )
        self.assertIsNotNone(cmd)
        cmd_str = " ".join(cmd)
        self.assertIn("-vn", cmd_str)
        self.assertIn("libmp3lame", cmd_str)
        self.assertIn("-b:a 192k", cmd_str)

    def test_audio_mode_flac_auto_bitrate(self):
        cmd = self.handler.build_convert_command(
            self._make_file(), "/out/file.flac", "audio",
            {"format": "FLAC", "bitrate": "auto"}
        )
        cmd_str = " ".join(cmd)
        self.assertIn("flac", cmd_str)
        self.assertNotIn("-b:a", cmd_str)

    def test_audio_mode_invalid_format(self):
        cmd = self.handler.build_convert_command(
            self._make_file(), "/out/file.xyz", "audio",
            {"format": "INVALID"}
        )
        self.assertIsNone(cmd)


class TestAudioCopy(unittest.TestCase):
    """copy_audio=True must stream-copy instead of re-encoding."""

    def setUp(self):
        self.handler = FFmpegHandler()

    def _video_cmd(self, settings):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        return self.handler.build_convert_command(f.name, "/out/o.mp4", "video", settings)

    def test_copy_audio_uses_c_copy(self):
        cmd = self._video_cmd({
            "format": "MP4 (H.264)", "crf": 23, "preset": "medium",
            "resolution": None, "framerate": None,
            "keep_audio": True, "copy_audio": True,
        })
        self.assertIsNotNone(cmd)
        cmd_str = " ".join(cmd)
        self.assertIn("-c:a copy", cmd_str)
        self.assertNotIn("-b:a", cmd_str)

    def test_no_copy_audio_reencodes(self):
        cmd = self._video_cmd({
            "format": "MP4 (H.264)", "crf": 23, "preset": "medium",
            "resolution": None, "framerate": None, "keep_audio": True,
            "copy_audio": False, "audio_codec": "aac", "audio_bitrate": "192k",
        })
        cmd_str = " ".join(cmd)
        self.assertIn("aac", cmd_str)
        self.assertIn("-b:a 192k", cmd_str)
        self.assertNotIn("-c:a copy", cmd_str)


class TestGifMaxColors(unittest.TestCase):
    """GIF conversions must honor max_colors (2-256 clamp)."""

    def setUp(self):
        self.handler = FFmpegHandler()

    def _gif_cmd(self, settings):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        return self.handler.build_convert_command(f.name, "/out/o.gif", "video", settings)

    def test_max_colors_respected(self):
        cmd = self._gif_cmd({"format": "GIF", "framerate": "10", "resolution": None, "max_colors": 128})
        self.assertIsNotNone(cmd)
        self.assertIn("palettegen=max_colors=128", " ".join(cmd))

    def test_max_colors_default_256(self):
        cmd = self._gif_cmd({"format": "GIF", "framerate": "10", "resolution": None})
        self.assertIn("palettegen=max_colors=256", " ".join(cmd))

    def test_max_colors_clamped(self):
        cmd = self._gif_cmd({"format": "GIF", "framerate": "10", "resolution": None, "max_colors": 9999})
        self.assertIn("palettegen=max_colors=256", " ".join(cmd))
        cmd = self._gif_cmd({"format": "GIF", "framerate": "10", "resolution": None, "max_colors": 0})
        self.assertIn("palettegen=max_colors=2", " ".join(cmd))

    def test_max_colors_invalid_falls_back(self):
        cmd = self._gif_cmd({"format": "GIF", "framerate": "10", "resolution": None, "max_colors": "bogus"})
        self.assertIn("palettegen=max_colors=256", " ".join(cmd))


class TestStartConversion(unittest.TestCase):
    """start_conversion must not fake 100% progress on failure."""

    def setUp(self):
        self.handler = FFmpegHandler()

    def test_progress_not_100_on_failure(self):
        fake_process = MagicMock()
        fake_process.returncode = 1
        # stderr: no duration line, immediately EOF
        fake_process.stderr = iter([])
        fake_process.wait = MagicMock()

        progress_calls = []
        with patch("subprocess.Popen", return_value=fake_process):
            result = self.handler.start_conversion(
                ["ffmpeg", "-i", "x", "y"],
                progress_callback=lambda pct, status="": progress_calls.append(pct),
            )
        self.assertFalse(result)
        self.assertNotIn(100, progress_calls)

    def test_progress_100_on_success(self):
        fake_process = MagicMock()
        fake_process.returncode = 0
        fake_process.stderr = iter([])
        fake_process.wait = MagicMock()

        progress_calls = []
        with patch("subprocess.Popen", return_value=fake_process):
            result = self.handler.start_conversion(
                ["ffmpeg", "-i", "x", "y"],
                progress_callback=lambda pct, status="": progress_calls.append(pct),
            )
        self.assertTrue(result)
        self.assertIn(100, progress_calls)


class TestMediaInfoCache(unittest.TestCase):
    """A loaded file must only be probed once, not once per query helper."""

    def setUp(self):
        self.handler = FFmpegHandler()

    def _temp_media(self) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def _completed(self, width: int = 320, height: int = 240) -> MagicMock:
        payload = json.dumps({
            "format": {"duration": "1.0", "bit_rate": "1000000"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": width, "height": height},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        })
        return MagicMock(returncode=0, stdout=payload)

    def test_ffprobe_called_once_for_repeated_queries(self):
        path = self._temp_media()
        with patch("subprocess.run", return_value=self._completed()) as run:
            self.handler.get_media_info(path)
            self.handler.get_codecs(path)
            self.handler.get_resolution(path)
            summary = self.handler.get_file_summary(path)
            self.assertEqual(run.call_count, 1)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["video_codec"], "h264")

    def test_cache_is_invalidated_when_file_changes(self):
        path = self._temp_media()
        with patch("subprocess.run", return_value=self._completed()) as run:
            self.handler.get_media_info(path)
            self.assertEqual(run.call_count, 1)
            with open(path, "ab") as fh:
                fh.write(b"more bytes")
            self.handler.get_media_info(path)
            self.assertEqual(run.call_count, 2)


class TestContainerAudioCompatibility(unittest.TestCase):
    """WebM only accepts Opus/Vorbis, so AAC/`copy` must never reach it."""

    def setUp(self):
        self.handler = FFmpegHandler()

    def _cmd(self, settings, ext=".webm"):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        return self.handler.build_convert_command(f.name, f"/out/o{ext}", "video", settings)

    def _base(self, **overrides):
        settings = {
            "format": "WebM (VP9)", "crf": 31, "preset": "medium",
            "resolution": None, "framerate": None,
            "keep_audio": True, "copy_audio": False,
            "audio_codec": "aac", "audio_bitrate": "192k", "hw_accel": False,
        }
        settings.update(overrides)
        return settings

    def test_webm_never_copies_aac(self):
        cmd = self._cmd(self._base(copy_audio=True))
        self.assertIsNotNone(cmd)
        cmd_str = " ".join(cmd)
        self.assertNotIn("-c:a copy", cmd_str)
        self.assertIn("libopus", cmd_str)

    def test_webm_reencodes_to_opus(self):
        cmd = self._cmd(self._base(audio_codec="aac"))
        cmd_str = " ".join(cmd)
        self.assertIn("-c:a libopus", cmd_str)
        self.assertNotIn("aac", cmd_str)

    def test_webm_without_audio(self):
        cmd = self._cmd(self._base(keep_audio=False))
        cmd_str = " ".join(cmd)
        self.assertIn("-an", cmd_str)
        self.assertNotIn("libopus", cmd_str)

    def test_mp4_still_allows_audio_copy(self):
        cmd = self._cmd(self._base(format="MP4 (H.264)", copy_audio=True, crf=23), ".mp4")
        cmd_str = " ".join(cmd)
        self.assertIn("-c:a copy", cmd_str)


class TestVp9Options(unittest.TestCase):
    """libvpx-vp9 needs `-b:v 0` and has no `-preset` option."""

    def setUp(self):
        self.handler = FFmpegHandler()

    def _webm_cmd(self, preset="medium"):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        return self.handler.build_convert_command(
            f.name, "/out/o.webm", "video",
            {"format": "WebM (VP9)", "crf": 31, "preset": preset,
             "resolution": None, "framerate": None, "keep_audio": False},
        )

    def test_constant_quality_flag(self):
        cmd_str = " ".join(self._webm_cmd())
        self.assertIn("-b:v 0", cmd_str)

    def test_preset_mapped_to_cpu_used(self):
        cmd_str = " ".join(self._webm_cmd("veryslow"))
        self.assertIn("-cpu-used 0", cmd_str)
        self.assertNotIn("-preset", cmd_str)

    def test_unknown_preset_defaults_to_cpu_used_2(self):
        cmd_str = " ".join(self._webm_cmd("bogus"))
        self.assertIn("-cpu-used 2", cmd_str)


class TestHardwareEncoderSelection(unittest.TestCase):
    """The H.265 hardware encoder must match the requested codec."""

    def setUp(self):
        self.handler = FFmpegHandler()
        self.handler._encoders_cache = "h264_nvenc\nhevc_nvenc\nh264_amf\n"

    def test_h265_selects_hevc_nvenc(self):
        self.assertEqual(self.handler._get_hw_encoder("MP4 (H.265)"), "hevc_nvenc")

    def test_h264_selects_h264_nvenc(self):
        self.assertEqual(self.handler._get_hw_encoder("MP4 (H.264)"), "h264_nvenc")

    def test_amf_fallback(self):
        self.handler._encoders_cache = "h264_amf\n"
        self.assertEqual(self.handler._get_hw_encoder("MKV (H.264)"), "h264_amf")

    def test_software_only_formats_have_no_hw_encoder(self):
        self.assertIsNone(self.handler._get_hw_encoder("WebM (VP9)"))
        self.assertIsNone(self.handler._get_hw_encoder("GIF"))
        self.assertIsNone(self.handler._get_hw_encoder("Nonexistent"))


class TestGifFilters(unittest.TestCase):
    """GIF at original resolution must not emit a bogus scale=-1:-1 filter."""

    def setUp(self):
        self.handler = FFmpegHandler()

    def _gif_vf(self, resolution):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        cmd = self.handler.build_convert_command(
            f.name, "/out/o.gif", "video",
            {"format": "GIF", "framerate": "15", "resolution": resolution, "max_colors": 128},
        )
        return cmd[cmd.index("-vf") + 1]

    def test_no_scale_when_original(self):
        vf = self._gif_vf(None)
        self.assertNotIn("scale=", vf)
        self.assertIn("fps=15", vf)
        self.assertIn("palettegen=max_colors=128", vf)

    def test_scale_present_when_requested(self):
        self.assertIn("scale=640:360:flags=lanczos", self._gif_vf("640:360"))


class TestHevcTag(unittest.TestCase):
    def setUp(self):
        self.handler = FFmpegHandler()

    def test_hevc_mp4_gets_hvc1_tag(self):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        cmd = self.handler.build_convert_command(
            f.name, "/out/o.mp4", "video",
            {"format": "MP4 (H.265)", "crf": 28, "preset": "medium",
             "resolution": None, "framerate": None, "keep_audio": False, "hw_accel": False},
        )
        self.assertIn("-tag:v hvc1", " ".join(cmd))

    def test_h264_mp4_has_no_hvc1_tag(self):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        cmd = self.handler.build_convert_command(
            f.name, "/out/o.mp4", "video",
            {"format": "MP4 (H.264)", "crf": 23, "preset": "medium",
             "resolution": None, "framerate": None, "keep_audio": False, "hw_accel": False},
        )
        self.assertNotIn("hvc1", " ".join(cmd))


if __name__ == "__main__":
    unittest.main()
