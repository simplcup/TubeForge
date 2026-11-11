"""Visual themes for TubeForge.

The palette in ``C`` is shared by every module (imported by reference), so
calling :func:`apply_theme` updates icon painting, custom widgets and the
generated stylesheet together.
"""

from __future__ import annotations

from string import Template

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

DEFAULT_THEME = "midnight"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
THEMES: dict[str, dict] = {
    "midnight": {
        "name": "Midnight Violet",
        "description": "Deep navy with violet and cyan accents.",
        "colors": {
            "bg": "#0B0E14", "sidebar": "#090B11", "card": "#111621",
            "card2": "#151B28", "input": "#0E131D", "border": "#202838",
            "border2": "#2B3548", "text": "#F3F6FC", "muted": "#8B95AB",
            "dim": "#66718A", "accent": "#7C5CFF", "accent2": "#22D3EE",
            "accent3": "#A78BFA", "success": "#34D399", "danger": "#FB7185",
            "warning": "#FBBF24",
        },
    },
    "aurora": {
        "name": "Aurora",
        "description": "Arctic green and sky blue over pine black.",
        "colors": {
            "bg": "#061210", "sidebar": "#040D0B", "card": "#0C1A16",
            "card2": "#10211C", "input": "#081511", "border": "#1B3128",
            "border2": "#274438", "text": "#EFFBF5", "muted": "#87A99A",
            "dim": "#5C7A6D", "accent": "#34D399", "accent2": "#38BDF8",
            "accent3": "#6EE7B7", "success": "#34D399", "danger": "#FB7185",
            "warning": "#FBBF24",
        },
    },
    "sunset": {
        "name": "Sunset Heat",
        "description": "Warm plum with orange and pink glow.",
        "colors": {
            "bg": "#140A10", "sidebar": "#0F060B", "card": "#1E1017",
            "card2": "#26151D", "input": "#180C12", "border": "#36202B",
            "border2": "#4A2C3A", "text": "#FFF3F0", "muted": "#B99099",
            "dim": "#7E616A", "accent": "#FB923C", "accent2": "#F472B6",
            "accent3": "#FDBA74", "success": "#4ADE80", "danger": "#FB7185",
            "warning": "#FBBF24",
        },
    },
    "ocean": {
        "name": "Deep Ocean",
        "description": "Midnight blue with electric blue and cyan.",
        "colors": {
            "bg": "#061019", "sidebar": "#040C13", "card": "#0A1926",
            "card2": "#0E2031", "input": "#07131F", "border": "#16324A",
            "border2": "#204560", "text": "#EFF7FF", "muted": "#86A3BC",
            "dim": "#5C7A93", "accent": "#3B82F6", "accent2": "#22D3EE",
            "accent3": "#7DD3FC", "success": "#34D399", "danger": "#FB7185",
            "warning": "#FBBF24",
        },
    },
    "forest": {
        "name": "Evergreen",
        "description": "Mossy black with lime and amber highlights.",
        "colors": {
            "bg": "#0A1009", "sidebar": "#070C06", "card": "#101A0F",
            "card2": "#152216", "input": "#0C140B", "border": "#21341F",
            "border2": "#2F4A2C", "text": "#F2FBEF", "muted": "#9AAF95",
            "dim": "#6A7F66", "accent": "#84CC16", "accent2": "#F59E0B",
            "accent3": "#BEF264", "success": "#4ADE80", "danger": "#FB7185",
            "warning": "#FBBF24",
        },
    },
    "crimson": {
        "name": "Crimson",
        "description": "Oxblood shadows with rose and red accents.",
        "colors": {
            "bg": "#130A0E", "sidebar": "#0E0609", "card": "#1D1015",
            "card2": "#27151C", "input": "#170B11", "border": "#39202B",
            "border2": "#4E2C3B", "text": "#FFF1F4", "muted": "#BE8F99",
            "dim": "#86626C", "accent": "#F43F5E", "accent2": "#FB7185",
            "accent3": "#FDA4AF", "success": "#34D399", "danger": "#FB7185",
            "warning": "#FBBF24",
        },
    },
    "graphite": {
        "name": "Graphite (mono)",
        "description": "Monochrome charcoal with silver accents.",
        "colors": {
            "bg": "#0B0B0D", "sidebar": "#070708", "card": "#131316",
            "card2": "#19191D", "input": "#0F0F12", "border": "#26262B",
            "border2": "#35353C", "text": "#F4F4F6", "muted": "#9C9CA4",
            "dim": "#6D6D75", "accent": "#A1A1AA", "accent2": "#D4D4D8",
            "accent3": "#E4E4E7", "success": "#A3B3A8", "danger": "#C9A7A7",
            "warning": "#C9C0A0",
        },
    },
    "sand": {
        "name": "Sepia (mono)",
        "description": "Warm monochrome sepia with sand accents.",
        "colors": {
            "bg": "#12100B", "sidebar": "#0D0B07", "card": "#1C1811",
            "card2": "#241F17", "input": "#16130D", "border": "#332C1F",
            "border2": "#473D2B", "text": "#F7F1E4", "muted": "#B3A58C",
            "dim": "#80745E", "accent": "#D4A373", "accent2": "#E9C46A",
            "accent3": "#FAEDCD", "success": "#B7C4A0", "danger": "#D9A3A3",
            "warning": "#E0C080",
        },
    },
}

THEME_ORDER = ["midnight", "aurora", "sunset", "ocean", "forest", "crimson", "graphite", "sand"]

CURRENT_THEME = DEFAULT_THEME
C: dict[str, str] = dict(THEMES[DEFAULT_THEME]["colors"])


def theme_name(theme_id: str) -> str:
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME])["name"]


def _mix(a: str, b: str, t: float) -> str:
    ca, cb = QColor(a), QColor(b)
    t = max(0.0, min(1.0, t))
    return QColor(
        round(ca.red() + (cb.red() - ca.red()) * t),
        round(ca.green() + (cb.green() - ca.green()) * t),
        round(ca.blue() + (cb.blue() - ca.blue()) * t),
    ).name()


def _rgba(color: str, alpha: float) -> str:
    c = QColor(color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {max(0.0, min(1.0, alpha)):.2f})"


def _derive(colors: dict[str, str]) -> dict[str, str]:
    p = dict(colors)
    text = p["text"]
    p["root_border"] = _mix(p["border"], text, 0.07)
    p["sidebar_border"] = _mix(p["border"], p["bg"], 0.35)
    p["bar_bg"] = _mix(p["input"], p["bg"], 0.30)
    p["bar_border"] = _mix(p["border2"], text, 0.04)
    p["bar_border_hover"] = _mix(p["border2"], text, 0.16)
    p["hover_bg"] = _mix(p["card2"], text, 0.05)
    p["pressed_bg"] = _mix(p["card"], p["bg"], 0.40)
    p["focus_bg"] = _mix(p["input"], p["accent"], 0.05)
    p["soft_bg"] = _mix(p["card2"], p["bg"], 0.35)
    p["accent_soft"] = _rgba(p["accent"], 0.14)
    p["accent_soft2"] = _rgba(p["accent"], 0.24)
    p["accent_border"] = _mix(p["accent"], p["bg"], 0.18)
    p["accent_text"] = _mix(p["accent3"], "#FFFFFF", 0.35)
    p["success_soft"] = _rgba(p["success"], 0.11)
    p["success_border"] = _rgba(p["success"], 0.32)
    p["success_text"] = _mix(p["success"], "#FFFFFF", 0.30)
    p["warning_soft"] = _rgba(p["warning"], 0.11)
    p["warning_border"] = _rgba(p["warning"], 0.32)
    p["warning_text"] = _mix(p["warning"], "#FFFFFF", 0.22)
    p["danger_soft"] = _rgba(p["danger"], 0.11)
    p["danger_border"] = _rgba(p["danger"], 0.32)
    p["danger_text"] = _mix(p["danger"], "#FFFFFF", 0.20)
    p["chip_bg"] = _mix(p["card2"], p["accent"], 0.08)
    p["chip_border"] = _mix(p["border2"], p["accent"], 0.16)
    p["chip_text"] = _mix(p["muted"], text, 0.45)
    p["scroll"] = _mix(p["border2"], p["bg"], 0.25)
    p["scroll_hover"] = _mix(p["border2"], text, 0.15)
    p["tooltip_bg"] = _mix(p["card2"], text, 0.04)
    p["tooltip_border"] = _mix(p["border2"], text, 0.10)
    p["menu_bg"] = _mix(p["card"], p["bg"], 0.25)
    p["menu_border"] = _mix(p["border2"], text, 0.03)
    p["menu_sel"] = _mix(p["card2"], p["accent"], 0.22)
    p["status_card"] = _mix(p["sidebar"], p["card"], 0.55)
    p["disabled_text"] = _mix(p["dim"], p["bg"], 0.25)
    return p


def ui_font(size: float = 10.0, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    families = set(QFontDatabase.families())
    for name in ("Segoe UI Variable Text", "Segoe UI"):
        if name in families:
            f = QFont(name)
            break
    else:
        f = QFont()
    f.setPointSizeF(size)
    f.setWeight(weight)
    return f


def display_font(size: float = 10.0, weight: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    families = set(QFontDatabase.families())
    for name in ("Segoe UI Variable Display", "Segoe UI"):
        if name in families:
            f = QFont(name)
            break
    else:
        f = QFont()
    f.setPointSizeF(size)
    f.setWeight(weight)
    return f


def apply_theme(app: QApplication, theme_id: str | None = None, font: QFont | None = None) -> str:
    """Apply *theme_id* to the application and update the shared palette."""
    global CURRENT_THEME
    if theme_id not in THEMES:
        theme_id = DEFAULT_THEME
    CURRENT_THEME = theme_id
    palette = _derive(THEMES[theme_id]["colors"])
    C.clear()
    C.update(palette)

    app.setStyle("Fusion")
    app.setFont(font or ui_font(10))

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(C["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(C["input"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(C["card"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(C["card2"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(C["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(C["card2"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(C["dim"]))
    app.setPalette(pal)
    app.setStyleSheet(build_stylesheet(C))
    return theme_id


def build_stylesheet(p: dict[str, str]) -> str:
    return Template(STYLESHEET_TEMPLATE).substitute(p)


STYLESHEET_TEMPLATE = """
* {
    outline: none;
}
QWidget {
    color: $text;
    font-family: "Segoe UI Variable Text", "Segoe UI";
    font-size: 10pt;
}
QFrame#Root {
    background: $bg;
    border: 1px solid $root_border;
    border-radius: 16px;
}
QFrame#Root[maximized="true"] {
    border: 0px;
    border-radius: 0px;
}
QFrame#Sidebar {
    background: $sidebar;
    border: none;
    border-top-left-radius: 16px;
    border-bottom-left-radius: 16px;
    border-right: 1px solid $sidebar_border;
}
QFrame#Sidebar[maximized="true"] {
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
}
QFrame#TitleBar {
    background: transparent;
    border: none;
}
QFrame#Card {
    background: $card;
    border: 1px solid $border;
    border-radius: 14px;
}
QFrame#UrlBar {
    background: $bar_bg;
    border: 1px solid $bar_border;
    border-radius: 12px;
}
QFrame#UrlBar:hover {
    border: 1px solid $bar_border_hover;
}
QFrame#JobCard {
    background: $card;
    border: 1px solid $border;
    border-radius: 12px;
}
QFrame#JobCard:hover {
    border: 1px solid $bar_border_hover;
}
QFrame#HistoryCard {
    background: $card;
    border: 1px solid $border;
    border-radius: 12px;
}
QFrame#HistoryCard:hover {
    border: 1px solid $bar_border_hover;
}
QFrame#ActiveCard {
    background: $card2;
    border: 1px solid $border2;
    border-radius: 12px;
}
QFrame#StatusCard {
    background: $status_card;
    border: 1px solid $border;
    border-radius: 10px;
}
QFrame#StatusCard:hover {
    border: 1px solid $bar_border_hover;
}
QFrame#HLine {
    background: $border;
    border: none;
    max-height: 1px;
    min-height: 1px;
}
QLineEdit {
    background: $input;
    border: 1px solid $border2;
    border-radius: 9px;
    padding: 8px 10px;
    color: $text;
    selection-background-color: $accent;
    selection-color: #FFFFFF;
}
QLineEdit:hover {
    border-color: $bar_border_hover;
}
QLineEdit:focus {
    border: 1px solid $accent;
    background: $focus_bg;
}
QLineEdit#UrlInput {
    background: transparent;
    border: none;
    padding: 0px 4px;
    font-size: 11pt;
}
QLineEdit#PathInput {
    background: transparent;
    border: none;
    color: $chip_text;
    padding: 0px 2px;
    font-size: 9pt;
}
QLineEdit#PathInput:focus {
    color: $text;
}
QPushButton#Ghost {
    background: $card2;
    border: 1px solid $border2;
    border-radius: 9px;
    padding: 7px 14px;
    color: $chip_text;
    font-weight: 600;
}
QPushButton#Ghost:hover {
    background: $hover_bg;
    border-color: $bar_border_hover;
    color: $text;
}
QPushButton#Ghost:pressed {
    background: $pressed_bg;
}
QPushButton#Ghost:disabled {
    color: $disabled_text;
    background: $soft_bg;
    border-color: $border;
}
QPushButton#AccentOutline {
    background: $accent_soft;
    border: 1px solid $accent_border;
    border-radius: 9px;
    padding: 7px 16px;
    color: $accent_text;
    font-weight: 600;
}
QPushButton#AccentOutline:hover {
    background: $accent_soft2;
    color: #FFFFFF;
}
QPushButton#AccentOutline:disabled {
    background: $soft_bg;
    border-color: $border;
    color: $disabled_text;
}
QPushButton#DangerGhost {
    background: transparent;
    border: 1px solid $danger_border;
    border-radius: 8px;
    padding: 6px 12px;
    color: $danger_text;
    font-weight: 600;
}
QPushButton#DangerGhost:hover {
    background: $danger_soft;
    border-color: $danger;
    color: #FFFFFF;
}
QLabel {
    background: transparent;
}
QLabel#PageTitle {
    font-size: 22pt;
    font-weight: 700;
    color: $text;
}
QLabel#PageSubtitle {
    color: $muted;
    font-size: 9.5pt;
}
QLabel#SectionLabel {
    color: $dim;
    font-size: 8pt;
    font-weight: 700;
}
QLabel#Muted {
    color: $muted;
}
QLabel#Dim {
    color: $dim;
}
QLabel#Hint {
    color: $dim;
    font-size: 8.5pt;
}
QLabel#ErrorLabel {
    color: $danger;
    font-size: 9pt;
}
QLabel#Crumb {
    color: $muted;
    font-size: 9pt;
    font-weight: 600;
}
QLabel#LogoTitle {
    color: $text;
    font-size: 15.5pt;
    font-weight: 700;
}
QLabel#LogoSub {
    color: $dim;
    font-size: 7pt;
    font-weight: 700;
}
QLabel#Chip {
    background: $chip_bg;
    color: $chip_text;
    border: 1px solid $chip_border;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 8pt;
    font-weight: 600;
}
QLabel#ChipSuccess {
    background: $success_soft;
    color: $success_text;
    border: 1px solid $success_border;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 8pt;
    font-weight: 600;
}
QLabel#ChipWarn {
    background: $warning_soft;
    color: $warning_text;
    border: 1px solid $warning_border;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 8pt;
    font-weight: 600;
}
QComboBox {
    background: $input;
    border: 1px solid $border2;
    border-radius: 9px;
    padding: 5px 10px;
    min-height: 22px;
    color: $text;
}
QComboBox:hover {
    border-color: $bar_border_hover;
}
QComboBox:focus {
    border-color: $accent;
}
QComboBox:disabled {
    color: $disabled_text;
    background: $soft_bg;
    border-color: $border;
}
QComboBox::drop-down {
    border: none;
    width: 26px;
}
QComboBox QAbstractItemView {
    background: $menu_bg;
    border: 1px solid $menu_border;
    border-radius: 8px;
    selection-background-color: $menu_sel;
    selection-color: $text;
    outline: none;
    padding: 4px;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: $scroll;
    border-radius: 3px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: $scroll_hover;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: $scroll;
    border-radius: 3px;
}
QToolTip {
    background: $tooltip_bg;
    color: $text;
    border: 1px solid $tooltip_border;
    padding: 6px 8px;
    border-radius: 6px;
}
QMessageBox {
    background: $card;
}
QMessageBox QLabel {
    color: $text;
}
QMenu {
    background: $menu_bg;
    border: 1px solid $menu_border;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 6px;
}
QMenu::item:selected {
    background: $menu_sel;
}
"""
