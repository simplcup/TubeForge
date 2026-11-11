"""Reusable custom-painted widgets for TubeForge."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .core import (
    APP_VERSION,
    Job,
    format_bytes,
    format_eta,
    format_label,
    format_speed,
    get_thumbs,
    open_folder,
    open_path,
)
from .theme import C, display_font, ui_font


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def hline() -> QFrame:
    line = QFrame()
    line.setObjectName("HLine")
    line.setFixedHeight(1)
    return line


class IconButton(QAbstractButton):
    """Compact square icon button with hover background."""

    def __init__(
        self,
        icon_name: str,
        color: str = C["muted"],
        hover_color: str = "#FFFFFF",
        hover_bg: str = "#1E2839",
        size: int = 30,
        icon_size: int = 16,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._color = color
        self._hover_color = hover_color
        self._hover_bg = hover_bg
        self._icon_size = icon_size
        self._hover = False
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def set_icon(self, name: str, color: str | None = None, size: int | None = None) -> None:
        self._icon_name = name
        if color:
            self._color = color
        if size:
            self._icon_size = size
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self._hover and self.isEnabled():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self._hover_bg))
            p.drawRoundedRect(r, 7, 7)
        color = self._hover_color if (self._hover and self.isEnabled()) else self._color
        if not self.isEnabled():
            color = C["dim"]
        pm = icons.pixmap(self._icon_name, color, self._icon_size)
        x = (self.width() - self._icon_size) / 2
        y = (self.height() - self._icon_size) / 2
        p.drawPixmap(int(x), int(y), pm)


class WindowButton(QAbstractButton):
    def __init__(self, kind: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.kind = kind
        self._hover = False
        self.setFixedSize(42, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        tips = {"minimize": "Minimize", "maximize": "Maximize", "restore": "Restore", "close": "Close"}
        self.setToolTip(tips.get(kind, ""))

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#E5484D" if self.kind == "close" else "#1C2434"))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 6, 6)
        color = "#FFFFFF" if (self.kind == "close" and self._hover) else "#AEB9CC"
        pm = icons.pixmap(self.kind, color, 13, 1.7)
        p.drawPixmap((self.width() - 13) // 2, (self.height() - 13) // 2, pm)


class TitleBar(QFrame):
    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.setObjectName("TitleBar")
        self.setFixedHeight(46)
        self._window = window
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 8, 0)
        lay.setSpacing(8)

        self._page_icon = QLabel()
        self._page_icon.setFixedSize(15, 15)
        self._page_icon.setPixmap(icons.pixmap("download", C["accent3"], 13))
        self._page_label = QLabel("Download")
        self._page_label.setObjectName("Crumb")
        lay.addWidget(self._page_icon)
        lay.addWidget(self._page_label)
        lay.addStretch()

        self.btn_min = WindowButton("minimize", window)
        self.btn_max = WindowButton("maximize", window)
        self.btn_close = WindowButton("close", window)
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_max)
        lay.addWidget(self.btn_close)

        self.btn_min.clicked.connect(window.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max)
        self.btn_close.clicked.connect(window.close)

    def set_page(self, title: str, icon_name: str) -> None:
        self._page_label.setText(title)
        self._page_icon.setPixmap(icons.pixmap(icon_name, C["accent3"], 13))

    def sync_max_button(self, maximized: bool) -> None:
        self.btn_max.kind = "restore" if maximized else "maximize"
        self.btn_max.update()

    def _toggle_max(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._window.windowHandle()
            if handle is not None:
                handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_max()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class NavButton(QWidget):
    clicked = Signal()

    def __init__(self, icon_name: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._text = text
        self._active = False
        self._hover = False
        self._badge = 0
        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.move(14, 11)
        self._text_label = QLabel(text, self)
        self._text_label.move(44, 10)
        self._text_label.setFont(ui_font(10, QFont.Weight.DemiBold))
        self._refresh()

    def _refresh(self) -> None:
        if self._active:
            icon_color, text_color = C["accent3"], C["text"]
        elif self._hover:
            icon_color, text_color = "#C7D0E0", C["text"]
        else:
            icon_color, text_color = "#6E7990", "#98A2B6"
        self._icon_label.setPixmap(icons.pixmap(self._icon_name, icon_color, 18))
        self._text_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._refresh()

    def set_badge(self, count: int) -> None:
        self._badge = max(0, int(count))
        self.update()

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self._refresh()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self._refresh()
        super().leaveEvent(event)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0, 1, 0, -1)
        if self._active:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#141A27"))
            p.drawRoundedRect(r.adjusted(8, 0, -8, 0), 9, 9)
            grad = QLinearGradient(8, 10, 8, self.height() - 10)
            grad.setColorAt(0, QColor(C["accent"]))
            grad.setColorAt(1, QColor(C["accent2"]))
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(8, 10, 3, self.height() - 20), 1.5, 1.5)
        elif self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#0F141F"))
            p.drawRoundedRect(r.adjusted(8, 0, -8, 0), 9, 9)

        if self._badge:
            text = str(self._badge)
            f = ui_font(7.5, QFont.Weight.Bold)
            p.setFont(f)
            fm = QFontMetrics(f)
            w = max(18, fm.horizontalAdvance(text) + 10)
            x = self.width() - w - 14
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(C["accent"]))
            p.drawRoundedRect(QRectF(x, 12, w, 18), 9, 9)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(QRectF(x, 12, w, 18), Qt.AlignmentFlag.AlignCenter, text)


class Sidebar(QFrame):
    nav_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(230)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 20, 14, 18)
        lay.setSpacing(4)

        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(10, 0, 0, 0)
        logo_row.setSpacing(11)
        logo = QLabel()
        logo.setFixedSize(38, 38)
        pm = QPixmap(str(icons.asset_path("logo.png")))
        if not pm.isNull():
            logo.setPixmap(pm.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo.setPixmap(icons.pixmap("play", C["accent3"], 30))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row.addWidget(logo)
        brand = QVBoxLayout()
        brand.setSpacing(0)
        title = QLabel("TubeForge")
        title.setObjectName("LogoTitle")
        sub = QLabel("MEDIA STUDIO")
        sub.setObjectName("LogoSub")
        brand.addWidget(title)
        brand.addWidget(sub)
        logo_row.addLayout(brand)
        logo_row.addStretch()
        lay.addLayout(logo_row)
        lay.addSpacing(26)

        self.nav_buttons: list[NavButton] = []
        for i, (icon_name, text) in enumerate(
            [("home", "Download"), ("queue", "Queue"), ("history", "History"), ("settings", "Settings")]
        ):
            btn = NavButton(icon_name, text)
            btn.clicked.connect(lambda idx=i: self.nav_requested.emit(idx))
            lay.addWidget(btn)
            self.nav_buttons.append(btn)

        lay.addStretch()

        self.status = QFrame()
        self.status.setObjectName("StatusCard")
        self.status.setFixedHeight(54)
        self.status.setCursor(Qt.CursorShape.PointingHandCursor)
        sl = QHBoxLayout(self.status)
        sl.setContentsMargins(12, 8, 10, 8)
        sl.setSpacing(9)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setStyleSheet("background: #34D399; border-radius: 3px;")
        sl.addWidget(self.status_dot)
        sv = QVBoxLayout()
        sv.setSpacing(0)
        self.status_title = QLabel("ffmpeg ready")
        self.status_title.setStyleSheet("color: #C9D3E4; font-size: 8.5pt; font-weight: 600;")
        self.status_sub = QLabel("Engine prepared")
        self.status_sub.setStyleSheet("color: #5E6980; font-size: 7.5pt;")
        sv.addWidget(self.status_title)
        sv.addWidget(self.status_sub)
        sl.addLayout(sv)
        sl.addStretch()
        self.status_icon = QLabel()
        self.status_icon.setPixmap(icons.pixmap("check", C["success"], 12))
        sl.addWidget(self.status_icon)
        self.status.mousePressEvent = lambda e: self.nav_requested.emit(3)  # type: ignore[assignment]
        lay.addWidget(self.status)
        lay.addSpacing(10)

        version = QLabel(f"v{APP_VERSION}  ·  yt-dlp engine")
        version.setStyleSheet("color: #4A546A; font-size: 7.5pt;")
        version.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(version)

    def set_active(self, index: int) -> None:
        for i, btn in enumerate(self.nav_buttons):
            btn.set_active(i == index)

    def set_ffmpeg(self, found: bool, detail: str = "") -> None:
        if found:
            self.status_dot.setStyleSheet("background: #34D399; border-radius: 3px;")
            self.status_title.setText("ffmpeg ready")
            self.status_sub.setText("Engine prepared")
            self.status_icon.setPixmap(icons.pixmap("check", C["success"], 12))
        else:
            self.status_dot.setStyleSheet("background: #FBBF24; border-radius: 3px;")
            self.status_title.setText("ffmpeg missing")
            self.status_sub.setText("Click to set up")
            self.status_icon.setPixmap(icons.pixmap("alert", C["warning"], 12))
        if detail:
            self.status.setToolTip(detail)


class FormatCard(QAbstractButton):
    def __init__(self, data: dict, accent: str = C["accent"], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data = data
        self.accent = accent
        self._hover = False
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(96)
        self.setFixedHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip(f"{data['label']} — {data['desc']}  ({data['tag']})")

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        checked = self.isChecked()
        hover = self._hover

        if checked:
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0, QColor(self.accent))
            grad.setColorAt(1, QColor(C["accent2"]))
            p.setPen(QPen(grad, 1.4))
            fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
            c0 = QColor(C["accent"])
            c0.setAlpha(40)
            c1 = QColor(C["accent2"])
            c1.setAlpha(24)
            fill.setColorAt(0, c0)
            fill.setColorAt(1, c1)
            p.setBrush(fill)
            p.drawRoundedRect(rect, 10, 10)
        else:
            p.setPen(QPen(QColor("#283245" if hover else "#202838"), 1))
            p.setBrush(QColor("#141A26" if hover else "#10151F"))
            p.drawRoundedRect(rect, 10, 10)

        title_font = display_font(10.2, QFont.Weight.DemiBold)
        p.setFont(title_font)
        p.setPen(QColor(C["text"]))
        p.drawText(QRectF(13, 8, rect.width() - 36, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.data["label"])

        desc_font = ui_font(7.6)
        p.setFont(desc_font)
        p.setPen(QColor("#9AA5BA" if checked else C["dim"]))
        desc = f"{self.data['desc']}"
        p.drawText(QRectF(13, 28, rect.width() - 34, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, desc)

        # check indicator
        cx = rect.right() - 17
        cy = rect.top() + 17
        p.setPen(Qt.PenStyle.NoPen)
        if checked:
            grad = QLinearGradient(cx - 7, cy - 7, cx + 7, cy + 7)
            grad.setColorAt(0, QColor(self.accent))
            grad.setColorAt(1, QColor(C["accent2"]))
            p.setBrush(grad)
            p.drawEllipse(QRectF(cx - 7, cy - 7, 14, 14))
            pm = icons.pixmap("check", "#0B0E14", 9, 2.6)
            p.drawPixmap(int(cx - 4.5), int(cy - 4.5), pm)
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#35415A"), 1.2))
            p.drawEllipse(QRectF(cx - 6, cy - 6, 12, 12))


class GradientButton(QPushButton):
    def __init__(self, text: str, icon_name: str = "download", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._icon_name = icon_name
        self._hover = False
        self.setFixedHeight(52)
        self.setMinimumWidth(236)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(display_font(10.8, QFont.Weight.DemiBold))
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(30)
        glow.setColor(QColor(C["accent"]))
        glow.setOffset(0, 7)
        self.setGraphicsEffect(glow)

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 13, 13)
        p.setClipPath(path)

        if not self.isEnabled():
            p.fillPath(path, QColor("#1A2130"))
        else:
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            if self._hover:
                grad.setColorAt(0, QColor(C["accent"]).lighter(118))
                grad.setColorAt(1, QColor(C["accent2"]).lighter(112))
            else:
                grad.setColorAt(0, QColor(C["accent"]))
                grad.setColorAt(1, QColor(C["accent2"]))
            p.fillPath(path, grad)
            shine = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            shine.setColorAt(0, QColor(255, 255, 255, 34))
            shine.setColorAt(0.5, QColor(255, 255, 255, 0))
            p.fillPath(path, shine)

        color = QColor("#FFFFFF") if self.isEnabled() else QColor("#5B6579")
        f = display_font(10.8, QFont.Weight.DemiBold)
        p.setFont(f)
        fm = QFontMetrics(f)
        text = self.text()
        tw = fm.horizontalAdvance(text)
        icon_size = 18
        gap = 10
        total = icon_size + gap + tw
        x = (self.width() - total) / 2
        pm = icons.pixmap(self._icon_name, color.name(), icon_size, 2.1)
        p.drawPixmap(int(x), int((self.height() - icon_size) / 2), pm)
        p.setPen(color)
        p.drawText(
            QRectF(x + icon_size + gap, 0, tw + 2, self.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text,
        )


class GlowProgress(QWidget):
    def __init__(self, height: int = 8, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._active = False
        self._phase = 0.0
        self.setFixedHeight(height)
        self._timer = QTimer(self)
        self._timer.setInterval(38)
        self._timer.timeout.connect(self._tick)

    def setValue(self, value: float) -> None:  # noqa: N802
        self._value = max(0.0, min(100.0, float(value)))
        self.update()

    def setActive(self, active: bool) -> None:  # noqa: N802
        if active == self._active:
            return
        self._active = active
        if active:
            self._timer.start()
        else:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 2.2) % 80
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        track = QRectF(0, 0, self.width(), h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1B2334"))
        p.drawRoundedRect(track, h / 2, h / 2)

        pct = self._value / 100.0
        if self._active and pct <= 0.001:
            pct = 0.035
        if pct <= 0:
            return
        w = max(h, self.width() * pct)
        fill_rect = QRectF(0, 0, min(w, self.width()), h)
        clip = QPainterPath()
        clip.addRoundedRect(track, h / 2, h / 2)
        p.setClipPath(clip)
        grad = QLinearGradient(0, 0, max(self.width(), 1), 0)
        grad.setColorAt(0, QColor(C["accent"]))
        grad.setColorAt(1, QColor(C["accent2"]))
        p.setBrush(grad)
        p.drawRoundedRect(fill_rect, h / 2, h / 2)

        if self._active and h >= 6:
            # Keep the moving stripes inside the filled part of the bar so the
            # leading edge always matches the reported progress.
            fill_clip = QPainterPath()
            fill_clip.addRoundedRect(fill_rect, h / 2, h / 2)
            p.setClipPath(fill_clip)
            p.setPen(QPen(QColor(255, 255, 255, 26), 2))
            x = -h * 3 + self._phase
            while x < fill_rect.width() + h * 3:
                p.drawLine(int(x), h + 2, int(x + h), -2)
                x += 9
        p.setClipping(False)


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._offset = 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.isChecked():
            grad = QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0, QColor(C["accent"]))
            grad.setColorAt(1, QColor(C["accent2"]))
            p.setBrush(grad)
        else:
            p.setBrush(QColor("#2A3448"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = 18
        x = 3 + self._offset * (self.width() - d - 6)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawEllipse(QRectF(x + 0.5, 4.5, d, d))
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, 3, d, d))


class ThumbLabel(QWidget):
    def __init__(
        self,
        width: int,
        height: int,
        radius: int = 10,
        fallback_icon: str = "play",
        show_badge: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._w = width
        self._h = height
        self._radius = radius
        self._fallback_icon = fallback_icon
        self._show_badge = show_badge
        self._pixmap: QPixmap | None = None
        self._url = ""
        self.setFixedSize(width, height)
        get_thumbs().loaded.connect(self._on_loaded)

    def set_url(self, url: str) -> None:
        if url == self._url:
            return
        self._url = url or ""
        self._pixmap = get_thumbs().get(self._url) if self._url else None
        self.update()

    def set_pixmap(self, pm: QPixmap | None) -> None:
        self._pixmap = pm
        self.update()

    def _on_loaded(self, url: str, pm: QPixmap) -> None:
        if url and url == self._url:
            self._pixmap = pm
            self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(rect, self._radius, self._radius)
        p.setClipPath(clip)

        if self._pixmap and not self._pixmap.isNull():
            src = self._pixmap
            scaled = src.scaled(
                self._w, self._h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - self._w) // 2
            y = (scaled.height() - self._h) // 2
            p.drawPixmap(0, 0, scaled, x, y, self._w, self._h)
            if self._show_badge:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(10, 13, 20, 165))
                d = 34
                p.drawEllipse(QRectF((self._w - d) / 2, (self._h - d) / 2, d, d))
                pm = icons.pixmap("play", "#FFFFFF", 15)
                p.drawPixmap((self._w - 15) // 2, (self._h - 15) // 2, pm)
        else:
            grad = QLinearGradient(0, 0, self._w, self._h)
            grad.setColorAt(0, QColor("#1A1F35"))
            grad.setColorAt(1, QColor("#101A24"))
            p.fillRect(self.rect(), grad)
            pm = icons.pixmap(self._fallback_icon, "#39445C", 30)
            p.drawPixmap((self._w - 30) // 2, (self._h - 30) // 2, pm)

        p.setClipping(False)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.drawRoundedRect(rect, self._radius, self._radius)


class Toast(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._kind = "success"
        self._text = ""
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedHeight(46)
        self.hide()
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(220)
        self._anim.finished.connect(self.hide)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

    def show_message(self, text: str, kind: str = "success") -> None:
        self._text = str(text)
        self._kind = kind
        f = ui_font(9.2, QFont.Weight.DemiBold)
        self.setFont(f)
        fm = QFontMetrics(f)
        max_w = max(260, self.parentWidget().width() - 60)
        w = min(max_w, fm.horizontalAdvance(self._text) + 78)
        self.setFixedWidth(int(w))
        self._effect.setOpacity(1.0)
        self._anim.stop()
        self._reposition()
        self.show()
        self.raise_()
        self._timer.start(3200)
        self.update()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent:
            self.move(
                max(12, parent.width() - self.width() - 24),
                max(12, parent.height() - self.height() - 24),
            )

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        # The parent may still be laying out when a toast is first shown
        # (e.g. right after a live theme rebuild), so settle on the final
        # geometry once the event loop has processed the layout pass.
        QTimer.singleShot(0, self._reposition)

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        colors = {
            "success": (C["success"], "check"),
            "error": (C["danger"], "alert"),
            "info": (C["accent2"], "info"),
        }
        color, icon_name = colors.get(self._kind, colors["info"])
        p.setBrush(QColor(C["card2"]))
        p.setPen(QPen(QColor(color), 1))
        p.drawRoundedRect(rect, 12, 12)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.setOpacity(0.14)
        p.drawEllipse(QRectF(12, 12, 22, 22))
        p.setOpacity(1.0)
        pm = icons.pixmap(icon_name, color, 13, 2.2)
        p.drawPixmap(16, 16, pm)

        p.setFont(self.font())
        p.setPen(QColor(C["text"]))
        text_rect = QRectF(44, 0, self.width() - 58, self.height())
        fm = QFontMetrics(self.font())
        text = fm.elidedText(self._text, Qt.TextElideMode.ElideRight, int(text_rect.width()))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)


class EmptyState(QWidget):
    def __init__(
        self,
        icon_name: str,
        title: str,
        subtitle: str,
        accent: str = C["accent"],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 30, 20, 30)
        lay.setSpacing(8)
        lay.addStretch()

        badge = QLabel()
        badge.setFixedSize(58, 58)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(icons.pixmap(icon_name, accent, 24))
        badge.setStyleSheet(
            f"background: rgba({QColor(accent).red()}, {QColor(accent).green()}, {QColor(accent).blue()}, 0.10);"
            f"border: 1px solid rgba({QColor(accent).red()}, {QColor(accent).green()}, {QColor(accent).blue()}, 0.25);"
            "border-radius: 18px;"
        )
        badge_row = QHBoxLayout()
        badge_row.addStretch()
        badge_row.addWidget(badge)
        badge_row.addStretch()
        lay.addLayout(badge_row)

        t = QLabel(title)
        t.setFont(display_font(12, QFont.Weight.DemiBold))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("color: #C7D0E1;")
        lay.addWidget(t)
        s = QLabel(subtitle)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setWordWrap(True)
        s.setStyleSheet("color: #66718A; font-size: 9pt;")
        lay.addWidget(s)
        lay.addStretch()


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None, color: str | None = None) -> None:
        super().__init__(text, parent)
        self._text_color = QColor(color) if color else None
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setFont(self.font())
        color = self._text_color or self.palette().color(QPalette.ColorRole.WindowText)
        p.setPen(color)
        fm = QFontMetrics(self.font())
        text = fm.elidedText(self.text(), Qt.TextElideMode.ElideRight, max(0, self.width()))
        p.drawText(self.rect(), int(self.alignment() | Qt.AlignmentFlag.AlignVCenter), text)


class JobCard(QFrame):
    action_requested = Signal(str, str)  # job id, action

    def __init__(self, job: Job, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.job = job
        self.setObjectName("JobCard")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(13, 11, 12, 11)
        outer.setSpacing(9)

        row = QHBoxLayout()
        row.setSpacing(11)
        self.thumb = ThumbLabel(58, 58, 9, "music" if job.kind == "audio" else "video")
        row.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignVCenter)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.title = ElidedLabel(job.title)
        self.title.setFont(ui_font(10.2, QFont.Weight.DemiBold))
        self.title.setStyleSheet("color: #EDF2FA;")
        self.meta = ElidedLabel("Queued")
        self.meta.setFont(ui_font(8.2))
        self.meta.setStyleSheet("color: #77839A;")
        info.addWidget(self.title)
        info.addWidget(self.meta)
        row.addLayout(info, 1)

        self.status = QLabel("Queued")
        self.status.setFont(ui_font(8, QFont.Weight.DemiBold))
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # Pin the font size in the stylesheet too: the global QWidget rule in the
        # theme sets 10pt and would otherwise override the font above, making the
        # measured width too small and clipping labels such as "Downloading".
        self.status.setStyleSheet("font-size: 8pt; font-weight: 600;")
        status_fm = QFontMetrics(self.status.font())
        self.status.setMinimumWidth(max(128, status_fm.horizontalAdvance("Downloading") + 36))
        self.status.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        row.addWidget(self.status)

        self.action_btn = IconButton("close", "#8B95AB", "#FFFFFF", "#26303F", 28, 14)
        self.action_btn.setToolTip("Cancel")
        self.action_btn.clicked.connect(self._on_action)
        row.addWidget(self.action_btn)

        self.dismiss_btn = IconButton("close", "#5E6880", "#FFFFFF", "#26303F", 28, 13, "Dismiss")
        self.dismiss_btn.clicked.connect(lambda: self.action_requested.emit(self.job.id, "dismiss"))
        self.dismiss_btn.hide()
        row.addWidget(self.dismiss_btn)
        outer.addLayout(row)

        self.progress = GlowProgress(6)
        outer.addWidget(self.progress)
        self.update_job(job)

    def _set_status_color(self, color: str) -> None:
        self.status.setStyleSheet(f"color: {color}; font-size: 8pt; font-weight: 600;")

    def _on_action(self) -> None:
        status = self.job.status
        if status in ("queued", "downloading", "processing"):
            self.action_requested.emit(self.job.id, "cancel")
        elif status == "done":
            self.action_requested.emit(self.job.id, "folder")
        elif status == "error":
            self.action_requested.emit(self.job.id, "retry")
        else:
            self.action_requested.emit(self.job.id, "dismiss")

    def update_job(self, job: Job) -> None:
        self.job = job
        self.title.setText(job.title)
        self.title.setToolTip(job.title)
        self.thumb.set_url(job.thumb_url)

        status = job.status
        active = status in ("downloading", "processing")
        terminal = status in ("done", "error", "cancelled")
        self.progress.setValue(job.progress)
        self.progress.setActive(active)
        self.progress.setVisible(status != "done")

        # Size the status label from the effective (stylesheet) font so labels
        # like "Downloading" are never clipped at any DPI scaling.
        label_text = {
            "queued": "Queued",
            "downloading": "Downloading",
            "processing": "Processing",
            "done": "Done",
            "error": "Failed",
        }.get(status, "Cancelled")
        metrics = self.status.fontMetrics()
        self.status.setFixedWidth(max(128, metrics.horizontalAdvance(label_text) + 36))

        base = format_label(job.fmt, job.kind, job.quality)
        if status == "queued":
            self.status.setText("Queued")
            self._set_status_color(C['muted'])
            self.meta.setText(f"{base}  ·  Waiting…")
            self.action_btn.set_icon("close", "#8B95AB")
            self.action_btn.setToolTip("Cancel download")
            self.dismiss_btn.hide()
        elif status == "downloading":
            self.status.setText("Downloading")
            self._set_status_color(C['accent2'])
            detail = []
            if job.speed:
                detail.append(format_speed(job.speed))
            if job.eta:
                detail.append(f"ETA {format_eta(job.eta)}")
            if job.total:
                total_text = format_bytes(job.total)
                if job.total_estimated:
                    total_text = f"~{total_text}"
                detail.append(f"{format_bytes(job.downloaded)} / {total_text}")
            suffix = "  ·  ".join(detail)
            self.meta.setText(f"{base}" + (f"  ·  {suffix}" if suffix else ""))
            self.action_btn.set_icon("close", "#8B95AB")
            self.action_btn.setToolTip("Cancel download")
            self.dismiss_btn.hide()
        elif status == "processing":
            self.status.setText("Processing")
            self._set_status_color(C['warning'])
            self.meta.setText(f"{base}  ·  {job.stage or 'Muxing streams…'}")
            self.action_btn.set_icon("close", "#8B95AB")
            self.action_btn.setToolTip("Cancel")
            self.dismiss_btn.hide()
        elif status == "done":
            self.status.setText("Done")
            self._set_status_color(C['success'])
            size = format_bytes(job.filesize) if job.filesize else "Saved"
            self.meta.setText(f"{base}  ·  {size}  ·  {job.stage if job.stage else 'Complete'}")
            self.action_btn.set_icon("folder-open", C["success"], 15)
            self.action_btn.setToolTip("Open in folder")
            self.dismiss_btn.show()
            self.progress.setValue(100)
        elif status == "error":
            self.status.setText("Failed")
            self._set_status_color(C['danger'])
            self.meta.setText(job.error or "Download failed")
            self.meta.setToolTip(job.error)
            self.action_btn.set_icon("refresh", C["warning"], 15)
            self.action_btn.setToolTip("Retry")
            self.dismiss_btn.show()
        else:
            self.status.setText("Cancelled")
            self._set_status_color(C['dim'])
            self.meta.setText(f"{base}  ·  Cancelled")
            self.action_btn.set_icon("refresh", "#8B95AB", 15)
            self.action_btn.setToolTip("Download again")
            self.dismiss_btn.show()

        if status == "error":
            self.status.setToolTip(job.error)


class HistoryCard(QFrame):
    open_file = Signal(dict)
    open_folder = Signal(dict)
    remove = Signal(dict)

    def __init__(self, entry: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("HistoryCard")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(11, 9, 9, 9)
        lay.setSpacing(12)
        self.thumb = ThumbLabel(92, 52, 8, "music" if entry.get("kind") == "audio" else "video")
        self.thumb.set_url(entry.get("thumb_url") or "")
        lay.addWidget(self.thumb)

        info = QVBoxLayout()
        info.setSpacing(2)
        title = ElidedLabel(entry.get("title") or "Untitled")
        title.setFont(ui_font(9.8, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #E6ECF7;")
        title.setToolTip(entry.get("title") or "")
        info.addWidget(title)
        meta_bits = [
            format_label(entry.get("fmt", "mp3"), entry.get("kind", "audio"), entry.get("quality", "best")),
            format_bytes(entry.get("filesize") or 0),
            entry.get("date", ""),
        ]
        meta = QLabel("  ·  ".join(x for x in meta_bits if x))
        meta.setStyleSheet("color: #6F7A92; font-size: 8.2pt;")
        info.addWidget(meta)
        lay.addLayout(info, 1)

        b_open = IconButton("play", C["success"], "#FFFFFF", "#1E2839", 30, 14, "Open file")
        b_open.clicked.connect(lambda: self.open_file.emit(self.entry))
        b_folder = IconButton("folder-open", "#9AA5BA", "#FFFFFF", "#1E2839", 30, 15, "Show in folder")
        b_folder.clicked.connect(lambda: self.open_folder.emit(self.entry))
        b_del = IconButton("trash", "#6E7990", C["danger"], "#2A1720", 30, 14, "Remove from history")
        b_del.clicked.connect(lambda: self.remove.emit(self.entry))
        lay.addWidget(b_open)
        lay.addWidget(b_folder)
        lay.addWidget(b_del)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self.open_file.emit(self.entry)
        super().mouseDoubleClickEvent(event)


def open_entry_file(entry: dict) -> None:
    path = entry.get("filepath") or ""
    if path and Path(path).exists():
        open_path(path)
    else:
        open_folder(path)


def open_entry_folder(entry: dict) -> None:
    open_folder(entry.get("filepath") or entry.get("output_dir") or "")
