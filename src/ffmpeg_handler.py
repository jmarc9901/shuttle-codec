import os
import subprocess
import json
import re
import time
import threading

from .ffmpeg_downloader import find_ffmpeg


class FFmpegHandler:
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self._process = None
        self._hw_cache = None
        self._encoders_cache = None
        self._try_detect()

    def _try_detect(self):
        ffmpeg, ffprobe = find_ffmpeg()
        if ffmpeg and ffprobe:
            self.ffmpeg_path = ffmpeg
            self.ffprobe_path = ffprobe

    def check_ffmpeg(self):
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def check_ffprobe(self):
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_media_info(self, file_path):
        if not os.path.exists(file_path):
            return None

        cmd = [
            self.ffprobe_path, "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            file_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return None
            return json.loads(result.stdout)
        except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def get_duration_string(self, seconds):
        if seconds is None:
            return "00:00:00"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_codecs(self, file_path):
        info = self.get_media_info(file_path)
        if not info:
            return {"video": None, "audio": None}

        codecs = {"video": None, "audio": None}
        streams = info.get("streams", [])
        if streams is None:
            return codecs
        for stream in streams:
            codec_type = stream.get("codec_type")
            codec_name = stream.get("codec_name")
            if codec_type in codecs and codecs[codec_type] is None:
                codecs[codec_type] = codec_name
        return codecs

    def get_resolution(self, file_path):
        info = self.get_media_info(file_path)
        if not info:
            return None, None

        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                return stream.get("width"), stream.get("height")
        return None, None

    def _load_encoders_cache(self):
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
        except:
            self._encoders_cache = ""

    def detect_hardware_acceleration(self):
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

    VIDEO_FORMATS = {
        "MP4 (H.264)": {
            "video_codec": "libx264",
            "extension": ".mp4",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 23,
        },
        "MP4 (H.265)": {
            "video_codec": "libx265",
            "extension": ".mp4",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 28,
        },
        "AVI": {
            "video_codec": "libx264",
            "extension": ".avi",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 23,
        },
        "MKV (H.264)": {
            "video_codec": "libx264",
            "extension": ".mkv",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 23,
        },
        "WebM (VP9)": {
            "video_codec": "libvpx-vp9",
            "extension": ".webm",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 63),
            "default_crf": 31,
        },
        "MOV": {
            "video_codec": "libx264",
            "extension": ".mov",
            "presets": ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            "quality_range": (0, 51),
            "default_crf": 23,
        },
    }

    AUDIO_FORMATS = {
        "MP3": {"audio_codec": "libmp3lame", "extension": ".mp3", "bitrates": ["128k", "192k", "256k", "320k"]},
        "AAC": {"audio_codec": "aac", "extension": ".aac", "bitrates": ["128k", "192k", "256k", "320k"]},
        "WAV": {"audio_codec": "pcm_s16le", "extension": ".wav", "bitrates": ["1411k"]},
        "FLAC": {"audio_codec": "flac", "extension": ".flac", "bitrates": ["auto"]},
        "OGG (Vorbis)": {"audio_codec": "libvorbis", "extension": ".ogg", "bitrates": ["128k", "192k", "256k", "320k"]},
        "M4A": {"audio_codec": "aac", "extension": ".m4a", "bitrates": ["128k", "192k", "256k", "320k"]},
        "WMA": {"audio_codec": "wmav2", "extension": ".wma", "bitrates": ["128k", "192k", "256k", "320k"]},
    }

    def _get_hw_encoder(self, fmt_name):
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

    def build_convert_command(self, input_file, output_file, mode, settings,
                              trim_start=None, trim_duration=None):
        cmd = [self.ffmpeg_path, "-i", input_file]

        if trim_start is not None and trim_duration is not None:
            cmd.extend(["-ss", str(trim_start)])
            cmd.extend(["-t", str(trim_duration)])

        if mode == "video":
            fmt = self.VIDEO_FORMATS.get(settings["format"])
            if not fmt:
                return None

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

    def start_conversion(self, cmd, progress_callback=None, eta_callback=None):
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        duration = None
        start_time = time.time()

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        duration_pattern = re.compile(r"Duration: (\d+):(\d+):(\d+\.\d+)")

        def read_stderr():
            nonlocal duration
            for line in self._process.stderr:
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
                        progress_callback(min(progress, 100))

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
            progress_callback(100)

        return self._process.returncode == 0

    def cancel_conversion(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            return True
        return False

    def get_supported_video_formats(self):
        return list(self.VIDEO_FORMATS.keys())

    def get_supported_audio_formats(self):
        return list(self.AUDIO_FORMATS.keys())
