"""Headless diagnostics used to validate packaged builds."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QApplication

from . import icons
from .core import (
    APP_VERSION,
    DownloadManager,
    Job,
    Settings,
    browser_cookie_database,
    find_ffmpeg,
    ffmpeg_version,
    impersonation_available,
)


def _write(data: dict) -> Path:
    path = Path(tempfile.gettempdir()) / "TubeForge-check.json"
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
    return path


def diagnostic_check() -> int:
    """Verify Qt, TLS, image/SVG support, yt-dlp and ffmpeg in a frozen build."""
    app = QApplication.instance() or QApplication(sys.argv)
    data: dict = {"app_version": APP_VERSION, "frozen": bool(getattr(sys, "frozen", False))}
    ok = True
    try:
        import PySide6
        import yt_dlp

        data["pyside6"] = PySide6.__version__
        data["yt_dlp"] = yt_dlp.version.__version__
        data["impersonation"] = impersonation_available()
        if data["impersonation"]:
            import curl_cffi

            data["curl_cffi"] = getattr(curl_cffi, "__version__", "installed")
        ok = ok and data["impersonation"]
    except Exception as exc:  # noqa: BLE001
        data["engine_error"] = repr(exc)
        ok = False

    try:
        pm = icons.pixmap("play", "#FFFFFF", 32)
        data["svg_ok"] = not pm.isNull() and pm.width() > 0
        ok = ok and data["svg_ok"]
    except Exception as exc:  # noqa: BLE001
        data["svg_ok"] = False
        data["svg_error"] = repr(exc)
        ok = False

    ffmpeg = find_ffmpeg("")
    data["ffmpeg"] = ffmpeg or ""
    data["ffmpeg_version"] = ffmpeg_version(ffmpeg) if ffmpeg else ""
    ok = ok and bool(ffmpeg)

    try:
        from PySide6.QtNetwork import QSslSocket

        data["ssl_support"] = QSslSocket.supportsSsl()
        data["ssl_backends"] = QSslSocket.availableBackends()
    except Exception as exc:  # noqa: BLE001
        data["ssl_error"] = repr(exc)

    # Live TLS + JPEG decode check (also validates bundled Qt TLS plugins).
    url = "https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg"
    nam = QNetworkAccessManager()
    req = QNetworkRequest(QUrl(url))
    req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "Mozilla/5.0")
    req.setTransferTimeout(15000)
    loop = QEventLoop()
    reply = nam.get(req)
    result: dict = {}

    def finished():
        result["status"] = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        result["error"] = reply.errorString()
        raw = bytes(reply.readAll())
        pm2 = QPixmap()
        result["image_ok"] = bool(pm2.loadFromData(raw)) and pm2.width() > 0
        result["bytes"] = len(raw)
        loop.quit()

    reply.finished.connect(finished)
    QTimer.singleShot(20000, loop.quit)
    loop.exec()
    data["network"] = result
    ok = ok and bool(result.get("image_ok"))
    if not reply.isFinished():
        reply.abort()
    nam.deleteLater()
    data["ok"] = ok
    path = _write(data)
    try:
        print(data, "->", path)
    except Exception:
        pass
    return 0 if ok else 1


def ui_test() -> int:
    """Exercise the real window (themes, proxy card, status label) in a frozen build."""
    import os
    import tempfile

    from PySide6.QtTest import QTest

    from . import theme
    from .window import MainWindow

    # Isolate from the user's real profile so theme switching cannot alter it.
    os.environ["APPDATA"] = tempfile.mkdtemp(prefix="tf-uitest-appdata-")
    app = QApplication.instance() or QApplication(sys.argv)
    out_dir = Path(tempfile.gettempdir()) / "TubeForge-ui-test"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings()
    settings.set("theme", "midnight")
    settings.set("proxy_url", "http://127.0.0.1:8080")
    theme.apply_theme(app, "midnight")

    data: dict = {"app_version": APP_VERSION, "checks": {}, "shots": [], "ok": False}
    window = MainWindow(settings)
    window.resize(1200, 860)
    window.show()
    QTest.qWait(700)

    # The frameless window must still expose the native minimise/maximise
    # boxes, otherwise the taskbar button only focuses it and DWM skips the
    # native animations.
    if sys.platform == "win32":
        try:
            hwnd = int(window.winId())
            get_long = ctypes.windll.user32.GetWindowLongPtrW
            get_long.restype = ctypes.c_ssize_t
            get_long.argtypes = [ctypes.c_void_p, ctypes.c_int]
            style = get_long(hwnd, -16)
            data["checks"]["ws_minimizebox"] = bool(style & 0x00020000)
            data["checks"]["ws_maximizebox"] = bool(style & 0x00010000)
            dwm = ctypes.windll.dwmapi
            value = ctypes.c_int(0)
            dwm.DwmSetWindowAttribute.argtypes = [
                ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint,
            ]
            dwm.DwmSetWindowAttribute.restype = ctypes.c_long
            hr = dwm.DwmSetWindowAttribute(
                hwnd, 3, ctypes.byref(value), ctypes.sizeof(value)
            )
            data["checks"]["dwm_transitions"] = hr == 0
        except Exception as exc:  # noqa: BLE001
            data["checks"]["ws_minimizebox"] = False
            data["checks"]["ws_maximizebox"] = False
            data["checks"]["dwm_transitions"] = False
            data["checks"]["style_error"] = repr(exc)
    else:
        data["checks"]["ws_minimizebox"] = True
        data["checks"]["ws_maximizebox"] = True
        data["checks"]["dwm_transitions"] = True

    def shot(name: str) -> None:
        path = out_dir / f"{name}.png"
        window.grab().save(str(path))
        data["shots"].append(str(path))

    # Download page exists and the proxy field is configured.
    data["checks"]["themes"] = window.settings_page.theme_combo.count()
    data["checks"]["proxy_field"] = (
        hasattr(window.settings_page, "proxy_edit")
        and window.settings_page.proxy_edit.text() == "http://127.0.0.1:8080"
    )
    data["checks"]["ytdlp_citation"] = (
        hasattr(window.settings_page, "about_citation")
        and "github.com/yt-dlp/yt-dlp" in window.settings_page.about_citation.text()
    )
    data["checks"]["cookie_file_field"] = hasattr(
        window.settings_page, "cookies_file_edit"
    )
    data["checks"]["cookie_lookup"] = (
        browser_cookie_database("vivaldi") is None
        or browser_cookie_database("vivaldi").name == "Cookies"
    )
    data["checks"]["impersonation"] = impersonation_available()
    shot("frozen_home")

    # Queue card with a live "Downloading" label.
    job = Job(
        url="https://soundcloud.com/x/test",
        fmt="mp3",
        kind="audio",
        title="Frozen build check — downloading label",
        uploader="TubeForge",
    )
    job.status = "downloading"
    job.progress = 64
    job.speed = 3.4 * 1024 * 1024
    job.eta = 12
    job.downloaded = 51 * 1024 * 1024
    job.total = 80 * 1024 * 1024
    job.stage = "Downloading…"
    window.queue.add_job(job)
    window.queue.cards[job.id].update_job(job)
    window.switch_page(1)
    QTest.qWait(400)
    card = window.queue.cards[job.id]
    needed = card.status.fontMetrics().horizontalAdvance("Downloading")
    data["checks"]["status_width"] = card.status.width()
    data["checks"]["status_needed"] = needed
    data["checks"]["status_ok"] = (
        card.status.width() >= needed + 12
        and 0 < card.status.font().pointSizeF() <= 8.5
    )
    shot("frozen_queue")

    # Settings: Proxy card visible.
    window.switch_page(3)
    QTest.qWait(300)
    window.settings_page.scroll.verticalScrollBar().setValue(520)
    QTest.qWait(300)
    shot("frozen_proxy")
    data["checks"]["proxy_value"] = window.settings_page.proxy_edit.text()

    # Live theme switch (rebuilds the window, must keep the page and settings).
    window.switch_page(3)
    combo = window.settings_page.theme_combo
    combo.setCurrentIndex(combo.findData("ocean"))
    deadline = time.time() + 10
    while time.time() < deadline and theme.CURRENT_THEME != "ocean":
        QTest.qWait(80)
    data["checks"]["theme_switched"] = theme.CURRENT_THEME == "ocean"
    data["checks"]["page_preserved"] = window._current_page == 3
    QTest.qWait(300)
    shot("frozen_theme_ocean")
    window.switch_page(0)
    QTest.qWait(300)
    shot("frozen_theme_home")

    data["ok"] = bool(
        data["checks"]["proxy_field"]
        and data["checks"]["ytdlp_citation"]
        and data["checks"]["cookie_file_field"]
        and data["checks"]["cookie_lookup"]
        and data["checks"]["impersonation"]
        and data["checks"]["ws_minimizebox"]
        and data["checks"]["ws_maximizebox"]
        and data["checks"]["dwm_transitions"]
        and data["checks"]["themes"] == 8
        and data["checks"]["status_ok"]
        and data["checks"]["theme_switched"]
        and data["checks"]["page_preserved"]
    )
    window.close()
    QTest.qWait(300)
    path = _write(data)
    try:
        print(data, "->", path)
    except Exception:
        pass
    return 0 if data["ok"] else 1


def download_test() -> int:
    """Download a short YouTube clip as MP3 through the real engine stack."""
    out = Path(tempfile.gettempdir()) / "TubeForge-dlcheck"
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    settings = Settings()
    settings.data["output_dir"] = str(out)
    settings.data["embed_thumbnail"] = False
    settings.data["embed_metadata"] = True
    settings.data["force_ipv4"] = True
    settings.data["cookies_browser"] = "none"
    settings.data["cookies_file"] = ""
    settings.clear_runtime()

    manager = DownloadManager(settings)
    state: dict = {"done": None, "error": None}
    loop = QEventLoop()
    manager.job_done.connect(lambda job: (state.update(done={"path": job.filepath, "size": job.filesize}), loop.quit()))
    manager.job_failed.connect(lambda _id, msg: (state.update(error=msg), loop.quit()))
    manager.job_cancelled.connect(lambda _id: (state.update(error="cancelled"), loop.quit()))
    manager.start()
    manager.enqueue(Job(url="https://www.youtube.com/watch?v=jNQXAC9IVRw", fmt="mp3", kind="audio"))
    QTimer.singleShot(240000, loop.quit)
    loop.exec()
    manager.stop()
    manager.wait(4000)

    info = {
        "app_version": APP_VERSION,
        "state": state,
        "files": [],
        "ok": False,
    }
    for p in sorted(out.glob("*")):
        info["files"].append({"name": p.name, "size": p.stat().st_size})
    done = state.get("done") or {}
    p = Path(done.get("path") or "")
    info["ok"] = bool(done and p.exists() and p.suffix == ".mp3" and p.stat().st_size > 1000)
    path = _write(info)
    try:
        print(info, "->", path)
    except Exception:
        pass
    return 0 if info["ok"] else 1
