"""Tests for themes, proxy settings, source labels and bot-check handling."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="tf-test-appdata-")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app import theme
from app.core import (
    CookieAccessError,
    DownloadManager,
    Job,
    ProgressTracker,
    Settings,
    apply_cookie_options,
    browser_cookie_database,
    build_attempts,
    cookie_database_locked,
    cookie_snapshot_fresh,
    enable_impersonation,
    estimate_output_size,
    has_cookie_options,
    has_playable_media,
    impersonation_available,
    is_bot_check_error,
    is_youtube_url,
    selected_source_size,
    session_cookie_path,
    _friendly_error,
)
from app.pages import _source_label
from app.widgets import JobCard


def wait_for(predicate, timeout: float = 10.0) -> bool:
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(80)

    def poll():
        if predicate():
            loop.quit()

    timer.timeout.connect(poll)
    timer.start()
    QTimer.singleShot(int(timeout * 1000), loop.quit)
    loop.exec()
    timer.stop()
    return bool(predicate())


def check_status_label(app: QApplication) -> None:
    job = Job(url="x", fmt="mp3", kind="audio")
    job.status = "downloading"
    card = JobCard(job)
    card.show()
    app.processEvents()
    card.update_job(job)
    app.processEvents()
    needed = card.status.fontMetrics().horizontalAdvance("Downloading")
    assert card.status.width() >= needed + 12, (card.status.width(), needed)
    assert 0 < card.status.font().pointSizeF() <= 8.5, card.status.font().pointSizeF()
    print(f"status label ok ({needed}px needed, {card.status.width()}px label)")
    card.close()
    card.deleteLater()
    app.processEvents()


def check_themes(app: QApplication) -> None:
    seen = set()
    for theme_id in theme.THEME_ORDER:
        applied = theme.apply_theme(app, theme_id)
        assert applied == theme_id
        sheet = app.styleSheet()
        assert "$" not in sheet, f"unsubstituted placeholder in {theme_id}"
        assert theme.C["bg"].lower() in sheet.lower(), theme_id
        seen.add(theme.C["accent"].lower())
    assert len(seen) >= 6, seen
    theme.apply_theme(app, "midnight")
    print(f"themes ok ({len(theme.THEME_ORDER)} palettes)")


def check_source_labels() -> None:
    cases = {
        "https://yummynime.tv/9036-gerb-demonov.html": "YUMMYNIME",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw": "YouTube",
        "https://youtu.be/jNQXAC9IVRw": "YouTube",
        "https://m.soundcloud.com/artist/track": "SoundCloud",
        "https://vimeo.com/12345": "Vimeo",
        "https://www.example.co.uk/watch": "EXAMPLE",
        "https://sub.domain.com/page": "DOMAIN",
    }
    for url, expected in cases.items():
        got = _source_label(url)
        assert got == expected, (url, got, expected)
    assert _source_label("") == "SOURCE"
    print("source labels ok")


def check_bot_checks() -> None:
    assert impersonation_available(), "curl_cffi is not installed"
    samples = [
        "Got HTTP Error 403 caused by Cloudflare anti-bot challenge; "
        'see https://github.com/yt-dlp/yt-dlp#impersonation for how to install '
        'the required impersonation dependency, and try again with  '
        '--extractor-args "generic:impersonate"',
        "Sign in to confirm you're not a bot",
        "HTTP Error 403: Forbidden",
    ]
    for text in samples:
        assert is_bot_check_error(text), text
    assert not is_bot_check_error("This video is private"), "false positive"
    opts: dict = {}
    enable_impersonation(opts)
    assert opts["extractor_args"]["generic"]["impersonate"] == [""], opts
    print("bot-check detection + impersonation args ok")


def check_proxy() -> None:
    settings = Settings()
    settings.set("proxy_url", "socks5://127.0.0.1:1080")
    assert settings.get("proxy_url") == "socks5://127.0.0.1:1080"
    assert "socks5" in settings.snapshot()["proxy_url"]
    print("proxy setting ok")


def check_cookies() -> None:
    import app.core as core

    tmp = Path(tempfile.mkdtemp(prefix="tf-cookies-"))
    cookie_file = tmp / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    settings = Settings()
    settings.set("cookies_browser", "vivaldi")
    settings.set("cookies_file", str(cookie_file))
    opts: dict = {}
    apply_cookie_options(opts, settings.snapshot())
    assert opts.get("cookiefile") == str(cookie_file), opts
    assert "cookiesfrombrowser" not in opts, opts

    # Firefox does not lock its database, so yt-dlp may read it directly.
    settings.set("cookies_browser", "firefox")
    settings.set("cookies_file", "")
    opts = {}
    apply_cookie_options(opts, settings.snapshot())
    assert opts.get("cookiesfrombrowser") == ("firefox",), opts
    assert "cookiefile" not in opts, opts

    override = tmp / "override.txt"
    override.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    settings.set_runtime("cookie_file_override", str(override))
    opts = {}
    apply_cookie_options(opts, settings.snapshot())
    assert opts.get("cookiefile") == str(override), opts
    settings.clear_runtime()
    assert "cookie_file_override" not in settings.snapshot()

    assert cookie_database_locked(cookie_file) is False
    assert cookie_database_locked(None) is False

    # Chromium browsers are exported to a cookies.txt instead of handing the
    # locked database to yt-dlp.
    settings.set("cookies_browser", "vivaldi")
    fake_db = tmp / "Cookies"
    fake_db.write_bytes(b"not really sqlite")
    original_db = core.browser_cookie_database
    original_locked = core.cookie_database_locked
    original_export = core.export_browser_cookies
    try:
        core.browser_cookie_database = lambda _browser: fake_db
        core.cookie_database_locked = lambda _path: False

        def fake_export(_browser, destination):
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
            return destination

        core.export_browser_cookies = fake_export
        opts = {}
        apply_cookie_options(opts, settings.snapshot())
        snapshot = Path(str(opts.get("cookiefile") or ""))
        assert snapshot.is_file(), opts
        assert "cookiesfrombrowser" not in opts, opts
        assert cookie_snapshot_fresh(snapshot), snapshot

        # An expired runtime snapshot is ignored in favour of a new export.
        stale = tmp / "stale.txt"
        stale.write_text("# stale\n", encoding="utf-8")
        old = time.time() - (core.COOKIE_SNAPSHOT_TTL + 60)
        os.utime(stale, (old, old))
        settings.set_runtime("cookie_file_override", str(stale))
        opts = {}
        apply_cookie_options(opts, settings.snapshot())
        assert opts.get("cookiefile") not in (None, str(stale)), opts
        assert Path(str(opts["cookiefile"])).is_file(), opts
        settings.clear_runtime()

        # A locked browser reuses the snapshot instead of failing.
        core.cookie_database_locked = lambda _path: True
        opts = {}
        apply_cookie_options(opts, settings.snapshot())
        assert Path(str(opts.get("cookiefile") or "")).is_file(), opts

        # Without a snapshot, the error explains how to proceed.
        snapshot.unlink()
        try:
            core.apply_cookie_options({}, settings.snapshot())
        except CookieAccessError as exc:
            text = str(exc)
            assert "Vivaldi" in text, text
            assert "Close Vivaldi and continue" in text, text
        else:
            raise AssertionError("locked cookie database did not raise")
    finally:
        core.browser_cookie_database = original_db
        core.cookie_database_locked = original_locked
        core.export_browser_cookies = original_export

    db = browser_cookie_database("vivaldi")
    if db is not None:
        assert db.name == "Cookies", db
        print(f"vivaldi cookie db: {db} (locked={cookie_database_locked(db)})")
    else:
        print("vivaldi cookie db: not present on this machine")

    assert session_cookie_path("vivaldi").parent.name == "cookies"
    message = _friendly_error(
        "ERROR: Could not copy Chrome cookie database. See issue 7271", "vivaldi"
    )
    assert "Vivaldi" in message and "cookies.txt" in message, message
    print("cookie handling ok")


def check_cookie_prompt(app: QApplication) -> None:
    """The locked-database prompt must snapshot cookies and set the override."""
    import app.pages as pages

    tmp = Path(tempfile.mkdtemp(prefix="tf-cookie-prompt-"))
    fake_db = tmp / "Cookies"
    fake_db.write_bytes(b"locked")
    snapshot = tmp / "snapshot.txt"
    snapshot.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    settings = Settings()
    settings.set("cookies_browser", "vivaldi")
    settings.set("cookies_file", "")
    settings.clear_runtime()

    originals = (
        pages.browser_cookie_database,
        pages.cookie_database_locked,
        pages.browser_running,
        pages.restart_and_export_cookies,
    )

    def click_continue() -> None:
        for widget in app.topLevelWidgets():
            if not isinstance(widget, QMessageBox) or not widget.isVisible():
                continue
            for button in widget.buttons():
                if "continue" in button.text().lower():
                    button.click()
                    return

    try:
        pages.browser_cookie_database = lambda _browser: fake_db
        pages.cookie_database_locked = lambda _path: True
        pages.browser_running = lambda _browser: True
        pages.restart_and_export_cookies = lambda _browser: (snapshot, True)

        QTimer.singleShot(120, click_continue)
        assert pages.ensure_cookie_access(None, settings) is True
        assert settings.snapshot().get("cookie_file_override") == str(snapshot)

        # A fresh snapshot is reused without another prompt.
        assert pages.ensure_cookie_access(None, settings) is True
    finally:
        (
            pages.browser_cookie_database,
            pages.cookie_database_locked,
            pages.browser_running,
            pages.restart_and_export_cookies,
        ) = originals
        settings.clear_runtime()
    print("locked-cookie prompt + snapshot reuse ok")


def check_download_retry() -> None:
    """A Cloudflare 403 must trigger one retry with generic:impersonate."""
    import yt_dlp
    import app.core as core

    original_ydl = yt_dlp.YoutubeDL
    original_ffmpeg = core.find_ffmpeg

    class FakeYDL:
        calls: list[dict] = []

        def __init__(self, opts):
            self.opts = opts
            FakeYDL.calls.append(opts)

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def extract_info(self, _url, download=False):  # noqa: ARG002
            if len(FakeYDL.calls) == 1:
                raise RuntimeError(
                    "Got HTTP Error 403 caused by Cloudflare anti-bot challenge"
                )
            return {"title": "Retried", "webpage_url": "https://example.com/x"}

        def process_ie_result(self, info, download=False):  # noqa: ARG002
            return info

    tmp = Path(tempfile.mkdtemp(prefix="tf-retry-"))
    out = tmp / "Retried.mp3"
    out.write_bytes(b"x" * 32)
    settings = Settings()
    settings.set("output_dir", str(tmp))
    settings.set("cookies_browser", "none")
    settings.set("cookies_file", "")
    job = Job(url="https://example.com/x", fmt="mp3", kind="audio")

    try:
        yt_dlp.YoutubeDL = FakeYDL
        core.find_ffmpeg = lambda _p="": "ffmpeg"
        manager = DownloadManager(settings)
        manager._resolve_output = lambda *_a, **_k: out
        manager._download(job)
    finally:
        yt_dlp.YoutubeDL = original_ydl
        core.find_ffmpeg = original_ffmpeg

    assert job.status == "done", (job.status, job.error)
    assert len(FakeYDL.calls) == 2, FakeYDL.calls
    assert "extractor_args" not in FakeYDL.calls[0], FakeYDL.calls[0]
    args = FakeYDL.calls[1].get("extractor_args") or {}
    assert args.get("generic", {}).get("impersonate") == [""], args
    print("download bot-check retry ok (2 attempts, impersonation args set)")


def check_youtube_attempts() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="tf-yt-"))
    cookie_file = tmp / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    snapshot = {
        "cookies_file": str(cookie_file),
        "cookies_browser": "vivaldi",
        "cookie_file_override": "",
    }

    assert is_youtube_url("https://www.youtube.com/watch?v=abc"), "youtube.com"
    assert is_youtube_url("https://youtu.be/abc"), "youtu.be"
    assert is_youtube_url("https://music.youtube.com/watch?v=abc"), "music"
    assert is_youtube_url("https://www.youtube-nocookie.com/embed/abc"), "nocookie"
    assert not is_youtube_url("https://vimeo.com/123"), "vimeo"
    assert not is_youtube_url("https://notyoutube.com/watch?v=abc"), "lookalike"

    opts = {"quiet": True, "noplaylist": True}
    attempts, youtube = build_attempts(
        opts, snapshot, "https://www.youtube.com/watch?v=abc"
    )
    assert youtube, attempts
    assert len(attempts) >= 2, attempts
    assert not has_cookie_options(attempts[0]), attempts[0]
    assert attempts[1].get("cookiefile") == str(cookie_file), attempts[1]

    # Every other site keeps its cookies on the first attempt.
    other, is_yt = build_attempts(opts, snapshot, "https://vimeo.com/123")
    assert not is_yt, other
    assert other[0].get("cookiefile") == str(cookie_file), other[0]

    assert has_playable_media({"formats": [{"format_id": "18"}]})
    assert has_playable_media({"url": "https://example.com/a.mp4"})
    assert not has_playable_media({"title": "youtube video #abc"})
    assert not has_playable_media({})

    assert "unavailable" in _friendly_error(
        "ERROR: Requested format is not available"
    ).lower()
    assert "unavailable" in _friendly_error("This video is unavailable").lower()
    print("youtube no-cookie-first attempts + unavailable message ok")


def check_size_estimate() -> None:
    duration = 558  # 9:18
    audio_fmt = {
        "format_id": "251",
        "filesize": 8_900_000,
        "asr": 48000,
        "audio_channels": 2,
    }
    info = {"duration": duration, "requested_formats": [audio_fmt]}
    source = selected_source_size(info)
    assert source == 8_900_000, source

    job = Job(url="https://example.com/x", fmt="mp3", kind="audio", duration=duration)
    output, estimated = estimate_output_size(job, info, source)
    assert estimated, (output, estimated)
    assert abs(output - int(duration * 320_000 / 8 * 1.02)) < 10, output

    tracker = ProgressTracker()
    tracker.configure(info, job)
    half = tracker.update({
        "info_dict": {"format_id": "251"},
        "total_bytes": source,
        "downloaded_bytes": source // 2,
    })
    assert half["total"] == output, half
    assert half["downloaded"] == output // 2, half
    assert half["estimated"] is True, half
    assert 49.0 <= half["progress"] <= 51.0, half

    # OPUS keeps the source stream, so its size is not an estimate.
    opus = Job(url="https://example.com/x", fmt="opus", kind="audio", duration=duration)
    opus_size, opus_estimated = estimate_output_size(opus, info, source)
    assert opus_size == source and not opus_estimated, (opus_size, opus_estimated)

    # Two-stream video: progress and size accumulate instead of resetting.
    video_info = {
        "duration": 19,
        "requested_formats": [
            {"format_id": "278", "filesize": 185292},
            {"format_id": "251", "filesize": 252182},
        ],
    }
    video = Job(url="https://example.com/x", fmt="mp4", kind="video", quality="144")
    vtracker = ProgressTracker()
    vtracker.configure(video_info, video)
    first = vtracker.update({
        "info_dict": {"format_id": "278"},
        "total_bytes": 185292,
        "downloaded_bytes": 185292,
    })
    second = vtracker.update({
        "info_dict": {"format_id": "251"},
        "total_bytes": 252182,
        "downloaded_bytes": 126091,
    })
    total = int((185292 + 252182) * 1.01)
    assert first["total"] == total and second["total"] == total, (first, second)
    assert first["progress"] < second["progress"], (first, second)
    assert first["downloaded"] < second["downloaded"], (first, second)
    print("output size estimate + merged progress ok")


def check_window_theme_switch(app: QApplication) -> None:
    from app.window import MainWindow

    settings = Settings()
    settings.set("proxy_url", "http://127.0.0.1:8080")
    window = MainWindow(settings)
    window.show()
    window.switch_page(3)
    app.processEvents()
    assert window.settings_page.theme_combo.count() == len(theme.THEME_ORDER)
    assert window.settings_page.proxy_edit.text() == "http://127.0.0.1:8080"
    assert hasattr(window.settings_page, "cookies_file_edit")
    assert not hasattr(window.home, "relay_btn"), "relay remnants still present"
    citation = window.settings_page.about_citation.text()
    assert "github.com/yt-dlp/yt-dlp" in citation, citation

    window.settings_page.theme_combo.setCurrentIndex(
        window.settings_page.theme_combo.findData("aurora")
    )
    assert wait_for(lambda: theme.CURRENT_THEME == "aurora", 10), theme.CURRENT_THEME
    assert window._current_page == 3, window._current_page
    assert window.settings_page.theme_combo.currentData() == "aurora"
    window.close()
    app.processEvents()
    theme.apply_theme(app, "midnight")
    print("live window theme switch + proxy card + citation ok")


def main() -> int:
    app = QApplication(sys.argv)
    theme.apply_theme(app, "midnight")

    check_status_label(app)
    check_themes(app)
    check_source_labels()
    check_bot_checks()
    check_proxy()
    check_cookies()
    check_cookie_prompt(app)
    check_download_retry()
    check_youtube_attempts()
    check_size_estimate()
    check_window_theme_switch(app)
    print("all theme/proxy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
