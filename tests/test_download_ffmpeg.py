import hashlib
import io
import os
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import download_ffmpeg
from download_ffmpeg import (
    _extract_tar,
    _is_safe_member,
    archive_sha256,
    resolve_archive_url,
    verify_archive_hash,
)


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


class TestArchiveIntegrity(unittest.TestCase):
    def test_sha256_matches_hashlib(self):
        # Well-known digest of the empty input, as a format sanity check.
        self.assertEqual(
            archive_sha256(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
        self.assertEqual(archive_sha256(b"shuttle"), hashlib.sha256(b"shuttle").hexdigest())

    def test_no_pin_accepts_anything(self):
        self.assertTrue(verify_archive_hash(b"whatever", ""))

    def test_matching_digest_is_accepted(self):
        data = b"ffmpeg archive"
        self.assertTrue(verify_archive_hash(data, archive_sha256(data)))

    def test_digest_check_is_case_insensitive(self):
        data = b"ffmpeg archive"
        self.assertTrue(verify_archive_hash(data, archive_sha256(data).upper()))

    def test_tampered_archive_is_rejected(self):
        expected = archive_sha256(b"original archive")
        self.assertFalse(verify_archive_hash(b"tampered archive", expected))

    def test_default_url_uses_latest(self):
        with patch.object(download_ffmpeg, "BUILD_TAG", ""):
            self.assertIn("/download/latest/", resolve_archive_url())

    def test_pinned_tag_is_used(self):
        with patch.object(download_ffmpeg, "BUILD_TAG", "autobuild-2025-06-30-12-00"):
            self.assertIn("/download/autobuild-2025-06-30-12-00/", resolve_archive_url())
            self.assertNotIn("/download/latest/", resolve_archive_url())


if __name__ == "__main__":
    unittest.main()
