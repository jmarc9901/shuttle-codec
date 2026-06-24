import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import MainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon


def _get_icon_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "logo.png")
    return os.path.join(os.path.dirname(__file__), "..", "logo.png")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Shuttle Codec")
    app.setApplicationVersion("1.0.0")
    app.setWindowIcon(QIcon(_get_icon_path()))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
