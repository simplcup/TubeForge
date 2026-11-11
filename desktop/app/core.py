"""Core services: settings, history, thumbnails and the yt-dlp download queue."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

APP_NAME = "TubeForge"
APP_VERSION = "1.0.8"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
# ---------------------------------------------------------------------------
# Format catalogue
# ---------------------------------------------------------------------------
AUDIO_FORMATS = [
    {"id": "mp3", "label": "MP3", "desc": "320 kbps", "tag": "UNIVERSAL"},
    {"id": "flac", "label": "FLAC", "desc": "Lossless", "tag": "LOSSLESS"},
    {"id": "wav", "label": "WAV", "desc": "Uncompressed", "tag": "PCM"},
    {"id": "opus", "label": "OPUS", "desc": "Original quality", "tag": "EFFICIENT"},
    {"id": "m4a", "label": "M4A", "desc": "AAC audio", "tag": "APPLE"},
]

VIDEO_FORMATS = [
    {"id": "mp4", "label": "MP4", "desc": "H.264 video", "tag": "COMPATIBLE"},
    {"id": "webm", "label": "WEBM", "desc": "VP9 · compact", "tag": "WEB"},
    {"id": "mkv", "label": "MKV", "desc": "Any codec", "tag": "FLEXIBLE"},
]

QUALITIES = [
    ("Best available", "best"),
    ("2160p · 4K", "2160"),
    ("1440p · 2K", "1440"),
    ("1080p · Full HD", "1080"),
    ("720p · HD", "720"),
    ("480p", "480"),
    ("360p", "360"),
]

_AUDIO_CODECS = {
    "mp3": ("mp3", "320"),
    "flac": ("flac", "0"),
    "wav": ("wav", "0"),
    "opus": ("opus", "0"),
    "m4a": ("m4a", "0"),
}

COOKIE_BROWSERS = ["none", "chrome", "edge", "firefox", "brave", "opera", "vivaldi"]
CHROMIUM_BROWSERS = {"chrome", "chromium", "edge", "brave", "opera", "vivaldi", "whale"}
BROWSER_LABELS = {
    "chrome": "Chrome",
    "chromium": "Chromium",
    "edge": "Edge",
    "firefox": "Firefox",
    "brave": "Brave",
    "opera": "Opera",
    "vivaldi": "Vivaldi",
    "whale": "Whale",
}
_BROWSER_PROCESSES = {
    "chrome": "chrome.exe",
    "chromium": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "brave": "brave.exe",
    "opera": "opera.exe",
    "vivaldi": "vivaldi.exe",
    "whale": "whale.exe",
}


def format_label(fmt: str, kind: str, quality: str) -> str:
    if kind == "audio":
        desc = next((f["desc"] for f in AUDIO_FORMATS if f["id"] == fmt), "")
        return f"{fmt.upper()} · {desc}"
    q = "Best" if quality in ("", "best", None) else f"{quality}p"
    return f"{fmt.upper()} · {q}"


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------
def appdata_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_output_dir() -> str:
    return str(Path.home() / "Downloads" / APP_NAME)


CACHE_DIR = appdata_dir() / "cache"


def format_bytes(n: Optional[float]) -> str:
    if not n or n <= 0:
        return "—"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return "—"


def format_speed(n: Optional[float]) -> str:
    if not n or n <= 0:
        return ""
    n = float(n)
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if n < 1024 or unit == "GB/s":
            return f"{n:.1f} {unit}" if unit != "B/s" else f"{int(n)} B/s"
        n /= 1024
    return ""


def format_eta(seconds: Optional[float]) -> str:
    if not seconds or seconds <= 0:
        return ""
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def format_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_views(n: Optional[int]) -> str:
    if not n:
        return ""
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B views"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M views"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K views"
    return f"{n} views"


def normalize_url(text: str) -> str:
    text = (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""
    if not text:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        text = "https://" + text
    return text


def is_valid_url(text: str) -> bool:
    url = QUrl(normalize_url(text))
    return url.isValid() and url.scheme() in ("http", "https") and bool(url.host())


def is_youtube_url(text: str) -> bool:
    """True for youtube.com, youtu.be and YouTube Music links."""
    host = (QUrl(normalize_url(text)).host() or "").lower()
    return (
        host == "youtu.be"
        or host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtube-nocookie.com"
        or host.endswith(".youtube-nocookie.com")
    )


def clean_error(message: str) -> str:
    msg = ANSI_RE.sub("", str(message or "")).replace("\r", "\n")
    lines = [ln.strip() for ln in msg.splitlines() if ln.strip()]
    if not lines:
        return "Unknown error"
    text = " ".join(lines[-3:])
    text = re.sub(r"^ERROR:\s*", "", text)
    return text[:700]


# ---------------------------------------------------------------------------
# Browser cookie helpers
# ---------------------------------------------------------------------------
def browser_label(browser: str) -> str:
    key = (browser or "").strip().lower()
    return BROWSER_LABELS.get(key, key.title() or "Browser")


def _chromium_user_data(browser: str) -> Optional[Path]:
    """Return the Chromium-style user-data folder used by *browser*."""
    key = (browser or "").strip().lower()
    if key not in CHROMIUM_BROWSERS:
        return None
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        roaming = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return {
            "chrome": local / "Google" / "Chrome" / "User Data",
            "chromium": local / "Chromium" / "User Data",
            "edge": local / "Microsoft" / "Edge" / "User Data",
            "brave": local / "BraveSoftware" / "Brave-Browser" / "User Data",
            "opera": roaming / "Opera Software" / "Opera Stable",
            "vivaldi": local / "Vivaldi" / "User Data",
            "whale": local / "Naver" / "Naver Whale" / "User Data",
        }.get(key)
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
        return {
            "chrome": base / "Google" / "Chrome",
            "chromium": base / "Chromium",
            "edge": base / "Microsoft Edge",
            "brave": base / "BraveSoftware" / "Brave-Browser",
            "opera": base / "com.operasoftware.Opera",
            "vivaldi": base / "Vivaldi",
            "whale": base / "Naver" / "Whale",
        }.get(key)
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return {
        "chrome": base / "google-chrome",
        "chromium": base / "chromium",
        "edge": base / "microsoft-edge",
        "brave": base / "BraveSoftware" / "Brave-Browser",
        "opera": base / "opera",
        "vivaldi": base / "vivaldi",
        "whale": base / "naver-whale",
    }.get(key)


def browser_cookie_database(browser: str) -> Optional[Path]:
    """Find the newest Cookies SQLite file for a Chromium browser."""
    root = _chromium_user_data(browser)
    if root is None or not root.exists():
        return None

    found: list[Path] = []

    def consider(profile: Path) -> None:
        for rel in (("Network", "Cookies"), ("Cookies",)):
            candidate = profile.joinpath(*rel)
            if candidate.is_file():
                found.append(candidate)

    try:
        # Chromium keeps profiles directly under User Data (Default, Profile 1…).
        for entry in root.iterdir():
            if entry.is_dir():
                consider(entry)
        # Opera stores its profile at the root instead of a profile subfolder.
        consider(root)
    except OSError:
        return None

    if not found:
        return None
    try:
        return max(found, key=lambda path: path.stat().st_mtime)
    except OSError:
        return found[0]


def cookie_database_locked(path: Optional[Path]) -> bool:
    """True when Windows refuses to read the database because a browser owns it."""
    if path is None:
        return False
    try:
        with open(path, "rb") as handle:
            handle.read(1)
        return False
    except PermissionError:
        return True
    except OSError as exc:
        return getattr(exc, "errno", None) in (13, 32)


class CookieAccessError(RuntimeError):
    """Raised when a Chromium browser's cookies cannot be read right now."""


# How long a copied cookie snapshot is reused before TubeForge asks again.
COOKIE_SNAPSHOT_TTL = 30 * 60


def cookie_snapshot_fresh(path: Path | str | None, max_age: float = COOKIE_SNAPSHOT_TTL) -> bool:
    """True when *path* is an existing cookies.txt newer than *max_age* seconds."""
    if not path:
        return False
    try:
        candidate = Path(path)
        return (
            candidate.is_file()
            and (time.time() - candidate.stat().st_mtime) <= max(0.0, max_age)
        )
    except OSError:
        return False


def cookie_lock_message(browser: str) -> str:
    """Friendly explanation for Chromium's exclusive cookie-database lock."""
    name = browser_label(browser)
    return (
        f"{name} is running and keeps an exclusive lock on its cookie database, "
        "so Windows will not let TubeForge read it.\n\n"
        f"Fetch again and choose \u201cClose {name} and continue\u201d so TubeForge can "
        f"copy the cookies and reopen {name} automatically. You can also close {name} "
        "yourself, or choose a Netscape cookies.txt file in Settings \u2192 Downloads."
    )


def browser_cookie_snapshot(browser: str, *, force: bool = False) -> Path:
    """Return a fresh Netscape cookie export for *browser*.

    Chromium-family browsers lock their SQLite cookie database while they run,
    so yt-dlp's own ``cookiesfrombrowser`` path cannot copy it. Export once to a
    temporary cookies.txt instead; that also keeps the original attempt and the
    impersonation retry on exactly the same cookies.
    """
    destination = session_cookie_path(browser)
    database = browser_cookie_database(browser)
    if database is None:
        raise CookieAccessError(
            f"TubeForge could not find {browser_label(browser)}\u2019s cookie database. "
            "Open the browser once, or choose a cookies.txt file in Settings \u2192 Downloads."
        )
    if not force and cookie_snapshot_fresh(destination):
        try:
            current = database.stat().st_mtime <= destination.stat().st_mtime
        except OSError:
            current = True
        if current or cookie_database_locked(database):
            return destination
    if cookie_database_locked(database):
        raise CookieAccessError(cookie_lock_message(browser))
    try:
        return export_browser_cookies(browser, destination)
    except Exception as exc:  # noqa: BLE001 - surface a readable lock message
        if cookie_database_locked(database):
            raise CookieAccessError(cookie_lock_message(browser)) from exc
        raise


def browser_process_name(browser: str) -> str:
    key = (browser or "").strip().lower()
    if os.name == "nt":
        return _BROWSER_PROCESSES.get(key, f"{key}.exe" if key else "")
    return key


def _list_browser_pids(browser: str) -> list[int]:
    name = browser_process_name(browser)
    if not name:
        return []
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH", "/FO", "CSV"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=_CREATE_NO_WINDOW,
            )
        except Exception:  # noqa: BLE001
            return []
        pids: list[int] = []
        for line in (proc.stdout or "").splitlines():
            parts = [part.strip().strip('"') for part in line.split(",")]
            if len(parts) >= 2 and parts[0].lower() == name.lower():
                try:
                    pids.append(int(parts[1]))
                except ValueError:
                    pass
        return pids
    try:
        proc = subprocess.run(
            ["pgrep", "-x", name], capture_output=True, text=True, timeout=8
        )
    except Exception:  # noqa: BLE001
        return []
    return [int(line) for line in (proc.stdout or "").split() if line.isdigit()]


def browser_running(browser: str) -> bool:
    return bool(_list_browser_pids(browser))


def browser_executable(browser: str) -> Optional[str]:
    key = (browser or "").strip().lower()
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA") or "")
        pf = Path(os.environ.get("ProgramFiles") or "")
        pf86 = Path(os.environ.get("ProgramFiles(x86)") or "")
        candidates = {
            "vivaldi": [
                local / "Vivaldi" / "Application" / "vivaldi.exe",
                pf / "Vivaldi" / "Application" / "vivaldi.exe",
            ],
            "chrome": [
                local / "Google" / "Chrome" / "Application" / "chrome.exe",
                pf / "Google" / "Chrome" / "Application" / "chrome.exe",
                pf86 / "Google" / "Chrome" / "Application" / "chrome.exe",
            ],
            "chromium": [local / "Chromium" / "Application" / "chrome.exe"],
            "edge": [
                pf86 / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                pf / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            ],
            "brave": [
                local / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
                pf / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
            ],
            "opera": [
                local / "Programs" / "Opera" / "opera.exe",
                pf / "Opera" / "launcher.exe",
                pf / "Opera" / "opera.exe",
            ],
            "whale": [
                local / "Naver" / "Naver Whale" / "Application" / "whale.exe",
                pf / "Naver" / "Naver Whale" / "Application" / "whale.exe",
            ],
        }.get(key, [])
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    else:
        commands = {
            "chrome": ("google-chrome", "google-chrome-stable", "chrome"),
            "chromium": ("chromium", "chromium-browser"),
            "edge": ("microsoft-edge", "microsoft-edge-stable"),
            "brave": ("brave", "brave-browser"),
            "opera": ("opera",),
            "vivaldi": ("vivaldi", "vivaldi-stable"),
            "whale": ("whale", "naver-whale"),
        }.get(key, (key,))
        for command in commands:
            found = shutil.which(command)
            if found:
                return found
    return None


def _wait_for_browser_exit(browser: str, timeout: float) -> bool:
    deadline = time.monotonic() + max(0.0, timeout)
    while time.monotonic() < deadline:
        if not browser_running(browser):
            return True
        time.sleep(0.2)
    return not browser_running(browser)


def close_browser(browser: str) -> bool:
    """Close *browser* so its cookie database can be read. Returns success."""
    name = browser_process_name(browser)
    if not name or not browser_running(browser):
        return True
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/IM", name],
                capture_output=True,
                timeout=15,
                creationflags=_CREATE_NO_WINDOW,
            )
            if _wait_for_browser_exit(browser, 10):
                return True
            subprocess.run(
                ["taskkill", "/IM", name, "/F"],
                capture_output=True,
                timeout=15,
                creationflags=_CREATE_NO_WINDOW,
            )
            return _wait_for_browser_exit(browser, 5)
        for signal_name in ("-TERM", "-KILL"):
            subprocess.run(
                ["pkill", signal_name, name],
                capture_output=True,
                timeout=10,
            )
            if _wait_for_browser_exit(browser, 8):
                return True
        return not browser_running(browser)
    except Exception:  # noqa: BLE001
        return not browser_running(browser)


def relaunch_browser(browser: str) -> bool:
    """Reopen a Chromium browser after its cookies were copied."""
    exe = browser_executable(browser)
    if not exe:
        return False
    args = [exe]
    if browser in CHROMIUM_BROWSERS:
        # Restore the user's tabs and leave the cookie DB shareable next time.
        args.extend(["--restore-last-session", "--disable-features=LockProfileCookieDatabase"])
    try:
        subprocess.Popen(args, close_fds=True)
        return True
    except OSError:
        return False


def session_cookie_path(browser: str) -> Path:
    return CACHE_DIR / "cookies" / f"{browser}-{os.getpid()}.txt"


def export_browser_cookies(browser: str, destination: Path) -> Path:
    """Write cookies from *browser* to a Netscape cookies.txt file."""
    import yt_dlp

    class _QuietLogger:
        def debug(self, _message: str) -> None:
            pass

        def info(self, _message: str) -> None:
            pass

        def warning(self, _message: str) -> None:
            pass

        def error(self, _message: str) -> None:
            pass

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.unlink(missing_ok=True)
    except OSError:
        pass
    opts = {
        "quiet": True,
        "no_warnings": True,
        "cookiesfrombrowser": (browser,),
        "cookiefile": str(destination),
        "logger": _QuietLogger(),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        _ = ydl.cookiejar
    try:
        size = destination.stat().st_size
    except OSError:
        size = 0
    if size <= 0:
        raise RuntimeError(f"No cookies were found in {browser_label(browser)}.")
    return destination


def restart_and_export_cookies(browser: str) -> tuple[Path, bool]:
    """Close *browser*, export its cookies, then reopen it.

    Returns ``(cookie_file, reopened)``. The caller should use the cookie file
    for the request instead of reading the browser database directly.
    """
    destination = session_cookie_path(browser)
    if not close_browser(browser):
        raise RuntimeError(
            f"TubeForge could not close {browser_label(browser)}. "
            "Close it manually and retry."
        )
    reopened = False
    try:
        export_browser_cookies(browser, destination)
    finally:
        reopened = relaunch_browser(browser)
    return destination, reopened


def prune_session_cookies(max_age_hours: float = 24.0) -> None:
    """Remove cookie snapshots left behind by earlier TubeForge sessions."""
    folder = CACHE_DIR / "cookies"
    if not folder.is_dir():
        return
    cutoff = time.time() - (max_age_hours * 3600)
    try:
        for path in folder.glob("*.txt"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
    except OSError:
        pass


def apply_cookie_options(opts: dict, snapshot: dict) -> None:
    """Add the best available cookie source to yt-dlp options.

    A manual cookies.txt (or the snapshot made by ``ensure_cookie_access``)
    wins. For Chromium browsers we copy cookies to our own file instead of
    handing ``cookiesfrombrowser`` to yt-dlp, because yt-dlp cannot copy the
    locked database while the browser is open.
    """
    opts.pop("cookiesfrombrowser", None)
    cookie_file = str(snapshot.get("cookies_file") or "").strip()
    override = str(snapshot.get("cookie_file_override") or "").strip()
    chosen = ""
    if cookie_file:
        candidate = Path(cookie_file).expanduser()
        if candidate.is_file():
            chosen = str(candidate)
    if not chosen and override:
        candidate = Path(override).expanduser()
        if candidate.is_file() and cookie_snapshot_fresh(candidate):
            chosen = str(candidate)
    if chosen:
        opts["cookiefile"] = chosen
        return
    browser = str(snapshot.get("cookies_browser") or "none").strip().lower()
    if not browser or browser == "none":
        return
    if browser in CHROMIUM_BROWSERS:
        opts["cookiefile"] = str(browser_cookie_snapshot(browser))
        return
    # Firefox keeps its cookie database readable while running.
    opts["cookiesfrombrowser"] = (browser,)


def has_cookie_options(opts: dict) -> bool:
    """True when yt-dlp options carry a browser/cookie-file source."""
    return bool(opts.get("cookiefile") or opts.get("cookiesfrombrowser"))


def has_playable_media(info: dict | None) -> bool:
    """True when extracted metadata actually contains something downloadable."""
    if not info:
        return False
    return bool(
        info.get("formats") or info.get("url") or info.get("requested_formats")
    )


def build_attempts(opts: dict, snapshot: dict, url: str) -> tuple[list[dict], bool]:
    """Return ordered yt-dlp option sets and whether the URL is YouTube.

    YouTube is tried *without* browser cookies first. A signed-in YouTube
    session can receive the SABR-only streaming experiment, which returns
    metadata but zero playable formats even for public videos. Cookies are
    still tried afterwards so private, age-restricted or region-locked videos
    keep working. Other sites use cookies immediately.
    """
    cookie_opts = dict(opts)
    apply_cookie_options(cookie_opts, snapshot)
    youtube = is_youtube_url(url)
    attempts: list[dict] = []

    if youtube and has_cookie_options(cookie_opts):
        plain = dict(opts)
        plain.pop("cookiefile", None)
        plain.pop("cookiesfrombrowser", None)
        attempts.append(plain)
        attempts.append(cookie_opts)
    else:
        attempts.append(cookie_opts)

    if impersonation_available():
        retry_opts = dict(attempts[-1])
        enable_impersonation(retry_opts)
        attempts.append(retry_opts)
    return attempts, youtube


def find_ffmpeg(override: str = "") -> Optional[str]:
    """Locate ffmpeg.exe across PATH, app folders and winget packages."""
    candidates: list[Path] = []
    if override:
        p = Path(override)
        if p.is_dir():
            p = p / "ffmpeg.exe"
        if p.is_file():
            return str(p)

    which = shutil.which("ffmpeg")
    if which:
        candidates.append(Path(which))

    exe_dir = Path(sys.executable).resolve().parent
    roots = [
        Path(getattr(sys, "_MEIPASS", exe_dir)),
        exe_dir,
        Path(__file__).resolve().parents[1],
        appdata_dir(),
        Path(os.environ.get("LOCALAPPDATA", "")) / APP_NAME,
    ]
    for root in roots:
        candidates += [root / "ffmpeg" / "bin" / "ffmpeg.exe", root / "ffmpeg.exe", root / "bin" / "ffmpeg.exe"]

    winget_root = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget_root.exists():
        try:
            candidates += list(winget_root.glob("*FFmpeg*/*/bin/ffmpeg.exe"))
            candidates += list(winget_root.glob("*FFmpeg*/bin/ffmpeg.exe"))
        except OSError:
            pass

    for p in candidates:
        try:
            if p and p.is_file():
                return str(p)
        except OSError:
            continue
    return None


def ffmpeg_version(path: str) -> str:
    if not path:
        return ""
    try:
        out = subprocess.run(
            [path, "-version"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=_CREATE_NO_WINDOW,
        )
        first = (out.stdout or "").splitlines()[0]
        m = re.search(r"ffmpeg version (\d+(?:\.\d+)+)", first)
        return m.group(1) if m else first[:40]
    except Exception:
        return ""


def open_path(path: str) -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    if path and Path(path).exists():
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    elif path:
        folder = str(Path(path).parent)
        if Path(folder).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))


def open_folder(path: str) -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    p = Path(path) if path else None
    if p and p.is_file():
        p = p.parent
    if p and p.exists():
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))


class Settings(QObject):
    changed = Signal()

    DEFAULTS = {
        "output_dir": default_output_dir(),
        "template": "%(title)s.%(ext)s",
        "force_ipv4": True,
        "embed_thumbnail": True,
        "embed_metadata": True,
        "cookies_browser": "none",
        "cookies_file": "",
        "ffmpeg_path": "",
        "theme": "midnight",
        "proxy_url": "",
    }

    def __init__(self) -> None:
        super().__init__()
        self.path = appdata_dir() / "settings.json"
        self.data = dict(self.DEFAULTS)
        self.runtime: dict = {}
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data.update({k: v for k, v in loaded.items() if k in self.DEFAULTS})
        except Exception:
            pass

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        if self.data.get(key) == value:
            return
        self.data[key] = value
        self.save()
        self.changed.emit()

    def snapshot(self) -> dict:
        data = dict(self.data)
        data.update(self.runtime)
        return data

    def set_runtime(self, key: str, value) -> None:
        self.runtime[key] = value

    def clear_runtime(self, key: str | None = None) -> None:
        if key is None:
            self.runtime.clear()
        else:
            self.runtime.pop(key, None)

    def save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
        except Exception:
            pass


class History(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.path = appdata_dir() / "history.json"
        self.items: list[dict] = []
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    self.items = [x for x in loaded if isinstance(x, dict)][:200]
        except Exception:
            self.items = []

    def add(self, entry: dict) -> None:
        entry = dict(entry)
        entry.setdefault("id", uuid.uuid4().hex[:12])
        entry.setdefault("completed_at", time.time())
        self.items.insert(0, entry)
        self.items = self.items[:200]
        self.save()
        self.changed.emit()

    def remove(self, item_id: str) -> None:
        self.items = [x for x in self.items if x.get("id") != item_id]
        self.save()
        self.changed.emit()

    def clear(self) -> None:
        self.items = []
        self.save()
        self.changed.emit()

    def save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.items, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Thumbnail cache (async through QtNetwork, cached to disk)
# ---------------------------------------------------------------------------
class ThumbnailService(QObject):
    loaded = Signal(str, QPixmap)

    def __init__(self) -> None:
        super().__init__()
        self.dir = CACHE_DIR / "thumbs"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.nam = QNetworkAccessManager(self)
        self._memory: dict[str, QPixmap] = {}
        self._pending: set[str] = set()

    def _cache_file(self, url: str) -> Path:
        return self.dir / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".png")

    def cached(self, url: str) -> Optional[QPixmap]:
        if not url:
            return None
        if url in self._memory:
            return self._memory[url]
        path = self._cache_file(url)
        if path.exists():
            pm = QPixmap(str(path))
            if not pm.isNull():
                self._memory[url] = pm
                return pm
        return None

    def get(self, url: str) -> Optional[QPixmap]:
        if not url:
            return None
        pm = self.cached(url)
        if pm is not None:
            return pm
        if url in self._pending:
            return None
        self._pending.add(url)
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader,
                      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36")
        req.setTransferTimeout(20000)
        reply = self.nam.get(req)
        reply.finished.connect(lambda u=url, r=reply: self._on_finished(u, r))
        return None

    def _on_finished(self, url: str, reply) -> None:
        self._pending.discard(url)
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = reply.readAll()
                pm = QPixmap()
                if pm.loadFromData(data) and not pm.isNull():
                    self._memory[url] = pm
                    try:
                        pm.save(str(self._cache_file(url)), "PNG")
                    except Exception:
                        pass
                    self.loaded.emit(url, pm)
        except Exception:
            pass
        finally:
            reply.deleteLater()


_thumbs: Optional[ThumbnailService] = None


def get_thumbs() -> ThumbnailService:
    global _thumbs
    if _thumbs is None:
        _thumbs = ThumbnailService()
    return _thumbs


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
@dataclass
class Job:
    url: str
    fmt: str
    kind: str = "audio"
    quality: str = "best"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    title: str = "Preparing download…"
    uploader: str = ""
    duration: int = 0
    thumb_url: str = ""
    status: str = "queued"          # queued | downloading | processing | done | error | cancelled
    progress: float = 0.0
    speed: float = 0.0
    eta: int = 0
    downloaded: int = 0
    total: int = 0
    total_estimated: bool = False
    filepath: str = ""
    filesize: int = 0
    stage: str = ""
    error: str = ""
    created: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# yt-dlp logger + workers
# ---------------------------------------------------------------------------
_IMPERSONATION_READY: bool | None = None
_BOT_CHECK_RE = re.compile(
    r"cloudflare|anti-bot|not a bot|sign in to confirm|"
    r"attention required|cf-mitigated|challenge|"
    r"http error 403|403 forbidden|access denied|impersonat",
    re.IGNORECASE,
)


def is_bot_check_error(message: str) -> bool:
    """True when an error looks like a site's bot / Cloudflare challenge."""
    return bool(_BOT_CHECK_RE.search(message or ""))


def impersonation_available() -> bool:
    """True when yt-dlp can actually impersonate a browser via curl_cffi.

    yt-dlp only accepts specific curl_cffi releases, so merely finding the
    package on disk is not enough: importing its request handler raises a
    clear error when the installed version is unsupported.
    """
    global _IMPERSONATION_READY
    if _IMPERSONATION_READY is not None:
        return _IMPERSONATION_READY
    try:
        from yt_dlp.networking._curlcffi import CurlCFFIRH

        _IMPERSONATION_READY = bool(
            getattr(CurlCFFIRH, "_SUPPORTED_IMPERSONATE_TARGET_MAP", None)
        )
    except Exception:  # noqa: BLE001
        _IMPERSONATION_READY = False
    return _IMPERSONATION_READY


def enable_impersonation(opts: dict) -> None:
    """Ask yt-dlp's generic extractor to impersonate a real browser.

    Equivalent to the CLI flag ``--extractor-args "generic:impersonate"``.
    """
    args = dict(opts.get("extractor_args") or {})
    generic = dict(args.get("generic") or {})
    generic["impersonate"] = [""]
    args["generic"] = generic
    opts["extractor_args"] = args


class YdlLogger:
    def __init__(self, emit, last_error: list[str]) -> None:
        self._emit = emit
        self._last_error = last_error

    def debug(self, msg: str) -> None:
        msg = ANSI_RE.sub("", str(msg)).strip()
        if not msg or msg.startswith("[debug]"):
            return
        if "[download]" in msg:
            return
        self._emit(msg)

    def info(self, msg: str) -> None:
        self.debug(msg)

    def warning(self, msg: str) -> None:
        self._emit(ANSI_RE.sub("", str(msg)).strip())

    def error(self, msg: str) -> None:
        text = ANSI_RE.sub("", str(msg)).strip()
        if text:
            self._last_error.append(text)
            self._emit(text)


class FetchWorker(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, url: str, settings: Settings) -> None:
        super().__init__()
        self.url = url
        self.settings = settings

    def run(self) -> None:
        import yt_dlp

        s = self.settings.snapshot()
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "skip_download": True,
            # Fetching is metadata-only. A removed/private/region-blocked video
            # has no formats; without this, yt-dlp reports the misleading
            # "Requested format is not available" instead of "unavailable".
            "ignore_no_formats_error": True,
            "socket_timeout": 30,
            "retries": 3,
            "extractor_retries": 3,
        }
        if s.get("force_ipv4"):
            opts["source_address"] = "0.0.0.0"
        proxy = str(s.get("proxy_url") or "").strip()
        if proxy:
            opts["proxy"] = proxy
        browser = str(s.get("cookies_browser") or "none").strip().lower()
        # Never close the browser from this worker thread. ensure_cookie_access
        # has already offered to snapshot locked cookies before the fetch.
        attempts, youtube = build_attempts(opts, s, self.url)

        last_exc: Exception | None = None
        last_message = ""
        info = None
        playlist = False
        try:
            for index, attempt_opts in enumerate(attempts):
                try:
                    with yt_dlp.YoutubeDL(attempt_opts) as ydl:
                        result = ydl.extract_info(self.url, download=False)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    last_message = clean_error(str(exc))
                    if index + 1 < len(attempts) and (
                        youtube or is_bot_check_error(last_message)
                    ):
                        continue
                    raise
                playlist = False
                if result and result.get("_type") == "playlist":
                    entries = [e for e in (result.get("entries") or []) if e]
                    if entries:
                        result = entries[0]
                    playlist = True
                if has_playable_media(result):
                    info = result
                    last_exc = None
                    break
                # Metadata without any playable format (removed video, or the
                # SABR-only experiment for a signed-in session).
                last_message = (
                    "This video is unavailable. It may have been removed, made "
                    "private, age-restricted, or blocked in your region."
                )
                if index + 1 < len(attempts) and youtube:
                    continue
                raise RuntimeError(last_message)
            if info is None:
                if last_exc is not None:
                    raise last_exc
                raise RuntimeError(
                    last_message
                    or "No media information was returned for this link."
                )
            thumb = info.get("thumbnail") or ""
            thumbs = info.get("thumbnails") or []
            if not thumb and thumbs:
                thumb = thumbs[-1].get("url") or ""
            self.done.emit({
                "title": info.get("title") or "Untitled",
                "uploader": info.get("uploader") or info.get("channel") or "",
                "duration": info.get("duration") or 0,
                "views": info.get("view_count") or 0,
                "thumb_url": thumb,
                "webpage_url": info.get("webpage_url") or self.url,
                "is_live": bool(info.get("is_live")),
                "playlist": playlist,
            })
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(_friendly_error(clean_error(str(exc)), browser))


_VIDEO_BITRATES = {
    2160: 18_000_000,
    1440: 10_000_000,
    1080: 5_000_000,
    720: 2_800_000,
    480: 1_400_000,
    360: 800_000,
    240: 450_000,
}


def selected_source_size(info: dict | None) -> int:
    """Sum the sizes of the streams yt-dlp selected for this download."""
    if not info:
        return 0
    duration = float(info.get("duration") or 0)
    total = 0
    for fmt in info.get("requested_formats") or [info]:
        size = fmt.get("filesize") or fmt.get("filesize_approx")
        if not size:
            tbr = fmt.get("tbr") or ((fmt.get("vbr") or 0) + (fmt.get("abr") or 0))
            if tbr and duration:
                size = float(tbr) * 1000.0 / 8.0 * duration
        if not size:
            return 0
        total += int(size)
    return total


def estimate_output_size(
    job: Job, info: dict | None, source_total: int = 0
) -> tuple[int, bool]:
    """Estimate the finished file's size.

    Returns ``(bytes, estimated)``. Audio is re-encoded at a known bitrate, so
    the source stream size is much smaller than the file the user gets (an
    MP3 at 320 kbps is about 2.5x its Opus source). Video is muxed, so the
    selected streams add up to roughly the final size.
    """
    duration = int((info or {}).get("duration") or job.duration or 0)
    if duration <= 0:
        return 0, False

    streams = (info or {}).get("requested_formats") or [(info or {})]
    asr, channels = 44100, 2
    for fmt in streams:
        asr = int(fmt.get("asr") or asr)
        channels = int(fmt.get("audio_channels") or channels)

    codec = (job.fmt or "").lower()
    if job.kind == "audio":
        if codec == "opus":
            # Nothing is re-encoded, so the source stream is the final size.
            return (source_total, False) if source_total else (0, False)
        if codec == "wav":
            return int(duration * asr * channels * 2 * 1.01) + 44, True
        if codec == "flac":
            return int(duration * asr * channels * 2 * 0.55 * 1.02), True
        if codec == "mp3":
            return int(duration * 320_000 / 8 * 1.02), True
        if codec == "m4a":
            return int(duration * 256_000 / 8 * 1.02), True
        return 0, False

    # Video: remuxing keeps the stream payload, so the selected sizes are a
    # good approximation of the finished container.
    if source_total:
        return int(source_total * 1.01), False
    try:
        height = int(job.quality)
    except (TypeError, ValueError):
        height = 0
    bitrate = _VIDEO_BITRATES.get(height)
    if bitrate:
        return int(duration * (bitrate + 128_000) / 8 * 1.02), True
    return 0, False


class ProgressTracker:
    """Turn per-stream yt-dlp progress into one smooth, output-sized bar.

    yt-dlp reports video and audio streams separately. Without this, the
    total jumps between the two streams and the displayed size is the source
    stream rather than the file the user ends up with.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.output_total = 0
        self.estimated = False
        self.stream_totals: dict[str, float] = {}
        self.stream_done: dict[str, float] = {}

    def configure(self, info: dict, job: Job) -> None:
        self.reset()
        duration = float((info or {}).get("duration") or job.duration or 0)
        for fmt in (info or {}).get("requested_formats") or [(info or {})]:
            fid = str(fmt.get("format_id") or "main")
            size = fmt.get("filesize") or fmt.get("filesize_approx") or 0
            if not size:
                tbr = fmt.get("tbr") or ((fmt.get("vbr") or 0) + (fmt.get("abr") or 0))
                if tbr and duration:
                    size = float(tbr) * 1000.0 / 8.0 * duration
            if size:
                self.stream_totals[fid] = float(size)
        source_total = int(sum(self.stream_totals.values()))
        self.output_total, self.estimated = estimate_output_size(job, info, source_total)

    def update(self, data: dict) -> dict:
        info = data.get("info_dict") or {}
        fid = str(info.get("format_id") or info.get("id") or "main")
        total = float(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)
        done = float(data.get("downloaded_bytes") or 0)
        self.stream_done[fid] = done
        if total > 0:
            self.stream_totals[fid] = max(self.stream_totals.get(fid, 0.0), total)

        source_total = sum(self.stream_totals.values())
        source_done = sum(self.stream_done.values())
        if source_total <= 0:
            source_total = total
            source_done = done

        progress = (source_done / source_total * 100.0) if source_total else 0.0
        progress = max(0.0, min(99.0, progress))

        if self.output_total and source_total:
            display_total = self.output_total
            display_done = int(self.output_total * min(1.0, source_done / source_total))
            estimated = self.estimated
        else:
            display_total = int(source_total)
            display_done = int(source_done)
            estimated = False
        return {
            "progress": progress,
            "downloaded": display_done,
            "total": display_total,
            "estimated": estimated,
        }


class DownloadManager(QThread):
    job_started = Signal(object)
    job_meta = Signal(str, dict)
    job_progress = Signal(str, dict)
    job_stage = Signal(str, str)
    job_done = Signal(object)
    job_failed = Signal(str, str)
    job_cancelled = Signal(str)
    log = Signal(str)

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self._queue: Queue[Job] = Queue()
        self._cancel_ids: set[str] = set()
        self._current: Optional[Job] = None
        self._cancel_current = False
        self._stop = False

    # -- public API -------------------------------------------------------
    def enqueue(self, job: Job) -> None:
        self._queue.put(job)

    def cancel(self, job_id: str) -> None:
        self._cancel_ids.add(job_id)
        if self._current and self._current.id == job_id:
            self._cancel_current = True
        else:
            self.job_cancelled.emit(job_id)

    def stop(self) -> None:
        self._stop = True
        self._cancel_current = True

    def has_work(self) -> bool:
        return bool(self._current) or not self._queue.empty()

    # -- thread loop ------------------------------------------------------
    def run(self) -> None:
        while not self._stop:
            try:
                job = self._queue.get(timeout=0.25)
            except Empty:
                continue
            if self._stop:
                break
            if job.id in self._cancel_ids:
                self._cancel_ids.discard(job.id)
                continue
            self._current = job
            self._cancel_current = False
            job.status = "downloading"
            job.stage = "Starting…"
            self.job_started.emit(job)
            try:
                self._download(job)
            except Exception as exc:  # noqa: BLE001 - always keep the worker alive
                if self._cancel_current or job.id in self._cancel_ids:
                    job.status = "cancelled"
                    self.job_cancelled.emit(job.id)
                else:
                    job.status = "error"
                    job.error = clean_error(str(exc)) or "Download failed"
                    self.job_failed.emit(job.id, job.error)
            finally:
                self._current = None
                self._cancel_ids.discard(job.id)
                self._cancel_current = False

    # -- download ---------------------------------------------------------
    def _download(self, job: Job) -> None:
        import yt_dlp
        from yt_dlp.utils import DownloadCancelled

        s = self.settings.snapshot()
        outdir = Path(s.get("output_dir") or default_output_dir()).expanduser()
        outdir.mkdir(parents=True, exist_ok=True)

        ffmpeg = find_ffmpeg(s.get("ffmpeg_path") or "")
        if not ffmpeg:
            raise RuntimeError(
                "ffmpeg was not found. Go to Settings → Tools and install or locate ffmpeg, then try again."
            )

        template = (s.get("template") or "%(title)s.%(ext)s").strip()
        if not template:
            template = "%(title)s.%(ext)s"

        last_error: list[str] = []
        logger = YdlLogger(self.log.emit, last_error)
        meta_sent = False
        start_ts = time.time()
        tracker = ProgressTracker()

        def progress_hook(d):
            nonlocal meta_sent
            if self._cancel_current:
                raise DownloadCancelled("Cancelled by user")
            info = d.get("info_dict") or {}
            if info and not meta_sent:
                meta_sent = True
                self.job_meta.emit(job.id, {
                    "title": info.get("title") or job.title,
                    "uploader": info.get("uploader") or info.get("channel") or "",
                    "duration": info.get("duration") or 0,
                    "thumb_url": info.get("thumbnail") or "",
                })
            status = d.get("status")
            if status in ("downloading", "finished"):
                snap = tracker.update(d)
                snap.update({
                    "speed": d.get("speed") or 0 if status == "downloading" else 0,
                    "eta": d.get("eta") or 0 if status == "downloading" else 0,
                    "stage": "Downloading…",
                })
                self.job_progress.emit(job.id, snap)

        def pp_hook(d):
            if self._cancel_current:
                raise DownloadCancelled("Cancelled by user")
            if d.get("status") != "started" and d.get("status") != "processing":
                return
            name = d.get("postprocessor") or ""
            stage = "Processing…"
            if "ExtractAudio" in name:
                stage = f"Converting to {job.fmt.upper()}…"
            elif "Merger" in name or "Remuxer" in name:
                stage = "Muxing streams…"
            elif "EmbedThumbnail" in name:
                stage = "Embedding cover art…"
            elif "Metadata" in name:
                stage = "Writing metadata…"
            elif "MoveFiles" in name:
                stage = "Finishing…"
            self.job_stage.emit(job.id, stage)

        opts = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "windowsfilenames": True,
            "trim_file_name": 180,
            "paths": {"home": str(outdir)},
            "outtmpl": {"default": template},
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 30,
            "concurrent_fragment_downloads": 4,
            "continuedl": True,
            "overwrites": False,
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [pp_hook],
            "logger": logger,
            "ffmpeg_location": ffmpeg,
            "ignoreerrors": False,
        }
        if s.get("force_ipv4"):
            opts["source_address"] = "0.0.0.0"
        proxy = str(s.get("proxy_url") or "").strip()
        if proxy:
            opts["proxy"] = proxy
        browser = str(s.get("cookies_browser") or "none")

        embed_thumb = bool(s.get("embed_thumbnail"))
        embed_meta = bool(s.get("embed_metadata"))
        postprocessors: list[dict] = []
        expected_ext = job.fmt.lower()

        if job.kind == "audio":
            opts["format"] = "bestaudio/best"
            codec, quality = _AUDIO_CODECS.get(job.fmt, ("mp3", "320"))
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": quality,
            })
            if embed_meta:
                postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
            if embed_thumb and job.fmt != "wav":
                opts["writethumbnail"] = True
                postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        else:
            height = None
            if job.quality not in ("", "best", None):
                try:
                    height = int(job.quality)
                except ValueError:
                    height = None
            hfilter = f"[height<={height}]" if height else ""
            if job.fmt == "mp4":
                fmt = (
                    f"bv*{hfilter}[vcodec^=avc1]+ba[acodec^=mp4a]"
                    f"/bv*{hfilter}+ba/b{hfilter}"
                )
                opts["postprocessor_args"] = {"merger": ["-movflags", "+faststart"]}
            elif job.fmt == "webm":
                fmt = f"bv*{hfilter}[vcodec^=vp9]+ba[acodec=opus]/bv*{hfilter}+ba/b{hfilter}"
            else:
                fmt = f"bv*{hfilter}+ba/b{hfilter}"
            opts["format"] = fmt
            opts["merge_output_format"] = job.fmt
            if embed_meta:
                postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
            if embed_thumb:
                opts["writethumbnail"] = True
                postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        if postprocessors:
            opts["postprocessors"] = postprocessors

        self.job_stage.emit(job.id, "Contacting site…")
        attempts, youtube = build_attempts(opts, s, job.url)
        info = None
        final_path = None
        last_exc: Exception | None = None
        completed = False
        for index, attempt_opts in enumerate(attempts):
            try:
                with yt_dlp.YoutubeDL(attempt_opts) as ydl:
                    # Resolve formats first so the UI can show the size of the
                    # finished file (MP3/WAV/FLAC are larger than their source
                    # stream) and so merged video progress does not jump
                    # between the video and audio streams.
                    info = ydl.extract_info(job.url, download=False)
                    if info and info.get("_type") == "playlist":
                        entries = [e for e in (info.get("entries") or []) if e]
                        if entries:
                            info = entries[0]
                    if not info:
                        raise RuntimeError("No media information was returned for this link.")
                    if self._cancel_current:
                        raise DownloadCancelled("Cancelled by user")
                    tracker.configure(info, job)
                    info = ydl.process_ie_result(info, download=True)
                    if info and info.get("_type") == "playlist":
                        entries = [e for e in (info.get("entries") or []) if e]
                        if entries:
                            info = entries[0]
                    if self._cancel_current:
                        raise DownloadCancelled("Cancelled by user")
                    final_path = self._resolve_output(ydl, info, outdir, expected_ext, start_ts)
                completed = True
                break
            except DownloadCancelled:
                job.status = "cancelled"
                self.job_cancelled.emit(job.id)
                return
            except Exception as exc:  # noqa: BLE001
                if self._cancel_current:
                    job.status = "cancelled"
                    self.job_cancelled.emit(job.id)
                    return
                message = clean_error(str(exc))
                if last_error:
                    candidate = clean_error(last_error[-1])
                    if candidate and (not message or len(candidate) > len(message)):
                        message = candidate
                if index + 1 < len(attempts) and (
                    youtube or is_bot_check_error(message)
                ):
                    last_exc = exc
                    last_error.clear()
                    if is_bot_check_error(message):
                        self.job_stage.emit(
                            job.id, "Bot check — retrying with browser impersonation…"
                        )
                    elif youtube and not has_cookie_options(attempt_opts):
                        self.job_stage.emit(
                            job.id, "Retrying with browser cookies…"
                        )
                    continue
                friendly = _friendly_error(message, browser)
                job.error = friendly
                job.status = "error"
                self.job_failed.emit(job.id, friendly)
                return
        if not completed:
            message = clean_error(str(last_exc) if last_exc else "Download failed")
            friendly = _friendly_error(message, browser)
            job.error = friendly
            job.status = "error"
            self.job_failed.emit(job.id, friendly)
            return

        info = info or {}
        job.status = "done"
        job.progress = 100.0
        job.stage = "Done"
        job.title = info.get("title") or job.title
        job.uploader = info.get("uploader") or info.get("channel") or job.uploader
        job.duration = info.get("duration") or job.duration
        job.thumb_url = info.get("thumbnail") or job.thumb_url
        job.filepath = str(final_path) if final_path else ""
        if final_path and final_path.exists():
            try:
                job.filesize = final_path.stat().st_size
            except OSError:
                job.filesize = 0
        self.job_stage.emit(job.id, "Done")
        self.job_done.emit(job)

    def _resolve_output(self, ydl, info: dict, outdir: Path, ext: str, start_ts: float) -> Optional[Path]:
        candidates: list[Path] = []
        if info:
            for rd in info.get("requested_downloads") or []:
                for key in ("filepath", "_filename"):
                    if rd.get(key):
                        candidates.append(Path(rd[key]))
            for key in ("filepath", "_filename"):
                if info.get(key):
                    candidates.append(Path(info[key]))
            try:
                prepared = ydl.prepare_filename(info)
                if prepared:
                    candidates.append(Path(prepared))
            except Exception:
                pass

        for path in candidates:
            try:
                if path.suffix.lower() == f".{ext}" and path.exists():
                    return path
                alt = path.with_suffix(f".{ext}")
                if alt.exists():
                    return alt
            except OSError:
                continue

        # Fall back to the newest matching file produced during this download.
        newest: Optional[Path] = None
        newest_ts = 0.0
        try:
            for dirpath, _dirnames, filenames in os.walk(outdir):
                for name in filenames:
                    if Path(name).suffix.lower() != f".{ext}":
                        continue
                    p = Path(dirpath) / name
                    try:
                        ts = p.stat().st_mtime
                    except OSError:
                        continue
                    if ts >= start_ts - 2 and ts > newest_ts:
                        newest, newest_ts = p, ts
        except OSError:
            pass
        return newest


def _friendly_error(message: str, browser: str = "") -> str:
    low = (message or "").lower()
    if (
        "could not copy chrome cookie database" in low
        or (
            "failed to load cookies" in low
            and (browser or "").strip().lower() in CHROMIUM_BROWSERS
        )
    ):
        name = browser_label(browser) if browser and browser != "none" else "your browser"
        return (
            message
            + f"\n\n{name} is using its cookie database, so Windows will not let "
            "TubeForge read it while the browser is open.\n\n"
            f"Fetch the link again and choose “Close {name} and continue” so TubeForge "
            f"can copy the cookies and reopen {name} automatically. You can also close "
            f"{name} yourself, or choose a Netscape cookies.txt file in "
            "Settings → Downloads. Firefox cookies work while Firefox is open."
        )
    if (
        "requested format is not available" in low
        or "no video formats found" in low
        or "video unavailable" in low
        or "this video is unavailable" in low
    ):
        return (
            "This video is unavailable. YouTube did not return any playable formats.\n\n"
            "It may have been removed, made private, age-restricted, or blocked in "
            "your region. If it plays in your browser, try a proxy in Settings → Proxy, "
            "or sign in to YouTube in the browser selected under Settings → Downloads "
            "and retry."
        )
    if is_bot_check_error(message):
        note = (
            message
            + "\n\nTubeForge retried with browser impersonation (the yt-dlp curl_cffi "
            "solution). If this still fails, enable browser cookies in Settings → Downloads "
            "and sign in to that browser first."
        )
        if not impersonation_available():
            note += (
                "\n\nImpersonation support is missing from this build. Reinstall TubeForge "
                "or install the Python package 'curl_cffi'."
            )
        return note
    if "ffmpeg" in low and "not found" in low:
        return "ffmpeg was not found. Install it from Settings → Tools and retry."
    if "private" in low and "video" in low:
        return message + "\n\nThis video is private. Try enabling browser cookies in Settings."
    return message or "Download failed"


class FfmpegInstallWorker(QThread):
    finished_ok = Signal(bool, str)

    def run(self) -> None:
        try:
            cmd = [
                "winget", "install", "--id", "Gyan.FFmpeg", "-e",
                "--accept-package-agreements", "--accept-source-agreements",
                "--silent", "--disable-interactivity",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900,
                creationflags=_CREATE_NO_WINDOW,
            )
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            if proc.returncode == 0:
                self.finished_ok.emit(True, output)
            else:
                self.finished_ok.emit(False, clean_error(output) or "winget could not install ffmpeg.")
        except FileNotFoundError:
            self.finished_ok.emit(False, "winget is not available on this system. Install ffmpeg manually and use Locate.")
        except Exception as exc:  # noqa: BLE001
            self.finished_ok.emit(False, clean_error(str(exc)))

