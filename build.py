"""
Build script for Shuttle Codec.
Embeds FFmpeg binaries into the executable.
"""
import os
import sys
import shutil

APP_NAME = "shuttle-codec"
RESOURCES_DIR = "resources"
BIN_DIR = os.path.join(RESOURCES_DIR, "bin")
SPEC_FILE = f"{APP_NAME}.spec"

SPEC_TEMPLATE = f"""# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Collect FFmpeg binaries
binaries = []
bin_path = Path(r"{BIN_DIR}")
if bin_path.exists():
    for exe in ["ffmpeg.exe", "ffprobe.exe"]:
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.png',
)
"""


def check_ffmpeg():
    """Check if FFmpeg binaries exist."""
    ffmpeg = os.path.join(BIN_DIR, "ffmpeg.exe")
    ffprobe = os.path.join(BIN_DIR, "ffprobe.exe")
    if not os.path.isfile(ffmpeg):
        print(f"ERROR: {ffmpeg} not found!")
        print("Run 'python download_ffmpeg.py' first.")
        return False
    if not os.path.isfile(ffprobe):
        print(f"ERROR: {ffprobe} not found!")
        return False
    size_mb = os.path.getsize(ffmpeg) / 1024 / 1024
    print(f"  ✓ ffmpeg.exe ({size_mb:.1f} MB)")
    size_mb = os.path.getsize(ffprobe) / 1024 / 1024
    print(f"  ✓ ffprobe.exe ({size_mb:.1f} MB)")
    return True


def write_spec():
    """Write the spec file with FFmpeg paths."""
    with open(SPEC_FILE, "w") as f:
        f.write(SPEC_TEMPLATE)
    print(f"  ✓ Created {SPEC_FILE}")


def build():
    print(f"\n{'='*50}")
    print(f"  Building {APP_NAME}")
    print(f"{'='*50}\n")

    # Check FFmpeg
    print("Checking FFmpeg binaries...")
    if not check_ffmpeg():
        sys.exit(1)

    # Write spec
    print("\nGenerating spec file...")
    write_spec()

    # Run PyInstaller
    print("\nRunning PyInstaller...")
    import subprocess
    result = subprocess.call(
        [sys.executable, "-m", "PyInstaller", SPEC_FILE, "--noconfirm"]
    )

    if result == 0:
        dist_path = os.path.join("dist", f"{APP_NAME}.exe")
        if os.path.isfile(dist_path):
            size_mb = os.path.getsize(dist_path) / 1024 / 1024
            print(f"\n{'='*50}")
            print(f"  ✅ BUILD SUCCESSFUL!")
            print(f"  📦 {dist_path} ({size_mb:.1f} MB)")
            print(f"{'='*50}")
        else:
            print(f"\n⚠️  Build completed but {dist_path} not found?")
    else:
        print(f"\n❌ Build failed with code {result}")
        sys.exit(1)


if __name__ == "__main__":
    build()