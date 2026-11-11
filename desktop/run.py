"""TubeForge — download media in the format you want."""

from __future__ import annotations

import multiprocessing
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.core import APP_NAME, Settings
from app.icons import asset_path
from app.theme import DEFAULT_THEME, apply_theme
from app.window import MainWindow


def main() -> int:
    multiprocessing.freeze_support()

    if "--check" in sys.argv:
        from app.diagnostics import diagnostic_check

        return diagnostic_check()
    if "--download-test" in sys.argv:
        from app.diagnostics import download_test

        return download_test()
    if "--ui-test" in sys.argv:
        from app.diagnostics import ui_test

        return ui_test()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setWindowIcon(QIcon(str(asset_path("icon.ico"))))
    settings = Settings()
    apply_theme(app, str(settings.get("theme") or DEFAULT_THEME))

    window = MainWindow(settings)
    window.show()

    if "--selftest" in sys.argv:
        QTimer.singleShot(1500, window.close)
        QTimer.singleShot(2000, app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
