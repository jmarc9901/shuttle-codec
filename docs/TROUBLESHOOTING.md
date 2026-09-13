# Troubleshooting & FAQ

🌐 **Español:** [TROUBLESHOOTING.es.md](TROUBLESHOOTING.es.md)

Before anything else: the **Log** panel at the bottom of the window contains the
exact FFmpeg command and its output. When reporting a problem, press **🐞 Report**
so that information is attached automatically.

---

## The app does not start (Windows)

- **"Windows protected your PC"** — SmartScreen on unsigned builds. Click *More
  info* → *Run anyway*, or use the installer signed by the project.
- **Nothing happens when I double-click** — try running it from a terminal
  (`.\shuttle-codec.exe`) to see the error. Antivirus software sometimes
  quarantines freshly built PyInstaller executables; allow it and try again.
- **The window opens but looks tiny/blurry** — the app enables Qt's HiDPI
  scaling. On multi-monitor setups with different scale factors, log out and back
  in so Windows applies the per-monitor scaling.

## macOS: "shuttle-codec is damaged and can't be opened"

Gatekeeper blocks unsigned/quarantined binaries. Either build from source, or
remove the quarantine attribute:

```bash
xattr -dr com.apple.quarantine ./shuttle-codec
```

## Linux: the AppImage does not run

```bash
chmod +x shuttle-codec-x86_64.AppImage
./shuttle-codec-x86_64.AppImage
```

If FUSE is unavailable (common in containers), run it with
`--appimage-extract-and-run`.

## "FFmpeg: ✗" in the header

Shuttle Codec looks for the binaries in this order:

1. `resources/bin/` next to the application (bundled builds ship them there).
2. Your system `PATH`.

If neither has them, install FFmpeg (`winget install Gyan.FFmpeg`,
`brew install ffmpeg`, `sudo apt install ffmpeg`) or run
`python download_ffmpeg.py` in a source checkout.

## Hardware acceleration fails or is greyed out

- The checkbox only appears when FFmpeg reports a usable encoder
  (NVENC/AMF/QSV) — the header shows which one was detected.
- If encoding fails anyway, Shuttle Codec **retries on the CPU automatically**
  and writes a warning in the log. This is the most common cause of "my video
  conversion always failed" reports and it is handled for you.
- To force the CPU, simply leave the checkbox off.

## The output file is bigger/smaller than the estimate

The `📏 ≈` estimate is a rule of thumb calibrated on H.264 CRF 23 at 30 fps.
Content complexity dominates the real result: a static screen encodes far below
the estimate and high-motion footage above it. For a hard limit, use **Target
size** — that mode computes the bitrate from the size you asked for.

## Target size does not change anything

The mode needs a duration to derive the bitrate. If FFprobe cannot read it (rare
containers, images, corrupted headers), the conversion falls back to CRF and the
log says so. Remuxing the file first (`ffmpeg -i broken.mkv -c copy fixed.mp4`)
usually fixes the metadata.

## "A conversion is in progress. Cancel and exit?" on close

Shuttle Codec asks before killing a running job. *Yes* cancels the FFmpeg
process; the partial output file is deleted before a retry, but a cancelled
conversion leaves whatever FFmpeg had written so far — delete it if you don't
want it.

## Where are my settings stored? How do I reset them?

Qt's settings store for the application:

- Windows: registry key `HKCU\Software\ShuttleCodec`
- macOS: `~/Library/Preferences/com.ShuttleCodec.ShuttleCodec.plist`
- Linux: `~/.config/ShuttleCodec.conf`

Delete that entry/file to get a clean first-run state.

## Batch queue is empty after restarting

The queue is restored from the previous session, but files that no longer exist
(renamed, moved, external drive disconnected) are skipped silently. It also
becomes a plain list of paths — handy for scripts: convert them from the command
line with FFmpeg if the GUI is not what you need.

## Can I use it from the command line?

Shuttle Codec is a GUI, but the FFmpeg command it builds is printed in the log,
so you can copy it into a script. Install the package (`pip install -e .`) and
run `shuttle-codec` to launch it from anywhere.

## Does it upload my files or collect telemetry?

No. The application makes no network requests: the only network access happens at
build time, when FFmpeg is downloaded. The version, OS and log data are only sent
if you press **Report** and submit the GitHub issue yourself.

## Supported formats

- **Video out**: MP4 (H.264, H.265), MKV, AVI, MOV, WebM (VP9), GIF
- **Audio out**: MP3, AAC, WAV, FLAC, OGG (Vorbis), M4A, WMA
- **Image out**: PNG, JPG, WebP, BMP, TIFF (plus single-frame export from video)
- **Input**: anything FFmpeg can decode (hundreds of containers and codecs)

## "Invalid or unsupported file" for a file that is fine

Shuttle Codec accepts files up to **10 GB** that FFmpeg can decode. Empty files,
files whose extension is not a media one and inputs above that limit are refused
before the conversion starts. For larger inputs, copy the command from the Log
panel and run it with FFmpeg directly.

## The conversion is very slow

- Enable hardware acceleration if the checkbox is available.
- Use a faster encoder preset (`ultrafast`/`veryfast`) instead of `slow`.
- Avoid H.265 for large files unless you need the smaller size — it is
  significantly slower than H.264 on the CPU.
- VP9 in WebM is CPU-only and slow by design.
