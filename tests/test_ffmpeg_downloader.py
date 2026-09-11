import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ffmpeg_downloader import FFmpegStatus, ensure_ffmpeg, find_ffmpeg, find_ffmpeg_status, get_bundled_dir


class TestFfmpegDownloader(unittest.TestCase):
    def test_get_bundled_dir_development(self):
        if hasattr(sys, "_MEIPASS"):
            del sys._MEIPASS
        result = get_bundled_dir()
        self.assertTrue(result.endswith(os.path.join("resources", "bin")))

    def test_get_bundled_dir_frozen(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.object(sys, "_MEIPASS", tmpdir, create=True):
            result = get_bundled_dir()
            self.assertEqual(
                result,
                os.path.join(tmpdir, "resources", "bin")
            )

    @patch("src.ffmpeg_downloader.which")
    @patch("os.path.isfile")
    def test_find_ffmpeg_status_bundled(self, mock_isfile, mock_which):
        mock_isfile.return_value = True
        mock_which.return_value = None
        status = find_ffmpeg_status()
        self.assertTrue(status.ok)
        self.assertTrue(status.bundled)
        self.assertIsNotNone(status.ffmpeg)
        self.assertIsNotNone(status.ffprobe)

    @patch("src.ffmpeg_downloader.which")
    @patch("os.path.isfile")
    def test_find_ffmpeg_status_system(self, mock_isfile, mock_which):
        mock_isfile.return_value = False
        mock_which.side_effect = lambda x: f"/usr/bin/{x}"
        status = find_ffmpeg_status()
        self.assertTrue(status.ok)
        self.assertFalse(status.bundled)
        self.assertIn("ffmpeg", str(status.ffmpeg))

    @patch("src.ffmpeg_downloader.which")
    @patch("os.path.isfile")
    def test_find_ffmpeg_status_not_found(self, mock_isfile, mock_which):
        mock_isfile.return_value = False
        mock_which.return_value = None
        status = find_ffmpeg_status()
        self.assertFalse(status.ok)
        self.assertIsNone(status.ffmpeg)
        self.assertIsNone(status.ffprobe)

    @patch("src.ffmpeg_downloader.find_ffmpeg_status")
    def test_find_ffmpeg_tuple_compat(self, mock_status):
        mock_status.return_value = FFmpegStatus("/usr/bin/ffmpeg", "/usr/bin/ffprobe", False)
        ffmpeg, ffprobe = find_ffmpeg()
        self.assertEqual(ffmpeg, "/usr/bin/ffmpeg")
        self.assertEqual(ffprobe, "/usr/bin/ffprobe")

    @patch("src.ffmpeg_downloader.find_ffmpeg_status")
    def test_ensure_ffmpeg_found(self, mock_status):
        mock_status.return_value = FFmpegStatus("/usr/bin/ffmpeg", "/usr/bin/ffprobe", False)
        result = ensure_ffmpeg()
        self.assertTrue(result.ok)

    @patch("src.ffmpeg_downloader.find_ffmpeg_status")
    def test_ensure_ffmpeg_not_found_raises(self, mock_status):
        mock_status.return_value = FFmpegStatus(None, None, False)
        with self.assertRaises(RuntimeError):
            ensure_ffmpeg()

    @patch("src.ffmpeg_downloader.find_ffmpeg_status")
    def test_ensure_ffmpeg_with_callback(self, mock_status):
        mock_status.return_value = FFmpegStatus("/usr/bin/ffmpeg", "/usr/bin/ffprobe", True)
        callback = MagicMock()
        ensure_ffmpeg(progress_callback=callback)
        callback.assert_called_once_with(100, "FFmpeg listo (embebido)")


if __name__ == "__main__":
    unittest.main()
