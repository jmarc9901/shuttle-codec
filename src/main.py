import sys
import os
from typing import List

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from src.app import MainWindow
from src.i18n import tr


def _get_icon_path() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "logo.png")  # type: ignore[attr-defined]
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "logo.png"))


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(tr("app_name"))
    app.setApplicationVersion("1.1.0")
    app.setWindowIcon(QIcon(_get_icon_path()))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
