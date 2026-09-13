import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.workers import BatchConversionManager, BatchItem, ConversionThread


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
        items = [BatchItem("/in1.mp4", "/out1.mp4", ["ffmpeg"], "d1")]
        self.manager.start(ffmpeg=None, items=items)
        # ffmpeg is None -> bail out immediately
        self.assertEqual(received, [(0, 1)])
        self.assertFalse(self.manager.is_running())


class TestBatchItem(unittest.TestCase):
    def test_fields_and_default_fallback(self):
        item = BatchItem("in.mp4", "out.mp4", ["ffmpeg"], "in → out")
        self.assertEqual(item.input_path, "in.mp4")
        self.assertEqual(item.output_path, "out.mp4")
        self.assertEqual(item.cmd, ["ffmpeg"])
        self.assertIsNone(item.fallback_cmd)

    def test_accepts_a_fallback_command(self):
        item = BatchItem("in.mp4", "out.mp4", ["a"], "d", ["b"])
        self.assertEqual(item.fallback_cmd, ["b"])


class FakeFFmpeg:
    """Minimal stand-in for FFmpegHandler that fails a set number of times."""

    def __init__(self, failures: int = 1, cancelled: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.failures = failures
        self._cancelled = cancelled

    def start_conversion(self, cmd, progress_callback=None, eta_callback=None) -> bool:
        self.calls.append(list(cmd))
        return len(self.calls) > self.failures

    def cancel_requested(self) -> bool:
        return self._cancelled


class TestConversionThreadFallback(unittest.TestCase):
    """Hardware encoding can fail at runtime; the job must retry on the CPU."""

    def _thread(self, ffmpeg, output_path, fallback_cmd):
        thread = ConversionThread(
            ffmpeg, ["ffmpeg", "-c:v", "h264_nvenc"], "test", output_path, fallback_cmd=fallback_cmd
        )
        results = []
        logs = []
        thread.conversion_done.connect(lambda ok, desc, out: results.append(ok))
        thread.log.connect(logs.append)
        return thread, results, logs

    def test_retries_in_software_after_a_hardware_failure(self):
        ffmpeg = FakeFFmpeg(failures=1)
        thread, results, logs = self._thread(ffmpeg, "", ["ffmpeg", "-c:v", "libx264"])
        thread.run()
        self.assertEqual(ffmpeg.calls, [["ffmpeg", "-c:v", "h264_nvenc"], ["ffmpeg", "-c:v", "libx264"]])
        self.assertEqual(results, [True])
        self.assertTrue(any("reintentando" in line or "retrying" in line for line in logs))

    def test_no_retry_without_a_fallback_command(self):
        ffmpeg = FakeFFmpeg(failures=1)
        thread, results, _ = self._thread(ffmpeg, "", None)
        thread.run()
        self.assertEqual(len(ffmpeg.calls), 1)
        self.assertEqual(results, [False])

    def test_no_retry_after_the_user_cancelled(self):
        ffmpeg = FakeFFmpeg(failures=1, cancelled=True)
        thread, results, _ = self._thread(ffmpeg, "", ["ffmpeg", "-c:v", "libx264"])
        thread.run()
        self.assertEqual(len(ffmpeg.calls), 1)
        self.assertEqual(results, [False])

    def test_partial_output_is_removed_before_the_retry(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            partial = f.name
            f.write(b"half-written")
        ffmpeg = FakeFFmpeg(failures=1)
        thread, results, _ = self._thread(ffmpeg, partial, ["ffmpeg", "-c:v", "libx264"])
        thread.run()
        try:
            self.assertFalse(os.path.exists(partial))
            self.assertEqual(results, [True])
        finally:
            if os.path.exists(partial):
                os.remove(partial)

    def test_successful_first_attempt_does_not_retry(self):
        ffmpeg = FakeFFmpeg(failures=0)
        thread, results, _ = self._thread(ffmpeg, "", ["ffmpeg", "-c:v", "libx264"])
        thread.run()
        self.assertEqual(len(ffmpeg.calls), 1)
        self.assertEqual(results, [True])


class TestBatchConversionManagerFlow(unittest.TestCase):
    """The queue must run every item in order and drain on cancel."""

    def _thread_class(self, emit: bool):
        instances: list[object] = []
        self.instances = instances

        class FakeThread:
            def __init__(self, ffmpeg, cmd, description, output_path, fallback_cmd=None, parent=None):
                self.cmd = cmd
                self.output_path = output_path
                self.fallback_cmd = fallback_cmd
                self.conversion_done = MagicMock()
                instances.append(self)

            def start(self) -> None:
                if not emit:
                    return
                for call in self.conversion_done.connect.call_args_list:
                    call[0][0](True, "done", self.output_path)

            def isRunning(self) -> bool:  # noqa: N802 - Qt naming
                return False

        return FakeThread

    def test_queue_runs_every_item_in_order(self):
        manager = BatchConversionManager()
        items = [BatchItem(f"/in{i}.mp4", f"/out{i}.mp4", ["ffmpeg"], f"d{i}") for i in range(3)]
        finished: list[tuple[int, bool]] = []
        all_done: list[tuple[int, int]] = []
        manager.file_finished.connect(lambda index, ok, out: finished.append((index, ok)))
        manager.all_finished.connect(lambda ok, total: all_done.append((ok, total)))

        with patch("src.workers.ConversionThread", self._thread_class(emit=True)):
            manager.start(FakeFFmpeg(failures=0), items)

        self.assertEqual([index for index, _ in finished], [0, 1, 2])
        self.assertTrue(all(ok for _, ok in finished))
        self.assertEqual(all_done, [(3, 3)])
        self.assertFalse(manager.is_running())

    def test_fallback_command_is_forwarded_to_the_thread(self):
        manager = BatchConversionManager()
        items = [BatchItem("/in.mp4", "/out.mp4", ["ffmpeg"], "d", ["ffmpeg", "-c:v", "libx264"])]

        with patch("src.workers.ConversionThread", self._thread_class(emit=True)):
            manager.start(FakeFFmpeg(failures=0), items)

        self.assertEqual(self.instances[0].fallback_cmd, ["ffmpeg", "-c:v", "libx264"])

    def test_cancel_drains_the_queue(self):
        manager = BatchConversionManager()
        items = [BatchItem(f"/in{i}.mp4", f"/out{i}.mp4", ["ffmpeg"], f"d{i}") for i in range(3)]

        with patch("src.workers.ConversionThread", self._thread_class(emit=False)):
            manager.start(FakeFFmpeg(failures=0), items)
            self.assertTrue(manager.is_running())
            manager.cancel()

        self.assertFalse(manager.is_running())
        self.assertEqual(manager.queue, [])
        self.assertTrue(manager.wait())


if __name__ == "__main__":
    unittest.main()
