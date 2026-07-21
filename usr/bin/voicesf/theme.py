"""
theme.py -- cyberpunk CRT theming for SERIF-VOICE.

Matches the Serif Graphics Suite's existing four-way theme system
(Green / Amber / Cyan / Mono) so the app feels like a sibling of the hub,
TXT viewer, Theater, and OBJ viewer. Cyan is the default here to lean into
the "cyberdeck" vocal-FX vibe the app is going for.

Everything is done with QSS + QPainter -- no shaders, no GPU cost, so it
runs fine on a Radeon HD 6450 / integrated-tier hardware.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QFont
from PyQt5.QtWidgets import QWidget

THEMES = {
    "cyan": {
        "bg": "#050b0d",
        "panel": "#0a1618",
        "fg": "#9ffcf0",
        "accent": "#00e5ff",
        "accent_dim": "#0a4a52",
        "warn": "#ff3ec8",
        "grid": "#0e2a2e",
    },
    "green": {
        "bg": "#040a04",
        "panel": "#081208",
        "fg": "#9dffa0",
        "accent": "#39ff6a",
        "accent_dim": "#0e3a16",
        "warn": "#ff5533",
        "grid": "#0c2410",
    },
    "amber": {
        "bg": "#0c0704",
        "panel": "#181005",
        "fg": "#ffd48a",
        "accent": "#ffaa33",
        "accent_dim": "#4a2e0a",
        "warn": "#ff4444",
        "grid": "#2a1a08",
    },
    "mono": {
        "bg": "#0a0a0a",
        "panel": "#161616",
        "fg": "#e6e6e6",
        "accent": "#ffffff",
        "accent_dim": "#3a3a3a",
        "warn": "#ff5555",
        "grid": "#222222",
    },
}

MONO_FONT = "DejaVu Sans Mono, Consolas, monospace"


def stylesheet(theme_name: str) -> str:
    t = THEMES[theme_name]
    return f"""
    QMainWindow, QWidget {{
        background-color: {t['bg']};
        color: {t['fg']};
        font-family: {MONO_FONT};
    }}
    QTabWidget::pane {{
        border: 1px solid {t['accent_dim']};
        background: {t['panel']};
    }}
    QTabBar::tab {{
        background: {t['panel']};
        color: {t['accent_dim']};
        border: 1px solid {t['accent_dim']};
        padding: 6px 16px;
        font-weight: bold;
        letter-spacing: 1px;
    }}
    QTabBar::tab:selected {{
        color: {t['accent']};
        border-bottom: 2px solid {t['accent']};
    }}
    QGroupBox {{
        border: 1px solid {t['accent_dim']};
        margin-top: 10px;
        font-weight: bold;
        color: {t['accent']};
        letter-spacing: 1px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }}
    QPushButton {{
        background: {t['panel']};
        color: {t['accent']};
        border: 1px solid {t['accent']};
        padding: 5px 12px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background: {t['accent_dim']};
    }}
    QPushButton:checked {{
        background: {t['accent']};
        color: {t['bg']};
    }}
    QPushButton:disabled {{
        color: {t['accent_dim']};
        border-color: {t['accent_dim']};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {t['accent_dim']};
    }}
    QSlider::handle:horizontal {{
        background: {t['accent']};
        width: 12px;
        margin: -6px 0;
    }}
    QComboBox {{
        background: {t['panel']};
        color: {t['fg']};
        border: 1px solid {t['accent_dim']};
        padding: 3px;
    }}
    QLabel {{
        color: {t['fg']};
    }}
    QLabel[role="heading"] {{
        color: {t['accent']};
        font-weight: bold;
        letter-spacing: 2px;
    }}
    QStatusBar {{
        background: {t['panel']};
        color: {t['accent_dim']};
    }}
    QProgressBar {{
        border: 1px solid {t['accent_dim']};
        background: {t['panel']};
        color: {t['fg']};
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {t['accent']};
    }}
    """


class ScanlineOverlay(QWidget):
    """Transparent CRT scanline + vignette layer painted above the UI.

    Cheap: a handful of translucent QPainter fillRects, no offscreen
    surfaces or shader passes -- fine even on very old integrated GPUs.
    """

    def __init__(self, parent=None, theme_name="cyan"):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.theme_name = theme_name
        self.setAttribute(Qt.WA_NoSystemBackground)

    def set_theme(self, theme_name):
        self.theme_name = theme_name
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        h = self.height()
        w = self.width()

        # scanlines
        p.setPen(Qt.NoPen)
        line_color = QColor(0, 0, 0, 28)
        p.setBrush(line_color)
        for y in range(0, h, 3):
            p.drawRect(0, y, w, 1)

        # soft vignette corners
        vig = QColor(0, 0, 0, 60)
        p.setBrush(vig)
        edge = 40
        p.drawRect(0, 0, w, edge)
        p.drawRect(0, h - edge, w, edge)
        p.end()
