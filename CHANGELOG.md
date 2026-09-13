# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed
- **`build.py` is now `build_exe.py`**: a top-level `build` module shadows the
  PyPI package of the same name, so on a checkout `python -m build` imported the
  PyInstaller script instead of running the standard packaging frontend. The
  references in the READMEs, the installer, the docs and both workflows moved
  with it.

### Fixed
- **The headless UI tests crashed the interpreter on Windows**: one test did not
  force FFmpeg to look available, so the app took its "FFmpeg missing" path and
  built a *real* `QMessageBox` — a native modal dialog in an offscreen
  `QApplication` aborts with an access violation. The smoke tests now stub every
  native dialog per test and no longer depend on FFmpeg being installed.
- **CI failed on every run**: the workflows installed `types-PyQt5`, a stub
  package that no longer exists on PyPI (`No matching distribution found`), so
  dependency installation died in all 12 matrix cells before any test ran. PyQt5
  ships its own `.pyi` stubs since 5.15.7, so the package is gone from CI, the
  `dev` extra and the third-party notices.
- **The Linux AppImage was never produced**: `appimagetool` aborts when the icon
  named in the `.desktop` file is not in the AppDir *root* — only the hicolor
  theme copy existed. The AppDir now also carries `shuttle-codec.png`, `.DirIcon`
  and an explicit `AppRun`, and the job warns when it still builds nothing
  instead of failing silently behind `continue-on-error`.

## v1.3.0 (2026-09-12)

### Added
- **Image conversion**: PNG, JPG, WebP, BMP and TIFF output with a 1-100 quality
  slider and Lanczos resizing, for still images as well as batch jobs. The file
  dialog no longer advertises images the app could not handle.
- **Frame export**: save a single frame of a video as an image at any timestamp
  (`-ss` before `-i`, so it is instant even in long files).
- **Target size**: enter a size in MB and the video bitrate is computed from the
  duration and the audio bitrate (single-pass rate control, `-b:v/-maxrate/
  -bufsize`), with `-crf` disabled in that mode. Files without a readable
  duration fall back to constant quality.
- **Extract audio only**: keep just the audio track of a video (`-vn`) in any
  supported audio format.
- **Automatic CPU fallback**: when a hardware encoder fails at runtime (outdated
  driver, GPU busy, session limit) the job is retried with `libx264`/`libx265`,
  the partial output is deleted first and the retry is logged. Retries are
  skipped when the user cancelled.
- **Batch queue persistence**: the queue is stored in the settings and restored
  on the next run, skipping files that no longer exist.
- **Shut down when finished**: optional, cancellable 60-second countdown after a
  batch (Windows, macOS and Linux commands).
- **Output size estimate**: live `≈ MB` forecast in the info panel, from a
  bits-per-pixel model for CRF encoding, the exact target in target-size mode and
  the bitrate in audio mode.
- **One-click bug report**: `src/diagnostics.py` builds the environment summary
  and a pre-filled GitHub issue URL; the 🐞 header button opens it (falling back
  to the clipboard). Nothing is ever sent automatically.
- **Documentation**: user guide, troubleshooting/FAQ and release notes in English
  and Spanish (`docs/`).
- **Distribution**: Inno Setup installer script (`installer/`), macOS zip and a
  best-effort Linux AppImage in the release workflow, `SHA256SUMS.txt` for every
  release and inert-but-ready signing/notarization hooks.
- **FFmpeg pinning**: `FFMPEG_BUILD_TAG` and `FFMPEG_ARCHIVE_SHA256` make the
  bundled binaries reproducible; a mismatching archive is never extracted.
- **Real FFmpeg integration tests** (`tests/test_ffmpeg_integration.py`): a dozen
  actual conversions on synthetic clips (H.264/H.265, WebM+Opus, GIF, trim,
  target size, scaling, images, frame export, CPU fallback), skipped per encoder
  when the local build lacks it. Mocked unit tests cannot catch a command FFmpeg
  itself rejects.
- **Repository consistency tests** (`tests/test_project_consistency.py`): the
  version against the CHANGELOG and both READMEs, ES/EN key parity and `{}`
  placeholder parity, preset labels, copy-safe audio coverage per container and
  every relative markdown link.
- **Accessibility**: `accessibleName`/`accessibleDescription` for every
  interactive control (re-applied on language change), timestamped log lines, and
  the invalid trim range stated in words instead of red text alone.
- **`docs/ARCHITECTURE.md`** and **`THIRD_PARTY_NOTICES.md`**: the module map,
  threading model and invariants, plus the GPL v3 obligations that come with the
  bundled FFmpeg and PyQt5.
- **Project standards**: `.pre-commit-config.yaml`, `CODEOWNERS`, CodeQL code
  scanning, a weekly `pip-audit` audit, and a release pipeline with SLSA build
  provenance, a `pip-freeze.txt` manifest and a reproducible `SOURCE_DATE_EPOCH`.

### Fixed
- **Unreadable completion dialog**: the message box shown after a conversion
  (and every other `QMessageBox`) rendered *light text on a light background*.
  The stylesheet colors `QLabel` with the theme's light text, while the dialog
  kept the platform's light palette because it had no background rule.
  `QDialog`, `QMessageBox` and `QToolTip` are now styled and the application gets
  a dark `QPalette`, so every palette-driven widget stays readable in dark mode.
- **AMF ignored the quality slider**: `h264_amf`/`hevc_amf` encoding now applies
  the CRF value through `-rc cqp -qp_i/-qp_p` instead of only `-quality balanced`.
- **Fallback command layout**: the rewritten CPU command keeps all options before
  the output path, where FFmpeg would otherwise ignore them.
- **Audio copied into an incompatible container**: "keep original audio"
  passed `-c:a copy` for *any* source codec. FFmpeg muxes Vorbis into MP4
  without complaining, but many players and hardware decoders reject that file,
  so the track is now stream-copied only when the target container really
  supports the source codec (`COPY_SAFE_AUDIO_CODECS`); otherwise it is
  re-encoded.
- **Simple mode offered a batch it could not show**: a queue restored from the
  previous session made the convert button read "Convert N file(s)" while the
  batch list was hidden, and pressing it converted a single file instead.
- **Cancelled batch reported completion**: the "batch completed" dialog and the
  shutdown prompt also fired after the user cancelled the batch.
- **Silent target-size fallback**: a file whose duration cannot be read now logs
  the fall back to constant quality instead of doing it silently (the
  troubleshooting guide already promised that log line).
- **Still images** report `—` instead of a fake `00:00:00` duration.
- The hardware-acceleration checkbox is honoured even when the window has not
  been shown yet (`isVisibleTo` instead of `isVisible`).

### Changed
- `__version__` in `src/__init__.py` is the single source of truth;
  `pyproject.toml` reads it dynamically (`dynamic = ["version"]`).
- `BatchItem` is now a `NamedTuple` carrying an optional `fallback_cmd`.
- HiDPI scaling and high-DPI pixmaps are enabled before the application starts.
- CI gained a coverage gate (80% floor) and a Windows job that builds and checks
  the packaged executable.
- `ruff` now also enforces the security rules (`S`, flake8-bandit); the patterns
  that are intentional here (external tools looked up on PATH, fixed https
  downloads) are documented in `pyproject.toml`.
- Dependabot keeps the pip dependencies and the GitHub Actions pinned and
  patched (`.github/dependabot.yml`).
- `mypy` now runs `strict` (plus `warn_unreachable`); the platform branches use
  a `PLATFORM` constant so the reachability check holds on every OS.
- CI uses least-privilege permissions, cancels superseded runs, caches pip and
  splits lint/type checking into its own job with a coverage artifact.

### Testing
- **262 tests** (up from 110) and 83% line coverage, including regression
  tests for the dialog styling, image/frame commands, target-size maths, size
  estimates, the CPU fallback, batch persistence, audio-copy safety and the
  diagnostics report. The headless UI tests now really isolate their
  `QSettings` (the two-argument constructor uses `NativeFormat`, i.e. the
  Windows registry, so an explicit `IniFormat` is required).

---

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
