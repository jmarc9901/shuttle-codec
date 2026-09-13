# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of Shuttle Codec seriously. If you believe you have found a security vulnerability, please report it to us as described below.

**Please do not report security vulnerabilities through public GitHub issues.**

Use GitHub's [private vulnerability reporting](https://github.com/jmarc9901/shuttle-codec/security/advisories/new)
(Security → Report a vulnerability), or email the maintainer at the address
listed in the [GitHub profile](https://github.com/jmarc9901).

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Preferred Languages

We prefer all communications to be in Spanish or English.

## How the project hardens itself

These are the controls already in place, so you can tell a real finding from a
known, accepted trade-off:

- **Supply chain**: FFmpeg is downloaded over HTTPS with an optional pinned build
  tag and a SHA-256 digest that is verified *before* extraction; the archive is
  extracted with path-traversal protection. Releases publish `SHA256SUMS.txt`,
  a resolved dependency manifest (`pip-freeze.txt`) and a SLSA build provenance
  attestation (`gh attestation verify <file> --repo jmarc9901/shuttle-codec`).
- **No network at runtime**: the application makes no outbound requests and
  collects no telemetry. Diagnostics are only sent if the user presses *Report*
  and submits the GitHub issue themselves.
- **Input handling**: paths are resolved with `realpath` and validated, media
  files are size-checked, and every external process is invoked with an argument
  list (never a shell string built from user input).
- **Automation**: `ruff` runs its security rules (flake8-bandit), CodeQL scans
  the code on every push, `pip-audit` audits the dependency tree weekly, and
  Dependabot keeps dependencies patched. CI runs with least-privilege tokens.
- **Opt-in side effects**: shutting the machine down after a batch is off by
  default and always shows a cancellable 60-second countdown.

## Policy

- We will acknowledge receipt of your vulnerability report within 48 hours
- We will send a more detailed response within 72 hours indicating the next steps
- We will keep you informed of the progress towards a fix
- We will publicly acknowledge your responsible disclosure, if you wish
