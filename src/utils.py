"""
Shared helpers for Shuttle Codec.

Small, dependency-light utilities used by several modules:
icon path resolution (dev vs PyInstaller-frozen) and time formatting.
"""

import os
import shutil
import sys
from collections.abc import Iterable
from typing import Protocol

# Still-image inputs are handled by the dedicated image conversion mode.
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
)


class TimeLike(Protocol):
    """Structural type for QTime-like objects (avoids importing PyQt5 here)."""

    def hour(self) -> int: ...

    def minute(self) -> int: ...

    def second(self) -> int: ...


def get_icon_path() -> str:
    """Return the absolute path to logo.png in both dev and frozen (PyInstaller) runs."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "logo.png")  # type: ignore[attr-defined]
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "logo.png"))


def format_seconds(seconds: float) -> str:
    """Format a number of seconds as a compact human string (45s / 3m 05s / 1h 02m 30s)."""
    s = max(0, int(seconds))
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {s:02d}s"


def qtime_to_seconds(qtime: TimeLike) -> int:
    """Convert a QTime to total seconds without importing PyQt5 here."""
    return int(qtime.hour() * 3600
               + qtime.minute() * 60
               + qtime.second())


def seconds_to_qtime_components(total_seconds: int) -> "tuple[int, int, int]":
    """Split a duration in seconds into (h, m, s) components."""
    total_seconds = max(0, int(total_seconds))
    return total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60


def open_folder(path: str) -> bool:
    """
    Open a folder in the OS file manager, cross-platform.

    Returns True on success. Uses QDesktopServices when available (the
    Qt way, works everywhere); falls back to platform-specific commands.
    """
    if not path or not os.path.isdir(path):
        return False
    try:
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices

        return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
    except ImportError:
        # Non-Qt context: fall back to OS commands
        try:
            if sys.platform == "win32":
                # `unused-ignore`: the attribute only exists on Windows typeshed,
                # so the ignore itself trips strict mode on a Windows machine.
                os.startfile(path)  # type: ignore[attr-defined, unused-ignore]  # noqa: S606
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", path])  # noqa: S603
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])  # noqa: S603
            return True
        except OSError:
            return False


def human_size(size_bytes: float) -> str:
    """Format a byte count in MB with one decimal."""
    return f"{size_bytes / 1024 / 1024:.1f} MB"


def is_image_file(path: str) -> bool:
    """True for still-image inputs, which use the image conversion mode."""
    return os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS


def filter_existing_files(paths: Iterable[str]) -> list[str]:
    """Keep only existing files (used when restoring a persisted batch queue)."""
    return [p for p in paths if isinstance(p, str) and os.path.isfile(p)]


# Copy of `sys.platform` typed as a plain string: typeshed narrows the original
# to the platform running mypy, which would mark the other branches of this
# module as unreachable (`warn_unreachable`) on every OS but one.
PLATFORM: str = sys.platform


def shutdown_command() -> list[str] | None:
    """
    Return the platform command that powers the machine off right now.

    Returns None when no supported command exists; callers must treat that
    as "cannot shut down" rather than silently doing nothing.
    """
    if PLATFORM == "win32":
        return ["shutdown", "/s", "/t", "0"]
    if PLATFORM == "darwin":
        return ["osascript", "-e", 'tell application "System Events" to shut down']
    if shutil.which("systemctl"):
        return ["systemctl", "poweroff"]
    if shutil.which("shutdown"):
        return ["shutdown", "-h", "now"]
    return None


def safe_int(value: str | None, default: int | None = None) -> int | None:
    """Parse an int from a string, returning `default` on failure."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
