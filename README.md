# Shuttle Codec

**A modern, elegant, and powerful GUI for FFmpeg** — Convert videos without writing a single command.

<p align="center">
  <img src="logo.png" alt="Shuttle Codec Logo" width="128"/>
</p>

<p align="center">
  <a href="https://github.com/jmarc9901/shuttle-codec/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/jmarc9901/shuttle-codec/ci.yml?branch=main&label=CI" alt="CI">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec">
    <img src="https://img.shields.io/github/stars/jmarc9901/shuttle-codec?style=flat&label=Stars" alt="Stars">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec/releases">
    <img src="https://img.shields.io/github/v/release/jmarc9901/shuttle-codec" alt="Release">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec/blob/main/CONTRIBUTING.md">
    <img src="https://img.shields.io/badge/contributions-welcome-brightgreen" alt="Contributions">
  </a>
  <a href="https://github.com/jmarc9901/shuttle-codec/actions/workflows/codeql.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/jmarc9901/shuttle-codec/codeql.yml?branch=main&label=CodeQL" alt="CodeQL">
  </a>
</p>

<p align="center">
  <a href="README.es.md">🇪🇸 Español</a>
</p>

> Drag & drop any video, audio or image file to convert. Batch processing, NVENC/AMF/QSV hardware acceleration (with automatic CPU fallback), video trimming, GIF conversion, image and single-frame export, target-size compression, audio extraction and expert mode. Catppuccin Mocha dark theme. Responsive interface adapts to any screen size.

---

## Screenshots

<p align="center">
  <img src="docs/demo.gif" alt="Shuttle Codec demo" width="800"/>
  <br/>
  <em>Simple mode → Presets → Expert mode → Language switch</em>
</p>

---

## Features

### User-Friendly
- **Simple/Expert Mode**: Simple mode by default (format only), toggle for advanced options
- **Drag & Drop**: Supports multiple files at once
- **Keyboard Shortcuts**: Ctrl+O (open), Ctrl+E (convert), Ctrl+Q (quit), Delete (remove)
- **Auto-detection**: Analyzes codec and resolution on file load, suggests optimal settings
- **Info Panel**: Codecs, resolution, size, and duration always visible
- **Responsive**: Adapts to any window size with automatic scrolling
- **🌐 Internationalization**: Spanish and English UI, switchable from the header

### Powerful
- **Video Conversion**: MP4 (H.264/H.265), MKV, AVI, MOV, WebM, **GIF**
- **Audio Conversion**: MP3, AAC, WAV, FLAC, OGG, M4A, WMA (audio-only inputs)
- **Extract Audio**: Pull the audio track out of any video (MP3, AAC, FLAC, …)
- **Image Conversion**: PNG, JPG, WebP, BMP, TIFF with quality and Lanczos resizing
- **Frame Export**: Save a single frame of a video as an image at any timestamp
- **Target Size**: "Compress this to 25 MB" — the bitrate is computed for you
- **Batch Processing**: Convert multiple files with the same settings; the queue survives restarts
- **GIF Conversion**: Optimized GIFs with palette optimization (palettegen + paletteuse)
- **Video Trimming**: Select start and end points to cut specific segments
- **Hardware Acceleration**: Auto-detects NVENC (NVIDIA), AMF (AMD), or QSV (Intel), and **retries on the CPU automatically** if the GPU encoder fails at runtime
- **Shut Down When Done**: Unattended batch jobs, with a cancellable 60-second countdown
- **Fine Control**: CRF, encoding preset, resolution, FPS, audio codec, and more

### Informative
- **ETA & Speed**: Estimated time remaining and speed during conversion
- **File Info**: Codecs, resolution, bitrate, duration on load
- **Size Estimate**: Live `≈ MB` forecast that follows your settings
- **Persistence**: Remembers window size/position, language, last settings and the batch queue
- **Detailed Log**: Complete record of all operations, including the exact FFmpeg command
- **One-Click Bug Report**: 🐞 button opens a GitHub issue pre-filled with diagnostics

---

## Quick Start

### Option 1: Download (Recommended)
1. Go to the [latest release](https://github.com/jmarc9901/shuttle-codec/releases/latest)
2. Download the installer (`shuttle-codec-<version>-setup.exe`) or the portable
   `shuttle-codec.exe`
3. Run it — FFmpeg is already included

Every release publishes `SHA256SUMS.txt` so you can verify the download.

### Option 2: Run from Source

```bash
# Clone
git clone https://github.com/jmarc9901/shuttle-codec.git
cd shuttle-codec

# Install dependencies
pip install -r requirements.txt

# Download FFmpeg (first time only)
python download_ffmpeg.py

# Run
python -m src.main
```

### Build Executable

```bash
python download_ffmpeg.py
pip install -e ".[build]"   # pyinstaller + pillow
python build.py
```

The executable will be at `dist/shuttle-codec.exe`.

A Windows installer can be built with [Inno Setup](https://jrsoftware.org/isinfo.php):

```bash
iscc installer/shuttle-codec.iss /DMyAppVersion=1.3.0
```

---

## Documentation

| Document | Contents |
|----------|----------|
| [User guide](docs/USER_GUIDE.md) ([es](docs/USER_GUIDE.es.md)) | Every feature, step by step |
| [Troubleshooting & FAQ](docs/TROUBLESHOOTING.md) ([es](docs/TROUBLESHOOTING.es.md)) | Common problems, supported formats, privacy |
| [Architecture](docs/ARCHITECTURE.md) | Module map, threading model, invariants, how to extend |
| [Releasing](docs/RELEASING.md) | Release process, code signing, FFmpeg pinning |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | Bundled FFmpeg/Qt licenses and what a release must ship |
| [CHANGELOG](CHANGELOG.md) | Version history |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| GUI | PyQt5 |
| Video Engine | FFmpeg (bundled) |
| Packaging | PyInstaller |
| Theme | Catppuccin Mocha |
| Testing | pytest, unittest.mock + real FFmpeg integration runs |

---

## What's new in v1.3.0

### ✨ Added
- **Image conversion**: PNG, JPG, WebP, BMP and TIFF output with a quality
  slider and Lanczos resizing — the file filter no longer promises images the
  app could not handle.
- **Frame export**: save a single frame of a video as an image at any timestamp
  (seeks before `-i`, so it is instant even in long files).
- **Target size**: ask for a size in MB and the video bitrate is computed for
  you (single-pass rate control); the output-size estimate updates live.
- **Extract audio only**: keep just the audio track of a video, in any supported
  audio format.
- **Automatic CPU fallback**: if a GPU encoder fails at runtime (old driver, GPU
  busy, session limit) the job is retried in software instead of failing.
- **Batch queue persistence** and **shut down when finished** with a cancellable
  60-second countdown.
- **One-click bug report**: pre-filled GitHub issue with version, OS, Python/Qt/
  FFmpeg versions and the log tail (nothing is ever sent automatically).
- **Predicted output size** (`📏 ≈ MB`) in the info panel.

### 🐛 Fixed
- **Unreadable completion dialog**: the message box after a conversion rendered
  light text on a light background. Dialogs, tooltips and menus now follow the
  dark theme through both the stylesheet and an application-wide dark palette.
- **AMF quality was ignored**: `h264_amf`/`hevc_amf` encoding now applies the
  CRF slider via `-rc cqp -qp_i/-qp_p` instead of only `-quality balanced`.
- The CPU fallback command is rewritten in place, so no option ends up after the
  output path (where FFmpeg warns and ignores it).

### 🚀 Distribution & quality
- **Windows installer** (Inno Setup, `installer/shuttle-codec.iss`),
  **macOS zip** and a best-effort **Linux AppImage** in the release workflow.
- **SHA-256 checksums** published with every release, plus optional signing and
  notarization hooks (see [RELEASING.md](docs/RELEASING.md)).
- **FFmpeg pinning**: `FFMPEG_BUILD_TAG` + `FFMPEG_ARCHIVE_SHA256` make the
  bundled binaries reproducible and tamper-evident; the script refuses to
  extract a mismatching archive.
- **Version single source of truth** (`src/__init__.py`), HiDPI scaling flags,
  and a CI job that builds the executable on Windows.
- **262 tests** with an enforced coverage floor (80%, currently ~83%): `ruff`
  clean on the whole tree (security rules included), `mypy --strict` clean on
  `src/`, CodeQL scanning, a weekly `pip-audit` run and Dependabot updates.
- **Real FFmpeg integration tests**: the suite runs a dozen actual conversions on
  synthetic clips and skips them when no usable binary is present.
- **Build provenance**: releases are attested with SLSA provenance, ship
  `SHA256SUMS.txt` and a `pip-freeze.txt` manifest, and set `SOURCE_DATE_EPOCH`
  so the same commit builds reproducibly.
- **Accessibility**: every control exposes an accessible name, the log is
  timestamped and state is never signalled by colour alone.

### 📚 Documentation
- Full user guide, troubleshooting/FAQ, architecture and release docs in English
  and Spanish, plus [third-party notice obligations](THIRD_PARTY_NOTICES.md).

> Older releases: see [CHANGELOG.md](CHANGELOG.md).

---

## Development

```bash
pip install -e ".[dev]"

python -m pytest tests/ -v                          # 262 tests
python -m pytest tests/ --cov=src --cov-report=term # coverage (floor: 80%)
ruff check .                                        # lint (security rules included)
mypy src/                                           # strict type check
```

Install the hooks to run the same checks before every commit:

```bash
pip install pre-commit && pre-commit install
```

`tests/test_ffmpeg_integration.py` runs real conversions on synthetic clips and
skips itself when FFmpeg is unavailable, so the suite stays green everywhere.

---

## Project Structure

```
shuttle-codec/
├── src/
│   ├── __init__.py
│   ├── main.py               # Entry point
│   ├── app.py                # Main window (PyQt5) + orchestration
│   ├── workers.py            # QThread conversion worker + batch manager
│   ├── ffmpeg_handler.py     # FFmpeg/FFprobe command building & execution
│   ├── ffmpeg_downloader.py  # Bundled vs system binary discovery
│   ├── presets.py            # Use-case presets + resolution map
│   ├── theme.py              # Catppuccin Mocha palette & stylesheet
│   ├── utils.py              # Icon path, time/size formatting helpers
│   ├── diagnostics.py        # Bug-report text and pre-filled issue URL
│   └── i18n.py               # ES/EN translations
├── tests/
│   ├── test_app_smoke.py        # headless UI wiring (skipped without Qt)
│   ├── test_ffmpeg_handler.py   # commands, formats, hardware, trim, audio, images
│   ├── test_ffmpeg_integration.py # real FFmpeg runs (skipped without FFmpeg)
│   ├── test_project_consistency.py # version, translations, docs links
│   ├── test_ffmpeg_downloader.py
│   ├── test_download_ffmpeg.py  # archive extraction safety & integrity
│   ├── test_diagnostics.py      # report assembly
│   ├── test_workers.py          # batch manager & CPU fallback
│   ├── test_presets.py
│   ├── test_theme.py
│   ├── test_utils.py
│   └── test_i18n.py
├── installer/               # Inno Setup script (Windows installer)
├── docs/                    # User guide, FAQ, architecture, release notes, demo.gif
├── resources/bin/           # Bundled FFmpeg binaries
├── download_ffmpeg.py       # FFmpeg downloader (with optional hash pinning)
├── build.py                 # PyInstaller builder
├── pyproject.toml
└── requirements.txt
```

---

## License

Apache 2.0 — With attribution and patent protection.

---

<p align="center">
  <b>Shuttle Codec</b> — Made by <a href="https://github.com/jmarc9901">@jmarc9901</a>
</p>
