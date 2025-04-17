import contextlib
import os
import sys

with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
    from qfluentwidgets import qconfig  # noqa: F401

from qfluentwidgets import FluentTranslator
from PySide6.QtCore import Qt, QTranslator
from PySide6.QtWidgets import QApplication
from src.gui.common.config import cfg
from src.gui.view.main_window import MainWindow


def wwa():
    # enable dpi scale
    if cfg.get(cfg.dpiScale) != "Auto":
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

    # create application
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    # internationalization
    locale = cfg.get(cfg.language).value
    translator = FluentTranslator(locale)
    galleryTranslator = QTranslator()
    galleryTranslator.load(locale, "gallery", ".", ":/gallery/i18n")

    app.installTranslator(translator)
    app.installTranslator(galleryTranslator)

    # create main window
    w = MainWindow()
    w.show()

    app.exec()


if __name__ == '__main__':
    wwa()
