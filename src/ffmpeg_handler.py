import json
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

from .ffmpeg_downloader import find_ffmpeg

ProgressCallback = Callable[[int, str], None]
EtaCallback = Callable[[str, str], None]

# Default audio codec used when re-encoding audio for a video container.
DEFAULT_AUDIO_CODEC = "aac"

# Containers that reject the default AAC stream. WebM only accepts Opus or
# Vorbis, and stream-copying an AAC/MP3 track into WebM fails with
# "Could not write header", so WebM always re-encodes audio to Opus.
CONTAINER_AUDIO_CODEC: dict[str, str] = {
    "WebM (VP9)": "libopus",
}

# libvpx-vp9 has no `-preset` option; the UI encoder preset is translated
# into `-cpu-used` (0 = slowest/best, 8 = fastest).
VP9_CPU_USED: dict[str, int] = {
    "ultrafast": 8,
    "superfast": 7,
    "veryfast": 6,
    "faster": 5,
    "fast": 4,
    "medium": 2,
    "slow": 1,
    "slower": 1,
    "veryslow": 0,
}


class FFmpegHandler:
    def __init__(self) -> None:
        self.ffmpeg_path: str = "ffmpeg"
        self.ffprobe_path: str = "ffprobe"
        self._process: subprocess.Popen | None = None
        self._hw_cache: str | None = None
        self._encoders_cache: str | None = None
        # Last ffprobe result, keyed by (path, mtime, size), so loading a file
        # only spawns ffprobe once instead of once per query helper.
        self._info_cache: tuple[tuple[str, int, int], dict[str, Any]] | None = None
        self._try_detect()

    def _try_detect(self) -> None:
        ffmpeg, ffprobe = find_ffmpeg()
        if ffmpeg and ffprobe:
            self.ffmpeg_path = ffmpeg
            self.ffprobe_path = ffprobe

    def check_ffmpeg(self) -> bool:
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def check_ffprobe(self) -> bool:
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _resolve_path(self, file_path: str) -> str | None:
        resolved = os.path.realpath(file_path)
        if os.path.isfile(resolved):
            return resolved
        return None

    def get_media_info(self, file_path: str) -> dict[str, Any] | None:
        resolved = self._resolve_path(file_path)
        if not resolved:
            return None

        try:
            stat = os.stat(resolved)
            cache_key = (resolved, stat.st_mtime_ns, stat.st_size)
        except OSError:
            return None

        cache = self._info_cache
        if cache is not None and cache[0] == cache_key:
            return cache[1]

        cmd = [
            self.ffprobe_path, "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            resolved
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return None
            info: dict[str, Any] = json.loads(result.stdout)
        except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
            return None
        self._info_cache = (cache_key, info)
        return info

    @staticmethod
    def get_duration_string(seconds: float | None) -> str:
        if seconds is None:
            return "00:00:00"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_codecs(self, file_path: str) -> dict[str, str | None]:
        info = self.get_media_info(file_path)
        if not info:
            return {"video": None, "audio": None}

        codecs: dict[str, str | None] = {"video": None, "audio": None}
        streams = info.get("streams")
        if not streams:
            return codecs
        for stream in streams:
            codec_type = stream.get("codec_type")
            codec_name = stream.get("codec_name")
            if codec_type in codecs and codecs[codec_type] is None:
                codecs[codec_type] = codec_name
        return codecs

    def get_resolution(self, file_path: str) -> tuple[int | None, int | None]:
        info = self.get_media_info(file_path)
        if not info:
            return None, None

        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                return stream.get("width"), stream.get("height")
        return None, None

    def _load_encoders_cache(self) -> None:
        if self._encoders_cache is not None:
            return
        if not self.check_ffmpeg():
            self._encoders_cache = ""
            return
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-encoders"],
                capture_output=True, text=True, timeout=10
            )
            self._encoders_cache = result.stdout
        except Exception:
            self._encoders_cache = ""

    def detect_hardware_acceleration(self) -> str:
        if self._hw_cache is not None:
            return self._hw_cache
        self._load_encoders_cache()
        encoders = self._encoders_cache or ""
        if "h264_nvenc" in encoders or "hevc_nvenc" in encoders:
            self._hw_cache = "NVENC (NVIDIA)"
        elif "h264_amf" in encoders or "hevc_amf" in encoders:
            self._hw_cache = "AMF (AMD)"
        elif "h264_qsv" in encoders or "hevc_qsv" in encoders:
            self._hw_cache = "QSV (Intel)"
        elif "h264_videotoolbox" in encoders:
            self._hw_cache = "VideoToolbox (Apple)"
        else:
            self._hw_cache = ""
        return self._hw_cache

    VIDEO_FORMATS: dict[str, dict[str, Any]] = {
        "MP4 (H.264)": {
            "video_codec": "libx264",
            "extension": ".mp4",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 23,
            "gif_mode": False,
        },
        "MP4 (H.265)": {
            "video_codec": "libx265",
            "extension": ".mp4",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 28,
            "gif_mode": False,
        },
        "AVI": {
            "video_codec": "libx264",
            "extension": ".avi",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 23,
            "gif_mode": False,
        },
        "MKV (H.264)": {
            "video_codec": "libx264",
            "extension": ".mkv",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 23,
            "gif_mode": False,
        },
        "WebM (VP9)": {
            "video_codec": "libvpx-vp9",
            "extension": ".webm",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 63),
            "default_crf": 31,
            "gif_mode": False,
        },
        "MOV": {
            "video_codec": "libx264",
            "extension": ".mov",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 23,
            "gif_mode": False,
        },
        "GIF": {
            "video_codec": "gif",
            "extension": ".gif",
            "presets": [],
            "quality_range": (1, 100),
            "default_crf": 50,
            "gif_mode": True,
        },
    }

    AUDIO_FORMATS: dict[str, dict[str, Any]] = {
        "MP3": {"audio_codec": "libmp3lame", "extension": ".mp3", "bitrates": ["128k", "192k", "256k", "320k"]},
        "AAC": {"audio_codec": "aac", "extension": ".aac", "bitrates": ["128k", "192k", "256k", "320k"]},
        "WAV": {"audio_codec": "pcm_s16le", "extension": ".wav", "bitrates": ["1411k"]},
        "FLAC": {"audio_codec": "flac", "extension": ".flac", "bitrates": ["auto"]},
        "OGG (Vorbis)": {"audio_codec": "libvorbis", "extension": ".ogg", "bitrates": ["128k", "192k", "256k", "320k"]},
        "M4A": {"audio_codec": "aac", "extension": ".m4a", "bitrates": ["128k", "192k", "256k", "320k"]},
        "WMA": {"audio_codec": "wmav2", "extension": ".wma", "bitrates": ["128k", "192k", "256k", "320k"]},
    }

    def _get_hw_encoder(self, fmt_name: str) -> str | None:
        """Return the hardware encoder matching the software codec of `fmt_name`.

        Selection is driven by the format's `video_codec` (libx264 -> h264_*,
        libx265 -> hevc_*) so an H.265 output can never fall back to an H.264
        hardware encoder. Software-only formats (VP9, GIF) return None.
        """
        fmt = self.VIDEO_FORMATS.get(fmt_name)
        if not fmt:
            return None
        codec = fmt["video_codec"]
        prefix = "h264" if codec == "libx264" else "hevc" if codec == "libx265" else None
        if prefix is None:
            return None
        self._load_encoders_cache()
        encoders = self._encoders_cache or ""
        for backend in ("nvenc", "amf", "qsv"):
            candidate = f"{prefix}_{backend}"
            if candidate in encoders:
                return candidate
        return None

    @staticmethod
    def _vp9_preset_args(preset: str) -> list[str]:
        """Translate a UI encoder preset into libvpx-vp9 speed options."""
        cpu_used = VP9_CPU_USED.get(preset, 2)
        return ["-deadline", "good", "-cpu-used", str(cpu_used)]

    def build_convert_command(
        self,
        input_file: str,
        output_file: str,
        mode: str,
        settings: dict[str, Any],
        trim_start: int | float | None = None,
        trim_duration: int | float | None = None,
    ) -> list[str] | None:
        resolved_input = self._resolve_path(input_file)
        if not resolved_input:
            return None

        cmd: list[str] = [self.ffmpeg_path, "-i", resolved_input]

        if trim_start is not None and trim_duration is not None:
            cmd.extend(["-ss", str(trim_start)])
            cmd.extend(["-t", str(trim_duration)])

        if mode == "video":
            fmt = self.VIDEO_FORMATS.get(settings["format"])
            if not fmt:
                return None

            if fmt.get("gif_mode"):
                fps = settings.get("framerate") or "10"
                res = settings.get("resolution")
                try:
                    max_colors = int(settings.get("max_colors", 256))
                except (TypeError, ValueError):
                    max_colors = 256
                max_colors = max(2, min(256, max_colors))
                filters = [f"fps={fps}"]
                if res:
                    filters.append(f"scale={res}:flags=lanczos")
                vf = (
                    f"{','.join(filters)},"
                    f"split[s0][s1];[s0]palettegen=max_colors={max_colors}[p];"
                    f"[s1][p]paletteuse=dither=bayer"
                )
                cmd.extend(["-vf", vf, "-loop", "0", "-an"])
            else:
                use_hw = settings.get("hw_accel", False)
                if use_hw:
                    hw_encoder = self._get_hw_encoder(settings["format"])
                    if hw_encoder:
                        cmd.extend(["-c:v", hw_encoder])
                        if "nvenc" in hw_encoder:
                            cmd.extend(["-cq", str(settings.get("crf", 23))])
                        elif "amf" in hw_encoder:
                            cmd.extend(["-quality", "balanced"])
                        elif "qsv" in hw_encoder:
                            cmd.extend(["-global_quality", str(settings.get("crf", 23))])
                    else:
                        # Hardware acceleration is unavailable for this format
                        # (e.g. VP9); fall back to the software encoder.
                        cmd.extend(["-c:v", fmt["video_codec"]])
                        if settings.get("crf") is not None:
                            cmd.extend(["-crf", str(settings["crf"])])
                        if fmt["video_codec"] == "libvpx-vp9":
                            cmd.extend(["-b:v", "0"])
                            cmd.extend(self._vp9_preset_args(str(settings.get("preset", ""))))
                        elif settings.get("preset"):
                            cmd.extend(["-preset", settings["preset"]])
                else:
                    codec = fmt["video_codec"]
                    cmd.extend(["-c:v", codec])
                    if settings.get("crf") is not None:
                        cmd.extend(["-crf", str(settings["crf"])])
                    if codec == "libvpx-vp9":
                        # Constant-quality VP9 requires an explicit zero target
                        # bitrate; libvpx has no `-preset`, so map it to `-cpu-used`.
                        cmd.extend(["-b:v", "0"])
                        cmd.extend(self._vp9_preset_args(str(settings.get("preset", ""))))
                    elif settings.get("preset"):
                        cmd.extend(["-preset", settings["preset"]])

                # Apple/QuickTime compatibility for HEVC in MP4/MOV.
                if fmt["video_codec"] == "libx265" and fmt["extension"] in (".mp4", ".mov"):
                    cmd.extend(["-tag:v", "hvc1"])

                if settings.get("resolution"):
                    cmd.extend(["-vf", f"scale={settings['resolution']}"])
                if settings.get("framerate"):
                    cmd.extend(["-r", str(settings["framerate"])])

                if settings.get("keep_audio", True):
                    container_audio = CONTAINER_AUDIO_CODEC.get(settings["format"], DEFAULT_AUDIO_CODEC)
                    wants_copy = bool(settings.get("copy_audio", False))
                    # Stream-copy is only safe into containers that accept the
                    # source codec (i.e. the AAC-based ones); WebM must re-encode.
                    if wants_copy and container_audio == DEFAULT_AUDIO_CODEC:
                        # Stream-copy the original audio (no re-encode, no quality loss)
                        cmd.extend(["-c:a", "copy"])
                    else:
                        # For WebM the container codec always wins (Opus);
                        # otherwise honor the requested codec, defaulting to AAC.
                        acodec = (
                            container_audio
                            if container_audio != DEFAULT_AUDIO_CODEC
                            else settings.get("audio_codec") or DEFAULT_AUDIO_CODEC
                        )
                        cmd.extend(["-c:a", acodec])
                        abitrate = settings.get("audio_bitrate", "192k")
                        if abitrate and abitrate != "auto":
                            cmd.extend(["-b:a", abitrate])
                else:
                    cmd.extend(["-an"])

        elif mode == "audio":
            fmt = self.AUDIO_FORMATS.get(settings["format"])
            if not fmt:
                return None
            cmd.extend(["-vn", "-c:a", fmt["audio_codec"]])
            if settings.get("bitrate") and settings["bitrate"] != "auto":
                cmd.extend(["-b:a", settings["bitrate"]])
            if settings.get("sample_rate"):
                cmd.extend(["-ar", str(settings["sample_rate"])])
            if settings.get("channels"):
                cmd.extend(["-ac", str(settings["channels"])])

        elif mode == "extract_audio":
            acodec = settings.get("audio_codec", "libmp3lame")
            cmd.extend(["-vn", "-c:a", acodec])
            if settings.get("bitrate") and settings["bitrate"] != "auto":
                cmd.extend(["-b:a", settings["bitrate"]])

        cmd.extend(["-y", output_file])
        return cmd

    def start_conversion(
        self,
        cmd: list[str],
        progress_callback: ProgressCallback | None = None,
        eta_callback: EtaCallback | None = None,
    ) -> bool:
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )

        duration: float | None = None
        start_time = time.time()

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        duration_pattern = re.compile(r"Duration: (\d+):(\d+):(\d+\.\d+)")

        def read_stderr() -> None:
            nonlocal duration
            proc = self._process
            if proc is None or proc.stderr is None:
                return
            for line in proc.stderr:
                if duration is None:
                    dur_match = duration_pattern.search(line)
                    if dur_match:
                        h, m, s = dur_match.groups()
                        duration = int(h) * 3600 + int(m) * 60 + float(s)

                time_match = time_pattern.search(line)
                if time_match and duration and duration > 0:
                    h, m, s = time_match.groups()
                    current = int(h) * 3600 + int(m) * 60 + float(s)
                    now = time.time()

                    progress = int((current / duration) * 100)
                    if progress_callback:
                        progress_callback(min(progress, 100), "")

                    elapsed = now - start_time
                    if current > 0 and elapsed > 2:
                        speed = current / elapsed
                        remaining = (duration - current) / speed if speed > 0 else 0
                        eta_str = f"{int(remaining // 60)}m {int(remaining % 60):02d}s"
                        speed_str = f"{speed:.1f}x"
                        if eta_callback:
                            eta_callback(eta_str, speed_str)

        reader = threading.Thread(target=read_stderr, daemon=True)
        reader.start()
        reader.join()

        self._process.wait()
        # Only report 100% on real success; on failure the UI keeps the
        # last valid progress so the bar never lies about completion.
        if self._process.returncode == 0 and progress_callback:
            progress_callback(100, "")

        return self._process.returncode == 0

    def cancel_conversion(self) -> bool:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            return True
        return False

    def get_supported_video_formats(self) -> list[str]:
        return list(self.VIDEO_FORMATS.keys())

    def get_supported_audio_formats(self) -> list[str]:
        return list(self.AUDIO_FORMATS.keys())

    def get_file_summary(self, file_path: str) -> dict[str, Any] | None:
        info = self.get_media_info(file_path)
        if not info:
            return None
        codecs = self.get_codecs(file_path)
        width, height = self.get_resolution(file_path)
        duration: float | None = None
        bitrate: str | None = None
        if info and "format" in info:
            duration_str = info["format"].get("duration")
            if duration_str:
                duration = float(duration_str)
            bitrate = info["format"].get("bit_rate")
        size_mb = os.path.getsize(file_path) / 1024 / 1024
        return {
            "filename": os.path.basename(file_path),
            "size_mb": size_mb,
            "video_codec": codecs.get("video"),
            "audio_codec": codecs.get("audio"),
            "width": width,
            "height": height,
            "duration": duration,
            "duration_str": self.get_duration_string(duration) if duration else "00:00:00",
            "bitrate": int(bitrate) // 1000 if bitrate else None,
        }
