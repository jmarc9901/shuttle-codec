import hashlib
import hmac
import io
import os
import platform
import shutil
import ssl
import sys
import tarfile
import urllib.request
import zipfile

# Platform-specific binary names and URLs
if sys.platform == "win32":
    FFMPEG_BIN = "ffmpeg.exe"
    FFPROBE_BIN = "ffprobe.exe"
    ARCHIVE_URL_TEMPLATE = (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/{tag}/"
        "ffmpeg-master-latest-win64-gpl.zip"
    )
    ARCHIVE_TYPE = "zip"
elif sys.platform == "darwin":
    FFMPEG_BIN = "ffmpeg"
    FFPROBE_BIN = "ffprobe"
    ARCHIVE_URL_TEMPLATE = (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/{tag}/"
        "ffmpeg-master-latest-macos64-gpl.zip"
    )
    ARCHIVE_TYPE = "zip"
else:  # Linux
    FFMPEG_BIN = "ffmpeg"
    FFPROBE_BIN = "ffprobe"
    ARCHIVE_URL_TEMPLATE = (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/{tag}/"
        "ffmpeg-master-latest-linux64-gpl.tar.xz"
    )
    ARCHIVE_TYPE = "tar.xz"

TARGET_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resources", "bin"
)

# Optional pinning, for reproducible and tamper-evident builds:
#   FFMPEG_BUILD_TAG=autobuild-2025-06-30-12-00
#   FFMPEG_ARCHIVE_SHA256=<sha256 of that archive>
# Without a tag the newest "latest" build is downloaded. Without a digest the
# hash of the archive is printed so it can be recorded and pinned later.
BUILD_TAG = os.environ.get("FFMPEG_BUILD_TAG", "").strip()
EXPECTED_SHA256 = os.environ.get("FFMPEG_ARCHIVE_SHA256", "").strip().lower()


def resolve_archive_url() -> str:
    """URL of the archive to download (pinned build tag when provided)."""
    return ARCHIVE_URL_TEMPLATE.format(tag=BUILD_TAG or "latest")


def archive_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


def verify_archive_hash(data: bytes, expected: str) -> bool:
    """True when the archive matches `expected` (an empty value means no pin)."""
    if not expected:
        return True
    return hmac.compare_digest(archive_sha256(data), expected.strip().lower())


def _create_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def _get_file_size(url: str, ctx: ssl.SSLContext) -> int:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }, method="HEAD")
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        return int(resp.headers.get("content-length", 0))
    except Exception:
        return 0


def _download_file(url: str, ctx: ssl.SSLContext, total: int) -> io.BytesIO:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    resp = urllib.request.urlopen(req, context=ctx, timeout=600)
    buffer = io.BytesIO()
    downloaded = 0
    last_pct = -1

    while True:
        chunk = resp.read(65536)
        if not chunk:
            break
        buffer.write(chunk)
        downloaded += len(chunk)
        if total > 0:
            pct = int((downloaded / total) * 100)
            if pct != last_pct:
                print(f"\rDownloading: {pct}% ({downloaded // 1024 // 1024}/{total // 1024 // 1024} MB)", end="")
                last_pct = pct

    print(f"\nDownloaded {downloaded // 1024 // 1024} MB successfully!")
    return buffer


def _extract_zip(buffer: io.BytesIO, target_dir: str) -> int:
    extracted = 0
    extracted_dirs: set[str] = set()
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as zf:
        for member in zf.namelist():
            if not _is_safe_member(target_dir, member):
                print(f"  Skipped unsafe entry: {member}")
                continue
            if member.endswith(FFMPEG_BIN) or member.endswith(FFPROBE_BIN):
                zf.extract(member, target_dir)
                src = os.path.join(target_dir, member)
                dst = os.path.join(target_dir, os.path.basename(member))
                if os.path.isfile(dst):
                    os.remove(dst)
                os.rename(src, dst)
                extracted += 1
                extracted_dirs.add(os.path.dirname(os.path.join(target_dir, member)))
                print(f"  Extracted: {os.path.basename(member)}")

    for d in extracted_dirs:
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"  Cleaned up: {os.path.relpath(d, target_dir)}")

    return extracted


def _is_safe_member(target_dir: str, member_name: str) -> bool:
    """Reject members that would extract outside `target_dir` (path traversal)."""
    base = os.path.realpath(target_dir)
    destination = os.path.realpath(os.path.join(base, member_name))
    return destination == base or destination.startswith(base + os.sep)


def _extract_tar(buffer: io.BytesIO, target_dir: str) -> int:
    extracted = 0
    buffer.seek(0)
    with tarfile.open(fileobj=buffer, mode="r:xz") as tf:
        for member in tf.getmembers():
            # Only regular files are considered; reject symlinks/devices and
            # anything whose resolved path escapes the target directory.
            if not member.isfile() or not _is_safe_member(target_dir, member.name):
                print(f"  Skipped unsafe entry: {member.name}")
                continue
            name = os.path.basename(member.name)
            if name != FFMPEG_BIN and name != FFPROBE_BIN:
                continue
            # Python 3.12+ wants an explicit extraction filter (CVE-2007-4559).
            if sys.version_info >= (3, 12):
                tf.extract(member, target_dir, filter="data")
            else:
                tf.extract(member, target_dir)
            src = os.path.join(target_dir, member.name)
            dst = os.path.join(target_dir, name)
            if os.path.isfile(dst):
                os.remove(dst)
            shutil.move(src, dst)
            os.chmod(dst, 0o755)
            extracted += 1
            print(f"  Extracted: {name}")

    return extracted


def _report_results(target_dir: str, extracted: int) -> None:
    if extracted == 2:
        print("\nSUCCESS: FFmpeg and FFprobe extracted correctly!")
    else:
        print(f"\nWARNING: Only extracted {extracted}/2 files!")

    for f in (FFMPEG_BIN, FFPROBE_BIN):
        path = os.path.join(target_dir, f)
        if os.path.isfile(path):
            size = os.path.getsize(path) / 1024 / 1024
            print(f"  {f}: {size:.1f} MB")
        else:
            print(f"  {f}: NOT FOUND!")

    print(f"\nLocation: {target_dir}")


def _try_package_manager() -> bool:
    if sys.platform == "darwin":
        print("\nAttempting to install via Homebrew...")
        return os.system("brew install ffmpeg") == 0
    elif sys.platform.startswith("linux"):
        for manager, cmd in [
            ("apt", "sudo apt install -y ffmpeg"),
            ("dnf", "sudo dnf install -y ffmpeg"),
            ("pacman", "sudo pacman -S --noconfirm ffmpeg"),
            ("zypper", "sudo zypper install -y ffmpeg"),
        ]:
            if shutil.which(manager):
                print(f"\nAttempting to install via {manager}...")
                return os.system(cmd) == 0
    return False


def main() -> None:
    os.makedirs(TARGET_DIR, exist_ok=True)

    archive_url = resolve_archive_url()
    print(f"Downloading FFmpeg for {platform.system()}...")
    print("URL: " + archive_url)
    if not BUILD_TAG:
        print("Note: no FFMPEG_BUILD_TAG set, using the newest 'latest' build.")

    ctx = _create_ssl_context()
    total = _get_file_size(archive_url, ctx)

    if total:
        print(f"File size: {total // 1024 // 1024} MB")
    else:
        print("Could not determine file size. Attempting download anyway...")

    print("Starting download (this may take a few minutes)...")
    try:
        buffer = _download_file(archive_url, ctx, total)
    except Exception as e:
        print(f"\nDownload failed: {e}")
        if sys.platform != "win32":
            print("\nTrying package manager instead...")
            if _try_package_manager():
                print("\nFFmpeg installed via package manager!")
                return
        print("\nPlease install FFmpeg manually:")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg  (or your package manager)")
        sys.exit(1)

    data = buffer.getvalue()
    print(f"Archive SHA-256: {archive_sha256(data)}")
    if not verify_archive_hash(data, EXPECTED_SHA256):
        print("\nERROR: the archive does not match FFMPEG_ARCHIVE_SHA256.")
        print("       Refusing to extract a possibly tampered download.")
        sys.exit(1)

    extracted = _extract_zip(buffer, TARGET_DIR) if ARCHIVE_TYPE == "zip" else _extract_tar(buffer, TARGET_DIR)

    _report_results(TARGET_DIR, extracted)


if __name__ == "__main__":
    main()
