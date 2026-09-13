# Third-party notices

Shuttle Codec's own source code is licensed under [Apache-2.0](LICENSE). The
**built artifacts** also contain or depend on the components below, and they
carry their own licenses. If you redistribute a build, read this page first.

> This document is a summary for maintainers, not legal advice. Review it with
> your own counsel before shipping binaries commercially.

## Bundled in the released executables

| Component | Version | License | Where |
|-----------|---------|---------|-------|
| [FFmpeg](https://ffmpeg.org/) | latest `-gpl` build (or the pinned `FFMPEG_BUILD_TAG`) | **GPL v3** (the GPL variants include libx264/libx265) | `resources/bin/`, embedded by `build_exe.py` into the executable |
| [PyQt5](https://riverbankcomputing.com/software/pyqt/) / [Qt 5](https://www.qt.io/) | >= 5.15 | **GPL v3** (or a commercial Riverbank license) | Python runtime dependency, frozen by PyInstaller |
| [Python](https://www.python.org/) | 3.10-3.13 | PSF-2.0 | Interpreter embedded by PyInstaller |
| [PyInstaller](https://pyinstaller.org/) | >= 6.0 | GPL-2.0 **with the bootloader exception** (frozen applications may be licensed freely) | Build tool |

FFmpeg is invoked as a separate process and Qt is linked as a library, but both
are still *conveyed* inside the packaged executable, which is what triggers the
obligations below.

## What this means for a release

The project's source stays Apache-2.0 (which is compatible with GPL v3), but a
**distributed binary is a GPL v3 combined work**. Whoever publishes the release
must therefore:

1. Keep the copyright notices and ship the full license texts for FFmpeg, Qt and
   PyQt5 alongside the artifacts.
2. Provide the corresponding source, or a written offer to provide it. In
   practice: point users at the exact FFmpeg build (pin `FFMPEG_BUILD_TAG` so the
   archive is reproducible and its source is identifiable) and at the PyQt5/Qt
   versions recorded in `dist/pip-freeze.txt`.
3. Not add restrictions on top of the GPL (for example, do not ship the build
   under a proprietary EULA).

If a permissively licensed binary is required instead, build it with an LGPL
FFmpeg variant (`FFMPEG_ARCHIVE_SHA256`/tag pointing at an `-lgpl` build that
excludes x264/x265) and a commercial Qt license.

## Development-only dependencies

Not shipped. They only need to satisfy their own licenses in CI:

| Component | License |
|-----------|---------|
| pytest, pytest-cov | MIT |
| ruff | MIT |
| mypy | MIT |
| Pillow | MIT-CMU (used by PyInstaller to convert the icon) |
| pip-audit | Apache-2.0 |
| build, twine | MIT / Apache-2.0 |
| Inno Setup | Inno Setup License (free for commercial use) |

## Assets

- `logo.png`, `logo.ico`, `screenshot*.png`, `docs/demo.gif` — project assets,
  covered by the repository license and the in-app author credit.
- The Catppuccin Mocha palette values in `src/theme.py` come from the
  [Catppuccin](https://github.com/catppuccin/catppuccin) project (MIT). Colors
  are facts and not copyrightable in most jurisdictions, but the credit is kept
  here out of courtesy.
