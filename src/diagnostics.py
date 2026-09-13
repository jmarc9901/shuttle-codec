"""
Diagnostics for the "report a problem" flow.

Pure functions (no Qt, no network) that assemble the environment summary
and the GitHub issue URL, so the whole thing is unit-testable.
"""

import platform
import urllib.parse

ISSUES_URL = "https://github.com/jmarc9901/shuttle-codec/issues/new"
REPO_URL = "https://github.com/jmarc9901/shuttle-codec"

# GitHub rejects URLs longer than ~8k characters; leave room for the title
# and the query-string encoding overhead.
MAX_BODY_CHARS = 5000
MAX_LOG_LINES = 25


def tail_lines(text: str, limit: int = MAX_LOG_LINES) -> str:
    """Return the last `limit` non-empty lines of `text`."""
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def collect_environment(
    version: str,
    language: str = "",
    ffmpeg_version: str = "",
    qt_version: str = "",
) -> str:
    """Build the environment block that goes at the top of a bug report."""
    lines = [
        "**Environment**",
        f"- Shuttle Codec: {version}",
        f"- OS: {platform.platform()}",
        f"- Python: {platform.python_version()}",
    ]
    if qt_version:
        lines.append(f"- Qt: {qt_version}")
    if language:
        lines.append(f"- UI language: {language}")
    lines.append(f"- FFmpeg: {ffmpeg_version.strip() or 'not detected'}")
    return "\n".join(lines)


def build_diagnostics(
    version: str,
    language: str = "",
    ffmpeg_version: str = "",
    qt_version: str = "",
    log_text: str = "",
    max_body_chars: int = MAX_BODY_CHARS,
) -> str:
    """Assemble the full diagnostic text (environment + last log lines)."""
    parts = [collect_environment(version, language, ffmpeg_version, qt_version)]
    tail = tail_lines(log_text)
    if tail:
        parts.append("**Log (last lines)**\n```text\n" + tail + "\n```")
    body = "\n\n".join(parts)
    if len(body) > max_body_chars:
        body = body[:max_body_chars].rstrip() + "\n… (truncated)"
    return body


def build_issue_url(diagnostics: str, title: str = "") -> str:
    """Return a pre-filled GitHub "new issue" URL for the given diagnostics."""
    params: dict[str, str] = {"body": diagnostics[:MAX_BODY_CHARS]}
    if title:
        params["title"] = title
    return f"{ISSUES_URL}?{urllib.parse.urlencode(params)}"
