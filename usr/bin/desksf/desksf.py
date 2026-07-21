#!/usr/bin/env python3
import sys
import math
import ctypes
import ctypes.util
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame, QSlider, QShortcut)


class X11ClickThrough:
    """Talks to the X11 Shape extension directly to set the window's INPUT
    shape - a server-side region distinct from the rendering/compositing
    shape. This is more reliable than Qt's WA_TransparentForMouseEvents
    alone, since some window managers (xfwm4 in particular) are inconsistent
    about honoring that hint for frameless/Tool windows. No-ops safely on
    Wayland, where Qt's own handling via wl_surface input regions is already
    solid."""
    def __init__(self):
        self.available = False
        self.display = None
        self.libX11 = None
        self.libXext = None

        if QApplication.platformName() != 'xcb':
            return  # Wayland (or other) - let Qt handle it natively

        try:
            x11_path = ctypes.util.find_library('X11')
            xext_path = ctypes.util.find_library('Xext')
            if not x11_path or not xext_path:
                return
            self.libX11 = ctypes.CDLL(x11_path)
            self.libXext = ctypes.CDLL(xext_path)
            self.libX11.XOpenDisplay.restype = ctypes.c_void_p
            self.display = self.libX11.XOpenDisplay(None)
            if not self.display:
                return
            self.available = True
        except OSError:
            self.available = False

    class _XRectangle(ctypes.Structure):
        _fields_ = [("x", ctypes.c_short), ("y", ctypes.c_short),
                    ("width", ctypes.c_ushort), ("height", ctypes.c_ushort)]

    def apply(self, win_id, clickable_rects):
        """clickable_rects: list of (x, y, w, h) in window-local coords.
        Everything outside these rects becomes a genuine click-through hole."""
        if not self.available:
            return False

        SHAPE_INPUT = 2   # ShapeInput
        SHAPE_SET = 0     # ShapeSet
        UNSORTED = 0

        n = len(clickable_rects)
        rects_arr = (self._XRectangle * n)()
        for i, (x, y, w, h) in enumerate(clickable_rects):
            rects_arr[i] = self._XRectangle(int(x), int(y), int(w), int(h))

        self.libXext.XShapeCombineRectangles(
            ctypes.c_void_p(self.display), ctypes.c_ulong(int(win_id)),
            SHAPE_INPUT, 0, 0, rects_arr, n, SHAPE_SET, UNSORTED
        )
        self.libX11.XFlush(ctypes.c_void_p(self.display))
        return True


class DragPanel(QFrame):
    """A QFrame that drags its owning top-level window when clicked on empty
    space (buttons/sliders inside it still get their own clicks first - Qt
    hit-tests children before falling back to the frame itself)."""
    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self.owner = owner
        self._drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.owner.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_offset is not None:
            self.owner.move(event.globalPos() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None


class CRTOverlayWidget(QWidget):
    """The transparent, click-through overlay that draws scanlines, grids,
    bezels, and color washes on top of whatever is beneath it on the desktop."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Click-through: lets mouse events fall through to whatever app is
        # running underneath this widget. This is the whole point of "glass".
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.active_overlay = 0
        # 0 None, 1 Monochrome, 2 Sepia, 3 Mono Green, 4 Amber,
        # 5 Virtual Boy, 6 Technicolor, 7 HDR
        self.active_lut = 0
        self.active_glsl = 0    # 0: None, 1: Flicker/Bloom, 2: Vignette, 3: Bad Signal Noise

        # Intensity scales (0.0 - 2.0), each slider defaults to 1.0 = the
        # original hardcoded look from the first version of this tool.
        self.wash_scale = 1.0
        self.scanline_scale = 1.0
        self.vignette_scale = 1.0
        self.noise_scale = 1.0
        self.flicker_scale = 1.0

        # Pixel-density scale for the resolution/DPI control. 1.0 = the
        # original hardcoded pitch (scanlines every 4px, grid every 40px,
        # grille every 3px). >1.0 = coarser/chunkier (retro CRT look, or
        # compensating for a low-res display); <1.0 = finer/denser
        # (compensating for a high-DPI display, or a subtler look).
        self.res_scale = 1.0

        self.radar_angle = 0.0
        self.noise_tick = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(33)  # ~30 FPS

    def update_animation(self):
        self.noise_tick = (self.noise_tick + 1) % 100
        if self.active_overlay == 3:  # Radar sweep
            self.radar_angle += 0.05
            if self.radar_angle > 2 * math.pi:
                self.radar_angle = 0.0
            self.update()
        elif self.active_glsl > 0 or self.active_overlay > 0:
            self.update()

    def _wash(self, painter, w, h, color):
        c = QColor(color)
        c.setAlpha(min(255, int(c.alpha() * self.wash_scale)))
        painter.fillRect(0, 0, w, h, c)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # --- 1. SCREEN COLOR WASHES ---
        # NOTE: these are translucent tints layered on top of the desktop,
        # not a true per-pixel color transform. A real desaturate/channel-
        # split (like the WebGL Theater shader does) would require capturing
        # the screen and reprocessing it, which is a much heavier pipeline
        # and would break click-through. These are stylized approximations.
        if self.active_lut == 1:  # Monochrome (approximation - can't truly desaturate)
            self._wash(painter, w, h, QColor(120, 120, 120, 55))
        elif self.active_lut == 2:  # Sepia
            self._wash(painter, w, h, QColor(112, 66, 20, 45))
        elif self.active_lut == 3:  # Mono Green
            self._wash(painter, w, h, QColor(0, 255, 60, 20))
        elif self.active_lut == 4:  # Amber
            self._wash(painter, w, h, QColor(255, 120, 0, 25))
        elif self.active_lut == 5:  # Virtual Boy
            self._wash(painter, w, h, QColor(200, 0, 0, 60))
        elif self.active_lut == 6:  # Technicolor (faked channel split via offset washes)
            self._wash(painter, w, h, QColor(255, 0, 60, 20))
            painter.save()
            painter.translate(2, 0)
            self._wash(painter, w, h, QColor(0, 200, 255, 20))
            painter.restore()
        elif self.active_lut == 7:  # HDR (punchy highlight lift)
            self._wash(painter, w, h, QColor(255, 240, 210, 30))

        # --- 2. GLSL-STYLE ANIMATED EFFECTS ---
        if self.active_glsl == 1:  # Dynamic CRT Flicker / Bloom
            flicker = int((math.sin(self.noise_tick * 0.5) * 4 + 12) * self.flicker_scale)
            painter.fillRect(0, 0, w, h, QColor(0, 255, 128, max(0, min(255, flicker))))
        elif self.active_glsl == 2:  # CRT Vignette
            gradient = QRadialGradient(w / 2, h / 2, w * 0.6)
            gradient.setColorAt(0, QColor(0, 0, 0, 0))
            end_alpha = max(0, min(255, int(180 * self.vignette_scale)))
            gradient.setColorAt(1, QColor(0, 0, 0, end_alpha))
            painter.fillRect(0, 0, w, h, QBrush(gradient))
        elif self.active_glsl == 3:  # Bad Signal Noise Line
            n_alpha = max(0, min(255, int(30 * self.noise_scale)))
            painter.setPen(QPen(QColor(255, 255, 255, n_alpha), 2))
            noise_y = int((self.noise_tick * 7) % h)
            painter.drawLine(0, noise_y, w, noise_y)

        # --- 3. CORE SCANLINES ---
        sl_alpha = max(0, min(255, int(40 * self.scanline_scale)))
        painter.setPen(QPen(QColor(0, 8, 2, sl_alpha), 1))
        scan_step = max(1, int(round(4 * self.res_scale)))
        for y in range(0, h, scan_step):
            painter.drawLine(0, y, w, y)

        # --- 4. DYNAMIC OVERLAYS ---
        if self.active_overlay == 1:  # Tech Alignment Grid
            painter.setPen(QPen(QColor(0, 255, 128, 50), 1))
            grid_step = max(1, int(round(40 * self.res_scale)))
            for x in range(grid_step, w, grid_step):
                painter.drawLine(x, 0, x, h)
            for y in range(grid_step, h, grid_step):
                painter.drawLine(0, y, w, y)

        elif self.active_overlay == 2:  # CRT Curved Bezel
            gradient = QRadialGradient(w / 2, h / 2, w * 0.65, w / 2, h / 2)
            gradient.setColorAt(0, QColor(0, 0, 0, 0))
            gradient.setColorAt(0.75, QColor(0, 15, 5, 30))
            gradient.setColorAt(1, QColor(0, 0, 0, 245))
            painter.fillRect(0, 0, w, h, QBrush(gradient))
            painter.setPen(QPen(QColor(0, 255, 128, 80), 3))
            painter.drawRect(8, 8, w - 16, h - 16)

        elif self.active_overlay == 3:  # Radar Scanning Scope
            cx, cy = w // 2, h // 2
            painter.setPen(QPen(QColor(0, 255, 128, 60), 1.5))
            painter.drawEllipse(cx - 150, cy - 150, 300, 300)
            painter.drawEllipse(cx - 75, cy - 75, 150, 150)
            rx = cx + int(math.cos(self.radar_angle) * 180)
            ry = cy + int(math.sin(self.radar_angle) * 180)
            painter.drawLine(cx, cy, rx, ry)

        elif self.active_overlay == 4:  # Aperture Grille Simulation
            painter.setPen(QPen(QColor(0, 5, 1, 65), 1))
            grille_step = max(1, int(round(3 * self.res_scale)))
            for x in range(0, w, grille_step):
                painter.drawLine(x, 0, x, h)

        elif self.active_overlay == 5:  # Broadcast Safe HUD
            pen = QPen(QColor(0, 255, 128, 70), 1.5, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(30, 20, w - 60, h - 40)
            painter.drawRect(60, 40, w - 120, h - 80)


class DesktopLens(QMainWindow):
    """The unified retro lens featuring drag areas and window state buttons."""
    def __init__(self):
        super().__init__()
        # Qt.Tool keeps this out of the taskbar/alt-tab list, which matters
        # for an always-on-top desktop overlay. Qt.SubWindow (the original
        # flag) is meant for MDI subwindows and can behave inconsistently
        # here across window managers.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(80, 80, 1024, 760)

        self._x11_click_through = X11ClickThrough()

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.panel_style = "background-color: rgba(0, 12, 3, 0.95); border: 1px solid #00ff80;"
        self.btn_style = """
            QPushButton {
                background-color: #001a05;
                color: #00ff80;
                border: 1px solid #00ff80;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 10px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #00ff80;
                color: #000000;
            }
            QPushButton:pressed {
                background-color: #00cc66;
            }
        """
        self.label_style = "color: #00ff80; font-family: 'Courier New'; font-size: 10px; font-weight: bold;"
        self.slider_style = """
            QSlider::groove:horizontal {
                background: #001a05;
                border: 1px solid #00ff80;
                height: 4px;
            }
            QSlider::handle:horizontal {
                background: #00ff80;
                width: 10px;
                margin: -5px 0;
            }
        """

        # 1. TOP PANEL (title + overlay controls + window controls)
        self.top_panel = DragPanel(self, self.central_widget)
        self.top_panel.setStyleSheet(self.panel_style)
        self.top_panel.setFixedHeight(38)

        top_layout = QHBoxLayout(self.top_panel)
        top_layout.setContentsMargins(10, 0, 10, 0)

        self.title_lbl = QLabel("GLORIA RETRO CONSOLE", self.top_panel)
        self.title_lbl.setStyleSheet("color: #00ff80; font-family: 'Courier New'; font-weight: bold; font-size: 11px;")

        self.btn_ov_none = QPushButton("OFF", self.top_panel)
        self.btn_ov_grid = QPushButton("GRID", self.top_panel)
        self.btn_ov_bezel = QPushButton("BEZEL", self.top_panel)
        self.btn_ov_radar = QPushButton("RADAR", self.top_panel)
        self.btn_ov_mask = QPushButton("RGB MASK", self.top_panel)
        self.btn_ov_hud = QPushButton("HUD", self.top_panel)

        for btn in [self.btn_ov_none, self.btn_ov_grid, self.btn_ov_bezel, self.btn_ov_radar, self.btn_ov_mask, self.btn_ov_hud]:
            btn.setStyleSheet(self.btn_style)

        self.btn_ov_none.clicked.connect(lambda: self.set_overlay(0))
        self.btn_ov_grid.clicked.connect(lambda: self.set_overlay(1))
        self.btn_ov_bezel.clicked.connect(lambda: self.set_overlay(2))
        self.btn_ov_radar.clicked.connect(lambda: self.set_overlay(3))
        self.btn_ov_mask.clicked.connect(lambda: self.set_overlay(4))
        self.btn_ov_hud.clicked.connect(lambda: self.set_overlay(5))

        top_layout.addWidget(self.title_lbl)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_ov_none)
        top_layout.addWidget(self.btn_ov_grid)
        top_layout.addWidget(self.btn_ov_bezel)
        top_layout.addWidget(self.btn_ov_radar)
        top_layout.addWidget(self.btn_ov_mask)
        top_layout.addWidget(self.btn_ov_hud)
        top_layout.addStretch()

        win_controls_layout = QHBoxLayout()
        win_controls_layout.setSpacing(4)

        btn_min = QPushButton("_", self.top_panel)
        btn_min.setStyleSheet("background-color: #002200; color: #00ff80; border: 1px solid #00ff80; font-weight: bold; font-size: 10px; width: 22px; height: 20px;")
        btn_min.clicked.connect(self.showMinimized)

        btn_max = QPushButton("\u25a2", self.top_panel)
        btn_max.setStyleSheet("background-color: #002200; color: #00ff80; border: 1px solid #00ff80; font-weight: bold; font-size: 10px; width: 22px; height: 20px;")
        btn_max.clicked.connect(self.toggle_maximize)

        btn_close = QPushButton("X", self.top_panel)
        btn_close.setStyleSheet("background-color: #330000; color: #ff5555; border: 1px solid #ff5555; font-weight: bold; font-size: 10px; width: 22px; height: 20px;")
        btn_close.clicked.connect(self.close)

        win_controls_layout.addWidget(btn_min)
        win_controls_layout.addWidget(btn_max)
        win_controls_layout.addWidget(btn_close)
        top_layout.addLayout(win_controls_layout)

        # 2. MIDDLE VIEWPORT (click-through overlay canvas)
        self.overlay_screen = CRTOverlayWidget(self)

        # 3. SCREEN COLOR PANEL (LUT washes, renamed/expanded to match the
        #    Theater app's color preset naming)
        self.color_panel = DragPanel(self, self.central_widget)
        self.color_panel.setStyleSheet(self.panel_style)
        self.color_panel.setFixedHeight(38)

        color_layout = QHBoxLayout(self.color_panel)
        color_layout.setContentsMargins(15, 0, 15, 0)

        color_lbl = QLabel("SCREEN COLOR:", self.color_panel)
        color_lbl.setStyleSheet(self.label_style)

        self.btn_lut_none = QPushButton("FULL", self.color_panel)
        self.btn_lut_mono = QPushButton("MONO", self.color_panel)
        self.btn_lut_sepia = QPushButton("SEPIA", self.color_panel)
        self.btn_lut_green = QPushButton("M.GREEN", self.color_panel)
        self.btn_lut_amber = QPushButton("AMBER", self.color_panel)
        self.btn_lut_vboy = QPushButton("V.BOY", self.color_panel)
        self.btn_lut_techni = QPushButton("TECHNI", self.color_panel)
        self.btn_lut_hdr = QPushButton("HDR", self.color_panel)

        lut_buttons = [self.btn_lut_none, self.btn_lut_mono, self.btn_lut_sepia, self.btn_lut_green,
                       self.btn_lut_amber, self.btn_lut_vboy, self.btn_lut_techni, self.btn_lut_hdr]
        for btn in lut_buttons:
            btn.setStyleSheet(self.btn_style)

        self.btn_lut_none.clicked.connect(lambda: self.set_lut(0))
        self.btn_lut_mono.clicked.connect(lambda: self.set_lut(1))
        self.btn_lut_sepia.clicked.connect(lambda: self.set_lut(2))
        self.btn_lut_green.clicked.connect(lambda: self.set_lut(3))
        self.btn_lut_amber.clicked.connect(lambda: self.set_lut(4))
        self.btn_lut_vboy.clicked.connect(lambda: self.set_lut(5))
        self.btn_lut_techni.clicked.connect(lambda: self.set_lut(6))
        self.btn_lut_hdr.clicked.connect(lambda: self.set_lut(7))

        color_layout.addWidget(color_lbl)
        for btn in lut_buttons:
            color_layout.addWidget(btn)
        color_layout.addStretch()

        # 4. GLSL MODE PANEL
        self.glsl_panel = DragPanel(self, self.central_widget)
        self.glsl_panel.setStyleSheet(self.panel_style)
        self.glsl_panel.setFixedHeight(38)

        glsl_layout = QHBoxLayout(self.glsl_panel)
        glsl_layout.setContentsMargins(15, 0, 15, 0)

        glsl_lbl = QLabel("GLSL MODE:", self.glsl_panel)
        glsl_lbl.setStyleSheet(self.label_style)

        self.btn_glsl_none = QPushButton("BYPASS", self.glsl_panel)
        self.btn_glsl_bloom = QPushButton("FLICKER", self.glsl_panel)
        self.btn_glsl_vig = QPushButton("VIGNETTE", self.glsl_panel)
        self.btn_glsl_noise = QPushButton("NOISE", self.glsl_panel)

        glsl_buttons = [self.btn_glsl_none, self.btn_glsl_bloom, self.btn_glsl_vig, self.btn_glsl_noise]
        for btn in glsl_buttons:
            btn.setStyleSheet(self.btn_style)

        self.btn_glsl_none.clicked.connect(lambda: self.set_glsl(0))
        self.btn_glsl_bloom.clicked.connect(lambda: self.set_glsl(1))
        self.btn_glsl_vig.clicked.connect(lambda: self.set_glsl(2))
        self.btn_glsl_noise.clicked.connect(lambda: self.set_glsl(3))

        glsl_layout.addWidget(glsl_lbl)
        for btn in glsl_buttons:
            glsl_layout.addWidget(btn)
        glsl_layout.addStretch()

        # 5. SETTINGS PANEL (intensity sliders - same concept as Theater's
        #    right-hand settings panel: Brightness/Noise/Vignette/Ghosting)
        self.settings_panel = DragPanel(self, self.central_widget)
        self.settings_panel.setStyleSheet(self.panel_style)
        self.settings_panel.setFixedHeight(46)

        settings_layout = QHBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(15, 4, 15, 4)
        settings_layout.setSpacing(18)

        self.slider_wash = self._make_slider("WASH", settings_layout, self.on_wash_changed)
        self.slider_scan = self._make_slider("SCANLINES", settings_layout, self.on_scanline_changed)
        self.slider_vig = self._make_slider("VIGNETTE", settings_layout, self.on_vignette_changed)
        self.slider_noise = self._make_slider("NOISE", settings_layout, self.on_noise_changed)
        self.slider_flicker = self._make_slider("FLICKER", settings_layout, self.on_flicker_changed)
        settings_layout.addStretch()

        # 6. DENSITY PANEL (resolution/DPI control - scales the pixel pitch
        #    of scanlines/grid/grille. One multiplier serves double duty:
        #    dial in a chunkier or finer retro look, and/or compensate for
        #    how those fixed-pixel effects read differently on a low-DPI vs
        #    high-DPI monitor.)
        self.density_panel = DragPanel(self, self.central_widget)
        self.density_panel.setStyleSheet(self.panel_style)
        self.density_panel.setFixedHeight(38)

        density_layout = QHBoxLayout(self.density_panel)
        density_layout.setContentsMargins(15, 0, 15, 0)

        density_lbl = QLabel("DENSITY (RES/DPI):", self.density_panel)
        density_lbl.setStyleSheet(self.label_style)

        self.btn_density_coarse = QPushButton("COARSE", self.density_panel)
        self.btn_density_medium = QPushButton("MEDIUM", self.density_panel)
        self.btn_density_std = QPushButton("STANDARD", self.density_panel)
        self.btn_density_fine = QPushButton("FINE", self.density_panel)
        self.btn_density_ultra = QPushButton("ULTRA-FINE", self.density_panel)

        density_buttons = [self.btn_density_coarse, self.btn_density_medium, self.btn_density_std,
                           self.btn_density_fine, self.btn_density_ultra]
        for btn in density_buttons:
            btn.setStyleSheet(self.btn_style)

        self.btn_density_coarse.clicked.connect(lambda: self.set_density(2.0, self.btn_density_coarse))
        self.btn_density_medium.clicked.connect(lambda: self.set_density(1.5, self.btn_density_medium))
        self.btn_density_std.clicked.connect(lambda: self.set_density(1.0, self.btn_density_std))
        self.btn_density_fine.clicked.connect(lambda: self.set_density(0.66, self.btn_density_fine))
        self.btn_density_ultra.clicked.connect(lambda: self.set_density(0.4, self.btn_density_ultra))

        density_layout.addWidget(density_lbl)
        for btn in density_buttons:
            density_layout.addWidget(btn)
        density_layout.addStretch()

        self._density_buttons = density_buttons
        self.btn_density_std.setStyleSheet(self.btn_style + "QPushButton { background-color: #00ff80; color: #000000; }")

        # Add all rows to the main layout
        self.main_layout.addWidget(self.top_panel)
        self.main_layout.addWidget(self.overlay_screen, 1)
        self.main_layout.addWidget(self.color_panel)
        self.main_layout.addWidget(self.glsl_panel)
        self.main_layout.addWidget(self.settings_panel)
        self.main_layout.addWidget(self.density_panel)

        # All the rows that get hidden in glass (true fullscreen) mode.
        self._ui_panels = [self.top_panel, self.color_panel, self.glsl_panel,
                            self.settings_panel, self.density_panel]
        self._glass_mode = False
        self._windowed_geom = None

        # Persistent corner button: NOT part of main_layout, floats on top of
        # everything and stays visible/clickable in both modes. This is the
        # guaranteed way back from glass mode - a global hotkey would depend
        # on the window actually holding keyboard focus, which isn't
        # guaranteed once the window is click-through almost everywhere.
        self.glass_toggle_btn = QPushButton("\u25a1", self.central_widget)
        self.glass_toggle_btn.setToolTip("Toggle fullscreen glass mode (hide UI)")
        self.glass_toggle_btn.setFixedSize(28, 28)
        self.glass_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 20, 8, 200);
                color: #00ff80;
                border: 1px solid #00ff80;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #00ff80; color: #000000; }
        """)
        self.glass_toggle_btn.clicked.connect(self.toggle_glass_mode)
        self.glass_toggle_btn.raise_()
        self._position_glass_toggle_btn()

        # Convenience hotkey. Not guaranteed to fire once the window has
        # almost no clickable surface left to gain keyboard focus through -
        # the corner button above is the reliable path back.
        self._glass_shortcut = QShortcut(QKeySequence("F11"), self)
        self._glass_shortcut.activated.connect(self.toggle_glass_mode)

    def _make_slider(self, label_text, layout, callback):
        """Builds a small labeled vertical group (label above slider) and
        adds it to the given layout. Range 0-100, default 50 (== 1.0x scale,
        matching the original hardcoded intensities)."""
        group = QVBoxLayout()
        group.setSpacing(2)
        lbl = QLabel(label_text, self.settings_panel)
        lbl.setStyleSheet(self.label_style + " font-size: 9px;")
        slider = QSlider(Qt.Horizontal, self.settings_panel)
        slider.setStyleSheet(self.slider_style)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(50)
        slider.setFixedWidth(120)
        slider.valueChanged.connect(callback)
        group.addWidget(lbl)
        group.addWidget(slider)
        wrapper = QWidget(self.settings_panel)
        wrapper.setLayout(group)
        layout.addWidget(wrapper)
        return slider

    def on_wash_changed(self, value):
        self.overlay_screen.wash_scale = value / 50.0
        self.overlay_screen.update()

    def on_scanline_changed(self, value):
        self.overlay_screen.scanline_scale = value / 50.0
        self.overlay_screen.update()

    def on_vignette_changed(self, value):
        self.overlay_screen.vignette_scale = value / 50.0
        self.overlay_screen.update()

    def on_noise_changed(self, value):
        self.overlay_screen.noise_scale = value / 50.0
        self.overlay_screen.update()

    def on_flicker_changed(self, value):
        self.overlay_screen.flicker_scale = value / 50.0
        self.overlay_screen.update()

    def set_overlay(self, index):
        self.overlay_screen.active_overlay = index
        self.overlay_screen.update()

    def set_lut(self, index):
        self.overlay_screen.active_lut = index
        self.overlay_screen.update()

    def set_glsl(self, index):
        self.overlay_screen.active_glsl = index
        self.overlay_screen.update()

    def set_density(self, scale, active_btn):
        self.overlay_screen.res_scale = scale
        self.overlay_screen.update()
        base = self.btn_style
        highlight = base + "QPushButton { background-color: #00ff80; color: #000000; }"
        for btn in self._density_buttons:
            btn.setStyleSheet(highlight if btn is active_btn else base)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _position_glass_toggle_btn(self):
        margin = 6
        self.glass_toggle_btn.move(self.width() - self.glass_toggle_btn.width() - margin, margin)
        self.glass_toggle_btn.raise_()

    def toggle_glass_mode(self):
        """True fullscreen, UI-hidden 'glass' mode. Everything except the
        small corner toggle button becomes click-through and the window
        covers the whole screen. Click the corner button again (it's the
        one thing guaranteed to still be reachable) to bring the panels
        back."""
        if not self._glass_mode:
            self._windowed_geom = self.geometry()
            for panel in self._ui_panels:
                panel.setVisible(False)
            screen_geo = QApplication.desktop().screenGeometry(self)
            self.setGeometry(screen_geo)
            self._glass_mode = True
            self.glass_toggle_btn.setText("\u25a3")  # filled square = "exit glass mode"
        else:
            for panel in self._ui_panels:
                panel.setVisible(True)
            if self._windowed_geom is not None:
                self.setGeometry(self._windowed_geom)
            self._glass_mode = False
            self.glass_toggle_btn.setText("\u25a1")  # hollow square = "enter glass mode"
        self._position_glass_toggle_btn()
        self.update_click_regions()

    def update_click_regions(self):
        """Restrict real mouse input (at the X server level, on X11) to just
        the control panels plus the corner toggle button. Everything else -
        the whole viewport - becomes a genuine click-through hole regardless
        of window-manager quirks. No-op on Wayland; Qt's own
        WA_TransparentForMouseEvents handling covers that case already."""
        if not self._x11_click_through.available:
            return
        rects = []
        if self._glass_mode:
            # Only the corner button is clickable in glass mode.
            pass
        else:
            for panel in self._ui_panels:
                geo = panel.geometry()
                rects.append((geo.x(), geo.y(), geo.width(), geo.height()))
        btn_geo = self.glass_toggle_btn.geometry()
        rects.append((btn_geo.x(), btn_geo.y(), btn_geo.width(), btn_geo.height()))
        self._x11_click_through.apply(int(self.winId()), rects)

    def showEvent(self, event):
        super().showEvent(event)
        # Defer slightly so the native window/winId is fully realized before
        # we try to shape its input region.
        QTimer.singleShot(0, self.update_click_regions)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_glass_toggle_btn()
        self.update_click_regions()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    lens = DesktopLens()
    lens.show()
    sys.exit(app.exec_())
