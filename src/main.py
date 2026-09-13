import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from src.app import VERSION, MainWindow
from src.i18n import tr
from src.utils import get_icon_path


def _enable_high_dpi() -> None:
    """
    Ask Qt for crisp scaling and sharp pixmaps on HiDPI displays.

    Must run before the QApplication exists; on Qt builds where the flags are
    already the default this is a no-op.
    """
    for attribute in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
        flag = getattr(Qt, attribute, None)
        if flag is not None:
            QApplication.setAttribute(flag, True)


def main() -> None:
    _enable_high_dpi()
    app = QApplication(sys.argv)
    app.setApplicationName(tr("app_name"))
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon(get_icon_path()))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
