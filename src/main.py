import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from src.app import VERSION, MainWindow
from src.i18n import tr
from src.utils import get_icon_path


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(tr("app_name"))
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon(get_icon_path()))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
