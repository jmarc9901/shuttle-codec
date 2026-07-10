import os
import sys
from shutil import which
from typing import Callable, Optional, Tuple


def get_bundled_dir() -> str:
    base: str
    try:
        base = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "resources", "bin")


def find_ffmpeg() -> Tuple[Optional[str], Optional[str]]:
    ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffprobe_exe = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"

    bundled_dir = get_bundled_dir()
    bundled_ffmpeg = os.path.join(bundled_dir, ffmpeg_exe)
    bundled_ffprobe = os.path.join(bundled_dir, ffprobe_exe)

    if os.path.isfile(bundled_ffmpeg) and os.path.isfile(bundled_ffprobe):
        return bundled_ffmpeg, bundled_ffprobe

    path_ffmpeg = which(ffmpeg_exe)
    path_ffprobe = which(ffprobe_exe)
    if path_ffmpeg and path_ffprobe:
        return path_ffmpeg, path_ffprobe

    return None, None


ProgressCallback = Callable[[int, str], None]


def ensure_ffmpeg(progress_callback: Optional[ProgressCallback] = None) -> Tuple[str, str]:
    ffmpeg, ffprobe = find_ffmpeg()
    if ffmpeg and ffprobe:
        if progress_callback:
            progress_callback(100, "FFmpeg listo (embebido)")
        return ffmpeg, ffprobe

    if progress_callback:
        progress_callback(0, "FFmpeg no encontrado")
    raise RuntimeError(
        "FFmpeg no está disponible.\n"
        "Asegúrate de que los binarios estén en resources/bin/\n"
        "o que FFmpeg esté instalado en el sistema."
    )
