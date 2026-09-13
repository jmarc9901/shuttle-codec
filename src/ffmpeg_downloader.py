"""
FFmpeg binary location for Shuttle Codec.

Finds ffmpeg/ffprobe either bundled in resources/bin/ (dev and
PyInstaller-frozen runs) or installed system-wide on PATH.
"""

import os
import sys
from collections.abc import Callable
from shutil import which
from typing import NamedTuple

from .i18n import tr


class FFmpegStatus(NamedTuple):
    """Result of locating FFmpeg, with user-facing status text."""

    ffmpeg: str | None
    ffprobe: str | None
    bundled: bool

    @property
    def ok(self) -> bool:
        return self.ffmpeg is not None and self.ffprobe is not None


def get_bundled_dir() -> str:
    base: str
    try:
        base = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "resources", "bin")


def find_ffmpeg_status() -> FFmpegStatus:
    """Locate FFmpeg, preferring bundled binaries over system PATH."""
    ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffprobe_exe = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"

    bundled_dir = get_bundled_dir()
    bundled_ffmpeg = os.path.join(bundled_dir, ffmpeg_exe)
    bundled_ffprobe = os.path.join(bundled_dir, ffprobe_exe)

    if os.path.isfile(bundled_ffmpeg) and os.path.isfile(bundled_ffprobe):
        return FFmpegStatus(bundled_ffmpeg, bundled_ffprobe, bundled=True)

    path_ffmpeg = which(ffmpeg_exe)
    path_ffprobe = which(ffprobe_exe)
    if path_ffmpeg and path_ffprobe:
        return FFmpegStatus(path_ffmpeg, path_ffprobe, bundled=False)

    return FFmpegStatus(None, None, bundled=False)


def find_ffmpeg() -> tuple[str | None, str | None]:
    """Backward-compatible tuple API used by FFmpegHandler and tests."""
    status = find_ffmpeg_status()
    return status.ffmpeg, status.ffprobe


ProgressCallback = Callable[[int, str], None]


def ensure_ffmpeg(progress_callback: ProgressCallback | None = None) -> FFmpegStatus:
    """Locate FFmpeg or raise RuntimeError with a translated message."""
    status = find_ffmpeg_status()
    if status.ok:
        if progress_callback:
            progress_callback(100, tr("ffmpeg_ready"))
        return status
    if progress_callback:
        progress_callback(0, tr("ffmpeg_missing"))
    raise RuntimeError(tr("ffmpeg_not_found"))
