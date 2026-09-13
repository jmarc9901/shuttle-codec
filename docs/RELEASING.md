# Releasing Shuttle Codec

Everything in this document is about the *distribution* of the application. What
is automated already lives in `.github/workflows/release.yml`; what needs
credentials from the maintainer is marked **manual**.

---

## 1. Cut a release

1. Update `__version__` in `src/__init__.py` (the single source of truth:
   `pyproject.toml` reads it, so the package metadata follows automatically).
2. Add the matching section to `CHANGELOG.md`.
3. Run the local checks (the same ones the hooks and CI run):

   ```bash
   python -m pytest tests/ -q --cov=src   # includes real FFmpeg conversions
   ruff check .                          # lint + security rules
   mypy src/                             # strict (see pyproject.toml)
   ```

   `python download_ffmpeg.py` first if you want the integration tests to run
   instead of skipping themselves.

4. Commit, tag and push:

   ```bash
   git tag v1.3.0
   git push origin main --tags
   ```

The tag triggers the release workflow, which builds on Windows, macOS and Linux
and publishes to GitHub Releases:

| Artifact | Produced by |
|----------|-------------|
| `shuttle-codec.exe` | PyInstaller (portable) |
| `shuttle-codec-<version>-setup.exe` | Inno Setup (`installer/shuttle-codec.iss`) |
| `shuttle-codec-macos.zip` | zip of the macOS binary |
| `shuttle-codec` (Linux) | PyInstaller |
| `shuttle-codec-x86_64.AppImage` | appimagetool, best effort (`continue-on-error`): the step logs a warning if it produced no file and the plain Linux binary stays the supported fallback |
| `SHA256SUMS.txt` | checksum step, uploaded next to the binaries |
| `pip-freeze.txt` | resolved dependency manifest recorded during the build |
| Build provenance | `actions/attest-build-provenance` (SLSA), attached to each binary |

## 2. Verify an artifact

```bash
sha256sum -c SHA256SUMS.txt                    # Linux / macOS
certutil -hashfile shuttle-codec.exe SHA256    # Windows
```

The checksums can themselves be tampered with, which is what the provenance
attestation is for: it is signed by the workflow identity and can be verified
independently of the release page.

```bash
gh attestation verify shuttle-codec.exe --repo jmarc9901/shuttle-codec
```

## 2b. Before you publish: license obligations (**manual, required**)

The binaries bundle GPL v3 software (the `-gpl` FFmpeg build and PyQt5/Qt). The
project's own code stays Apache-2.0, but publishing a *binary* means complying
with the GPL for the combined work: ship the license texts, keep the notices and
make the corresponding source identifiable.

See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for the exact list and
what each artifact must include. Pinning `FFMPEG_BUILD_TAG` also makes the
FFmpeg source reproducible and therefore identifiable.

## 3. Pin the bundled FFmpeg (**manual, recommended**)

`download_ffmpeg.py` downloads BtbN's `latest` build by default, and prints the
archive SHA-256. To make builds reproducible and tamper-evident, set two
repository variables (Settings → Secrets and variables → Actions → Variables):

| Variable | Example |
|----------|---------|
| `FFMPEG_BUILD_TAG` | `autobuild-2026-05-01-12-00` (any tag from [BtbN/FFmpeg-Builds releases](https://github.com/BtbN/FFmpeg-Builds/releases)) |
| `FFMPEG_ARCHIVE_SHA256` | the hash printed by `python download_ffmpeg.py` |

The workflow passes both to the downloader; when the digest does not match, the
script refuses to extract the archive and the build fails. Locally:

```bash
FFMPEG_BUILD_TAG=autobuild-2026-05-01-12-00 \
FFMPEG_ARCHIVE_SHA256=<sha256> \
python download_ffmpeg.py
```

## 4. Code signing (**manual, requires a certificate**)

Without this, Windows shows "Unknown publisher" and SmartScreen, and macOS
Gatekeeper blocks the app. There is no way around buying/providing these
credentials; the workflow steps are already written and stay inert until the
secrets exist.

### Windows (Authenticode)

1. Buy an OV/EV code-signing certificate (DigiCert, Sectigo, SSL.com, …) or an
   Azure Trusted Signing subscription.
2. Export it as `.pfx` and base64-encode it:

   ```bash
   base64 -w0 cert.pfx > cert.b64      # macOS: base64 -i cert.pfx
   ```

3. Add repository secrets:
   - `WIN_CERT_PFX` — the base64 contents
   - `WIN_CERT_PASSWORD` — the `.pfx` password

The workflow step *Sign the Windows executable* signs `dist\shuttle-codec.exe`
before the installer is built (with `signtool` and an RFC 3161 timestamp).

### macOS (Developer ID + notarization)

Requires a paid Apple Developer account, a *Developer ID Application*
certificate exported as `.p12`, and an app-specific password. After signing:

```bash
xcrun notarytool submit shuttle-codec.zip \
  --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD" --wait
xcrun stapler staple shuttle-codec
```

Add `MACOS_CERT_P12`, `MACOS_CERT_PASSWORD`, `APPLE_ID`, `APPLE_TEAM_ID` and
`APPLE_PASSWORD` as secrets, then mirror the commands in the macOS branch of
`.github/workflows/release.yml` (the PyInstaller output is a plain Mach-O
binary, so signing must happen *before* zipping).

### Linux

No signing needed. `SHA256SUMS.txt` published with the release is the integrity
mechanism.

## 5. After publishing

- Check the release page: all artifacts present, checksums uploaded and the
  attestation visible (`gh attestation verify <file> --repo jmarc9901/shuttle-codec`).
- Install on a clean Windows VM and run one conversion of each kind (video,
  audio extraction, image, frame export) to verify the packaged build, not just
  the source tree.
- Check the [Security workflow](../.github/workflows/security.yml) run and the
  CodeQL alerts: both are scheduled, so a quiet week is not the same as a green
  build.
- Update the README screenshots if the UI changed (`create_demo.py` regenerates
  `docs/demo.gif`).

## 6. What runs automatically, and when

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | push/PR to `main` | lint, strict types, 12-cell test matrix, coverage gate, Windows packaging |
| `codeql.yml` | push/PR + weekly | GitHub code scanning (security-and-quality queries) |
| `security.yml` | weekly + dependency changes | `pip-audit` on the runtime dependencies |
| `release.yml` | `v*` tag | builds, signs, attests and publishes the artifacts |
| Dependabot | monthly | pip and GitHub Actions updates |
