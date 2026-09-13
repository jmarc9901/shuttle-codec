# Architecture

How Shuttle Codec is put together, why the modules are split the way they are,
and where to add things. Written for contributors; the user-facing docs live in
[USER_GUIDE.md](USER_GUIDE.md).

## Layers

```
        ┌──────────────────────────────────────────┐
        │ src/main.py                              │  bootstrap (HiDPI, QApplication)
        ├──────────────────────────────────────────┤
        │ src/app.py       MainWindow              │  UI + orchestration
        │ src/theme.py     palette + stylesheet    │
        │ src/i18n.py      ES/EN strings           │
        │ src/presets.py   use-case presets        │
        ├──────────────────────────────────────────┤
        │ src/workers.py   ConversionThread        │  QThread + batch manager
        │                  BatchConversionManager  │
        ├──────────────────────────────────────────┤
        │ src/ffmpeg_handler.py   FFmpegHandler    │  command building + execution
        │ src/ffmpeg_downloader.py  binary lookup  │
        ├──────────────────────────────────────────┤
        │ src/utils.py                             │  helpers with no Qt/FFmpeg state
        │ src/diagnostics.py   bug-report text     │
        └──────────────────────────────────────────┘
```

The rule of thumb: **no FFmpeg knowledge in the UI and no Qt in the FFmpeg
layer.** `FFmpegHandler` never imports PyQt5; `diagnostics.py` and `presets.py`
are pure data/functions. That is what makes the whole command surface testable
without a display.

## Threading model

- The GUI thread never blocks on a conversion: `MainWindow._run_conversion_thread`
  builds the command, then hands it to `ConversionThread` (a `QThread`).
- `ConversionThread.run()` calls `FFmpegHandler.start_conversion()`, which spawns
  FFmpeg with `stderr=PIPE` and drains it on a **daemon reader thread**. FFmpeg's
  progress uses carriage returns; reading it line by line on a separate thread is
  what keeps the UI responsive and prevents the pipe from filling up and
  deadlocking the encoder.
- Results come back as Qt signals (`progress`, `eta_update`, `log`,
  `conversion_done`). The custom completion signal is named `conversion_done` on
  purpose: overriding `QThread.finished` is a classic PyQt footgun.
- `BatchConversionManager` runs the queue sequentially, one `ConversionThread` per
  item. `cancel()` cancels the in-flight FFmpeg process, drains the queue and
  resets the index; the late `conversion_done` of the cancelled item is handled
  without reporting a completed batch.
- Closing the window during a conversion asks for confirmation, cancels, and
  joins the worker (`wait()`) before the process exits.

## Anatomy of a conversion

1. **Load.** `MainWindow.load_file()` probes the input once
   (`FFmpegHandler.get_media_info`) and derives everything else — codecs,
   resolution, duration, size — from that single ffprobe result. The result is
   cached by `(path, mtime, size)`, so re-probing the same file is free. The
   window then decides the mode: `video`, `audio` (no video stream), `image`
   (still image) or `extract_audio` (explicit toggle).
2. **Settings.** `_get_settings_from_ui()` returns `(mode, settings)`. In simple
   mode the settings come from the selected preset instead of the expert widgets.
   The returned dict is the only contract between the UI and the handler.
3. **Command.** `FFmpegHandler.build_convert_command()` turns `(input, output,
   mode, settings, trim)` into an argument list. Each mode has one code path;
   shared pieces (hardware encoder choice, target bitrate, image quality) are
   helpers. For a single frame the seek (`-ss`) goes **before** `-i`, which is
   orders of magnitude faster on long files; for a trim it goes after, where it is
   accurate.
4. **Execution.** `start_conversion()` parses `time=` and `Duration:` from FFmpeg's
   stderr to drive the progress bar and the ETA, and returns the process exit
   code. Progress is only forced to 100 % on a real success.
5. **Retry.** When the command uses a GPU encoder, the UI also builds a CPU
   equivalent (`build_software_fallback`, created before the job starts). If the
   hardware encoder fails at runtime, the worker deletes the partial output and
   reruns the fallback — unless the user cancelled.

## Invariants worth preserving

- **Every option precedes the output path.** FFmpeg silently ignores trailing
  options, so the software fallback rewrites the command *in place* and the
  integration tests assert the output path is the last argument.
- **Stream-copy only what the container really supports.** `COPY_SAFE_AUDIO_CODECS`
  lists the codecs each container accepts for `-c:a copy`; ffmpeg will happily mux
  Vorbis into MP4, but many players and hardware decoders reject the result, so
  anything else is re-encoded. An unknown source codec is never copied.
- **WebM always re-encodes audio** (`CONTAINER_AUDIO_CODEC`): AAC/MP3 in WebM
  fails to mux at all.
- **The hardware encoder is chosen from the format's software codec**, so
  "MP4 (H.265)" can never end up on `h264_*`.
- **Video quality knobs are mutually exclusive**: target size (rate control)
  replaces CRF, and the UI disables the CRF slider to make that visible.
- **The settings a job is built from are never persisted mid-build.** The batch
  queue is only saved when it actually changes, otherwise a refresh during
  startup would erase the queue restored from the previous session.

## Extension points

| Task | Where |
|------|-------|
| Add an output container | `FFmpegHandler.VIDEO_FORMATS`, plus a `COPY_SAFE_AUDIO_CODECS` entry (a consistency test enforces this) |
| Add an audio format | `FFmpegHandler.AUDIO_FORMATS` |
| Add an image format | `FFmpegHandler.IMAGE_FORMATS` (`quality` says how the 1-100 slider maps) |
| Add a use-case preset | `src/presets.py` (`PRESETS` + `PRESET_ORDER`) and its two translation keys |
| Add any user-visible string | `src/i18n.py`, both languages; a consistency test fails if a key is missing in one of them or uses different `{}` placeholders |
| Change a color | `src/theme.py` (single source of truth for the stylesheet and inline labels) |

## Testing strategy

| Suite | What it covers |
|-------|----------------|
| `test_ffmpeg_handler.py` | Command construction: formats, hardware, trim, audio, images, target size, fallback rewriting |
| `test_ffmpeg_integration.py` | **Real** FFmpeg runs on 2-second synthetic clips; skips when FFmpeg or an encoder is missing |
| `test_app_smoke.py` | Headless UI (`QT_QPA_PLATFORM=offscreen`): wiring, modes, dialogs, persistence, accessibility, log |
| `test_workers.py` | Batch manager, cancellation, CPU fallback |
| `test_project_consistency.py` | Version vs CHANGELOG/README, translation parity, markdown links, documented formats |
| `test_utils.py`, `test_presets.py`, `test_theme.py`, `test_i18n.py`, `test_diagnostics.py`, `test_download_ffmpeg.py` | Helpers, presets, palette, translations, report assembly, archive safety |

Unit tests mock `subprocess`, so they cannot catch a command FFmpeg rejects —
that is what the integration suite is for. Anything touching file paths or
settings isolation must work on Windows too (see the `QSettings` note in
`test_app_smoke.py`: the two-argument constructor uses `NativeFormat`, i.e. the
registry, so tests build an explicit `IniFormat`).
