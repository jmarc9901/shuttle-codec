"""End-to-end tests that really execute FFmpeg.

The unit tests mock the subprocess layer, so they cannot catch a command that
FFmpeg itself rejects (a wrong filter, a codec the container refuses, an option
after the output path). These run tiny 2-second 160x120 conversions with the
bundled or system FFmpeg and describe what actually came out.

The whole module skips itself when no usable FFmpeg is installed, and each test
skips when the encoder it needs is missing from that build.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ffmpeg_downloader import find_ffmpeg_status
from src.ffmpeg_handler import FFmpegHandler

_STATUS = find_ffmpeg_status()
HAS_FFMPEG = _STATUS.ok


def _encoder_list() -> str:
    """`ffmpeg -encoders` output, or an empty string when FFmpeg is missing."""
    if not HAS_FFMPEG:
        return ""
    result = subprocess.run(
        [FFmpegHandler().ffmpeg_path, "-encoders"], capture_output=True, text=True
    )
    return result.stdout


ENCODERS = _encoder_list()


def has_encoder(name: str) -> bool:
    return name in ENCODERS


requires_ffmpeg = unittest.skipUnless(HAS_FFMPEG, "FFmpeg/ffprobe not available")


@unittest.skipUnless(HAS_FFMPEG, "FFmpeg/ffprobe not available")
class FFmpegIntegrationTestCase(unittest.TestCase):
    """Scratch directory, synthetic sources and small assertion helpers."""

    def setUp(self) -> None:
        self.handler = FFmpegHandler()
        self._tmp = tempfile.TemporaryDirectory(prefix="shuttle-codec-it-")
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name

    # ─── helpers ────────────────────────────────────────────────────────────
    def run_ffmpeg(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"{' '.join(cmd)}\n{result.stderr}")
        return result

    def make_video(
        self, name: str = "src.mp4", video: str = "libx264", audio: str = "aac",
        duration: int = 2,
    ) -> str:
        """A tiny synthetic clip: colour bars plus a sine tone."""
        path = os.path.join(self.dir, name)
        cmd = [
            self.handler.ffmpeg_path, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc=size=160x120:rate=10:duration={duration}",
        ]
        if audio:
            cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
        cmd += ["-c:v", video]
        if audio:
            cmd += ["-c:a", audio]
        cmd += ["-pix_fmt", "yuv420p", "-y", path]
        self.run_ffmpeg(cmd)
        return path

    def make_image(self, name: str = "src.png") -> str:
        path = os.path.join(self.dir, name)
        self.run_ffmpeg([
            self.handler.ffmpeg_path, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=64x48:rate=1:duration=1",
            "-frames:v", "1", "-y", path,
        ])
        return path

    def stream_types(self, path: str) -> dict[str, str]:
        """Map codec_type -> codec_name for the first stream of each type.

        JSON rather than CSV: ffprobe emits CSV fields in its own order, not in
        the order they were requested.
        """
        result = subprocess.run(
            [
                self.handler.ffprobe_path, "-v", "error",
                "-show_entries", "stream=codec_type,codec_name",
                "-print_format", "json", path,
            ],
            capture_output=True, text=True,
        )
        streams: dict[str, str] = {}
        for stream in json.loads(result.stdout or "{}").get("streams", []):
            codec_type = stream.get("codec_type")
            if codec_type:
                streams.setdefault(codec_type, stream.get("codec_name", ""))
        return streams

    def duration(self, path: str) -> float:
        result = subprocess.run(
            [
                self.handler.ffprobe_path, "-v", "error",
                "-show_entries", "format=duration", "-of", "csv=p=0", path,
            ],
            capture_output=True, text=True,
        )
        return float(result.stdout.strip())

    def video_settings(self, **overrides: object) -> dict[str, object]:
        """The same shape `MainWindow._collect_video_settings` produces."""
        settings: dict[str, object] = {
            "format": "MP4 (H.264)", "crf": 30, "max_colors": 256, "preset": "ultrafast",
            "resolution": None, "framerate": None, "keep_audio": True, "copy_audio": False,
            "audio_codec": "aac", "audio_bitrate": "128k", "hw_accel": False,
            "extension": ".mp4", "target_size_mb": None,
        }
        settings.update(overrides)
        return settings

    def convert(self, source: str, mode: str, settings: dict[str, object], **kwargs: object) -> str:
        output = os.path.join(self.dir, f"out_{mode}{settings.get('extension', '.bin')}")
        cmd = self.handler.build_convert_command(source, output, mode, settings, **kwargs)  # type: ignore[arg-type]
        self.assertIsNotNone(cmd, "build_convert_command returned None")
        self.run_ffmpeg(cmd)  # type: ignore[arg-type]
        self.assertTrue(os.path.isfile(output), f"{output} was not created")
        return output

    # ─── video ──────────────────────────────────────────────────────────────
    @requires_ffmpeg
    def test_mp4_h264_with_audio_copy(self) -> None:
        source = self.make_video()
        output = self.convert(
            source, "video", self.video_settings(copy_audio=True, extension=".mp4")
        )
        self.assertEqual(self.stream_types(output), {"video": "h264", "audio": "aac"})

    @requires_ffmpeg
    def test_mp4_h265_is_tagged_for_quicktime(self) -> None:
        if not has_encoder("libx265"):
            self.skipTest("libx265 not available in this FFmpeg build")
        source = self.make_video()
        output = self.convert(
            source, "video",
            self.video_settings(format="MP4 (H.265)", crf=32, extension=".mp4"),
        )
        self.assertEqual(self.stream_types(output)["video"], "hevc")

    @requires_ffmpeg
    def test_webm_gets_vp9_and_opus(self) -> None:
        if not (has_encoder("libvpx-vp9") and has_encoder("libopus")):
            self.skipTest("VP9/Opus not available in this FFmpeg build")
        source = self.make_video()
        output = self.convert(
            source, "video",
            self.video_settings(format="WebM (VP9)", crf=40, preset="ultrafast", extension=".webm"),
        )
        self.assertEqual(self.stream_types(output), {"video": "vp9", "audio": "opus"})

    @requires_ffmpeg
    def test_gif_output_is_a_single_stream(self) -> None:
        source = self.make_video()
        output = self.convert(
            source, "video",
            self.video_settings(
                format="GIF", crf=None, max_colors=64, framerate="10",
                keep_audio=False, extension=".gif",
            ),
        )
        self.assertEqual(self.stream_types(output), {"video": "gif"})

    @requires_ffmpeg
    def test_trim_honours_the_requested_duration(self) -> None:
        source = self.make_video(duration=4)
        output = self.convert(
            source, "video", self.video_settings(preset="ultrafast"),
            trim_start=1.0, trim_duration=1.0,
        )
        self.assertAlmostEqual(self.duration(output), 1.0, delta=0.35)

    @requires_ffmpeg
    def test_target_size_lands_near_the_requested_size(self) -> None:
        source = self.make_video(duration=2)
        output = self.convert(
            source, "video",
            self.video_settings(target_size_mb=0.5, preset="ultrafast"),
        )
        size_mb = os.path.getsize(output) / 1024 / 1024
        # Single-pass rate control, so this is a sanity band and not an equality.
        self.assertLess(abs(size_mb - 0.5), 0.5, f"got {size_mb:.2f} MB")

    @requires_ffmpeg
    def test_scaled_output_uses_the_requested_resolution(self) -> None:
        source = self.make_video()
        output = self.convert(
            source, "video", self.video_settings(resolution="80:60", preset="ultrafast")
        )
        result = subprocess.run(
            [
                self.handler.ffprobe_path, "-v", "error",
                "-select_streams", "v", "-show_entries", "stream=width,height",
                "-of", "csv=p=0", output,
            ],
            capture_output=True, text=True,
        )
        self.assertEqual(result.stdout.strip(), "80,60")

    @requires_ffmpeg
    def test_audio_only_conversion(self) -> None:
        source = self.make_video()
        output = self.convert(
            source, "audio",
            {"format": "MP3", "bitrate": "128k", "extension": ".mp3"},
        )
        streams = self.stream_types(output)
        self.assertEqual(streams.get("audio"), "mp3")
        self.assertNotIn("video", streams)

    @requires_ffmpeg
    def test_extract_audio_drops_the_video_stream(self) -> None:
        source = self.make_video()
        output = self.convert(
            source, "extract_audio",
            {
                "format": "MP3", "audio_codec": "libmp3lame", "bitrate": "128k",
                "extension": ".mp3", "target_size_mb": None,
            },
        )
        streams = self.stream_types(output)
        self.assertEqual(streams.get("audio"), "mp3")
        self.assertNotIn("video", streams)

    # ─── images ─────────────────────────────────────────────────────────────
    @requires_ffmpeg
    def test_image_conversion_changes_the_format(self) -> None:
        source = self.make_image()
        output = self.convert(
            source, "image",
            {"format": "JPG", "quality": 85, "resolution": None, "extension": ".jpg"},
        )
        self.assertEqual(self.stream_types(output).get("video"), "mjpeg")

    @requires_ffmpeg
    def test_frame_export_seeks_and_writes_one_image(self) -> None:
        source = self.make_video(duration=3)
        output = self.convert(
            source, "image",
            {"format": "PNG", "quality": 92, "resolution": None, "extension": ".png"},
            trim_start=2.0,
        )
        self.assertEqual(self.stream_types(output).get("video"), "png")

    # ─── hardware fallback ──────────────────────────────────────────────────
    @requires_ffmpeg
    def test_the_cpu_fallback_command_converts_a_real_file(self) -> None:
        """The rewritten command must be valid FFmpeg, options and all."""
        source = self.make_video()
        output = os.path.join(self.dir, "fallback.mp4")
        gpu_cmd = [
            self.handler.ffmpeg_path, "-i", source, "-c:v", "h264_nvenc",
            "-cq", "30", "-c:a", "aac", "-b:a", "128k", "-y", output,
        ]
        fallback = self.handler.build_software_fallback(gpu_cmd)
        self.assertIsNotNone(fallback)
        assert fallback is not None
        self.assertIn("libx264", fallback)
        self.assertIn("-crf", fallback)
        # Everything must still precede the output path, or FFmpeg ignores it.
        self.assertEqual(fallback[-1], output)
        self.run_ffmpeg(fallback)
        self.assertEqual(self.stream_types(output)["video"], "h264")


if __name__ == "__main__":
    unittest.main()
