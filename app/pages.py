"""Application pages."""

from __future__ import annotations

import re
import time
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .core import (
    AUDIO_FORMATS,
    CHROMIUM_BROWSERS,
    COOKIE_BROWSERS,
    QUALITIES,
    VIDEO_FORMATS,
    DownloadManager,
    FetchWorker,
    FfmpegInstallWorker,
    History,
    Job,
    Settings,
    appdata_dir,
    browser_label,
    browser_cookie_database,
    browser_running,
    cookie_database_locked,
    cookie_snapshot_fresh,
    default_output_dir,
    find_ffmpeg,
    ffmpeg_version,
    format_bytes,
    format_duration,
    format_eta,
    format_label,
    format_speed,
    format_views,
    is_valid_url,
    normalize_url,
    restart_and_export_cookies,
)
from .theme import C, THEME_ORDER, THEMES, display_font, ui_font
from .widgets import (
    ElidedLabel,
    EmptyState,
    FormatCard,
    GlowProgress,
    GradientButton,
    HistoryCard,
    IconButton,
    JobCard,
    ThumbLabel,
    Toast,
    ToggleSwitch,
    hline,
    open_entry_file,
    open_entry_folder,
)


class BasePage(QWidget):
    """Scrollable page with a centred content column."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body.setObjectName("PageBody")
        self.vbox = QVBoxLayout(self.body)
        self.vbox.setContentsMargins(30, 22, 30, 22)
        self.vbox.setSpacing(12)
        self.scroll.setWidget(self.body)
        outer.addWidget(self.scroll)


def header_layout(title: str, subtitle: str, right: QWidget | None = None) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 2)
    row.setSpacing(14)
    col = QVBoxLayout()
    col.setSpacing(1)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    s = QLabel(subtitle)
    s.setObjectName("PageSubtitle")
    col.addWidget(t)
    col.addWidget(s)
    row.addLayout(col)
    row.addStretch()
    if right is not None:
        row.addWidget(right, 0, Qt.AlignmentFlag.AlignBottom)
    return row


def _chip(text: str, kind: str = "normal") -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("ChipSuccess" if kind == "success" else ("ChipWarn" if kind == "warn" else "Chip"))
    return lab


def _ghost(text: str, icon_name: str = "") -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("Ghost")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon_name:
        b.setIcon(icons.icon(icon_name, "#AEB9CC", 14))
        b.setIconSize(QSize(14, 14))
    return b


# Friendly names for common hosts; everything else falls back to the domain.
_SITE_NAMES = {
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "m.youtube.com": "YouTube",
    "music.youtube.com": "YouTube Music",
    "soundcloud.com": "SoundCloud",
    "m.soundcloud.com": "SoundCloud",
    "vimeo.com": "Vimeo",
    "dailymotion.com": "Dailymotion",
    "twitch.tv": "Twitch",
    "instagram.com": "Instagram",
    "tiktok.com": "TikTok",
    "twitter.com": "X",
    "x.com": "X",
    "facebook.com": "Facebook",
    "bandcamp.com": "Bandcamp",
    "spotify.com": "Spotify",
    "bilibili.com": "BiliBili",
    "nicovideo.jp": "niconico",
    "rumble.com": "Rumble",
    "odysee.com": "Odysee",
    "bitchute.com": "BitChute",
}

# Second-level labels used by country-code domains (example.co.uk, site.com.au).
_SLD = {"co", "com", "net", "org", "gov", "edu", "ac", "or", "ne", "go"}


def _source_label(url: str, fallback: str = "SOURCE") -> str:
    """Return a short, human-friendly source name for the URL the user entered."""
    try:
        host = (QUrl(url).host() or "").strip().lower().removeprefix("www.")
    except Exception:  # noqa: BLE001
        host = ""
    if not host:
        return fallback
    for domain, name in _SITE_NAMES.items():
        if host == domain or host.endswith("." + domain):
            return name
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 2:
        name = parts[-2]
        # For example.co.uk / site.com.au take the label before the ccTLD.
        if len(parts) >= 3 and name in _SLD and len(parts[-1]) == 2:
            name = parts[-3]
    else:
        name = parts[0] if parts else ""
    return name.upper() if name else fallback


def _cookie_browser_name(browser: str) -> str:
    return browser_label(browser)


def ensure_cookie_access(parent: QWidget, settings: Settings) -> bool:
    """Make sure the selected browser's cookies can be read.

    Chromium browsers keep an exclusive lock on their cookie database while
    they run. When that happens, offer to briefly close the browser, copy the
    cookies to a temporary Netscape file and reopen it.
    """
    snapshot = settings.snapshot()
    configured = str(snapshot.get("cookies_file") or "").strip()
    if configured and Path(configured).expanduser().is_file():
        return True

    browser = str(snapshot.get("cookies_browser") or "none").strip().lower()
    if browser not in CHROMIUM_BROWSERS:
        return True

    override = str(snapshot.get("cookie_file_override") or "").strip()
    if override and cookie_snapshot_fresh(override):
        # Reuse the snapshot taken during an earlier fetch; asking again would
        # close the browser every single time.
        return True

    database = browser_cookie_database(browser)
    if database is None:
        QMessageBox.warning(
            parent,
            "Browser cookies not found",
            f"TubeForge could not find {_cookie_browser_name(browser)}’s cookie "
            "database.\n\nOpen the browser once, choose another browser in "
            "Settings → Downloads, or select a Netscape cookies.txt file.",
        )
        return False
    if not cookie_database_locked(database):
        return True

    name = _cookie_browser_name(browser)
    running = browser_running(browser)
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Browser cookies are locked")
    box.setText(
        f"{name} is using its cookie database, so Windows will not let TubeForge read it."
    )
    if running:
        box.setInformativeText(
            f"TubeForge can briefly close {name}, copy the cookies it needs and reopen "
            f"{name} automatically. Save anything you are working on in the browser first.\n\n"
            f"You can also close {name} yourself and press Retry, or choose a cookies.txt "
            "file in Settings → Downloads."
        )
        close_button = box.addButton(
            f"Close {name} and continue", QMessageBox.ButtonRole.AcceptRole
        )
    else:
        box.setInformativeText(
            "The database appears to be locked by a background process, but no browser "
            "window was found. Close any background browser processes and press Retry, "
            "or choose a cookies.txt file in Settings → Downloads."
        )
        close_button = None
    retry_button = box.addButton("Retry", QMessageBox.ButtonRole.ActionRole)
    box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    if close_button is not None:
        box.setDefaultButton(close_button)
    else:
        box.setDefaultButton(retry_button)
    box.exec()
    clicked = box.clickedButton()

    if clicked is retry_button:
        if not cookie_database_locked(database):
            return True
        QMessageBox.warning(
            parent,
            "Cookies are still locked",
            f"{name} is still running or still owns its cookie database. "
            f"Close {name} completely and try again.",
        )
        return False
    if close_button is None or clicked is not close_button:
        return False

    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        destination, reopened = restart_and_export_cookies(browser)
        settings.set_runtime("cookie_file_override", str(destination))
        if not reopened:
            QMessageBox.warning(
                parent,
                "Browser not reopened",
                f"TubeForge copied the cookies, but could not reopen {name}. "
                f"Open {name} again manually.",
            )
        return True
    except Exception as exc:  # noqa: BLE001
        QMessageBox.warning(
            parent,
            "Could not read cookies",
            f"TubeForge could not copy cookies from {name}.\n\n{exc}\n\n"
            f"Close {name} completely and retry, or choose a Netscape cookies.txt "
            "file in Settings → Downloads.",
        )
        return False
    finally:
        QApplication.restoreOverrideCursor()



# ---------------------------------------------------------------------------
# Download page
# ---------------------------------------------------------------------------
class HomePage(BasePage):
    download_requested = Signal(dict)
    notify = Signal(str, str)

    def __init__(self, settings: Settings, manager: DownloadManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.manager = manager
        self.meta: dict | None = None
        self._fetch_worker: FetchWorker | None = None
        self._fetch_url = ""
        self._active_id = ""
        self._syncing_path = False
        self.kind = "audio"

        self.vbox.addLayout(
            header_layout("Download", "Paste a link, pick a format, and get your media.")
        )
        self.vbox.addSpacing(2)

        # --- URL bar -----------------------------------------------------
        bar = QFrame()
        bar.setObjectName("UrlBar")
        bar.setFixedHeight(58)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 9, 10, 9)
        bl.setSpacing(10)
        link_icon = QLabel()
        link_icon.setFixedSize(20, 20)
        link_icon.setPixmap(icons.pixmap("link", C["accent3"], 18))
        bl.addWidget(link_icon)
        self.url_edit = QLineEdit()
        self.url_edit.setObjectName("UrlInput")
        self.url_edit.setPlaceholderText("Paste a YouTube link, or any of 1,000+ supported sites…")
        self.url_edit.setClearButtonEnabled(False)
        bl.addWidget(self.url_edit, 1)
        self.paste_btn = _ghost("Paste", "clipboard")
        self.paste_btn.setFixedHeight(34)
        bl.addWidget(self.paste_btn)
        self.fetch_btn = QPushButton("Fetch")
        self.fetch_btn.setObjectName("AccentOutline")
        self.fetch_btn.setFixedHeight(34)
        self.fetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fetch_btn.setIcon(icons.icon("bolt", C["accent3"], 13))
        self.fetch_btn.setIconSize(QSize(13, 13))
        bl.addWidget(self.fetch_btn)
        self.vbox.addWidget(bar)

        self.error_label = QLabel()
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.vbox.addWidget(self.error_label)

        # --- preview -----------------------------------------------------
        self.preview_card = QFrame()
        self.preview_card.setObjectName("Card")
        self.preview_card.setFixedHeight(152)
        pc = QVBoxLayout(self.preview_card)
        pc.setContentsMargins(12, 12, 12, 12)
        pc.setSpacing(0)
        self.preview_stack = QStackedWidget()
        pc.addWidget(self.preview_stack)

        # empty preview
        empty = QWidget()
        el = QHBoxLayout(empty)
        el.setContentsMargins(10, 0, 10, 0)
        el.setSpacing(16)
        badge = QLabel()
        badge.setFixedSize(54, 54)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(icons.pixmap("download", C["accent3"], 22))
        badge.setStyleSheet(
            f"background: {C['accent_soft']}; border: 1px solid {C['accent_border']};"
            "border-radius: 16px;"
        )
        el.addWidget(badge)
        ev = QVBoxLayout()
        ev.setSpacing(2)
        et = QLabel("Paste a link to get started")
        et.setFont(display_font(11.5, QFont.Weight.DemiBold))
        et.setStyleSheet("color: #D7DFEC;")
        es = QLabel("Preview the title, thumbnail and details before downloading. Enter a link and press Fetch.")
        es.setStyleSheet("color: #6F7A92; font-size: 9pt;")
        es.setWordWrap(True)
        ev.addStretch()
        ev.addWidget(et)
        ev.addWidget(es)
        ev.addStretch()
        el.addLayout(ev, 1)
        self.preview_stack.addWidget(empty)

        # loaded preview
        loaded = QWidget()
        ll = QHBoxLayout(loaded)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(15)
        self.preview_thumb = ThumbLabel(220, 124, 10, "play", show_badge=True)
        ll.addWidget(self.preview_thumb)

        info = QVBoxLayout()
        info.setSpacing(4)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.preview_title = QLabel("—")
        self.preview_title.setFont(display_font(13.2, QFont.Weight.DemiBold))
        self.preview_title.setStyleSheet("color: #F0F4FB;")
        self.preview_title.setWordWrap(True)
        self.preview_title.setMaximumHeight(46)
        title_row.addWidget(self.preview_title, 1)
        self.clear_btn = IconButton("close", "#66718A", "#FFFFFF", "#232D40", 28, 13, "Clear preview")
        title_row.addWidget(self.clear_btn, 0, Qt.AlignmentFlag.AlignTop)
        info.addLayout(title_row)
        self.preview_meta = QLabel("")
        self.preview_meta.setStyleSheet("color: #8B95AB; font-size: 9pt;")
        info.addWidget(self.preview_meta)
        info.addStretch()
        chips = QHBoxLayout()
        chips.setSpacing(6)
        self.chip_source = _chip("YouTube")
        self.chip_info = _chip("—")
        self.chip_status = _chip("Ready", "success")
        chips.addWidget(self.chip_source)
        chips.addWidget(self.chip_info)
        chips.addWidget(self.chip_status)
        self.chip_playlist = _chip("Playlist · first item", "warn")
        self.chip_playlist.hide()
        chips.addWidget(self.chip_playlist)
        chips.addStretch()
        info.addLayout(chips)
        ll.addLayout(info, 1)
        self.preview_stack.addWidget(loaded)
        self.preview_stack.setCurrentIndex(0)
        self.vbox.addWidget(self.preview_card)

        # --- formats -----------------------------------------------------
        fmt_card = QFrame()
        fmt_card.setObjectName("Card")
        fc = QVBoxLayout(fmt_card)
        fc.setContentsMargins(14, 12, 14, 12)
        fc.setSpacing(9)

        arow = QHBoxLayout()
        arow.setSpacing(7)
        ai = QLabel()
        ai.setPixmap(icons.pixmap("music", C["accent3"], 13))
        arow.addWidget(ai)
        al = QLabel("AUDIO")
        al.setObjectName("SectionLabel")
        arow.addWidget(al)
        arow.addStretch()
        ah = QLabel("MP3 · FLAC · WAV · OPUS · M4A")
        ah.setObjectName("Hint")
        arow.addWidget(ah)
        fc.addLayout(arow)

        self.format_group = QButtonGroup(self)
        self.format_group.setExclusive(True)
        self.cards: dict[str, FormatCard] = {}
        audio_row = QHBoxLayout()
        audio_row.setSpacing(8)
        for data in AUDIO_FORMATS:
            card = FormatCard(data, C["accent"])
            audio_row.addWidget(card)
            self.format_group.addButton(card)
            self.cards[data["id"]] = card
        fc.addLayout(audio_row)
        fc.addWidget(hline())

        vrow = QHBoxLayout()
        vrow.setSpacing(7)
        vi = QLabel()
        vi.setPixmap(icons.pixmap("video", C["accent2"], 13))
        vrow.addWidget(vi)
        vl = QLabel("VIDEO")
        vl.setObjectName("SectionLabel")
        vrow.addWidget(vl)
        vrow.addStretch()
        vh = QLabel("Mixed with best audio")
        vh.setObjectName("Hint")
        vrow.addWidget(vh)
        fc.addLayout(vrow)

        video_row = QHBoxLayout()
        video_row.setSpacing(8)
        for data in VIDEO_FORMATS:
            card = FormatCard(data, C["accent2"])
            video_row.addWidget(card)
            self.format_group.addButton(card)
            self.cards[data["id"]] = card
        video_row.addStretch(1)
        qlabel = QLabel("Quality")
        qlabel.setStyleSheet("color: #7E89A0; font-size: 8.5pt; font-weight: 600;")
        video_row.addWidget(qlabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.quality_combo = QComboBox()
        for text, value in QUALITIES:
            self.quality_combo.addItem(text, value)
        self.quality_combo.setFixedWidth(158)
        self.quality_combo.setEnabled(False)
        video_row.addWidget(self.quality_combo, 0, Qt.AlignmentFlag.AlignVCenter)
        fc.addLayout(video_row)
        self.vbox.addWidget(fmt_card)

        # --- destination -------------------------------------------------
        save_card = QFrame()
        save_card.setObjectName("Card")
        save_card.setFixedHeight(46)
        sl = QHBoxLayout(save_card)
        sl.setContentsMargins(12, 6, 8, 6)
        sl.setSpacing(8)
        fi = QLabel()
        fi.setPixmap(icons.pixmap("folder", "#7E89A0", 16))
        sl.addWidget(fi)
        save_lbl = QLabel("Save to")
        save_lbl.setStyleSheet("color: #8B95AB; font-size: 8.8pt;")
        sl.addWidget(save_lbl)
        self.path_edit = QLineEdit()
        self.path_edit.setObjectName("PathInput")
        self.path_edit.setText(str(settings.get("output_dir")))
        sl.addWidget(self.path_edit, 1)
        self.browse_btn = _ghost("Browse")
        self.browse_btn.setFixedHeight(30)
        sl.addWidget(self.browse_btn)
        self.open_folder_btn = IconButton(
            "folder-open", "#7E89A0", "#FFFFFF", "#232D40", 30, 15, "Open download folder"
        )
        sl.addWidget(self.open_folder_btn)
        self.vbox.addWidget(save_card)

        # --- action row --------------------------------------------------
        action = QHBoxLayout()
        action.setSpacing(14)
        av = QVBoxLayout()
        av.setSpacing(1)
        self.selection_label = QLabel("MP3 · 320 kbps · audio only")
        self.selection_label.setFont(ui_font(9.6, QFont.Weight.DemiBold))
        self.selection_label.setStyleSheet("color: #A9B4C8;")
        self.queue_hint = QLabel("Runs in the background — track it on the Queue page.")
        self.queue_hint.setStyleSheet("color: #5E6980; font-size: 8.2pt;")
        av.addWidget(self.selection_label)
        av.addWidget(self.queue_hint)
        action.addLayout(av)
        action.addStretch()
        self.download_btn = GradientButton("Download", "download")
        self.download_btn.setEnabled(False)
        action.addWidget(self.download_btn)
        self.vbox.addLayout(action)

        # --- active download --------------------------------------------
        self.active_card = QFrame()
        self.active_card.setObjectName("ActiveCard")
        ac = QVBoxLayout(self.active_card)
        ac.setContentsMargins(14, 11, 14, 11)
        ac.setSpacing(7)
        top = QHBoxLayout()
        top.setSpacing(9)
        self.active_status = QLabel("Downloading")
        self.active_status.setStyleSheet(f"color: {C['accent2']}; font-size: 8.5pt; font-weight: 700;")
        top.addWidget(self.active_status)
        self.active_title = ElidedLabel("—")
        self.active_title.setStyleSheet("color: #AEB9CC; font-size: 9pt;")
        top.addWidget(self.active_title, 1)
        self.cancel_btn = IconButton("close", "#98A2B6", "#FFFFFF", "#26303F", 26, 13, "Cancel download")
        top.addWidget(self.cancel_btn)
        ac.addLayout(top)
        self.active_progress = GlowProgress(8)
        ac.addWidget(self.active_progress)
        bottom = QHBoxLayout()
        self.active_stage = QLabel("Starting…")
        self.active_stage.setStyleSheet("color: #6F7A92; font-size: 8.2pt;")
        bottom.addWidget(self.active_stage)
        bottom.addStretch()
        self.active_stats = QLabel("")
        self.active_stats.setStyleSheet("color: #7E89A0; font-size: 8.2pt;")
        bottom.addWidget(self.active_stats)
        ac.addLayout(bottom)
        self.active_card.hide()
        self.vbox.addWidget(self.active_card)
        self.vbox.addStretch(1)

        # --- wiring ------------------------------------------------------
        self.cards["mp3"].setChecked(True)
        self.format_group.buttonClicked.connect(self._on_format_changed)
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        self.url_edit.textChanged.connect(self._on_url_changed)
        self.url_edit.returnPressed.connect(self.fetch)
        self.paste_btn.clicked.connect(self._paste)
        self.fetch_btn.clicked.connect(self.fetch)
        self.download_btn.clicked.connect(self._download)
        self.clear_btn.clicked.connect(self._clear_preview)
        self.browse_btn.clicked.connect(self._browse)
        self.path_edit.editingFinished.connect(self._save_path)
        self.open_folder_btn.clicked.connect(lambda: self._open_output_folder())
        self.cancel_btn.clicked.connect(self._cancel_active)

        self.settings.changed.connect(self._sync_settings)
        self.manager.job_started.connect(self._on_started)
        self.manager.job_meta.connect(self._on_meta)
        self.manager.job_progress.connect(self._on_progress)
        self.manager.job_stage.connect(self._on_stage)
        self.manager.job_done.connect(self._on_done)
        self.manager.job_failed.connect(self._on_failed)
        self.manager.job_cancelled.connect(self._on_cancelled)

    # -- url / fetch ------------------------------------------------------
    def _on_url_changed(self, text: str) -> None:
        self.download_btn.setEnabled(is_valid_url(text))
        if self.error_label.isVisible():
            self.error_label.hide()

    def _paste(self) -> None:
        from PySide6.QtWidgets import QApplication

        text = QApplication.clipboard().text().strip()
        if not text:
            self.notify.emit("Clipboard is empty.", "info")
            return
        self.url_edit.setText(text.splitlines()[0])
        self.fetch()

    def _show_error(self, text: str) -> None:
        self.error_label.setText(text)
        self.error_label.show()

    def fetch(self) -> None:
        url = normalize_url(self.url_edit.text())
        if not url or not is_valid_url(url):
            self._show_error("That doesn't look like a valid link. Try a full URL such as https://youtube.com/watch?v=…")
            return
        if not ensure_cookie_access(self, self.settings):
            return
        if self._fetch_worker and self._fetch_worker.isRunning():
            return
        self.url_edit.setText(url)
        self.error_label.hide()
        self._clear_preview(keep_url=True)
        self._fetch_url = url
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Fetching…")
        self.paste_btn.setEnabled(False)
        worker = FetchWorker(url, self.settings)
        self._fetch_worker = worker
        worker.done.connect(self._fetch_done)
        worker.failed.connect(self._fetch_failed)
        worker.finished.connect(self._fetch_finished)
        worker.start()

    def _fetch_finished(self) -> None:
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch")
        self.paste_btn.setEnabled(True)
        if self._fetch_worker:
            self._fetch_worker.deleteLater()
            self._fetch_worker = None

    def _fetch_done(self, info: dict) -> None:
        self.meta = info
        self.preview_title.setText(info.get("title") or "Untitled")
        bits = []
        if info.get("uploader"):
            bits.append(info["uploader"])
        if info.get("duration"):
            bits.append(format_duration(info["duration"]))
        if info.get("views"):
            bits.append(format_views(info["views"]))
        self.preview_meta.setText("  ·  ".join(bits))
        self.preview_thumb.set_url(info.get("thumb_url") or "")
        self.chip_source.setText(_source_label(self._fetch_url or ""))
        self.chip_info.setText(format_duration(info.get("duration")) or "Media")
        self.chip_playlist.setVisible(bool(info.get("playlist")))
        self.preview_stack.setCurrentIndex(1)
        if info.get("is_live"):
            self._show_error("This looks like a live stream — download may only capture what plays while connected.")

    def _fetch_failed(self, message: str) -> None:
        self._show_error(message)
        self.notify.emit("Could not fetch media info.", "error")

    def _clear_preview(self, keep_url: bool = False) -> None:
        self.meta = None
        self.preview_stack.setCurrentIndex(0)
        self.preview_title.setText("—")
        self.preview_meta.setText("")
        self.preview_thumb.set_url("")
        self.chip_playlist.hide()
        if not keep_url:
            self.url_edit.clear()
            self.error_label.hide()
            self.download_btn.setEnabled(False)

    # -- format -----------------------------------------------------------
    def _on_format_changed(self, button: FormatCard) -> None:
        fmt = button.data["id"]
        self.kind = "audio" if fmt in {f["id"] for f in AUDIO_FORMATS} else "video"
        if self.kind == "video":
            self.quality_combo.setEnabled(True)
            q = self.quality_combo.currentText()
            self.selection_label.setText(f"{fmt.upper()} · {q} · video + audio")
        else:
            self.quality_combo.setEnabled(False)
            self.selection_label.setText(f"{format_label(fmt, 'audio', 'best')} · audio only")

    def _on_quality_changed(self, _index: int) -> None:
        button = self.format_group.checkedButton()
        if isinstance(button, FormatCard) and button.data["id"] in {f["id"] for f in VIDEO_FORMATS}:
            self.selection_label.setText(
                f"{button.data['id'].upper()} · {self.quality_combo.currentText()} · video + audio"
            )

    def _current_quality(self) -> str:
        data = self.quality_combo.currentData()
        return data or "best"

    # -- download ---------------------------------------------------------
    def _download(self) -> None:
        url = normalize_url(self.url_edit.text())
        if not is_valid_url(url):
            self._show_error("Enter a valid link first.")
            return
        if not ensure_cookie_access(self, self.settings):
            return
        out = Path(self.settings.get("output_dir") or default_output_dir()).expanduser()
        try:
            out.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            self.notify.emit(f"Cannot create output folder: {exc}", "error")
            return

        button = self.format_group.checkedButton()
        if not isinstance(button, FormatCard):
            return
        fmt = button.data["id"]
        kind = "audio" if fmt in {f["id"] for f in AUDIO_FORMATS} else "video"
        quality = self._current_quality() if kind == "video" else "best"
        meta = self.meta if (self.meta and (self.meta.get("webpage_url") == url or self._fetch_url == url)) else {}
        payload = {
            "url": url,
            "fmt": fmt,
            "kind": kind,
            "quality": quality,
            "title": meta.get("title") or "Preparing download…",
            "uploader": meta.get("uploader") or "",
            "duration": meta.get("duration") or 0,
            "thumb_url": meta.get("thumb_url") or "",
        }
        self.download_requested.emit(payload)
        self.notify.emit(f"Added to queue · {format_label(fmt, kind, quality)}", "success")

    def _browse(self) -> None:
        start = self.settings.get("output_dir") or default_output_dir()
        folder = QFileDialog.getExistingDirectory(self, "Choose download folder", start)
        if folder:
            self.settings.set("output_dir", folder)
            self.path_edit.setText(folder)
            self.notify.emit("Download folder updated.", "success")

    def _save_path(self) -> None:
        if self._syncing_path:
            return
        text = self.path_edit.text().strip().strip('"')
        if not text:
            self.path_edit.setText(self.settings.get("output_dir"))
            return
        try:
            Path(text).expanduser().mkdir(parents=True, exist_ok=True)
        except Exception:
            self.notify.emit("That folder cannot be created.", "error")
            self.path_edit.setText(self.settings.get("output_dir"))
            return
        self.settings.set("output_dir", text)

    def _sync_settings(self) -> None:
        path = str(self.settings.get("output_dir"))
        if self.path_edit.text() != path:
            self._syncing_path = True
            self.path_edit.setText(path)
            self._syncing_path = False

    def _open_output_folder(self) -> None:
        out = self.settings.get("output_dir") or default_output_dir()
        Path(out).mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(out))

    # -- active job -------------------------------------------------------
    def _on_started(self, job: Job) -> None:
        self._active_id = job.id
        self.active_card.show()
        self.active_status.setText("Downloading")
        self.active_status.setStyleSheet(f"color: {C['accent2']}; font-size: 8.5pt; font-weight: 700;")
        self.active_title.setText(job.title)
        self.active_stage.setText("Starting…")
        self.active_stats.setText("")
        self.active_progress.setValue(0)
        self.active_progress.setActive(True)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.set_icon("close", "#98A2B6")

    def _on_meta(self, job_id: str, info: dict) -> None:
        if job_id == self._active_id:
            if info.get("title"):
                self.active_title.setText(info["title"])

    def _on_progress(self, job_id: str, data: dict) -> None:
        if job_id != self._active_id:
            return
        pct = float(data.get("progress") or 0)
        self.active_progress.setValue(pct)
        stage = data.get("stage") or "Downloading…"
        self.active_stage.setText(stage)
        bits = []
        if data.get("speed"):
            bits.append(format_speed(data["speed"]))
        if data.get("eta"):
            bits.append(f"ETA {format_eta(data['eta'])}")
        if data.get("total"):
            total_text = format_bytes(data.get("total"))
            if data.get("estimated"):
                total_text = f"~{total_text}"
            bits.append(f"{format_bytes(data.get('downloaded'))} / {total_text}")
        self.active_stats.setText("  ·  ".join(bits))

    def _on_stage(self, job_id: str, stage: str) -> None:
        if job_id != self._active_id:
            return
        self.active_stage.setText(stage)
        if stage == "Processing…":
            self.active_status.setText("Processing")
            self.active_status.setStyleSheet(f"color: {C['warning']}; font-size: 8.5pt; font-weight: 700;")
            self.active_progress.setActive(False)
        elif stage == "Downloading…":
            self.active_status.setText("Downloading")
            self.active_status.setStyleSheet(f"color: {C['accent2']}; font-size: 8.5pt; font-weight: 700;")
            self.active_progress.setActive(True)

    def _on_done(self, job: Job) -> None:
        if job.id != self._active_id:
            return
        self.active_status.setText("Saved")
        self.active_status.setStyleSheet(f"color: {C['success']}; font-size: 8.5pt; font-weight: 700;")
        self.active_progress.setValue(100)
        self.active_progress.setActive(False)
        self.active_stage.setText(format_bytes(job.filesize) if job.filesize else "Complete")
        self.active_stats.setText("")
        self.cancel_btn.setEnabled(False)
        QTimer.singleShot(1600, lambda jid=job.id: self._hide_active(jid))

    def _on_failed(self, job_id: str, message: str) -> None:
        if job_id == self._active_id:
            self.active_card.hide()
            self.active_progress.setActive(False)
            self._active_id = ""

    def _on_cancelled(self, job_id: str) -> None:
        if job_id == self._active_id:
            self.active_card.hide()
            self.active_progress.setActive(False)
            self._active_id = ""

    def _hide_active(self, job_id: str) -> None:
        if job_id == self._active_id:
            self.active_card.hide()
            self._active_id = ""

    def _cancel_active(self) -> None:
        if not self._active_id:
            return
        self.manager.cancel(self._active_id)
        self.active_status.setText("Cancelling…")
        self.active_status.setStyleSheet(f"color: {C['muted']}; font-size: 8.5pt; font-weight: 700;")
        self.cancel_btn.setEnabled(False)


# ---------------------------------------------------------------------------
# Queue page
# ---------------------------------------------------------------------------
class QueuePage(BasePage):
    notify = Signal(str, str)
    count_changed = Signal(int)

    def __init__(self, settings: Settings, manager: DownloadManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.manager = manager
        self.cards: dict[str, JobCard] = {}
        self._active = 0

        self.clear_btn = _ghost("Clear finished", "trash")
        self.vbox.addLayout(
            header_layout("Queue", "Downloads run one at a time. Queue up as many as you like.", self.clear_btn)
        )
        self.vbox.addSpacing(2)

        self.summary = QLabel("No active downloads")
        self.summary.setStyleSheet("color: #6F7A92; font-size: 9pt;")
        self.vbox.addWidget(self.summary)

        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(9)
        self.card_container = QWidget()
        self.card_container.setLayout(self.list_box)
        self.list_box.addStretch(1)
        self.vbox.addWidget(self.card_container)

        self.empty = EmptyState(
            "queue",
            "Your queue is empty",
            "Downloads you start will line up here with live progress, speed and status.",
            C["accent"],
        )
        self.empty.setMinimumHeight(280)
        self.vbox.addWidget(self.empty)
        self.vbox.addStretch(1)

        self.clear_btn.clicked.connect(self._clear_finished)
        manager.job_started.connect(self._on_started)
        manager.job_meta.connect(self._on_meta)
        manager.job_progress.connect(self._on_progress)
        manager.job_stage.connect(self._on_stage)
        manager.job_done.connect(self._on_done)
        manager.job_failed.connect(self._on_failed)
        manager.job_cancelled.connect(self._on_cancelled)
        self._sync_summary()

    def _ensure_card(self, job: Job) -> JobCard:
        card = self.cards.get(job.id)
        if card is None:
            card = JobCard(job)
            card.action_requested.connect(self._on_action)
            self.cards[job.id] = card
            self.list_box.insertWidget(self.list_box.count() - 1, card)
        card.update_job(job)
        self._sync_summary()
        return card

    def add_job(self, job: Job) -> None:
        """Register a freshly queued job immediately (before it starts)."""
        self._ensure_card(job)

    def _on_started(self, job: Job) -> None:
        self._ensure_card(job)

    def _on_meta(self, job_id: str, info: dict) -> None:
        card = self.cards.get(job_id)
        if not card:
            return
        for key in ("title", "uploader", "duration", "thumb_url"):
            if info.get(key):
                setattr(card.job, key, info[key])
        card.update_job(card.job)

    def _on_progress(self, job_id: str, data: dict) -> None:
        card = self.cards.get(job_id)
        if not card:
            return
        job = card.job
        job.progress = float(data.get("progress") or 0)
        job.speed = data.get("speed") or 0
        job.eta = data.get("eta") or 0
        job.downloaded = data.get("downloaded") or 0
        job.total = data.get("total") or 0
        job.total_estimated = bool(data.get("estimated"))
        job.status = "downloading"
        card.update_job(job)

    def _on_stage(self, job_id: str, stage: str) -> None:
        card = self.cards.get(job_id)
        if not card:
            return
        card.job.stage = stage
        idle_stages = ("", "Downloading…", "Contacting site…", "Starting…")
        if stage == "Done":
            card.job.status = "done"
            card.update_job(card.job)
        elif stage and stage not in idle_stages:
            card.job.status = "processing"
            card.update_job(card.job)

    def _on_done(self, job: Job) -> None:
        card = self.cards.get(job.id)
        if card:
            card.job = job
            card.update_job(job)
        self._sync_summary()

    def _on_failed(self, job_id: str, message: str) -> None:
        card = self.cards.get(job_id)
        if card:
            card.job.status = "error"
            card.job.error = message
            card.update_job(card.job)
        self._sync_summary()

    def _on_cancelled(self, job_id: str) -> None:
        card = self.cards.get(job_id)
        if card:
            card.job.status = "cancelled"
            card.update_job(card.job)
        self._sync_summary()

    def _on_action(self, job_id: str, action: str) -> None:
        card = self.cards.get(job_id)
        if not card:
            return
        if action == "cancel":
            self.manager.cancel(job_id)
        elif action == "folder":
            from .widgets import open_folder

            open_folder(card.job.filepath or self.settings.data.get("output_dir", ""))
        elif action == "open":
            from .widgets import open_folder, open_path

            if card.job.filepath:
                if Path(card.job.filepath).exists():
                    open_path(card.job.filepath)
                else:
                    open_folder(card.job.filepath)
        elif action == "retry":
            if not ensure_cookie_access(self, self.settings):
                return
            old = card.job
            job = Job(
                url=old.url,
                fmt=old.fmt,
                kind=old.kind,
                quality=old.quality,
                title=old.title or "Preparing download…",
                uploader=old.uploader,
                duration=old.duration,
                thumb_url=old.thumb_url,
            )
            self._ensure_card(job)
            self.manager.enqueue(job)
            self.notify.emit("Retrying download…", "info")
        elif action == "dismiss":
            self._remove_card(job_id)

    def _remove_card(self, job_id: str) -> None:
        card = self.cards.pop(job_id, None)
        if card:
            card.setParent(None)
            card.deleteLater()
            self._sync_summary()

    def _clear_finished(self) -> None:
        for job_id, card in list(self.cards.items()):
            if card.job.status in ("done", "error", "cancelled"):
                self._remove_card(job_id)
        self._sync_summary()

    def _sync_summary(self) -> None:
        active = sum(1 for c in self.cards.values() if c.job.status in ("queued", "downloading", "processing"))
        total = len(self.cards)
        self.empty.setVisible(total == 0)
        self.card_container.setVisible(total > 0)
        if total == 0:
            self.summary.setText("No active downloads")
        elif active:
            self.summary.setText(
                f"{active} active  ·  {total} in this session  ·  one download at a time"
            )
        else:
            self.summary.setText(f"{total} finished  ·  history keeps a copy of completed files")
        self.count_changed.emit(active)


# ---------------------------------------------------------------------------
# History page
# ---------------------------------------------------------------------------
class HistoryPage(BasePage):
    notify = Signal(str, str)

    def __init__(self, history: History, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.history = history
        self.clear_btn = QPushButton("Clear history")
        self.clear_btn.setObjectName("DangerGhost")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vbox.addLayout(
            header_layout("History", "Everything you've downloaded, ready to open again.", self.clear_btn)
        )
        self.vbox.addSpacing(2)

        self.info = QLabel("")
        self.info.setStyleSheet("color: #6F7A92; font-size: 9pt;")
        self.vbox.addWidget(self.info)

        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(8)
        self.container = QWidget()
        self.container.setLayout(self.list_box)
        self.vbox.addWidget(self.container)
        self.empty = EmptyState(
            "history",
            "Nothing here yet",
            "Completed downloads will appear here so you can jump back to them.",
            C["accent2"],
        )
        self.empty.setMinimumHeight(280)
        self.vbox.addWidget(self.empty)
        self.vbox.addStretch(1)

        self.clear_btn.clicked.connect(self._clear)
        history.changed.connect(self.rebuild)
        self.rebuild()

    def rebuild(self) -> None:
        while self.list_box.count():
            item = self.list_box.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        items = self.history.items
        self.info.setText(f"{len(items)} item{'s' if len(items) != 1 else ''}" if items else "")
        self.empty.setVisible(not items)
        self.container.setVisible(bool(items))
        for entry in items[:200]:
            card = HistoryCard(entry)
            card.open_file.connect(self._open_file)
            card.open_folder.connect(self._open_folder)
            card.remove.connect(self._remove)
            self.list_box.addWidget(card)
        self.list_box.addStretch(1)

    def _open_file(self, entry: dict) -> None:
        path = entry.get("filepath") or ""
        if path and Path(path).exists():
            open_entry_file(entry)
        else:
            open_entry_folder(entry)
            self.notify.emit("The original file is gone — opened its folder instead.", "info")

    def _open_folder(self, entry: dict) -> None:
        open_entry_folder(entry)

    def _remove(self, entry: dict) -> None:
        self.history.remove(entry.get("id") or "")

    def _clear(self) -> None:
        if not self.history.items:
            return
        box = QMessageBox(self)
        box.setWindowTitle("Clear history")
        box.setText("Remove every item from your download history?")
        box.setInformativeText("Files on disk will not be deleted.")
        box.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes)
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.notify.emit("History cleared.", "info")


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------
class SettingsPage(BasePage):
    notify = Signal(str, str)
    ffmpeg_status = Signal(bool, str)

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._installer: FfmpegInstallWorker | None = None
        self._sync_guard = False

        self.vbox.addLayout(header_layout("Settings", "Tune where files go, how they're saved, and the engine."))
        self.vbox.addSpacing(2)

        # Appearance ------------------------------------------------------
        theme_card, theme_lay = self._section(
            "Appearance", "Colour palette for the whole app. Changes apply instantly."
        )
        self.theme_combo = QComboBox()
        for theme_id in THEME_ORDER:
            self.theme_combo.addItem(THEMES[theme_id]["name"], theme_id)
        current_theme = str(settings.get("theme") or THEME_ORDER[0])
        if self.theme_combo.findData(current_theme) < 0:
            current_theme = THEME_ORDER[0]
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(current_theme))
        self.theme_combo.setFixedWidth(220)
        theme_lay.addLayout(
            self._row(
                "Theme",
                "Eight palettes — six colourful and two monochrome.",
                self.theme_combo,
            )
        )
        self.theme_hint = QLabel(THEMES[current_theme]["description"])
        self.theme_hint.setObjectName("Hint")
        self.theme_hint.setWordWrap(True)
        theme_lay.addWidget(self.theme_hint)
        self.vbox.addWidget(theme_card)

        # Output ----------------------------------------------------------
        out_card, out_lay = self._section("Output", "Where finished downloads are written.")
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.out_edit = QLineEdit(str(settings.get("output_dir")))
        self.out_edit.setPlaceholderText(default_output_dir())
        path_row.addWidget(self.out_edit, 1)
        browse = _ghost("Browse", "folder")
        browse.clicked.connect(self._browse_output)
        path_row.addWidget(browse)
        open_btn = _ghost("Open", "external")
        open_btn.clicked.connect(self._open_output)
        path_row.addWidget(open_btn)
        out_lay.addLayout(path_row)

        self.template_edit = QLineEdit(str(settings.get("template")))
        self.template_edit.setPlaceholderText("%(title)s.%(ext)s")
        out_lay.addWidget(QLabel("File name template"))
        out_lay.addWidget(self.template_edit)
        hint = QLabel("Use %(title)s, %(uploader)s or %(id)s. Folders work too — e.g. %(uploader)s/%(title)s.%(ext)s")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        out_lay.addWidget(hint)
        self.vbox.addWidget(out_card)

        # Downloads -------------------------------------------------------
        dl_card, dl_lay = self._section("Downloads", "Behaviour of the download engine.")
        self.ipv4_toggle = ToggleSwitch()
        self.ipv4_toggle.setChecked(bool(settings.get("force_ipv4")))
        dl_lay.addLayout(
            self._row(
                "Force IPv4",
                "Recommended. Fixes stalls and connection resets on some networks and VPNs.",
                self.ipv4_toggle,
            )
        )
        dl_lay.addWidget(hline())
        self.thumb_toggle = ToggleSwitch()
        self.thumb_toggle.setChecked(bool(settings.get("embed_thumbnail")))
        dl_lay.addLayout(
            self._row("Embed cover art", "Adds the thumbnail as cover art where the format supports it.", self.thumb_toggle)
        )
        dl_lay.addWidget(hline())
        self.meta_toggle = ToggleSwitch()
        self.meta_toggle.setChecked(bool(settings.get("embed_metadata")))
        dl_lay.addLayout(self._row("Write metadata", "Stores title, artist and upload date in the file.", self.meta_toggle))
        dl_lay.addWidget(hline())

        self.cookies_combo = QComboBox()
        for browser in COOKIE_BROWSERS:
            self.cookies_combo.addItem("Don't use cookies" if browser == "none" else browser.title(), browser)
        idx = max(0, self.cookies_combo.findData(settings.get("cookies_browser")))
        self.cookies_combo.setCurrentIndex(idx)
        self.cookies_combo.setFixedWidth(180)
        dl_lay.addLayout(
            self._row(
                "Browser cookies",
                "Use your signed-in browser to access private, age-restricted or members-only media.",
                self.cookies_combo,
            )
        )
        dl_lay.addWidget(hline())
        cookie_file_box = QWidget()
        cookie_file_row = QHBoxLayout(cookie_file_box)
        cookie_file_row.setContentsMargins(0, 0, 0, 0)
        cookie_file_row.setSpacing(6)
        self.cookies_file_edit = QLineEdit()
        self.cookies_file_edit.setReadOnly(True)
        self.cookies_file_edit.setPlaceholderText("No cookie file selected")
        self.cookies_file_edit.setMinimumWidth(250)
        cookie_file_row.addWidget(self.cookies_file_edit, 1)
        browse_cookies = _ghost("Browse", "folder")
        browse_cookies.clicked.connect(self._browse_cookies)
        cookie_file_row.addWidget(browse_cookies)
        clear_cookies = _ghost("Clear")
        clear_cookies.clicked.connect(self._clear_cookies)
        cookie_file_row.addWidget(clear_cookies)
        dl_lay.addLayout(
            self._row(
                "Cookie file",
                "Optional Netscape cookies.txt export. Overrides browser cookies and "
                "works even while the browser is open.",
                cookie_file_box,
            )
        )
        self.vbox.addWidget(dl_card)

        # Proxy -----------------------------------------------------------
        proxy_card, proxy_lay = self._section(
            "Proxy",
            "Route downloads through a proxy when a site is blocked in your region.",
        )
        self.proxy_edit = QLineEdit(str(settings.get("proxy_url") or ""))
        self.proxy_edit.setPlaceholderText("http://127.0.0.1:8080 or socks5://127.0.0.1:1080")
        self.proxy_edit.setMinimumWidth(340)
        proxy_lay.addLayout(
            self._row(
                "Proxy address",
                "Optional. HTTP, HTTPS or SOCKS5 — used by the yt-dlp engine for fetching and downloading.",
                self.proxy_edit,
            )
        )
        self.proxy_status = QLabel(
            "Leave blank to connect directly. Example: http://127.0.0.1:7890 "
            "(Clash/V2Ray) or socks5://127.0.0.1:1080 (common SOCKS port)."
        )
        self.proxy_status.setObjectName("Hint")
        self.proxy_status.setWordWrap(True)
        proxy_lay.addWidget(self.proxy_status)
        note = QLabel(
            "A proxy changes the IP address seen by the site, which can bypass "
            "\"not available in your country\" errors. It does not speed up downloads; "
            "a slow proxy can make them slower."
        )
        note.setObjectName("Hint")
        note.setWordWrap(True)
        proxy_lay.addWidget(note)
        self.vbox.addWidget(proxy_card)

        # Tools -----------------------------------------------------------
        tools_card, tools_lay = self._section("Tools", "TubeForge uses ffmpeg to merge and convert media.")
        status_row = QHBoxLayout()
        status_row.setSpacing(11)
        self.ffmpeg_icon = QLabel()
        self.ffmpeg_icon.setFixedSize(38, 38)
        self.ffmpeg_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_row.addWidget(self.ffmpeg_icon)
        sv = QVBoxLayout()
        sv.setSpacing(1)
        self.ffmpeg_title = QLabel("Checking…")
        self.ffmpeg_title.setFont(ui_font(10, QFont.Weight.DemiBold))
        self.ffmpeg_path = ElidedLabel("", color="#6F7A92")
        self.ffmpeg_path.setStyleSheet("font-size: 8pt;")
        self.ffmpeg_path.setFixedHeight(14)
        sv.addWidget(self.ffmpeg_title)
        sv.addWidget(self.ffmpeg_path)
        status_row.addLayout(sv, 1)
        self.locate_btn = _ghost("Locate", "folder-open")
        self.locate_btn.clicked.connect(self._locate_ffmpeg)
        status_row.addWidget(self.locate_btn)
        self.install_btn = QPushButton("Install with winget")
        self.install_btn.setObjectName("AccentOutline")
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.clicked.connect(self._install_ffmpeg)
        status_row.addWidget(self.install_btn)
        tools_lay.addLayout(status_row)
        tools_lay.addWidget(hline())
        self.engine_label = QLabel("yt-dlp engine  ·  loading version…")
        self.engine_label.setStyleSheet("color: #7E89A0; font-size: 8.5pt;")
        tools_lay.addWidget(self.engine_label)
        self.vbox.addWidget(tools_card)

        # About -----------------------------------------------------------
        about_card, about_lay = self._section("About", "A small native studio for downloading media.")
        from .core import APP_VERSION

        about = QLabel(
            f"TubeForge  v{APP_VERSION}\n"
            "Built with PySide6 and the yt-dlp engine.\n"
            "Only download content you have the right to save."
        )
        about.setStyleSheet("color: #7E89A0; font-size: 8.8pt;")
        about_lay.addWidget(about)

        self.about_citation = QLabel(
            'Download engine: <a href="https://github.com/yt-dlp/yt-dlp" '
            f'style="color: {C["accent3"]}; text-decoration: none;">yt-dlp</a> '
            "by the yt-dlp contributors, licensed under the Unlicense. "
            'Source: <a href="https://github.com/yt-dlp/yt-dlp" '
            f'style="color: {C["accent3"]}; text-decoration: none;">github.com/yt-dlp/yt-dlp</a>'
        )
        citation = self.about_citation
        citation.setOpenExternalLinks(True)
        citation.setWordWrap(True)
        citation.setTextFormat(Qt.TextFormat.RichText)
        citation.setStyleSheet("color: #7E89A0; font-size: 8.2pt;")
        about_lay.addWidget(citation)
        about_row = QHBoxLayout()
        about_row.setSpacing(8)
        appdata = _ghost("App data", "folder")
        appdata.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(appdata_dir()))))
        about_row.addWidget(appdata)
        reset = QPushButton("Reset settings")
        reset.setObjectName("DangerGhost")
        reset.clicked.connect(self._reset)
        about_row.addWidget(reset)
        about_row.addStretch()
        about_lay.addLayout(about_row)
        self.vbox.addWidget(about_card)
        self.vbox.addStretch(1)

        # wiring
        self.out_edit.editingFinished.connect(self._save_output)
        self.template_edit.editingFinished.connect(self._save_template)
        self.ipv4_toggle.toggled.connect(lambda v: settings.set("force_ipv4", bool(v)))
        self.thumb_toggle.toggled.connect(lambda v: settings.set("embed_thumbnail", bool(v)))
        self.meta_toggle.toggled.connect(lambda v: settings.set("embed_metadata", bool(v)))
        self.cookies_combo.currentIndexChanged.connect(
            self._save_cookies_browser
        )
        self.theme_combo.currentIndexChanged.connect(self._save_theme)
        self.proxy_edit.editingFinished.connect(self._save_proxy)
        settings.changed.connect(self._sync)
        self.refresh_engine()

    # -- layout helpers ---------------------------------------------------
    def _section(self, title: str, subtitle: str):
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(9)
        t = QLabel(title)
        t.setFont(display_font(11.5, QFont.Weight.DemiBold))
        t.setStyleSheet("color: #EAF0FA;")
        s = QLabel(subtitle)
        s.setStyleSheet("color: #6F7A92; font-size: 8.5pt;")
        s.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(s)
        lay.addSpacing(2)
        return card, lay

    def _row(self, title: str, desc: str, control: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel(title)
        t.setFont(ui_font(9.8, QFont.Weight.DemiBold))
        t.setStyleSheet("color: #DCE4F2;")
        d = QLabel(desc)
        d.setStyleSheet("color: #6F7A92; font-size: 8.2pt;")
        d.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(d)
        row.addLayout(col, 1)
        row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    # -- settings ---------------------------------------------------------
    def _save_theme(self, _index: int) -> None:
        if self._sync_guard:
            return
        theme_id = str(self.theme_combo.currentData() or THEME_ORDER[0])
        theme = THEMES.get(theme_id, THEMES[THEME_ORDER[0]])
        self.theme_hint.setText(theme["description"])
        self.settings.set("theme", theme_id)

    def _save_proxy(self) -> None:
        if self._sync_guard:
            return
        proxy = self.proxy_edit.text().strip()
        if self.settings.get("proxy_url") != proxy:
            self.settings.set("proxy_url", proxy)

    def _save_cookies_browser(self, _index: int) -> None:
        if self._sync_guard:
            return
        browser = self.cookies_combo.currentData()
        self.settings.clear_runtime("cookie_file_override")
        if self.settings.get("cookies_browser") != browser:
            self.settings.set("cookies_browser", browser)

    def _browse_cookies(self) -> None:
        current = str(self.settings.get("cookies_file") or "")
        start = str(Path(current).parent) if current else str(Path.home())
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Choose a Netscape cookies.txt file",
            start,
            "Cookie files (*.txt);;All files (*)",
        )
        if not path:
            return
        self.settings.clear_runtime("cookie_file_override")
        self.settings.set("cookies_file", path)
        self._sync()
        self.notify.emit("Cookie file saved.", "success")

    def _clear_cookies(self) -> None:
        self.settings.clear_runtime("cookie_file_override")
        self.settings.set("cookies_file", "")
        self._sync()
        self.notify.emit("Cookie file cleared.", "info")

    def _save_output(self) -> None:
        if self._sync_guard:
            return
        text = self.out_edit.text().strip().strip('"')
        if not text:
            self.out_edit.setText(str(self.settings.get("output_dir")))
            return
        try:
            Path(text).expanduser().mkdir(parents=True, exist_ok=True)
        except Exception:
            self.notify.emit("That folder cannot be created.", "error")
            return
        self.settings.set("output_dir", text)

    def _save_template(self) -> None:
        text = self.template_edit.text().strip()
        if not text:
            text = "%(title)s.%(ext)s"
        if "%(ext)s" not in text:
            text += ".%(ext)s"
            self.template_edit.setText(text)
        self.settings.set("template", text)

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose download folder", str(self.settings.get("output_dir"))
        )
        if folder:
            self.settings.set("output_dir", folder)
            self.out_edit.setText(folder)

    def _open_output(self) -> None:
        out = Path(str(self.settings.get("output_dir")))
        out.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(out)))

    def _sync(self) -> None:
        self._sync_guard = True
        try:
            self.out_edit.setText(str(self.settings.get("output_dir")))
            self.template_edit.setText(str(self.settings.get("template")))
            theme_id = str(self.settings.get("theme") or THEME_ORDER[0])
            idx = self.theme_combo.findData(theme_id)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
                self.theme_hint.setText(THEMES[theme_id]["description"])
            for widget, key in (
                (self.proxy_edit, "proxy_url"),
                (self.cookies_file_edit, "cookies_file"),
            ):
                value = str(self.settings.get(key) or "")
                if widget.text() != value:
                    widget.setText(value)
        finally:
            self._sync_guard = False

    def refresh_engine(self) -> None:
        try:
            import yt_dlp

            self.engine_label.setText(f"yt-dlp engine  ·  version {yt_dlp.version.__version__}")
        except Exception:
            self.engine_label.setText("yt-dlp engine  ·  version unavailable")
        self._detect_ffmpeg()

    def _detect_ffmpeg(self) -> None:
        path = find_ffmpeg(self.settings.get("ffmpeg_path") or "")
        if path:
            version = ffmpeg_version(path)
            self.ffmpeg_title.setText(f"ffmpeg {version} detected" if version else "ffmpeg detected")
            self.ffmpeg_title.setStyleSheet(f"color: {C['success']};")
            self.ffmpeg_path.setText(path)
            self.ffmpeg_path.setToolTip(path)
            self.ffmpeg_icon.setPixmap(icons.pixmap("check", C["success"], 18))
            self.ffmpeg_icon.setStyleSheet(
                "background: rgba(52, 211, 153, 0.10); border: 1px solid rgba(52, 211, 153, 0.25); border-radius: 11px;"
            )
            self.install_btn.setText("Reinstall")
            self.ffmpeg_status.emit(True, path)
        else:
            self.ffmpeg_title.setText("ffmpeg not found")
            self.ffmpeg_title.setStyleSheet(f"color: {C['warning']};")
            self.ffmpeg_path.setText("Downloading and converting need ffmpeg. Install it below or locate ffmpeg.exe.")
            self.ffmpeg_path.setToolTip("")
            self.ffmpeg_icon.setPixmap(icons.pixmap("alert", C["warning"], 18))
            self.ffmpeg_icon.setStyleSheet(
                "background: rgba(251, 191, 36, 0.10); border: 1px solid rgba(251, 191, 36, 0.25); border-radius: 11px;"
            )
            self.install_btn.setText("Install with winget")
            self.ffmpeg_status.emit(False, "")

    def _locate_ffmpeg(self) -> None:
        start = str(Path(self.settings.get("output_dir")).parent)
        path, _ = QFileDialog.getOpenFileName(self, "Locate ffmpeg.exe", start, "ffmpeg (ffmpeg.exe);;Executables (*.exe)")
        if not path:
            return
        if Path(path).name.lower() != "ffmpeg.exe":
            self.notify.emit("Please choose ffmpeg.exe.", "error")
            return
        self.settings.set("ffmpeg_path", path)
        self._detect_ffmpeg()
        self.notify.emit("ffmpeg location saved.", "success")

    def _install_ffmpeg(self) -> None:
        if self._installer and self._installer.isRunning():
            return
        self.install_btn.setEnabled(False)
        self.install_btn.setText("Installing…")
        self.notify.emit("Installing ffmpeg via winget. This can take a few minutes…", "info")
        worker = FfmpegInstallWorker()
        self._installer = worker
        worker.finished_ok.connect(self._install_done)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _install_done(self, ok: bool, message: str) -> None:
        self.install_btn.setEnabled(True)
        self._installer = None
        self._detect_ffmpeg()
        if ok:
            self.notify.emit("ffmpeg installed successfully.", "success")
        else:
            self.notify.emit("ffmpeg install failed. Use Locate to point at ffmpeg.exe.", "error")

    def _reset(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Reset settings")
        box.setText("Restore all settings to their defaults?")
        box.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes)
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        for key, value in Settings.DEFAULTS.items():
            self.settings.set(key, value)
        self.settings.clear_runtime()
        self.ipv4_toggle.setChecked(bool(self.settings.get("force_ipv4")))
        self.thumb_toggle.setChecked(bool(self.settings.get("embed_thumbnail")))
        self.meta_toggle.setChecked(bool(self.settings.get("embed_metadata")))
        idx = max(0, self.cookies_combo.findData(self.settings.get("cookies_browser")))
        self.cookies_combo.setCurrentIndex(idx)
        self._sync()
        self._detect_ffmpeg()
        self.notify.emit("Settings restored.", "info")
