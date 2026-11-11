"""Main application window."""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme
from .core import (
    APP_NAME,
    APP_VERSION,
    DownloadManager,
    History,
    Job,
    Settings,
    find_ffmpeg,
    prune_session_cookies,
)
from .pages import HistoryPage, HomePage, QueuePage, SettingsPage
from .theme import C
from .widgets import Sidebar, TitleBar, Toast

HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT = 10, 11, 12, 13, 14
HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 15, 16, 17
WM_NCHITTEST = 0x0084
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_EX_APPWINDOW = 0x00040000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020


class MainWindow(QWidget):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Media Studio")
        # Keep the native minimise/maximise boxes even though the frame is
        # custom-drawn: Windows uses WS_MINIMIZEBOX to decide whether clicking
        # the taskbar button (or the title-bar button) minimises the window,
        # and its DWM minimise/maximise animations depend on it too.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
        )
        self.setWindowIcon(QIcon(str(icons.asset_path("icon.ico"))))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(1000, 700)
        self.resize(1200, 860)
        self.setAcceptDrops(True)

        self.settings = settings or Settings()
        prune_session_cookies()
        self.history = History()
        self.manager = DownloadManager(self.settings)
        self._jobs: dict[str, Job] = {}
        self._active_ids: set[str] = set()
        self._current_page = 0
        self._rebuilding = False
        self._orphan_workers: list[QWidget] = []

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._build_ui()

        # Window-level wiring (survives theme rebuilds) ---------------------
        self.manager.job_started.connect(self._job_started)
        self.manager.job_done.connect(self._job_done)
        self.manager.job_failed.connect(self._job_failed)
        self.manager.job_cancelled.connect(self._job_cancelled)
        self.settings.changed.connect(self._settings_changed)

        shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut.activated.connect(self._focus_url)
        for i in range(4):
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.activated.connect(lambda idx=i: self.switch_page(idx))
        quit_sc = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_sc.activated.connect(self.close)

        self._refresh_ffmpeg()
        self.manager.start()
        self._restore_geometry()

        # Warm up yt-dlp's YouTube extractor in the background so the first
        # fetch feels instant instead of waiting on module imports.
        import threading

        def _warm():
            try:
                import yt_dlp  # noqa: F401
                from yt_dlp.extractor.youtube import YoutubeIE  # noqa: F401
            except Exception:
                pass

        threading.Thread(target=_warm, daemon=True).start()

        if not find_ffmpeg(self.settings.get("ffmpeg_path") or ""):
            QTimer.singleShot(1500, lambda: self._toast(
                "ffmpeg is missing. Open Settings → Tools to install it.", "error"
            ))

    def _build_ui(self) -> None:
        old = getattr(self, "root", None)
        if old is not None:
            self._outer.removeWidget(old)
            old.hide()
            old.setParent(None)
            old.deleteLater()

        self.root = QFrame()
        self.root.setObjectName("Root")
        self.root.setMouseTracking(True)
        root_lay = QVBoxLayout(self.root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        self.sidebar = Sidebar()
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.sidebar)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        self.titlebar = TitleBar(self)
        right_lay.addWidget(self.titlebar)
        self.stack = QStackedWidget()
        right_lay.addWidget(self.stack, 1)
        body.addWidget(right, 1)
        root_lay.addLayout(body)

        self._outer.addWidget(self.root)

        # Pages ------------------------------------------------------------
        self.home = HomePage(self.settings, self.manager)
        self.queue = QueuePage(self.settings, self.manager)
        self.history_page = HistoryPage(self.history)
        self.settings_page = SettingsPage(self.settings)
        for page in (self.home, self.queue, self.history_page, self.settings_page):
            self.stack.addWidget(page)

        self.toast = Toast(self.root)
        self.toast.hide()

        # Page wiring ------------------------------------------------------
        self.sidebar.nav_requested.connect(self.switch_page)
        self.home.download_requested.connect(self._enqueue)
        self.home.notify.connect(self._toast)
        self.queue.notify.connect(self._toast)
        self.history_page.notify.connect(self._toast)
        self.settings_page.notify.connect(self._toast)
        self.settings_page.ffmpeg_status.connect(self._on_ffmpeg_status)
        self.queue.count_changed.connect(self._update_badge)

        # Restore cards for jobs that already exist this session.
        for job in self._jobs.values():
            self.queue.add_job(job)

        self.switch_page(self._current_page)
        self._refresh_ffmpeg()

    # -- pages ------------------------------------------------------------
    PAGE_META = [
        ("Download", "home"),
        ("Queue", "queue"),
        ("History", "history"),
        ("Settings", "settings"),
    ]

    def switch_page(self, index: int) -> None:
        if index < 0 or index >= self.stack.count():
            return
        self._current_page = index
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active(index)
        title, icon_name = self.PAGE_META[index]
        self.titlebar.set_page(title, icon_name)

    def _focus_url(self) -> None:
        self.switch_page(0)
        self.home.url_edit.setFocus()
        self.home.url_edit.selectAll()

    # -- jobs -------------------------------------------------------------
    def _enqueue(self, payload: dict) -> None:
        job = Job(
            url=payload["url"],
            fmt=payload["fmt"],
            kind=payload.get("kind", "audio"),
            quality=payload.get("quality", "best"),
            title=payload.get("title") or "Preparing download…",
            uploader=payload.get("uploader") or "",
            duration=payload.get("duration") or 0,
            thumb_url=payload.get("thumb_url") or "",
        )
        self._jobs[job.id] = job
        self.manager.enqueue(job)
        self.queue.add_job(job)

    def _job_started(self, job: Job) -> None:
        self._active_ids.add(job.id)

    def _job_done(self, job: Job) -> None:
        self._active_ids.discard(job.id)
        self._jobs[job.id] = job
        entry = {
            "id": job.id,
            "title": job.title,
            "url": job.url,
            "fmt": job.fmt,
            "kind": job.kind,
            "quality": job.quality,
            "filepath": job.filepath,
            "filesize": job.filesize,
            "duration": job.duration,
            "uploader": job.uploader,
            "thumb_url": job.thumb_url,
            "completed_at": time.time(),
            "date": datetime.now().strftime("%b %d, %Y"),
            "output_dir": str(self.settings.get("output_dir")),
        }
        self.history.add(entry)
        self._toast(f"Saved · {job.title}", "success")

    def _job_failed(self, job_id: str, message: str) -> None:
        self._active_ids.discard(job_id)
        first = (message or "Download failed").splitlines()[0]
        self._toast(f"Download failed · {first}", "error")

    def _job_cancelled(self, job_id: str) -> None:
        self._active_ids.discard(job_id)
        self._toast("Download cancelled.", "info")

    # -- misc -------------------------------------------------------------
    def _toast(self, text: str, kind: str = "info") -> None:
        self.toast.show_message(text, kind)

    def _update_badge(self, active: int) -> None:
        self.sidebar.nav_buttons[1].set_badge(active)

    def _refresh_ffmpeg(self) -> None:
        path = find_ffmpeg(self.settings.get("ffmpeg_path") or "")
        self.sidebar.set_ffmpeg(bool(path), path or "")

    def _on_ffmpeg_status(self, found: bool, detail: str) -> None:
        self.sidebar.set_ffmpeg(found, detail)

    def _settings_changed(self) -> None:
        self._refresh_ffmpeg()
        if self._rebuilding:
            return
        wanted = str(self.settings.get("theme") or theme.DEFAULT_THEME)
        if wanted != theme.CURRENT_THEME:
            QTimer.singleShot(0, self._apply_theme_setting)

    def _apply_theme_setting(self) -> None:
        if self._rebuilding:
            return
        wanted = str(self.settings.get("theme") or theme.DEFAULT_THEME)
        if wanted == theme.CURRENT_THEME:
            return
        # Keep a running fetch worker alive across the rebuild so its QThread
        # is not collected while it is still executing.
        worker = getattr(self.home, "_fetch_worker", None)
        if worker is not None and worker.isRunning():
            try:
                self.home._fetch_worker = None
            except Exception:
                pass
            self._orphan_workers.append(worker)
            worker.finished.connect(lambda w=worker: self._release_worker(w))
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app, wanted)
        self._rebuilding = True
        try:
            self._build_ui()
        finally:
            self._rebuilding = False
        self._toast(f"{theme.theme_name(wanted)} theme applied.", "success")

    def _release_worker(self, worker) -> None:
        try:
            self._orphan_workers.remove(worker)
        except ValueError:
            pass
        try:
            worker.deleteLater()
        except Exception:
            pass

    # -- window chrome ----------------------------------------------------
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._ensure_native_window_styles()

    def _ensure_native_window_styles(self) -> None:
        """Make the frameless window behave like a normal taskbar app.

        Qt's frameless hint asks Windows for a popup-style window. Without the
        minimise/maximise boxes, the shell only focuses the window when its
        taskbar button is clicked instead of minimising it, and DWM skips the
        native minimise/maximise animations. Restore those style bits directly.
        """
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            get_long.restype = ctypes.c_ssize_t
            get_long.argtypes = [wintypes.HWND, ctypes.c_int]
            set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            set_long.restype = ctypes.c_ssize_t
            set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]

            style = get_long(hwnd, GWL_STYLE) | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
            set_long(hwnd, GWL_STYLE, style)
            ex_style = get_long(hwnd, GWL_EXSTYLE) | WS_EX_APPWINDOW
            set_long(hwnd, GWL_EXSTYLE, ex_style)
            user32.SetWindowPos.argtypes = [
                wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, ctypes.c_uint,
            ]
            user32.SetWindowPos.restype = wintypes.BOOL
            user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
            )
            # Keep DWM's native minimise/maximise transitions enabled for this
            # window (attribute 3 = DWMWA_TRANSITIONS_FORCEDISABLED; 0 = animating).
            try:
                value = ctypes.c_int(0)
                dwm = ctypes.windll.dwmapi
                dwm.DwmSetWindowAttribute.argtypes = [
                    wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint,
                ]
                dwm.DwmSetWindowAttribute.restype = ctypes.c_long
                dwm.DwmSetWindowAttribute(
                    hwnd, 3, ctypes.byref(value), ctypes.sizeof(value)
                )
            except Exception:
                pass
        except Exception:
            pass

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            maximized = self.isMaximized()
            for widget in (self.root, self.sidebar):
                widget.setProperty("maximized", maximized)
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            self.titlebar.sync_max_button(maximized)
        super().changeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast._reposition()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        text = event.mimeData().text().strip()
        if text:
            self.switch_page(0)
            self.home.url_edit.setText(text.splitlines()[0])
            self.home.fetch()
            event.acceptProposedAction()

    def nativeEvent(self, eventType, message):
        if sys.platform == "win32" and not self.isMaximized():
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_NCHITTEST:
                    x = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    pos = self.mapFromGlobal(QPoint(x, y))
                    gx, gy = pos.x(), pos.y()
                    w, h = self.width(), self.height()
                    b = 7
                    left, right = gx < b, gx >= w - b
                    top, bottom = gy < b, gy >= h - b
                    if top and left:
                        return True, HTTOPLEFT
                    if top and right:
                        return True, HTTOPRIGHT
                    if bottom and left:
                        return True, HTBOTTOMLEFT
                    if bottom and right:
                        return True, HTBOTTOMRIGHT
                    if left:
                        return True, HTLEFT
                    if right:
                        return True, HTRIGHT
                    if top:
                        return True, HTTOP
                    if bottom:
                        return True, HTBOTTOM
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

    # -- geometry ---------------------------------------------------------
    def _restore_geometry(self) -> None:
        try:
            qs = QSettings(APP_NAME, APP_NAME)
            geo = qs.value("window_geometry")
            if geo is not None:
                self.restoreGeometry(geo)
            else:
                screen = QApplication.primaryScreen()
                if screen:
                    area = screen.availableGeometry()
                    self.move(
                        area.x() + (area.width() - self.width()) // 2,
                        area.y() + (area.height() - self.height()) // 2,
                    )
        except Exception:
            pass

    def _save_geometry(self) -> None:
        try:
            QSettings(APP_NAME, APP_NAME).setValue("window_geometry", self.saveGeometry())
        except Exception:
            pass

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.manager.has_work():
            box = QMessageBox(self)
            box.setWindowTitle("Quit TubeForge?")
            box.setText("A download is still in progress.")
            box.setInformativeText("Quitting now will cancel it.")
            box.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes)
            box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if box.exec() != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self._save_geometry()
        self.manager.stop()
        if not self.manager.wait(4000):
            self.manager.terminate()
            self.manager.wait(1000)
        super().closeEvent(event)
