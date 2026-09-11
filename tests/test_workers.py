import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.workers import BatchConversionManager


def make_cmd_tool(path: str):
    """Return a callable that records calls and returns a canned value."""
    calls = []

    def recorder(*args, **kwargs):
        calls.append((args, kwargs))
        return path

    recorder.calls = calls
    return recorder


class TestBatchConversionManager(unittest.TestCase):
    def setUp(self):
        self.manager = BatchConversionManager()
        self.finished_signals = []

    def test_initial_state(self):
        self.assertFalse(self.manager.is_running())
        self.assertEqual(self.manager.total, 0)
        self.assertEqual(self.manager.success_count, 0)

    def test_empty_queue_emits_all_finished_immediately(self):
        received = []
        self.manager.all_finished.connect(lambda ok, total: received.append((ok, total)))
        self.manager.start(ffmpeg=None, items=[])
        self.assertEqual(received, [(0, 0)])

    def test_wait_returns_true_when_idle(self):
        self.assertTrue(self.manager.wait())

    def test_start_rejects_without_ffmpeg(self):
        received = []
        self.manager.all_finished.connect(lambda ok, total: received.append((ok, total)))
        items = [("/in1.mp4", "/out1.mp4", ["ffmpeg"], "d1")]
        self.manager.start(ffmpeg=None, items=items)
        # ffmpeg is None -> bail out immediately
        self.assertEqual(received, [(0, 1)])
        self.assertFalse(self.manager.is_running())


if __name__ == "__main__":
    unittest.main()
