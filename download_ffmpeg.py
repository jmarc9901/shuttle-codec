import urllib.request
import io
import os
import sys
import zipfile
import ssl
import shutil
from typing import Optional

FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

TARGET_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resources", "bin"
)


def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    return ctx


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


def _extract_ffmpeg(buffer: io.BytesIO, target_dir: str) -> int:
    extracted = 0
    extracted_dirs: set[str] = set()

    print("Extracting ZIP...")
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as zf:
        for member in zf.namelist():
            if member.endswith("ffmpeg.exe") or member.endswith("ffprobe.exe"):
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


def _report_results(target_dir: str, extracted: int) -> None:
    if extracted == 2:
        print("\nSUCCESS: FFmpeg and FFprobe extracted correctly!")
    else:
        print(f"\nWARNING: Only extracted {extracted}/2 files!")

    for f in ("ffmpeg.exe", "ffprobe.exe"):
        path = os.path.join(target_dir, f)
        if os.path.isfile(path):
            size = os.path.getsize(path) / 1024 / 1024
            print(f"  {f}: {size:.1f} MB")
        else:
            print(f"  {f}: NOT FOUND!")

    print(f"\nLocation: {target_dir}")


def main() -> None:
    os.makedirs(TARGET_DIR, exist_ok=True)

    print(f"Downloading FFmpeg from GitHub...")
    print("URL: " + FFMPEG_URL)

    ctx = _create_ssl_context()
    total = _get_file_size(FFMPEG_URL, ctx)

    if total:
        print(f"File size: {total // 1024 // 1024} MB")

    print("Starting download (this may take a few minutes)...")
    buffer = _download_file(FFMPEG_URL, ctx, total)
    extracted = _extract_ffmpeg(buffer, TARGET_DIR)
    _report_results(TARGET_DIR, extracted)


if __name__ == "__main__":
    main()
