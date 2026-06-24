import os
import sys


def get_bundled_dir():
    """Get the directory where bundled FFmpeg binaries are located."""
    try:
        # PyInstaller bundled mode
        base = sys._MEIPASS
    except AttributeError:
        # Development mode
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "resources", "bin")


def find_ffmpeg():
    """Find ffmpeg and ffprobe executables (bundled or system)."""
    ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffprobe_exe = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"

    # 1. Try bundled version first
    bundled_dir = get_bundled_dir()
    bundled_ffmpeg = os.path.join(bundled_dir, ffmpeg_exe)
    bundled_ffprobe = os.path.join(bundled_dir, ffprobe_exe)

    if os.path.isfile(bundled_ffmpeg) and os.path.isfile(bundled_ffprobe):
        return bundled_ffmpeg, bundled_ffprobe

    # 2. Try system PATH
    from shutil import which
    path_ffmpeg = which(ffmpeg_exe)
    path_ffprobe = which(ffprobe_exe)
    if path_ffmpeg and path_ffprobe:
        return path_ffmpeg, path_ffprobe

    return None, None


def ensure_ffmpeg(progress_callback=None):
    """Ensure FFmpeg is available. No download needed - uses bundled binaries."""
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