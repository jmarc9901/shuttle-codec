import unittest
import sys
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

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
        for name, fmt in self.handler.VIDEO_FORMATS.items():
            self.assertIn("video_codec", fmt)
            self.assertIn("extension", fmt)
            self.assertIn("presets", fmt)
            self.assertIn("gif_mode", fmt)
            self.assertIn("quality_range", fmt)
            self.assertIn("default_crf", fmt)
            self.assertIsInstance(fmt["gif_mode"], bool)

    def test_audio_formats_structure(self):
        for name, fmt in self.handler.AUDIO_FORMATS.items():
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


if __name__ == "__main__":
    unittest.main()
