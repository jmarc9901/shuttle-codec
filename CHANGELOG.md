# Changelog

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
