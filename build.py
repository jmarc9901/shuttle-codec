"""
Build script for Shuttle Codec.
Embeds FFmpeg binaries into the executable.
Supports Windows, macOS, and Linux.
"""
import os
import sys
import shutil
import platform

APP_NAME = "shuttle-codec"
RESOURCES_DIR = "resources"
BIN_DIR = os.path.join(RESOURCES_DIR, "bin")

# Platform-specific binary names
if sys.platform == "win32":
    FFMPEG_BIN = "ffmpeg.exe"
    FFPROBE_BIN = "ffprobe.exe"
    TARGET_EXT = ".exe"
elif sys.platform == "darwin":
    FFMPEG_BIN = "ffmpeg"
    FFPROBE_BIN = "ffprobe"
    TARGET_EXT = ""
else:  # Linux
    FFMPEG_BIN = "ffmpeg"
    FFPROBE_BIN = "ffprobe"
    TARGET_EXT = ""

SPEC_FILE = f"{APP_NAME}{TARGET_EXT}.spec" if TARGET_EXT else f"{APP_NAME}.spec"

SPEC_TEMPLATE = f"""# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Collect FFmpeg binaries
binaries = []
bin_path = Path(r"{BIN_DIR}")
if bin_path.exists():
    for exe in ["{FFMPEG_BIN}", "{FFPROBE_BIN}"]:
        exe_path = bin_path / exe
        if exe_path.exists():
            binaries.append((
                str(exe_path),
                str(Path("resources") / "bin")
            ))
            print(f"  Bundling: {{exe_path.name}}")

# Collect logo
logo_path = Path("logo.png")
datas = []
if logo_path.exists():
    datas.append((str(logo_path), "."))
    print(f"  Bundling: {{logo_path.name}}")

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['PyQt5.sip'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={str(sys.platform != "win32")},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.png',
)
"""


def check_ffmpeg() -> bool:
    """Check if FFmpeg binaries exist. Returns False if not found (non-fatal on macOS/Linux)."""
    ffmpeg = os.path.join(BIN_DIR, FFMPEG_BIN)
    ffprobe = os.path.join(BIN_DIR, FFPROBE_BIN)
    if not os.path.isfile(ffmpeg):
        print(f"  [WARN] {ffmpeg} not found")
        print("  The app will use system FFmpeg from PATH at runtime.")
        return False
    if not os.path.isfile(ffprobe):
        print(f"  [WARN] {ffprobe} not found")
        return False
    size_mb = os.path.getsize(ffmpeg) / 1024 / 1024
    print(f"  [OK] {FFMPEG_BIN} ({size_mb:.1f} MB)")
    size_mb = os.path.getsize(ffprobe) / 1024 / 1024
    print(f"  [OK] {FFPROBE_BIN} ({size_mb:.1f} MB)")
    return True


def write_spec() -> None:
    """Write the spec file with FFmpeg paths."""
    with open(SPEC_FILE, "w") as f:
        f.write(SPEC_TEMPLATE)
    print(f"  [OK] Created {SPEC_FILE}")


def build() -> None:
    print(f"\n{'='*50}")
    print(f"  Building {APP_NAME} for {platform.system()}")
    print(f"{'='*50}\n")

    print("Checking FFmpeg binaries...")
    has_ffmpeg = check_ffmpeg()
    if not has_ffmpeg and sys.platform == "win32":
        print("ERROR: FFmpeg binaries required for Windows build.")
        print("Run 'python download_ffmpeg.py' first.")
        sys.exit(1)

    print("\nGenerating spec file...")
    write_spec()

    print("\nRunning PyInstaller...")
    import subprocess
    result = subprocess.call(
        [sys.executable, "-m", "PyInstaller", SPEC_FILE, "--noconfirm"]
    )

    if result == 0:
        dist_name = f"{APP_NAME}{TARGET_EXT}" if TARGET_EXT else APP_NAME
        dist_path = os.path.join("dist", dist_name)
        if os.path.isfile(dist_path):
            size_mb = os.path.getsize(dist_path) / 1024 / 1024
            print(f"\n{'='*50}")
            print(f"  [SUCCESS] Build completed!")
            print(f"  Output: {dist_path} ({size_mb:.1f} MB)")
            print(f"{'='*50}")
        elif os.path.isdir(dist_name):
            # macOS .app bundle
            print(f"\n{'='*50}")
            print(f"  [SUCCESS] Build completed!")
            print(f"  Output: {dist_name}")
            print(f"{'='*50}")
        else:
            print(f"\n[WARNING] Build completed but {dist_path} not found?")
    else:
        print(f"\n[ERROR] Build failed with code {result}")
        sys.exit(1)


if __name__ == "__main__":
    build()