import sys, os, time
from pathlib import Path

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

app = QApplication(sys.argv)

from src.app import MainWindow
from src.i18n import get_language, set_language

window = MainWindow()
window.show()
window.resize(960, 680)

frames = []
save_dir = Path("docs")
save_dir.mkdir(exist_ok=True)

def capture(name: str) -> None:
    for _ in range(3):
        app.processEvents()
    pixmap = window.grab()
    path = save_dir / name
    pixmap.save(str(path))
    print(f"  Captured: {name}")
    frames.append(str(path))

def step1_intro() -> None:
    print("\n[1/5] Simple mode with YouTube preset...")
    set_language("es")
    idx = window.preset_combo.findData("youtube_1080p")
    if idx >= 0:
        window.preset_combo.setCurrentIndex(idx)
    capture("demo_01_simple_es.png")

def step2_change_preset() -> None:
    print("[2/5] Switching to Twitter GIF preset...")
    idx = window.preset_combo.findData("twitter_gif")
    if idx >= 0:
        window.preset_combo.setCurrentIndex(idx)
    capture("demo_02_gif_preset.png")

def step3_toggle_expert() -> None:
    print("[3/5] Switching to expert mode...")
    window.expert_btn.setChecked(True)
    window._toggle_mode()
    capture("demo_03_expert_es.png")

def step4_change_language() -> None:
    print("[4/5] Changing language to English...")
    idx = window.lang_combo.findData("en")
    if idx >= 0:
        window.lang_combo.setCurrentIndex(idx)
    window._on_language_change(idx)
    capture("demo_04_expert_en.png")

def step5_back_to_simple() -> None:
    print("[5/5] Back to simple mode, English...")
    window.expert_btn.setChecked(False)
    window._toggle_mode()
    idx = window.preset_combo.findData("youtube_1080p")
    if idx >= 0:
        window.preset_combo.setCurrentIndex(idx)
    capture("demo_05_simple_en.png")

QTimer.singleShot(500, step1_intro)
QTimer.singleShot(1500, step2_change_preset)
QTimer.singleShot(2500, step3_toggle_expert)
QTimer.singleShot(3500, step4_change_language)
QTimer.singleShot(4500, step5_back_to_simple)
QTimer.singleShot(5500, lambda: (window.close(), app.quit()))

app.exec_()

print(f"\nCaptured {len(frames)} frames in docs/")
print("Creating GIF with FFmpeg...")
os.system(
    'ffmpeg -y -framerate 0.8 '
    '-i docs/demo_%02d_*.png '
    '-filter_complex "fps=1,scale=800:-1:flags=lanczos,split[s0][s1];'
    '[s0]palettegen=max_colors=64[p];[s1][p]paletteuse=dither=bayer" '
    'docs/demo.gif'
)
print("Done! docs/demo.gif created.")
