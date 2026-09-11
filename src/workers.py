"""
Background workers for Shuttle Codec.

Contains the QThread-based conversion worker and the batch queue
manager. All Qt signal definitions live here so the main window stays
free of threading logic.

Note: `ConversionThread` intentionally does NOT override QThread's
built-in `finished` signal (a classic PyQt footgun); the custom
completion signal is named `conversion_done`.
"""

import time

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from .ffmpeg_handler import FFmpegHandler
from .i18n import tr
from .utils import format_seconds

# (input_path, output_path, cmd, description)
BatchItem = tuple[str, str, list[str], str]


class ConversionThread(QThread):
    """Runs one FFmpeg conversion in a background thread."""

    progress = pyqtSignal(int, str)
    conversion_done = pyqtSignal(bool, str, str)  # success, description, output_path
    log = pyqtSignal(str)
    eta_update = pyqtSignal(str, str)

    def __init__(
        self,
        ffmpeg: FFmpegHandler,
        cmd: list[str],
        description: str,
        output_path: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.ffmpeg = ffmpeg
        self.cmd = cmd
        self.description = description
        self.output_path = output_path

    def run(self) -> None:
        start_time = time.time()
        self.log.emit(tr("log_conversion_start", self.description))
        self.log.emit(tr("log_conversion_cmd", ' '.join(self.cmd)))
        success = self.ffmpeg.start_conversion(
            self.cmd,
            progress_callback=self.on_progress,
            eta_callback=self.on_eta,
        )
        elapsed = time.time() - start_time
        if success:
            self.log.emit(tr("log_conversion_done", format_seconds(elapsed)))
        else:
            self.log.emit(tr("log_conversion_error"))
        self.conversion_done.emit(success, self.description, self.output_path)

    def on_progress(self, pct: int, status: str = "") -> None:
        self.progress.emit(pct, status)

    def on_eta(self, eta: str, speed: str) -> None:
        self.eta_update.emit(eta, speed)


class BatchConversionManager(QObject):
    """Sequentially runs a queue of conversions, emitting per-file signals."""

    file_finished = pyqtSignal(int, bool, str)  # index, success, output_path
    all_finished = pyqtSignal(int, int)         # successful, total

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.queue: list[BatchItem] = []
        self.current_index: int = -1
        self.total: int = 0
        self.success_count: int = 0
        # Named with a leading underscore: QObject already owns `thread()`.
        self._thread: ConversionThread | None = None
        self.ffmpeg: FFmpegHandler | None = None
        self.results: list[tuple[bool, str]] = []
        self.cancelled: bool = False
        self._running: bool = False

    def is_running(self) -> bool:
        """True while a batch is being processed."""
        return self._running

    def start(self, ffmpeg: FFmpegHandler, items: list[BatchItem]) -> None:
        self.ffmpeg = ffmpeg
        self.queue = list(items)
        self.total = len(self.queue)
        self.current_index = 0
        self.success_count = 0
        self.results = []
        self.cancelled = False
        self._running = True
        self._process_next()

    def _process_next(self) -> None:
        if self.current_index >= len(self.queue) or self.current_index < 0:
            self._running = False
            self.all_finished.emit(self.success_count, self.total)
            return
        item = self.queue[self.current_index]
        _inp, out, cmd, desc = item
        if self.ffmpeg is None:
            self._running = False
            self.all_finished.emit(self.success_count, self.total)
            return
        self._thread = ConversionThread(self.ffmpeg, cmd, desc, out, parent=self)
        self._thread.conversion_done.connect(self._on_item_finished)
        self._thread.start()

    def _on_item_finished(self, success: bool, desc: str, outpath: str) -> None:
        self.results.append((success, outpath))
        if success:
            self.success_count += 1
        self.file_finished.emit(self.current_index, success, outpath)
        self.current_index += 1
        self._process_next()

    def cancel(self) -> None:
        """Cancel the running conversion and drain the queue."""
        self.cancelled = True
        self._running = False
        if self._thread and self._thread.isRunning() and self.ffmpeg:
            self.ffmpeg.cancel_conversion()
        self.queue = []
        self.current_index = -1

    def wait(self, timeout_ms: int = 5000) -> bool:
        """Block until the in-flight item thread stops. True if it finished."""
        if self._thread is not None and self._thread.isRunning():
            return bool(self._thread.wait(timeout_ms))
        return True
