# Shuttle Codec — User Guide

🌐 **Español:** [USER_GUIDE.es.md](USER_GUIDE.es.md)

Shuttle Codec converts video, audio and images using FFmpeg, without typing a
single command. FFmpeg is bundled inside the application, so there is nothing
else to install.

---

## 1. Installing

| Platform | How |
|----------|-----|
| Windows | Download `shuttle-codec-<version>-setup.exe` from the [releases page](https://github.com/jmarc9901/shuttle-codec/releases) and run it, or use the portable `shuttle-codec.exe` |
| macOS | Download `shuttle-codec-macos.zip`, unzip it and drag the binary wherever you like |
| Linux | Download `shuttle-codec-x86_64.AppImage`, `chmod +x` it and run it |

> The first launch of an unsigned build can be flagged by SmartScreen
> ("Windows protected your PC" → *More info* → *Run anyway*) or by Gatekeeper.
> That warning disappears once the release is code-signed; see
> [RELEASING.md](RELEASING.md).

## 2. The interface

```
┌───────────────────────────────────────────────────────────────────────┐
│ Shuttle Codec · author            🐞 Report   [language]   FFmpeg: ✓  │  header
├───────────────────────────────────────────────────────────────────────┤
│ [ file path ......................... ]  📁 Browse  ✕                 │  file bar
│ 📄 clip.mp4   📦 42.1 MB   🎬 H264 1920x1080   🎵 AAC   ⏱ 01:23  📏 ≈ 32 MB │  info panel
├───────────────────────────────────────────────────────────────────────┤
│ ⚙ Show advanced options                                               │  mode toggle
│ ⚡ Quick convert → [ YouTube (1080p H.264) ▾ ]                        │  presets (simple mode)
├───────────────────────────────────────────────────────────────────────┤
│ 🎬 Video            │  📦 Batch list                                │
│ 🎵 Audio            │  ...                                          │
│ 🖼 Image            │                                               │  expert mode
│ ✂ Trim              │                                               │
├───────────────────────────────────────────────────────────────────────┤
│ Progress: ⏱ Remaining 00:12  ⚡ 3.4x                                   │
│ ▶ Start conversion        ✕ Cancel                                    │
├───────────────────────────────────────────────────────────────────────┤
│ Log                                                                   │
└───────────────────────────────────────────────────────────────────────┘
```

### Simple mode (default)

Pick a **preset** and press **Start conversion**. Presets are tuned per
destination: YouTube 1080p/4K, WhatsApp, Telegram, Discord, Twitter GIF, high
quality and small size.

### Expert mode

Click **⚙ Show advanced options** to get full control:

- **🎬 Video** — output format (MP4 H.264/H.265, MKV, AVI, MOV, WebM VP9, GIF),
  encoder preset, quality (CRF), resolution, FPS, keep the original audio,
  hardware acceleration, **target size** and **extract audio only**.
- **🎵 Audio** — audio-only inputs (MP3, AAC, WAV, FLAC, OGG, M4A, WMA) plus the
  format used by *Extract audio only*.
- **🖼 Image** — output format (PNG, JPG, WebP, BMP, TIFF), quality, resolution,
  and **export a single frame** from a video.
- **✂ Trim** — cut a segment by start/end time.
- **📦 Batch list** — queue many files and convert them one after another.

## 3. Everyday workflows

### Drag & drop

Drop one or more files anywhere in the window. A single file is loaded for
editing; multiple files are queued in the batch list automatically.

### Compress to a size limit (e.g. Discord's 25 MB)

1. Open the file and switch to expert mode.
2. Tick **Target size** and type `25` MB.
3. Check the estimate in the info panel (it shows `≈ 25 MB`).
4. Convert.

The CRF slider is disabled in this mode: Shuttle Codec computes the bitrate
needed to land near that size. If a file has no readable duration, it falls back
to constant quality automatically.

### Export a frame (thumbnail / screenshot)

1. Load the video and switch to expert mode.
2. In **🖼 Image**, tick **Export a single frame** and choose the timestamp.
3. Pick PNG (lossless) or JPG/WebP (smaller) and convert.

### Convert images

Loading a `.png`, `.jpg`, `.webp`, `.bmp` or `.tiff` switches the window to
image mode: choose the output format, quality and resolution (Lanczos
downscaling) and convert. Batch conversion of images works the same way.

### Extract the audio of a video

Tick **Extract audio only** in the Video group, choose MP3/AAC/FLAC/… in the
Audio group and convert. The video stream is dropped (`-vn`).

### Convert a whole folder

Add files to the **Batch list** with ➕, remove the ones you don't want with ➖
(or the `Delete` key), then press **Start conversion**. Every item uses the
current settings, and the queue is remembered for the next session (files that
no longer exist are skipped).

Tick **Shut down when finished** to power the machine off after a long batch.
A 60-second countdown is shown and you can cancel it.

## 4. Hardware acceleration

If NVENC (NVIDIA), AMF (AMD) or QSV (Intel) is available, the checkbox appears in
the Video group. Enable it for much faster encoding.

**If the GPU encoder fails for any reason** (outdated driver, GPU busy, too many
concurrent sessions), Shuttle Codec retries the same job on the CPU instead of
failing and says so in the log. You never lose a conversion because of a driver.

## 5. Knowing what you will get

The info panel always shows the input (codec, resolution, size, duration) and an
estimated output size (`📏 ≈ 32 MB`). The estimate is a rule of thumb calibrated
on H.264 CRF 23 and shows `—` when it cannot be computed (GIF, unknown duration,
"auto" audio bitrate).

During a conversion you get a progress bar, the remaining time and the encoding
speed. The **Log** panel keeps the full record, including the exact FFmpeg
command that was run.

## 6. Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Browse for a file |
| `Ctrl+E` | Start the conversion |
| `Ctrl+Q` | Quit |
| `Delete` | Remove the selected batch items |

## 7. Language and settings

Use the language selector in the header to switch between **Español** and
**English**; the change is instant and is remembered.

Shuttle Codec remembers the window size and position, the mode, the last
settings and the batch queue. That data lives in the Qt settings store for the
application (`HKCU\Software\ShuttleCodec` on Windows, the Qt configuration file
for `ShuttleCodec` on macOS/Linux).

## 8. Reporting a problem

Click **🐞 Report** in the header: GitHub opens a new issue pre-filled with your
version, operating system, Python/Qt/FFmpeg versions and the last lines of the
log. Describe what happened and submit it. If the browser cannot be opened, the
same text is copied to the clipboard.

## 9. Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
