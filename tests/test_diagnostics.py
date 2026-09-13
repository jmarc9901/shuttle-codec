import os
import sys
import unittest
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.diagnostics import (
    ISSUES_URL,
    MAX_BODY_CHARS,
    build_diagnostics,
    build_issue_url,
    collect_environment,
    tail_lines,
)


class TestTailLines(unittest.TestCase):
    def test_keeps_only_the_last_lines(self):
        text = "\n".join(f"line {i}" for i in range(50))
        tail = tail_lines(text, 3)
        self.assertEqual(tail.splitlines(), ["line 47", "line 48", "line 49"])

    def test_ignores_blank_lines(self):
        self.assertEqual(tail_lines("a\n\n\nb\n   \n", 5), "a\nb")

    def test_empty_input(self):
        self.assertEqual(tail_lines(""), "")
        self.assertEqual(tail_lines(None), "")  # type: ignore[arg-type]


class TestCollectEnvironment(unittest.TestCase):
    def test_includes_version_and_ffmpeg(self):
        text = collect_environment("1.3.0", language="es", ffmpeg_version="ffmpeg version 7.0")
        self.assertIn("1.3.0", text)
        self.assertIn("es", text)
        self.assertIn("ffmpeg version 7.0", text)

    def test_missing_ffmpeg_is_reported(self):
        self.assertIn("not detected", collect_environment("1.3.0"))

    def test_qt_version_is_optional(self):
        self.assertNotIn("Qt:", collect_environment("1.3.0"))
        self.assertIn("Qt: 5.15.2", collect_environment("1.3.0", qt_version="5.15.2"))


class TestBuildDiagnostics(unittest.TestCase):
    def test_includes_environment_and_log(self):
        text = build_diagnostics("1.3.0", language="en", log_text="▶ start\n✅ done")
        self.assertIn("**Environment**", text)
        self.assertIn("**Log (last lines)**", text)
        self.assertIn("✅ done", text)

    def test_without_log_has_no_log_section(self):
        self.assertNotIn("**Log", build_diagnostics("1.3.0"))

    def test_truncates_long_reports(self):
        text = build_diagnostics("1.3.0", log_text="x" * 20000, max_body_chars=500)
        self.assertLessEqual(len(text), 520)
        self.assertIn("truncated", text)


class TestBuildIssueUrl(unittest.TestCase):
    def test_points_at_the_issue_tracker(self):
        url = build_issue_url("hello")
        self.assertTrue(url.startswith(ISSUES_URL))

    def test_encodes_the_body_and_title(self):
        url = build_issue_url("line1\nline2", title="[Bug] crash")
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        self.assertEqual(query["body"], ["line1\nline2"])
        self.assertEqual(query["title"], ["[Bug] crash"])

    def test_body_is_capped(self):
        url = build_issue_url("y" * (MAX_BODY_CHARS * 3))
        body = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["body"][0]
        self.assertEqual(len(body), MAX_BODY_CHARS)

    def test_omits_an_empty_title(self):
        self.assertNotIn("title=", build_issue_url("body only"))


if __name__ == "__main__":
    unittest.main()
