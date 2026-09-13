import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ffmpeg_handler import COPY_SAFE_AUDIO_CODECS, FFmpegHandler


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
        with patch.object(self.handler, "get_codecs", return_value={"video": "h264", "audio": "aac"}):
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
        with patch.object(FFmpegHandler, "get_codecs", return_value={"video": "h264", "audio": "aac"}):
            cmd = self._cmd(self._base(format="MP4 (H.264)", copy_audio=True, crf=23), ".mp4")
        cmd_str = " ".join(cmd)
        self.assertIn("-c:a copy", cmd_str)


class TestAudioCopySafety(unittest.TestCase):
    """`-c:a copy` must only be used when the container supports the source codec.

    ffmpeg happily muxes Vorbis into MP4, but many players and hardware
    decoders reject that file, so an incompatible track is re-encoded instead.
    """

    def setUp(self):
        self.handler = FFmpegHandler()
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"test")
        f.close()
        self.addCleanup(os.unlink, f.name)
        self.input_file = f.name

    def _cmd(self, fmt_name, source_codec, ext=".mp4"):
        codecs = {"video": "h264", "audio": source_codec}
        with patch.object(self.handler, "get_codecs", return_value=codecs):
            return self.handler.build_convert_command(
                self.input_file, f"/out/o{ext}", "video",
                {
                    "format": fmt_name, "crf": 23, "preset": "medium",
                    "resolution": None, "framerate": None, "keep_audio": True,
                    "copy_audio": True, "audio_codec": "aac", "audio_bitrate": "192k",
                },
            )

    def test_aac_into_mp4_is_copied(self):
        cmd = self._cmd("MP4 (H.264)", "aac")
        self.assertIn("-c:a copy", " ".join(cmd))

    def test_mp3_into_mp4_is_copied(self):
        self.assertIn("-c:a copy", " ".join(self._cmd("MP4 (H.264)", "mp3")))

    def test_vorbis_into_mp4_is_reencoded(self):
        cmd_str = " ".join(self._cmd("MP4 (H.264)", "vorbis"))
        self.assertNotIn("-c:a copy", cmd_str)
        self.assertIn("-c:a aac", cmd_str)

    def test_opus_into_mp4_is_reencoded(self):
        self.assertNotIn("-c:a copy", " ".join(self._cmd("MP4 (H.264)", "opus")))

    def test_opus_into_mkv_is_copied(self):
        cmd = self._cmd("MKV (H.264)", "opus", ext=".mkv")
        self.assertIn("-c:a copy", " ".join(cmd))

    def test_alac_into_avi_is_reencoded(self):
        cmd_str = " ".join(self._cmd("AVI", "alac", ext=".avi"))
        self.assertNotIn("-c:a copy", cmd_str)

    def test_unknown_source_codec_is_reencoded(self):
        cmd_str = " ".join(self._cmd("MP4 (H.264)", ""))
        self.assertNotIn("-c:a copy", cmd_str)
        self.assertIn("-c:a aac", cmd_str)

    def test_can_copy_audio_rejects_an_unknown_source(self):
        with patch.object(self.handler, "get_codecs", return_value={"video": "h264", "audio": None}):
            self.assertFalse(self.handler.can_copy_audio(self.input_file, "MP4 (H.264)"))
        with patch.object(self.handler, "get_codecs", return_value={"video": "h264", "audio": "AAC"}):
            self.assertTrue(self.handler.can_copy_audio(self.input_file, "MP4 (H.264)"))

    def test_webm_is_not_in_the_copy_safe_map(self):
        # WebM re-encodes to Opus regardless, so it has no copy-safe entry.
        self.assertNotIn("WebM (VP9)", COPY_SAFE_AUDIO_CODECS)


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


class TestImageConversion(unittest.TestCase):
    def setUp(self):
        self.handler = FFmpegHandler()

    def _temp_file(self, suffix: str = ".png") -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        f.write(b"fake image")
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_supported_image_formats(self):
        formats = self.handler.get_supported_image_formats()
        for name in ("PNG", "JPG", "WebP", "BMP", "TIFF"):
            self.assertIn(name, formats)

    def test_image_formats_structure(self):
        for fmt in self.handler.IMAGE_FORMATS.values():
            self.assertIn("image_codec", fmt)
            self.assertIn("extension", fmt)
            self.assertIn("quality", fmt)
            self.assertTrue(fmt["extension"].startswith("."))

    def test_image_to_image_command(self):
        cmd = self.handler.build_convert_command(
            self._temp_file(".png"), "/out/o.webp", "image", {"format": "WebP", "quality": 80}
        )
        self.assertIsNotNone(cmd)
        assert cmd is not None
        self.assertIn("libwebp", cmd)
        self.assertIn("-q:v", cmd)
        self.assertIn("80", cmd)
        self.assertIn("-frames:v", cmd)
        self.assertEqual(cmd[-1], "/out/o.webp")

    def test_frame_export_seeks_before_the_input(self):
        cmd = self.handler.build_convert_command(
            self._temp_file(".mp4"), "/out/frame.png", "image", {"format": "PNG"},
            trim_start=12,
        )
        assert cmd is not None
        self.assertLess(cmd.index("-ss"), cmd.index("-i"))
        self.assertIn("12", cmd)
        self.assertIn("png", cmd)

    def test_image_resolution_is_scaled(self):
        cmd = self.handler.build_convert_command(
            self._temp_file(".png"), "/out/o.png", "image",
            {"format": "PNG", "resolution": "1280:720"},
        )
        assert cmd is not None
        self.assertIn("scale=1280:720:flags=lanczos", cmd)

    def test_jpg_quality_slider_is_inverted(self):
        fmt = self.handler.IMAGE_FORMATS["JPG"]
        self.assertEqual(self.handler._image_quality_args(fmt, 100), ["-q:v", "2"])
        self.assertEqual(self.handler._image_quality_args(fmt, 1), ["-q:v", "31"])

    def test_png_uses_compression_level(self):
        fmt = self.handler.IMAGE_FORMATS["PNG"]
        self.assertEqual(self.handler._image_quality_args(fmt, 50), ["-compression_level", "6"])

    def test_lossless_formats_have_no_quality_flag(self):
        for name in ("BMP", "TIFF"):
            self.assertEqual(self.handler._image_quality_args(self.handler.IMAGE_FORMATS[name], 90), [])

    def test_unknown_image_format_returns_none(self):
        self.assertIsNone(
            self.handler.build_convert_command(
                self._temp_file(".png"), "/out/o.xyz", "image", {"format": "Nope"}
            )
        )


class TestTargetSize(unittest.TestCase):
    def setUp(self):
        self.handler = FFmpegHandler()

    def _temp_file(self) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"fake video")
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def _settings(self, **overrides):
        settings = {
            "format": "MP4 (H.264)", "crf": 23, "preset": "medium", "resolution": None,
            "framerate": None, "keep_audio": True, "hw_accel": False, "audio_bitrate": "192k",
        }
        settings.update(overrides)
        return settings

    def test_zero_inputs_return_zero(self):
        self.assertEqual(FFmpegHandler.compute_target_video_bitrate(0, 60), 0)
        self.assertEqual(FFmpegHandler.compute_target_video_bitrate(25, 0), 0)

    def test_bitrate_matches_the_requested_size(self):
        # 25 MB in 60 s with 192 kbps of audio is roughly 3.2 Mbps of video.
        bitrate = FFmpegHandler.compute_target_video_bitrate(25, 60, 192)
        self.assertGreater(bitrate, 2800)
        self.assertLess(bitrate, 3400)

    def test_shorter_video_needs_more_bitrate(self):
        short = FFmpegHandler.compute_target_video_bitrate(25, 10, 192)
        long = FFmpegHandler.compute_target_video_bitrate(25, 120, 192)
        self.assertGreater(short, long)

    def test_bitrate_never_drops_to_zero(self):
        self.assertGreaterEqual(FFmpegHandler.compute_target_video_bitrate(0.1, 600, 192), 50)

    def test_target_size_uses_bitrate_instead_of_crf(self):
        cmd = self.handler.build_convert_command(
            self._temp_file(), "/out/o.mp4", "video",
            self._settings(duration=60, target_size_mb=25),
        )
        assert cmd is not None
        self.assertIn("-b:v", cmd)
        self.assertIn("-maxrate", cmd)
        self.assertNotIn("-crf", cmd)

    @patch.object(FFmpegHandler, "get_file_summary", return_value=None)
    def test_missing_duration_falls_back_to_crf(self, _mock_summary):
        cmd = self.handler.build_convert_command(
            self._temp_file(), "/out/o.mp4", "video", self._settings(target_size_mb=25),
        )
        assert cmd is not None
        self.assertIn("-crf", cmd)
        self.assertNotIn("-b:v", cmd)

    @patch.object(FFmpegHandler, "get_file_summary", return_value=None)
    def test_video_target_bitrate_is_zero_without_a_duration(self, _mock_summary):
        """The UI relies on 0 to log the documented fallback to CRF."""
        bitrate = self.handler.video_target_bitrate(
            self._settings(target_size_mb=25), self._temp_file(), None
        )
        self.assertEqual(bitrate, 0)

    def test_trim_duration_limits_the_target(self):
        cmd = self.handler.build_convert_command(
            self._temp_file(), "/out/o.mp4", "video",
            self._settings(duration=600, target_size_mb=25),
            trim_start=0, trim_duration=60,
        )
        assert cmd is not None
        # A 60 s cut of a 10 min target is the same bitrate as 25 MB / 60 s.
        self.assertIn(f"{FFmpegHandler.compute_target_video_bitrate(25, 60, 192)}k", cmd)

    def test_audio_bitrate_is_subtracted(self):
        cmd = self.handler.build_convert_command(
            self._temp_file(), "/out/o.mp4", "video",
            self._settings(duration=60, target_size_mb=25, keep_audio=False),
        )
        assert cmd is not None
        self.assertIn(f"{FFmpegHandler.compute_target_video_bitrate(25, 60, 0)}k", cmd)


class TestSizeEstimate(unittest.TestCase):
    def setUp(self):
        self.handler = FFmpegHandler()
        self.summary = {"duration": 60.0, "width": 1920, "height": 1080}

    def test_target_size_is_returned_exactly(self):
        self.assertEqual(
            self.handler.estimate_output_size_mb(self.summary, {"target_size_mb": 25}), 25.0
        )

    def test_1080p_crf23_is_plausible(self):
        estimate = self.handler.estimate_output_size_mb(
            self.summary,
            {"format": "MP4 (H.264)", "crf": 23, "keep_audio": True, "audio_bitrate": "192k"},
        )
        assert estimate is not None
        # ~30-35 MB per minute of 1080p30 at CRF 23.
        self.assertGreater(estimate, 20)
        self.assertLess(estimate, 45)

    def test_lower_crf_estimates_bigger_files(self):
        high = self.handler.estimate_output_size_mb(
            self.summary, {"format": "MP4 (H.264)", "crf": 18, "keep_audio": False}
        )
        low = self.handler.estimate_output_size_mb(
            self.summary, {"format": "MP4 (H.264)", "crf": 32, "keep_audio": False}
        )
        assert high is not None and low is not None
        self.assertGreater(high, low)

    def test_resolution_scales_the_estimate(self):
        full = self.handler.estimate_output_size_mb(
            self.summary, {"format": "MP4 (H.264)", "crf": 23, "resolution": "1920:1080", "keep_audio": False}
        )
        small = self.handler.estimate_output_size_mb(
            self.summary, {"format": "MP4 (H.264)", "crf": 23, "resolution": "640:360", "keep_audio": False}
        )
        assert full is not None and small is not None
        self.assertGreater(full, small * 5)  # 9x fewer pixels, same fps

    def test_audio_mode_uses_its_bitrate(self):
        estimate = self.handler.estimate_output_size_mb(self.summary, {"format": "MP3", "bitrate": "192k"})
        assert estimate is not None
        self.assertAlmostEqual(estimate, 1.37, places=1)

    def test_auto_audio_bitrate_is_unknown(self):
        self.assertIsNone(self.handler.estimate_output_size_mb(self.summary, {"format": "FLAC", "bitrate": "auto"}))

    def test_gif_has_no_estimate(self):
        self.assertIsNone(self.handler.estimate_output_size_mb(self.summary, {"format": "GIF", "max_colors": 256}))

    def test_unknown_duration_and_summary(self):
        self.assertIsNone(self.handler.estimate_output_size_mb(None, {"format": "MP4 (H.264)", "crf": 23}))
        self.assertIsNone(
            self.handler.estimate_output_size_mb(
                {"duration": None, "width": 1920, "height": 1080},
                {"format": "MP4 (H.264)", "crf": 23},
            )
        )


class TestSoftwareFallback(unittest.TestCase):
    def setUp(self):
        self.handler = FFmpegHandler()

    def test_nvenc_becomes_crf_x264(self):
        fallback = self.handler.build_software_fallback(
            ["ffmpeg", "-i", "in.mp4", "-c:v", "h264_nvenc", "-cq", "20", "-y", "out.mp4"]
        )
        assert fallback is not None
        self.assertIn("libx264", fallback)
        self.assertIn("-crf", fallback)
        self.assertIn("20", fallback)
        self.assertNotIn("-cq", fallback)
        self.assertEqual(fallback[-1], "out.mp4")

    def test_qsv_maps_to_libx265_for_hevc(self):
        fallback = self.handler.build_software_fallback(
            ["ffmpeg", "-i", "i.mkv", "-c:v", "hevc_qsv", "-global_quality", "28", "-y", "o.mkv"]
        )
        assert fallback is not None
        self.assertIn("libx265", fallback)
        self.assertIn("28", fallback)

    def test_amf_rate_control_is_dropped(self):
        fallback = self.handler.build_software_fallback(
            ["ffmpeg", "-i", "i.mp4", "-c:v", "h264_amf", "-quality", "balanced",
             "-rc", "cqp", "-qp_i", "19", "-qp_p", "19", "-y", "o.mp4"]
        )
        assert fallback is not None
        self.assertIn("libx264", fallback)
        self.assertIn("19", fallback)
        for dropped in ("-quality", "-rc", "-qp_i", "-qp_p", "balanced", "cqp"):
            self.assertNotIn(dropped, fallback)
        self.assertEqual(fallback.count("-crf"), 1)

    def test_bitrate_mode_keeps_the_bitrate(self):
        fallback = self.handler.build_software_fallback(
            ["ffmpeg", "-i", "i.mp4", "-c:v", "h264_nvenc", "-rc", "vbr",
             "-b:v", "3200k", "-maxrate", "4800k", "-y", "o.mp4"]
        )
        assert fallback is not None
        self.assertIn("-b:v", fallback)
        self.assertNotIn("-crf", fallback)
        self.assertNotIn("-rc", fallback)

    def test_default_crf_is_added_when_missing(self):
        fallback = self.handler.build_software_fallback(["ffmpeg", "-c:v", "h264_nvenc", "-y", "o.mp4"])
        assert fallback is not None
        self.assertEqual(fallback[fallback.index("-crf"):fallback.index("-crf") + 2], ["-crf", "23"])
        self.assertEqual(fallback[-1], "o.mp4")

    def test_options_always_precede_the_output_path(self):
        # ffmpeg treats options after the output file as trailing and ignores them.
        fallback = self.handler.build_software_fallback(
            ["ffmpeg", "-i", "i.mp4", "-c:v", "h264_nvenc", "-cq", "20", "-y", "out.mp4"]
        )
        assert fallback is not None
        self.assertEqual(fallback[-1], "out.mp4")
        self.assertLess(fallback.index("-crf"), fallback.index("out.mp4"))
        self.assertEqual(fallback[fallback.index("-c:v"):fallback.index("-c:v") + 2], ["-c:v", "libx264"])

    def test_software_command_returns_none(self):
        self.assertIsNone(
            self.handler.build_software_fallback(["ffmpeg", "-c:v", "libx264", "-crf", "23", "-y", "o.mp4"])
        )

    def test_command_without_video_encoder_returns_none(self):
        self.assertIsNone(self.handler.build_software_fallback(["ffmpeg", "-c:a", "copy", "-y", "o.mkv"]))

    def test_dangling_encoder_flag_returns_none(self):
        self.assertIsNone(self.handler.build_software_fallback(["ffmpeg", "-c:v"]))

    @patch.object(FFmpegHandler, "_get_hw_encoder", return_value="h264_amf")
    def test_amf_honours_the_crf_slider(self, _mock_hw):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"fake video")
        f.close()
        self.addCleanup(os.unlink, f.name)
        cmd = self.handler.build_convert_command(
            f.name, "/out/o.mp4", "video",
            {"format": "MP4 (H.264)", "crf": 20, "preset": "medium", "resolution": None,
             "framerate": None, "keep_audio": False, "hw_accel": True},
        )
        assert cmd is not None
        # AMF used to ignore the slider entirely (only "-quality balanced").
        self.assertIn("-rc", cmd)
        self.assertIn("cqp", cmd)
        self.assertIn("20", cmd)


class TestCancelFlag(unittest.TestCase):
    def test_cancel_requested_tracks_cancel_conversion(self):
        handler = FFmpegHandler()
        self.assertFalse(handler.cancel_requested())
        handler.cancel_conversion()
        self.assertTrue(handler.cancel_requested())

    def test_get_ffmpeg_version_never_raises(self):
        handler = FFmpegHandler()
        handler.ffmpeg_path = "definitely-not-a-binary"
        self.assertEqual(handler.get_ffmpeg_version(), "")


if __name__ == "__main__":
    unittest.main()
