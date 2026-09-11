# Changelog

## v1.2.0 (2026-09-11)

### Fixed
- **WebM output**: audio is now re-encoded to Opus (WebM rejects AAC) and
  stream-copy is skipped, fixing `Could not write header (incorrect codec
  parameters)` on every WebM conversion with audio.
- **HEVC hardware acceleration**: `_get_hw_encoder()` is driven by the format's
  software codec, so MP4 (H.265) selects `hevc_nvenc`/`hevc_amf`/`hevc_qsv`
  instead of `h264_*`.
- **VP9 constant quality**: added the required `-b:v 0` and mapped the UI
  preset to libvpx `-deadline`/`-cpu-used` (libvpx has no `-preset`).
- **GIF filter**: no longer emits the invalid `scale=-1:-1` at original resolution.
- **HEVC in MP4/MOV**: tagged `hvc1` for Apple/QuickTime compatibility.
- **Batch worker**: renamed the `thread` attribute, which shadowed `QObject.thread()`,
  and closing the window during a batch now cancels and joins the worker
  instead of leaving it running.
- **Performance**: loading a file probes it with ffprobe once instead of once
  per helper (`get_media_info`/`get_codecs`/`get_resolution`/`get_file_summary`).
- **i18n**: the FFmpeg status badge and hardware label re-render correctly after
  a language change; the hardware label is backend-agnostic (NVENC/AMF/QSV).

### Security
- Safe tar/zip extraction in `download_ffmpeg.py` (CVE-2007-4559 path traversal)
  plus `filter="data"` on Python 3.12+.

### Changed
- **Python baseline raised to 3.10+** (3.9 reached end of life): `requires-python`,
  ruff target, mypy target and the CI matrix now cover 3.10-3.13.
- Modern PEP 604 type unions (`X | None`) across the codebase.
- Packaging metadata: SPDX license expression, project URLs and a proper
  setuptools package declaration.

### Testing
- 110 unit tests (up from 37), including regression tests for the WebM/Opus,
  HEVC hardware, VP9, GIF filter and archive-extraction fixes, plus a headless
  UI smoke test that skips itself when Qt cannot start.
- The **Start conversion** button now stays disabled until a file is loaded or
  the batch queue has items.
- CI now lints the whole tree with `ruff check .` and type-checks with `mypy src/`.

---

## v1.1.0 (2026-07-10)

### Added
- 🌐 **Live i18n**: UI texts update instantly when changing language without restart
- 🔒 **Security**: SSL verification for FFmpeg download, path validation, media file validation
- 🎯 **Type hints**: Full type annotations across all modules
- 🧪 **Test suite**: 37 unit tests (handler, downloader, i18n)
- 🤝 **Community files**: SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md
- 🏷️ **GitHub templates**: Issue templates (bug report, feature request) and PR template
- ⚙️ **CI pipeline**: GitHub Actions with ruff linting + pytest (Python 3.9-3.12)
- 📸 **Screenshots**: Visual preview in README
- 🌍 **Bilingual README**: English primary + Spanish (README.es.md)

### Changed
- License conflict marker removed from LICENSE
- Version bumped from 1.0.0 to 1.1.0
- README completely rewritten in English with bilingual toggle

---

## v1.0.0 (2026-06-14)

### Added
- Initial release
- Video conversion (MP4 H.264/H.265, MKV, AVI, MOV, WebM, GIF)
- Audio conversion (MP3, AAC, WAV, FLAC, OGG, M4A, WMA)
- Batch processing
- GIF conversion with palette optimization
- Video trimming
- Hardware acceleration (NVENC, AMF, QSV)
- Catppuccin Mocha dark theme
- Drag & drop support
- Keyboard shortcuts
- Responsive UI
