import io
import os
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import download_ffmpeg
from download_ffmpeg import _extract_tar, _is_safe_member


class TestSafeMember(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_regular_relative_member_is_safe(self):
        self.assertTrue(_is_safe_member(self.tmp, "ffmpeg-7.0/ffmpeg"))
        self.assertTrue(_is_safe_member(self.tmp, "ffmpeg"))

    def test_parent_traversal_is_rejected(self):
        self.assertFalse(_is_safe_member(self.tmp, "../ffmpeg"))
        self.assertFalse(_is_safe_member(self.tmp, "../../etc/passwd"))

    def test_absolute_path_is_rejected(self):
        self.assertFalse(_is_safe_member(self.tmp, "/tmp/ffmpeg"))


def _tar_with_member(member_name: str) -> io.BytesIO:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:xz") as tf:
        info = tarfile.TarInfo(name=member_name)
        payload = b"not a real binary"
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))
    buffer.seek(0)
    return buffer


class TestExtractTarSafety(unittest.TestCase):
    """CVE-2007-4559: archive members must never escape the target directory."""

    def test_path_traversal_member_is_not_extracted(self):
        parent = tempfile.mkdtemp()
        target = os.path.join(parent, "bin")
        os.makedirs(target)
        # A member whose basename is a real binary but escapes the target dir.
        escaping = os.path.join("..", download_ffmpeg.FFMPEG_BIN)

        extracted = _extract_tar(_tar_with_member(escaping), target)

        self.assertEqual(extracted, 0)
        self.assertFalse(os.path.exists(os.path.join(parent, download_ffmpeg.FFMPEG_BIN)))

    def test_expected_member_is_extracted(self):
        target = tempfile.mkdtemp()
        member = f"ffmpeg-master/bin/{download_ffmpeg.FFMPEG_BIN}"

        extracted = _extract_tar(_tar_with_member(member), target)

        self.assertEqual(extracted, 1)
        self.assertTrue(os.path.isfile(os.path.join(target, download_ffmpeg.FFMPEG_BIN)))


if __name__ == "__main__":
    unittest.main()
