import os
import subprocess
import json
import re
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .ffmpeg_downloader import find_ffmpeg

ProgressCallback = Callable[[int, str], None]
EtaCallback = Callable[[str, str], None]


class FFmpegHandler:
    def __init__(self) -> None:
        self.ffmpeg_path: str = "ffmpeg"
        self.ffprobe_path: str = "ffprobe"
        self._process: Optional[subprocess.Popen] = None
        self._hw_cache: Optional[str] = None
        self._encoders_cache: Optional[str] = None
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

    def _resolve_path(self, file_path: str) -> Optional[str]:
        resolved = os.path.realpath(file_path)
        if os.path.isfile(resolved):
            return resolved
        return None

    def get_media_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        resolved = self._resolve_path(file_path)
        if not resolved:
            return None

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
            return json.loads(result.stdout)
        except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
            return None

    @staticmethod
    def get_duration_string(seconds: Optional[float]) -> str:
        if seconds is None:
            return "00:00:00"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_codecs(self, file_path: str) -> Dict[str, Optional[str]]:
        info = self.get_media_info(file_path)
        if not info:
            return {"video": None, "audio": None}

        codecs: Dict[str, Optional[str]] = {"video": None, "audio": None}
        streams = info.get("streams")
        if not streams:
            return codecs
        for stream in streams:
            codec_type = stream.get("codec_type")
            codec_name = stream.get("codec_name")
            if codec_type in codecs and codecs[codec_type] is None:
                codecs[codec_type] = codec_name
        return codecs

    def get_resolution(self, file_path: str) -> Tuple[Optional[int], Optional[int]]:
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

    VIDEO_FORMATS: Dict[str, Dict[str, Any]] = {
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

    AUDIO_FORMATS: Dict[str, Dict[str, Any]] = {
        "MP3": {"audio_codec": "libmp3lame", "extension": ".mp3", "bitrates": ["128k", "192k", "256k", "320k"]},
        "AAC": {"audio_codec": "aac", "extension": ".aac", "bitrates": ["128k", "192k", "256k", "320k"]},
        "WAV": {"audio_codec": "pcm_s16le", "extension": ".wav", "bitrates": ["1411k"]},
        "FLAC": {"audio_codec": "flac", "extension": ".flac", "bitrates": ["auto"]},
        "OGG (Vorbis)": {"audio_codec": "libvorbis", "extension": ".ogg", "bitrates": ["128k", "192k", "256k", "320k"]},
        "M4A": {"audio_codec": "aac", "extension": ".m4a", "bitrates": ["128k", "192k", "256k", "320k"]},
        "WMA": {"audio_codec": "wmav2", "extension": ".wma", "bitrates": ["128k", "192k", "256k", "320k"]},
    }

    def _get_hw_encoder(self, fmt_name: str) -> Optional[str]:
        if fmt_name == "GIF":
            return None
        self._load_encoders_cache()
        encoders = self._encoders_cache or ""
        if "H.264" in fmt_name or "MP4" in fmt_name or "AVI" in fmt_name or "MKV" in fmt_name or "MOV" in fmt_name:
            if "h264_nvenc" in encoders:
                return "h264_nvenc"
            if "h264_amf" in encoders:
                return "h264_amf"
            if "h264_qsv" in encoders:
                return "h264_qsv"
        if "H.265" in fmt_name or "HEVC" in fmt_name:
            if "hevc_nvenc" in encoders:
                return "hevc_nvenc"
            if "hevc_amf" in encoders:
                return "hevc_amf"
            if "hevc_qsv" in encoders:
                return "hevc_qsv"
        return None

    def build_convert_command(
        self,
        input_file: str,
        output_file: str,
        mode: str,
        settings: Dict[str, Any],
        trim_start: Optional[Union[int, float]] = None,
        trim_duration: Optional[Union[int, float]] = None,
    ) -> Optional[List[str]]:
        resolved_input = self._resolve_path(input_file)
        if not resolved_input:
            return None

        cmd: List[str] = [self.ffmpeg_path, "-i", resolved_input]

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
                scale_filter = f"scale={res}:flags=lanczos" if res else "scale=-1:-1"
                vf = f"fps={fps},{scale_filter},split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer"
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
                        cmd.extend(["-c:v", fmt["video_codec"]])
                        if settings.get("crf") is not None:
                            cmd.extend(["-crf", str(settings["crf"])])
                        if settings.get("preset"):
                            cmd.extend(["-preset", settings["preset"]])
                else:
                    cmd.extend(["-c:v", fmt["video_codec"]])
                    if settings.get("crf") is not None:
                        cmd.extend(["-crf", str(settings["crf"])])
                    if settings.get("preset"):
                        cmd.extend(["-preset", settings["preset"]])

                if settings.get("resolution"):
                    cmd.extend(["-vf", f"scale={settings['resolution']}"])
                if settings.get("framerate"):
                    cmd.extend(["-r", str(settings["framerate"])])

                if settings.get("keep_audio", True):
                    acodec = settings.get("audio_codec", "aac")
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
        cmd: List[str],
        progress_callback: Optional[ProgressCallback] = None,
        eta_callback: Optional[EtaCallback] = None,
    ) -> bool:
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        duration: Optional[float] = None
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
        if progress_callback:
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

    def get_supported_video_formats(self) -> List[str]:
        return list(self.VIDEO_FORMATS.keys())

    def get_supported_audio_formats(self) -> List[str]:
        return list(self.AUDIO_FORMATS.keys())

    def get_file_summary(self, file_path: str) -> Optional[Dict[str, Any]]:
        info = self.get_media_info(file_path)
        if not info:
            return None
        codecs = self.get_codecs(file_path)
        width, height = self.get_resolution(file_path)
        duration: Optional[float] = None
        bitrate: Optional[str] = None
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
