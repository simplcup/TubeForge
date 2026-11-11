"""Inline SVG icon helpers (no external assets required)."""

from functools import lru_cache
from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{width}" '
    'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)

_PATHS = {
    "home": '<path d="M3 10.6 12 3l9 7.6V20a1 1 0 0 1-1 1h-5v-6.4H9V21H4a1 1 0 0 1-1-1z"/>',
    "download": '<path d="M12 3v12"/><path d="m8 11 4 4 4-4"/><path d="M4 17v3h16v-3"/>',
    "link": '<path d="M10.5 13.5a5 5 0 0 0 7.07 0l2.12-2.12a5 5 0 0 0-7.07-7.07L11.2 5.73"/>'
            '<path d="M13.5 10.5a5 5 0 0 0-7.07 0L4.3 12.62a5 5 0 0 0 7.07 7.07l1.42-1.42"/>',
    "clipboard": '<rect x="8" y="2" width="8" height="4" rx="1.5"/>'
                 '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
                 '<path d="M8 11h8M8 15h5"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4.6l2 2H19a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "folder-open": '<path d="M3 7a2 2 0 0 1 2-2h4.6l2 2H19a2 2 0 0 1 2 2v1H3z"/>'
                   '<path d="M3 10h18l-2.2 9a2 2 0 0 1-1.95 1.5H5.2A2 2 0 0 1 3.25 19z"/>',
    "music": '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    "video": '<rect x="2.5" y="5" width="14" height="14" rx="3"/>'
             '<path d="m16.5 10 5-3v10l-5-3z"/>',
    "settings": '<path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/>'
                '<circle cx="8" cy="17" r="2"/>',
    "queue": '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "minimize": '<path d="M5 12h14"/>',
    "maximize": '<rect x="5" y="5" width="14" height="14" rx="1.5"/>',
    "restore": '<rect x="8" y="8" width="11" height="11" rx="1.5"/><path d="M5 15V6a1 1 0 0 1 1-1h9"/>',
    "check": '<path d="m4.5 12.5 5 5 10-11"/>',
    "trash": '<path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'
             '<path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13"/><path d="M10 11v6M14 11v6"/>',
    "external": '<path d="M14 4h6v6"/><path d="M20 4 10 14"/>'
                '<path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "play": '<path d="M8 5.5v13l11-6.5z" fill="{color}" stroke="none"/>',
    "bolt": '<path d="M13 2 4 14h6l-1 8 9-12h-6z"/>',
    "alert": '<path d="M12 3 2.5 20h19z"/><path d="M12 9v5M12 17.5h.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
    "refresh": '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v6h-6"/>',
    "waveform": '<path d="M3 10v4M7 7v10M11 4v16M15 8v8M19 6v12M22 10v4"/>',
    "shield": '<path d="M12 3 5 6v6c0 5 3.5 7.5 7 9 3.5-1.5 7-4 7-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/>'
            '<path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
}


@lru_cache(maxsize=256)
def _render(name: str, color: str, size: int, stroke: float) -> QPixmap:
    body = _PATHS[name].replace("{color}", color)
    svg = _SVG_TEMPLATE.format(color=color, width=stroke, body=body)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    scale = 2
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(scale)
    return pm


def pixmap(name: str, color: str = "#F3F6FC", size: int = 20, stroke: float = 1.9) -> QPixmap:
    if name not in _PATHS:
        name = "info"
    return _render(name, color, size, stroke)


def icon(name: str, color: str = "#F3F6FC", size: int = 20, stroke: float = 1.9) -> QIcon:
    return QIcon(pixmap(name, color, size, stroke))


def asset_path(name: str) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "assets" / name
    return Path(__file__).resolve().parents[1] / "assets" / name
