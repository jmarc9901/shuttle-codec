import unittest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ffmpeg_downloader import get_bundled_dir, find_ffmpeg, ensure_ffmpeg


class TestFfmpegDownloader(unittest.TestCase):
    def test_get_bundled_dir_development(self):
        if hasattr(sys, "_MEIPASS"):
            del sys._MEIPASS
        result = get_bundled_dir()
        self.assertTrue(result.endswith(os.path.join("resources", "bin")))

    def test_get_bundled_dir_frozen(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(sys, "_MEIPASS", tmpdir, create=True):
                result = get_bundled_dir()
                self.assertEqual(
                    result,
                    os.path.join(tmpdir, "resources", "bin")
                )

    @patch("src.ffmpeg_downloader.which")
    @patch("os.path.isfile")
    def test_find_ffmpeg_bundled(self, mock_isfile, mock_which):
        mock_isfile.return_value = True
        mock_which.return_value = None
        ffmpeg, ffprobe = find_ffmpeg()
        self.assertIsNotNone(ffmpeg)
        self.assertIsNotNone(ffprobe)

    @patch("src.ffmpeg_downloader.which")
    @patch("os.path.isfile")
    def test_find_ffmpeg_system(self, mock_isfile, mock_which):
        mock_isfile.return_value = False
        mock_which.side_effect = lambda x: f"/usr/bin/{x}"
        ffmpeg, ffprobe = find_ffmpeg()
        self.assertIsNotNone(ffmpeg)
        self.assertIsNotNone(ffprobe)
        self.assertTrue("ffmpeg" in str(ffmpeg))

    @patch("src.ffmpeg_downloader.which")
    @patch("os.path.isfile")
    def test_find_ffmpeg_not_found(self, mock_isfile, mock_which):
        mock_isfile.return_value = False
        mock_which.return_value = None
        ffmpeg, ffprobe = find_ffmpeg()
        self.assertIsNone(ffmpeg)
        self.assertIsNone(ffprobe)

    @patch("src.ffmpeg_downloader.find_ffmpeg")
    def test_ensure_ffmpeg_found(self, mock_find):
        mock_find.return_value = ("/usr/bin/ffmpeg", "/usr/bin/ffprobe")
        result = ensure_ffmpeg()
        self.assertEqual(result, ("/usr/bin/ffmpeg", "/usr/bin/ffprobe"))

    @patch("src.ffmpeg_downloader.find_ffmpeg")
    def test_ensure_ffmpeg_not_found(self, mock_find):
        mock_find.return_value = (None, None)
        with self.assertRaises(RuntimeError):
            ensure_ffmpeg()

    @patch("src.ffmpeg_downloader.find_ffmpeg")
    def test_ensure_ffmpeg_with_callback(self, mock_find):
        mock_find.return_value = ("/usr/bin/ffmpeg", "/usr/bin/ffprobe")
        callback = MagicMock()
        result = ensure_ffmpeg(progress_callback=callback)
        callback.assert_called_once_with(100, "FFmpeg listo (embebido)")


if __name__ == "__main__":
    unittest.main()
