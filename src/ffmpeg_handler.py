import contextlib
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

# Audio codecs each container accepts as-is for a stream-copy. Copying anything
# else (for instance Vorbis into MP4) produces a file ffmpeg writes happily but
# that many players and hardware decoders reject, so those tracks are re-encoded
# instead of copied. Keep this list conservative: re-encoding is always safe.
COPY_SAFE_AUDIO_CODECS: dict[str, frozenset[str]] = {
    "MP4 (H.264)": frozenset({"aac", "mp3", "ac3", "eac3", "alac"}),
    "MP4 (H.265)": frozenset({"aac", "mp3", "ac3", "eac3", "alac"}),
    "MOV": frozenset({"aac", "mp3", "ac3", "eac3", "alac", "pcm_s16le", "pcm_s24le"}),
    "MKV (H.264)": frozenset({
        "aac", "mp3", "ac3", "eac3", "alac", "flac", "opus", "vorbis",
        "pcm_s16le", "pcm_s24le", "dts", "truehd",
    }),
    "AVI": frozenset({"mp3", "ac3", "mp2", "pcm_s16le", "pcm_s24le"}),
}

# Used for containers missing from the map and for unknown source codecs:
# the AAC-based set is the strictest one, and copying less often is harmless.
DEFAULT_COPY_SAFE_AUDIO_CODECS: frozenset[str] = COPY_SAFE_AUDIO_CODECS["MP4 (H.264)"]

# Hardware encoders and their software equivalent, used to retry a failed
# conversion on the CPU (outdated driver, GPU busy, session limit, ...).
SOFTWARE_ALTERNATIVES: dict[str, str] = {
    "h264_nvenc": "libx264",
    "hevc_nvenc": "libx265",
    "h264_amf": "libx264",
    "hevc_amf": "libx265",
    "h264_qsv": "libx264",
    "hevc_qsv": "libx265",
    "h264_videotoolbox": "libx264",
    "hevc_videotoolbox": "libx265",
}

# Options that only exist for hardware encoders: dropped when building the
# software fallback. `-cq`/`-global_quality`/`-qp_i` become `-crf` instead.
QUALITY_OPTION_ALIASES: frozenset[str] = frozenset({"-cq", "-global_quality", "-qp_i"})
DROPPED_OPTIONS_WITH_VALUE: frozenset[str] = frozenset({"-qp_p", "-qp_b", "-rc", "-quality"})

# Default CRF per software encoder, used when the fallback has no quality flag.
DEFAULT_CRF_BY_CODEC: dict[str, int] = {"libx264": 23, "libx265": 28}

# Rough bits-per-pixel values for the output-size estimate (x264/x265/VP9 at
# CRF 23, 30 fps). Only ever shown with a "≈" prefix: it is a rule of thumb.
BASE_BPP: dict[str, float] = {"libx264": 0.07, "libx265": 0.045, "libvpx-vp9": 0.05}

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
        self._process: subprocess.Popen[str] | None = None
        self._cancelled: bool = False
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

    def can_copy_audio(self, input_file: str, fmt_name: str) -> bool:
        """
        True when the input's audio track can be stream-copied into `fmt_name`.

        Stream-copying is lossless and instant, but only safe when the target
        container really supports the source codec: ffmpeg muxes Vorbis into
        MP4 without complaining, yet plenty of players and hardware decoders
        reject the resulting file. A codec that cannot be determined is never
        copied, because re-encoding is always safe.
        """
        source = str(self.get_codecs(input_file).get("audio") or "").lower()
        if not source:
            return False
        safe = COPY_SAFE_AUDIO_CODECS.get(fmt_name, DEFAULT_COPY_SAFE_AUDIO_CODECS)
        return source in safe

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

    # Still images produced by the "image" mode: either an image-to-image
    # conversion or a single frame exported from a video.
    # `quality` describes how the 1-100 UI slider is translated:
    #   "mjpeg" -> -q:v 2 (best) .. 31 (worst)   |  "webp" -> -q:v 1..100
    IMAGE_FORMATS: dict[str, dict[str, Any]] = {
        "PNG": {"image_codec": "png", "extension": ".png", "quality": "png"},
        "JPG": {"image_codec": "mjpeg", "extension": ".jpg", "quality": "mjpeg"},
        "WebP": {"image_codec": "libwebp", "extension": ".webp", "quality": "webp"},
        "BMP": {"image_codec": "bmp", "extension": ".bmp", "quality": None},
        "TIFF": {"image_codec": "tiff", "extension": ".tiff", "quality": None},
    }

    # ─── Hardware fallback ──────────────────────────────────────────────────
    def build_software_fallback(self, cmd: list[str]) -> list[str] | None:
        """
        Return an equivalent command that encodes on the CPU, or None when the
        command does not use a hardware encoder.

        Hardware encoding can still fail at runtime (outdated driver, GPU in
        use, session limit), so the worker retries the job in software instead
        of failing the whole conversion.
        """
        try:
            index = cmd.index("-c:v")
        except ValueError:
            return None
        if index + 1 >= len(cmd):
            return None
        software = SOFTWARE_ALTERNATIVES.get(cmd[index + 1])
        if software is None:
            return None

        fallback: list[str] = []
        quality_value: str | None = None
        # Where the removed quality flag used to be: options must stay before
        # the output file, otherwise ffmpeg warns about trailing options.
        insert_at: int | None = None
        i = 0
        while i < len(cmd):
            token = cmd[i]
            if i == index + 1:
                fallback.append(software)
                i += 1
                continue
            if token in DROPPED_OPTIONS_WITH_VALUE:
                insert_at = len(fallback) if insert_at is None else insert_at
                i += 2
                continue
            if token in QUALITY_OPTION_ALIASES:
                insert_at = len(fallback) if insert_at is None else insert_at
                if quality_value is None and i + 1 < len(cmd):
                    quality_value = cmd[i + 1]
                i += 2
                continue
            fallback.append(token)
            i += 1

        if insert_at is None:
            # No quality flag to rewrite: insert before the output path, which
            # is always the last token of the command.
            insert_at = max(0, len(fallback) - 1)

        if quality_value is not None:
            fallback[insert_at:insert_at] = ["-crf", quality_value]
        elif "-crf" not in fallback and "-b:v" not in fallback:
            fallback[insert_at:insert_at] = ["-crf", str(DEFAULT_CRF_BY_CODEC.get(software, 23))]
        return fallback

    # ─── Target size / size estimate ────────────────────────────────────────
    @staticmethod
    def compute_target_video_bitrate(
        target_mb: float, duration_s: float, audio_kbps: int = 0, overhead: float = 0.97
    ) -> int:
        """Video bitrate in kbps that makes the output land close to `target_mb`."""
        if target_mb <= 0 or duration_s <= 0:
            return 0
        total_kbps = (float(target_mb) * 8 * 1024 * 1024 / float(duration_s)) / 1000
        video_kbps = int(total_kbps * overhead) - max(0, int(audio_kbps))
        return max(50, video_kbps)

    @staticmethod
    def _parse_kbps(value: Any, default: int = 192) -> int:
        """Parse an audio bitrate such as "192k" into kbps."""
        try:
            return max(0, int(str(value).rstrip("kK")))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _scale_pixels(value: Any) -> int | None:
        """Return the pixel count of a "width:height" scale value, if parseable."""
        if not value:
            return None
        parts = str(value).split(":")
        if len(parts) != 2:
            return None
        try:
            width, height = int(parts[0]), int(parts[1])
        except ValueError:
            return None
        if width <= 0 or height <= 0:
            return None
        return width * height

    def video_target_bitrate(
        self, settings: dict[str, Any], input_file: str, trim_duration: int | float | None
    ) -> int:
        """
        Video bitrate (kbps) for the requested target size; 0 when not usable.

        Returns 0 when no target size is set *and* when one is set but cannot be
        honoured (no readable duration): the caller uses that to warn the user
        that the job falls back to constant quality.
        """
        target_mb = settings.get("target_size_mb")
        if not target_mb:
            return 0
        try:
            target_mb = float(target_mb)
        except (TypeError, ValueError):
            return 0
        if target_mb <= 0:
            return 0

        duration = settings.get("duration")
        if not duration:
            summary = self.get_file_summary(input_file) or {}
            duration = summary.get("duration")
        if not duration:
            return 0
        duration = float(duration)
        if trim_duration:
            duration = min(duration, float(trim_duration))

        audio_kbps = self._parse_kbps(settings.get("audio_bitrate", "192k")) if settings.get("keep_audio", True) else 0
        return self.compute_target_video_bitrate(target_mb, duration, audio_kbps)

    def estimate_output_size_mb(
        self, summary: dict[str, Any] | None, settings: dict[str, Any]
    ) -> float | None:
        """
        Rough output size in MB for the "≈ size" hint shown in the UI.

        Target-size mode returns the requested size exactly. CRF-based video
        encoding is estimated with a bits-per-pixel model (calibrated on x264
        CRF 23 at 30 fps) and audio mode from its bitrate. Returns None when an
        estimate would be meaningless (GIF, unknown input, "auto" bitrate).
        """
        target_mb = settings.get("target_size_mb")
        if target_mb:
            # A target size is exact by definition: known without the input.
            try:
                return float(target_mb)
            except (TypeError, ValueError):
                return None

        if not summary:
            return None

        duration = summary.get("duration")
        if not duration or float(duration) <= 0:
            return None
        duration = float(duration)

        # Audio-only conversion: size is bitrate x duration.
        if settings.get("bitrate") is not None:
            if str(settings.get("bitrate")) == "auto":
                return None
            kbps = self._parse_kbps(settings.get("bitrate"))
            return kbps * 1000 * duration / 8 / 1024 / 1024

        fmt = self.VIDEO_FORMATS.get(str(settings.get("format", "")))
        if not fmt or fmt.get("gif_mode"):
            return None
        bpp = BASE_BPP.get(fmt["video_codec"])
        if bpp is None:
            return None

        crf = settings.get("crf")
        if crf is not None:
            with contextlib.suppress(TypeError, ValueError):
                bpp *= 2 ** ((23.0 - float(crf)) / 6.0)

        pixels = self._scale_pixels(settings.get("resolution")) or (
            int(summary.get("width") or 0) * int(summary.get("height") or 0)
        )
        if not pixels:
            return None

        fps = 30.0
        raw_fps: Any = settings.get("framerate")
        if raw_fps:
            with contextlib.suppress(TypeError, ValueError):
                fps = float(raw_fps)

        video_kbps = pixels * fps * bpp / 1000
        audio_kbps = (
            self._parse_kbps(settings.get("audio_bitrate", "192k"))
            if settings.get("keep_audio", True)
            else 0
        )
        return (video_kbps + audio_kbps) * 1000 * duration / 8 / 1024 / 1024

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

    def _append_video_codec_args(
        self,
        cmd: list[str],
        fmt: dict[str, Any],
        settings: dict[str, Any],
        target_kbps: int = 0,
    ) -> None:
        """
        Append the video encoder and its quality/bitrate options.

        Three mutually exclusive modes: target size (single-pass rate control),
        hardware encoder (CRF-style quality knobs) or software encoder.
        """
        hw_encoder = self._get_hw_encoder(settings["format"]) if settings.get("hw_accel") else None
        crf = settings.get("crf")

        if target_kbps > 0:
            # The output size is the goal, so the quality knob does not apply.
            cmd.extend(["-c:v", hw_encoder or fmt["video_codec"]])
            if hw_encoder and "nvenc" in hw_encoder:
                cmd.extend(["-rc", "vbr"])
            cmd.extend([
                "-b:v", f"{target_kbps}k",
                "-maxrate", f"{target_kbps * 3 // 2}k",
                "-bufsize", f"{target_kbps * 3}k",
            ])
            if not hw_encoder and fmt["presets"] and settings.get("preset"):
                cmd.extend(["-preset", settings["preset"]])
            return

        if hw_encoder:
            cmd.extend(["-c:v", hw_encoder])
            quality = str(crf if crf is not None else 23)
            if "nvenc" in hw_encoder:
                cmd.extend(["-cq", quality])
            elif "amf" in hw_encoder:
                # AMF needs explicit rate control: `-quality` alone ignores the
                # quality slider, so the chosen CRF was silently discarded.
                cmd.extend(["-quality", "balanced", "-rc", "cqp", "-qp_i", quality, "-qp_p", quality])
            elif "qsv" in hw_encoder:
                cmd.extend(["-global_quality", quality])
            return

        codec = fmt["video_codec"]
        cmd.extend(["-c:v", codec])
        if crf is not None:
            cmd.extend(["-crf", str(crf)])
        if codec == "libvpx-vp9":
            # Constant-quality VP9 requires an explicit zero target bitrate;
            # libvpx has no `-preset`, so map it to `-cpu-used`.
            cmd.extend(["-b:v", "0"])
            cmd.extend(self._vp9_preset_args(str(settings.get("preset", ""))))
        elif settings.get("preset"):
            cmd.extend(["-preset", settings["preset"]])

    @staticmethod
    def _image_quality_args(fmt: dict[str, Any], quality: int) -> list[str]:
        """Translate the 1-100 image quality slider into encoder options."""
        quality = max(1, min(100, int(quality)))
        kind = fmt.get("quality")
        if kind == "mjpeg":
            # mjpeg uses -q:v 2 (best) .. 31 (worst): invert the slider.
            value = round(31 - (quality - 1) * 29 / 99)
            return ["-q:v", str(max(2, min(31, value)))]
        if kind == "webp":
            return ["-q:v", str(quality)]
        if kind == "png":
            return ["-compression_level", "6"]
        return []

    def _build_image_command(
        self,
        input_file: str,
        output_file: str,
        settings: dict[str, Any],
        frame_time: int | float | None = None,
    ) -> list[str] | None:
        """Build an image command: image-to-image, or one frame from a video."""
        fmt = self.IMAGE_FORMATS.get(str(settings.get("format", "PNG")))
        if not fmt:
            return None

        cmd: list[str] = [self.ffmpeg_path]
        if frame_time is not None:
            # Seeking before -i is much faster than decoding up to that point.
            cmd.extend(["-ss", str(frame_time)])
        cmd.extend(["-i", input_file])

        if settings.get("resolution"):
            cmd.extend(["-vf", f"scale={settings['resolution']}:flags=lanczos"])
        cmd.extend(["-frames:v", "1", "-an", "-c:v", fmt["image_codec"]])
        cmd.extend(self._image_quality_args(fmt, settings.get("quality", 92)))
        cmd.extend(["-y", output_file])
        return cmd

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

        # Image mode: a still-image conversion, or a single frame exported
        # from a video (trim_start doubles as the frame timestamp).
        if mode == "image":
            return self._build_image_command(
                resolved_input, output_file, settings, frame_time=trim_start
            )

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
                self._append_video_codec_args(
                    cmd,
                    fmt,
                    settings,
                    target_kbps=self.video_target_bitrate(settings, resolved_input, trim_duration),
                )

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
                    # source codec (i.e. the AAC-based ones) and only when the
                    # source codec itself is supported by the target container;
                    # WebM always re-encodes.
                    if (
                        wants_copy
                        and container_audio == DEFAULT_AUDIO_CODEC
                        and self.can_copy_audio(resolved_input, settings["format"])
                    ):
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
        self._cancelled = False
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
        self._cancelled = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            return True
        return False

    def cancel_requested(self) -> bool:
        """True once the user cancelled, so failures are not retried."""
        return self._cancelled

    def get_ffmpeg_version(self) -> str:
        """First line of `ffmpeg -version` (used by the bug report)."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.splitlines()[0].strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return ""

    def get_supported_video_formats(self) -> list[str]:
        return list(self.VIDEO_FORMATS.keys())

    def get_supported_audio_formats(self) -> list[str]:
        return list(self.AUDIO_FORMATS.keys())

    def get_supported_image_formats(self) -> list[str]:
        return list(self.IMAGE_FORMATS.keys())

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
