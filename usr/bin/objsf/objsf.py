#!/usr/bin/env python3
import sys
import os
import math
import numpy as np
from PyQt5.QtCore import Qt, QPoint, QRect, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QPixmap, QImage, QPainterPath, QBrush
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, 
                             QFileDialog, QShortcut, QMenu)

# Retro Theme Color Palettes
THEMES = {
    "GREEN": {"primary": "#00ff80", "bg": "#001100", "panel_bg": "#002211", "dim": "#006633"},
    "AMBER": {"primary": "#ffb000", "bg": "#110700", "panel_bg": "#2b1400", "dim": "#804000"},
    "CYAN":  {"primary": "#00dcff", "bg": "#00111a", "panel_bg": "#002b33", "dim": "#006680"},
    "MONO":  {"primary": "#dcdcdc", "bg": "#0a0a0a", "panel_bg": "#222222", "dim": "#666666"}
}
THEME_ORDER = ["GREEN", "AMBER", "CYAN", "MONO"]

# Shading Render Modes
RENDER_MODES = [
    "PEN & INK",
    "SOLID WORKBENCH",
    "GREEN WIREFRAME",
    "X-RAY TRANSPARENT",
    "BOUNDS BOX COLLISION",
    "PROCEDURAL UV TEXTURE",
    "PHOSPHOR T_MIST"
]

# F6 Lens Analyzer Filter Configurations
LENS_TYPES = [
    {"name": "MAGNIFY 3X", "zoom": 3.0, "effect": "none"},
    {"name": "MAGNIFY 6X", "zoom": 6.0, "effect": "none"},
    {"name": "CRT SCANLINES", "zoom": 3.0, "effect": "scanlines"},
    {"name": "THERMAL HUD", "zoom": 3.0, "effect": "thermal"},
    {"name": "1-BIT VECTOR", "zoom": 3.0, "effect": "binary"}
]

class ViewportCanvas(QWidget):
    """Real-time 3D Viewport. Handles vectorized projections, lighting shading, 

    custom shader simulation, and coordinate transformations."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vertices = np.array([], dtype=np.float32) # Shape: (N, 3)
        self.faces = []                                # List of list of indices
        
        # Camera & Rotation Parameters
        self.yaw = 3.92
        self.pitch = 0.40
        self.grid_range = 6
        self.current_render_mode = 3 # Green Wireframe default
        self.edge_enhance = False
        
        # Interactive Lens State
        self.lens_active = False
        self.lens_pos = QPoint(150, 150)
        self.lens_radius = 65 # LENS_SIZE / 2
        self.current_lens_idx = 0
        
        # F5 Custom shader state
        self.custom_shader_active = False
        self.shader_config = {
            "r_scale": 1.0,
            "g_scale": 1.0,
            "b_scale": 1.0,
            "scanlines": False,
            "scan_interval": 4,
            "color_invert": False
        }
        
        # Mouse Interaction for dragging to orbit camera
        self.last_mouse_pos = QPoint()
        self.setMouseTracking(True)

    def load_obj(self, file_path):
        """Standard lightning-fast Wavefront OBJ parser."""
        verts = []
        faces = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('v '):
                        parts = line.split()[1:4]
                        verts.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    elif line.startswith('f '):
                        parts = line.split()[1:]
                        face_indices = []
                        for p in parts:
                            # Safely split vertex index from uv/normal mappings
                            idx = int(p.split('/')[0]) - 1
                            if idx >= 0:
                                face_indices.append(idx)
                        if len(face_indices) >= 3:
                            faces.append(face_indices)
                            
            self.vertices = np.array(verts, dtype=np.float32)
            self.faces = faces
            self.update()
            return len(verts), len(faces)
        except Exception as e:
            print(f"Error parsing OBJ: {e}")
            return 0, 0

    def project_vertices(self):
        """Vectorized 3D Yaw/Pitch coordinate rotation and perspective transform."""
        if len(self.vertices) == 0:
            return np.array([])
            
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)
        
        # Extract components for array manipulation
        x = self.vertices[:, 0]
        y = self.vertices[:, 1]
        z = self.vertices[:, 2]
        
        # Rotation Calculations
        x1 = x * cos_y - z * sin_y
        z1 = x * sin_y + z * cos_y
        y1 = y * cos_p - z1 * sin_p
        z2 = y * sin_p + z1 * cos_p
        
        fov = 450.0
        d = 7.0
        half_w = self.width() / 2
        half_h = self.height() / 2
        
        # Depth perspective divide
        depth = z2 + d
        depth = np.where(depth < 0.1, 0.1, depth) # Avoid division by zero
        
        proj_x = half_w + (x1 * fov) / depth
        proj_y = half_h - (y1 * fov) / depth
        
        # Return projected array space: (X, Y, Camera_Depth)
        return np.stack([proj_x, proj_y, depth], axis=-1)

    def calculate_normal(self, v0, v1, v2):
        """Simple cross product calculation for normal backface-culling & lighting."""
        ax, ay, az = v1 - v0
        bx, by, bz = v2 - v0
        return np.array([
            ay * bz - az * by,
            az * bx - ax * bz,
            ax * by - ay * bx
        ])

    def paintEvent(self, event):
        # We draw onto a clean intermediate backbuffer QImage to perform GLSL/NumPy post-processes
        backbuffer = QImage(self.size(), QImage.Format_RGB32)
        backbuffer.fill(QColor("#000a05")) # Deep CRT background glow
        
        painter = QPainter(backbuffer)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 1. Render floor grid lines
        self.draw_floor_grid(painter)
        
        # 2. Render origin vertical axis vector
        self.draw_3d_line(painter, 0, 0, 0, 0, 1.2, 0, QColor("#ffffff"), 2)
        
        # 3. Project and draw mesh data
        if len(self.vertices) > 0:
            self.render_mesh(painter)
            
        painter.end()
        
        # 4. Handle custom shader transformations over backbuffer image (F5)
        if self.custom_shader_active:
            backbuffer = self.apply_custom_shader(backbuffer)
            
        # 5. Draw the completed backbuffer directly onto the viewport
        widget_painter = QPainter(self)
        widget_painter.drawImage(0, 0, backbuffer)
        
        # 6. Apply Interactive F6 Lens Overlay (drawn over all structures)
        if self.lens_active:
            self.draw_magnifying_scope(widget_painter, backbuffer)

    def draw_3d_line(self, painter, x1, y1, z1, x2, y2, z2, color, width=1):
        """Transforms two 3D vectors to screenspace and draws a clean line."""
        # Create temp coordinate matrix
        temp_pts = np.array([[x1, y1, z1], [x2, y2, z2]], dtype=np.float32)
        
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)
        
        x, y, z = temp_pts[:, 0], temp_pts[:, 1], temp_pts[:, 2]
        x1_rot = x * cos_y - z * sin_y
        z1_rot = x * sin_y + z * cos_y
        y1_rot = y * cos_p - z1_rot * sin_p
        z2_rot = y * sin_p + z1_rot * cos_p
        
        fov = 450.0
        d = 7.0
        depth = np.clip(z2_rot + d, 0.1, 100.0)
        
        sx = (self.width() / 2) + (x1_rot * fov) / depth
        sy = (self.height() / 2) - (y1_rot * fov) / depth
        
        painter.setPen(QPen(color, width))
        painter.drawLine(int(sx[0]), int(sy[0]), int(sx[1]), int(sy[1]))

    def draw_floor_grid(self, painter):
        """Renders grid coordinate lines."""
        for i in range(-self.grid_range, self.grid_range + 1):
            color = QColor("#00ff80") if i == 0 else QColor("#00230a") # Bright green on origin
            width = 2 if i == 0 else 1
            self.draw_3d_line(painter, i, 0, -self.grid_range, i, 0, self.grid_range, color, width)
            self.draw_3d_line(painter, -self.grid_range, 0, i, self.grid_range, 0, i, color, width)

    def render_mesh(self, painter):
        """Calculates polygons face depth sorting, illumination shading profiles, and normal vectors."""
        projected = self.project_vertices()
        if len(projected) == 0:
            return
            
        # Draw Collision Bounds Box directly if mode 5 is active
        if self.current_render_mode == 5:
            self.draw_collision_bounding_box(painter)
            return

        # 1. Fast Depth Sort (Painter's algorithm) to resolve z-ordering issues
        face_depths = []
        for i, face in enumerate(self.faces):
            avg_depth = np.mean(projected[face, 2])
            face_depths.append((i, avg_depth))
        face_depths.sort(key=lambda x: x[1], reverse=True) # Sort back-to-front

        light_dir = np.array([0.57, 0.57, 0.57]) # Normalized vector

        for face_idx, depth in face_depths:
            face = self.faces[face_idx]
            v0 = self.vertices[face[0]]
            v1 = self.vertices[face[1]]
            v2 = self.vertices[face[2]]
            
            # 2. Backface-culling vector calculation
            normal = self.calculate_normal(v0, v1, v2)
            norm_len = np.linalg.norm(normal)
            if norm_len == 0:
                continue
            normal = normal / norm_len
            
            # Simple camera backface culling dot check
            dot_cam = normal[0] * v0[0] + normal[1] * v0[1] + normal[2] * (v0[2] + 7.0)
            if dot_cam > 0 and self.current_render_mode not in [3, 4]: 
                continue

            # 3. Calculate Light Shading Intensity
            dot_light = np.dot(normal, light_dir)
            intensity = max(0.15, min(1.0, dot_light))
            depth_factor = max(0.0, min(1.0, (14.0 - depth) / 10.0)) # Phosphor/fog depth falloff

            # 4. Shading Profile Modes Setup
            fill_brush = QBrush(Qt.NoBrush)
            pen = QPen(QColor("#00ff80"), 1)
            
            if self.current_render_mode == 1: # Pen and Ink
                fill_brush = QBrush(QColor("#ffffff"))
                pen = QPen(QColor("#000000"), 1.5)
            elif self.current_render_mode == 2: # Solid Workbench
                r = int(10 * intensity)
                g = int(180 * intensity)
                b = int(100 * intensity)
                fill_brush = QBrush(QColor(r, g, b))
                pen = QPen(QColor(int(r*0.6), int(g*0.6), int(b*0.6)), 1)
            elif self.current_render_mode == 3: # Green Wireframe
                fill_brush = QBrush(Qt.NoBrush)
                pen = QPen(QColor("#00ff80"), 1)
            elif self.current_render_mode == 4: # X-Ray / Transparent
                fill_brush = QBrush(QColor(0, 80, 50, 90)) # alpha blending
                pen = QPen(QColor("#00ffaa"), 1)
            elif self.current_render_mode == 6: # Procedural Checkered Map
                check = (int(v0[0]*4) + int(v0[1]*4) + int(v0[2]*4)) % 2 == 0
                fill_brush = QBrush(QColor("#002a14") if check else QColor("#005522"))
                pen = QPen(QColor("#00ffaa"), 1)
            elif self.current_render_mode == 7: # Phosphor Depth Mist
                fog_g = int(255 * depth_factor)
                fill_brush = QBrush(QColor(0, int(fog_g * 0.2), 0, int(depth_factor * 255)))
                pen = QPen(QColor(0, fog_g, 80, int(depth_factor * 255)), 1)

            # 5. Draw Polygon
            poly_path = QPainterPath()
            for idx, vert_idx in enumerate(face):
                pt = projected[vert_idx]
                if idx == 0:
                    poly_path.moveTo(pt[0], pt[1])
                else:
                    poly_path.lineTo(pt[0], pt[1])
            poly_path.closeSubpath()

            # Fill shape
            if fill_brush.style() != Qt.NoBrush:
                painter.fillPath(poly_path, fill_brush)

            # 6. F4 Phosphor Bloom Wide Edge Enhancement Pass
            if self.edge_enhance:
                painter.save()
                painter.setOpacity(0.28)
                painter.setPen(QPen(pen.color(), pen.width() + 4))
                painter.drawPath(poly_path)
                painter.restore()

            # Standard crisp outline
            painter.setPen(pen)
            painter.drawPath(poly_path)

    def draw_collision_bounding_box(self, painter):
        """Draws red 12-line 3D wireframe bounding box representing model extents."""
        min_coords = np.min(self.vertices, axis=0)
        max_coords = np.max(self.vertices, axis=0)
        min_x, min_y, min_z = min_coords
        max_x, max_y, max_z = max_coords

        color = QColor("#ff0055")
        # Bottom bounds
        self.draw_3d_line(painter, min_x, min_y, min_z, max_x, min_y, min_z, color, 2)
        self.draw_3d_line(painter, max_x, min_y, min_z, max_x, max_y, min_z, color, 2)
        self.draw_3d_line(painter, max_x, max_y, min_z, min_x, max_y, min_z, color, 2)
        self.draw_3d_line(painter, min_x, max_y, min_z, min_x, min_y, min_z, color, 2)
        # Top bounds
        self.draw_3d_line(painter, min_x, min_y, max_z, max_x, min_y, max_z, color, 2)
        self.draw_3d_line(painter, max_x, min_y, max_z, max_x, max_y, max_z, color, 2)
        self.draw_3d_line(painter, max_x, max_y, max_z, min_x, max_y, max_z, color, 2)
        self.draw_3d_line(painter, min_x, max_y, max_z, min_x, min_y, max_z, color, 2)
        # Connecting lines
        self.draw_3d_line(painter, min_x, min_y, min_z, min_x, min_y, max_z, color, 2)
        self.draw_3d_line(painter, max_x, min_y, min_z, max_x, min_y, max_z, color, 2)
        self.draw_3d_line(painter, max_x, max_y, min_z, max_x, max_y, max_z, color, 2)
        self.draw_3d_line(painter, min_x, max_y, min_z, min_x, max_y, max_z, color, 2)

    def apply_custom_shader(self, img):
        """Applies flat configuration metrics parsed from external shader targets (F5)."""
        w, h = img.width(), img.height()
        ptr = img.bits()
        ptr.setsize(img.byteCount())
        
        # Pull pixel bytes directly into NumPy mapping for real-time transformations
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4))
        
        # Create floating matrix for transformations
        rgb = arr[:, :, 0:3].astype(np.float32)
        
        # Handle Inversion
        if self.shader_config["color_invert"]:
            rgb = 255.0 - rgb
            
        # Apply floating rgb dynamic scale matrices
        rgb[:, :, 0] = np.clip(rgb[:, :, 0] * self.shader_config["b_scale"], 0, 255) # format maps BGRA
        rgb[:, :, 1] = np.clip(rgb[:, :, 1] * self.shader_config["g_scale"], 0, 255)
        rgb[:, :, 2] = np.clip(rgb[:, :, 2] * self.shader_config["r_scale"], 0, 255)
        
        arr[:, :, 0:3] = rgb.astype(np.uint8)
        
        # Build back standard QImage from transformed matrix
        result_img = QImage(arr.data, w, h, w * 4, QImage.Format_RGB32).copy()
        
        # Fast vector overlay of horizontal scanline blocks
        if self.shader_config["scanlines"]:
            painter = QPainter(result_img)
            painter.setPen(QPen(QColor(0, 5, 0, 75), 2))
            for y in range(0, h, self.shader_config["scan_interval"]):
                painter.drawLine(0, y, w, y)
            painter.end()
            
        return result_img

    def draw_magnifying_scope(self, painter, base_img):
        """Magnifying microscope lens using radial crops and procedural filters (F6)."""
        lens = LENS_TYPES[self.current_lens_idx]
        zoom = lens["zoom"]
        
        lx, ly = self.lens_pos.x(), self.lens_pos.y()
        r = self.lens_radius
        
        # Compute sub-rectangle crop bounds
        crop_w = int((r * 2) / zoom)
        crop_h = int((r * 2) / zoom)
        
        src_rect = QRect(
            max(0, lx - crop_w // 2),
            max(0, ly - crop_h // 2),
            min(crop_w, base_img.width()),
            min(crop_h, base_img.height())
        )
        
        cropped_qimg = base_img.copy(src_rect).convertToFormat(QImage.Format_RGB888)
        
        # Process filter algorithms over scope data array
        if lens["effect"] in ["thermal", "binary"]:
            ptr = cropped_qimg.bits()
            ptr.setsize(cropped_qimg.byteCount())
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape((cropped_qimg.height(), cropped_qimg.width(), 3))
            
            # Map luminosity intensity channels
            luma = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
            
            if lens["effect"] == "thermal": # Heat mapping profile
                arr[:, :, 2] = np.clip(luma * 1.8, 0, 255)          # Red
                arr[:, :, 1] = np.clip(180.0 - luma, 0, 255)        # Green
                arr[:, :, 0] = np.clip((255.0 - luma) * 1.5, 0, 255) # Blue
            elif lens["effect"] == "binary": # Pixel threshold vector
                binary = np.where(luma > 35, 255, 0).astype(np.uint8)
                arr[:, :, 0] = binary * 0.4                         # Blue dim
                arr[:, :, 1] = binary                               # Green high glow
                arr[:, :, 2] = 0                                    # Red out
                
        # Scale cropped slice
        scaled = cropped_qimg.scaled(r * 2, r * 2, Qt.KeepAspectRatioByExpanding, Qt.FastTransformation)
        
        # Blit magnified circle area using alpha path mapping
        painter.save()
        circle_path = QPainterPath()
        circle_path.addEllipse(QPoint(lx, ly), r, r)
        painter.setClipPath(circle_path)
        painter.drawImage(QRect(lx - r, ly - r, r * 2, r * 2), scaled)
        
        # Overlay CRT Scanline overlays inside lens mask
        if lens["effect"] == "scanlines":
            painter.setPen(QPen(QColor(0, 10, 2, 100), 2))
            for scan_y in range(ly - r, ly + r, 4):
                painter.drawLine(lx - r, scan_y, lx + r, scan_y)
        painter.restore()
        
        # Draw Scope Boundary UI line indicators
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawEllipse(QPoint(lx, ly), r, r)
        painter.setPen(QPen(QColor("#ff3333"), 1.5, Qt.DashLine)) # Scope Target Red Reticle
        painter.drawLine(lx - 15, ly, lx + 15, ly)
        painter.drawLine(lx, ly - 15, lx, ly + 15)

    # --- Mouse camera dragging interactions ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            self.yaw += dx * 0.01
            self.pitch = max(-0.2, min(1.4, self.pitch + dy * 0.01))
            self.last_mouse_pos = event.pos()
            self.update()
        elif self.lens_active:
            self.lens_pos = event.pos()
            self.update()

    def wheelEvent(self, event):
        """Scroll wheel input rotation handles lens filter cycle adjustments."""
        if self.lens_active:
            delta = event.angleDelta().y()
            if delta > 0:
                self.current_lens_idx = (self.current_lens_idx + 1) % len(LENS_TYPES)
            else:
                self.current_lens_idx = (self.current_lens_idx - 1) % len(LENS_TYPES)
            
            # Emit notification signal to parent window status bar
            window = self.window()
            if hasattr(window, "set_status_message"):
                window.set_status_message(f"LENS EFFECT: {LENS_TYPES[self.current_lens_idx]['name']}")
            self.update()


class GloriaObjViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GLORIA RETRO CAD - CORE ENGINE")
        self.setMinimumSize(960, 640)
        self.resize(980, 660)

        self.theme_index = 0
        self.theme_name = "GREEN"

        self.init_ui()
        self.apply_theme("GREEN")
        self.setup_shortcuts()

    def init_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)

        # 1. TOP BAR menu
        self.top_bar = QFrame(self)
        self.top_bar.setFixedHeight(40)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(10, 0, 10, 0)

        self.btn_f1 = QPushButton("F1 LOAD OBJ", self.top_bar)
        self.btn_f2 = QPushButton("F2 ROTATION RESET", self.top_bar)
        self.btn_f3 = QPushButton("F3 SHADING MODES", self.top_bar)
        self.btn_f4 = QPushButton("F4 ENHANCE LINES", self.top_bar)
        self.btn_f5 = QPushButton("F5 LOAD SHADER", self.top_bar)
        self.btn_f6 = QPushButton("F6 ANALYZE LENS", self.top_bar)

        for btn in [self.btn_f1, self.btn_f2, self.btn_f3, self.btn_f4, self.btn_f5, self.btn_f6]:
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)

        self.btn_f1.clicked.connect(self.action_load_obj)
        self.btn_f2.clicked.connect(self.action_reset_camera)
        self.btn_f3.clicked.connect(self.action_show_modes_menu)
        self.btn_f4.clicked.connect(self.action_toggle_edge_bloom)
        self.btn_f5.clicked.connect(self.action_load_shader_config)
        self.btn_f6.clicked.connect(self.action_toggle_lens)

        top_layout.addWidget(self.btn_f1)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f2)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f3)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f4)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f5)
        top_layout.addWidget(QLabel("|", self.top_bar))
        top_layout.addWidget(self.btn_f6)
        top_layout.addStretch()

        # 2. MIDDLE VIEWPORT (SIDEBAR + IMAGE CANVAS)
        self.middle_frame = QFrame(self)
        middle_layout = QHBoxLayout(self.middle_frame)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(6)

        # Sidebar Panel
        self.sidebar = QFrame(self.middle_frame)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(10)

        self.lbl_file_header = QLabel("OBJECT NAME:", self.sidebar)
        self.lbl_file_name = QLabel("DEMO_AXIS_MARKER", self.sidebar)
        self.lbl_file_name.setWordWrap(True)

        self.lbl_analytics_header = QLabel("DATA ANALYTICS:", self.sidebar)
        self.lbl_stat_verts = QLabel("Vertices: 1", self.sidebar)
        self.lbl_stat_polys = QLabel("Polygons: 0", self.sidebar)
        
        self.lbl_shader_header = QLabel("ACTIVE SHADER:", self.sidebar)
        self.lbl_shader_name = QLabel("DEFAULT_MONITOR", self.sidebar)

        self.btn_f4_sidebar = QPushButton("BLOOM: OFF", self.sidebar)
        self.btn_f4_sidebar.clicked.connect(self.action_toggle_edge_bloom)
        
        self.btn_lens_sidebar = QPushButton("LENS: OFF", self.sidebar)
        self.btn_lens_sidebar.clicked.connect(self.action_toggle_lens)

        sidebar_layout.addWidget(self.lbl_file_header)
        sidebar_layout.addWidget(self.lbl_file_name)
        sidebar_layout.addWidget(QFrame(self.sidebar))
        sidebar_layout.addWidget(self.lbl_analytics_header)
        sidebar_layout.addWidget(self.lbl_stat_verts)
        sidebar_layout.addWidget(self.lbl_stat_polys)
        sidebar_layout.addWidget(QFrame(self.sidebar))
        sidebar_layout.addWidget(self.lbl_shader_header)
        sidebar_layout.addWidget(self.lbl_shader_name)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.btn_f4_sidebar)
        sidebar_layout.addWidget(self.btn_lens_sidebar)

        # GPU-Assisted NumPy Projection Viewport Canvas Area
        self.canvas = ViewportCanvas(self.middle_frame)

        middle_layout.addWidget(self.sidebar)
        middle_layout.addWidget(self.canvas, 1)

        # 3. BOTTOM BAR TERMINAL
        self.bottom_bar = QFrame(self)
        self.bottom_bar.setFixedHeight(65)
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(15, 10, 15, 10)

        status_text_layout = QVBoxLayout()
        self.lbl_status = QLabel("SYSTEM_STATUS: READY", self.central_widget)
        self.lbl_mode_msg = QLabel("ACTIVE_MODE: GREEN WIREFRAME", self.central_widget)
        status_text_layout.addWidget(self.lbl_status)
        status_text_layout.addWidget(self.lbl_mode_msg)

        self.btn_theme = QPushButton("THEME: GREEN", self.bottom_bar)
        self.btn_theme.clicked.connect(self.action_cycle_theme)
        self.btn_theme.setCursor(Qt.PointingHandCursor)

        bottom_layout.addLayout(status_text_layout, 1)
        bottom_layout.addWidget(self.btn_theme)

        self.main_layout.addWidget(self.top_bar)
        self.main_layout.addWidget(self.middle_frame, 1)
        self.main_layout.addWidget(self.bottom_bar)

    def setup_shortcuts(self):
        QShortcut(Qt.Key_F1, self, self.action_load_obj)
        QShortcut(Qt.Key_F2, self, self.action_reset_camera)
        QShortcut(Qt.Key_F3, self, self.action_show_modes_menu)
        QShortcut(Qt.Key_F4, self, self.action_toggle_edge_bloom)
        QShortcut(Qt.Key_F5, self, self.action_load_shader_config)
        QShortcut(Qt.Key_F6, self, self.action_toggle_lens)
        
        # Keyboard Orbit controls mapped directly to 3D matrix system
        QShortcut(Qt.Key_Left, self, lambda: self.adjust_camera(-0.08, 0))
        QShortcut(Qt.Key_Right, self, lambda: self.adjust_camera(0.08, 0))
        QShortcut(Qt.Key_Up, self, lambda: self.adjust_camera(0, 0.05))
        QShortcut(Qt.Key_Down, self, lambda: self.adjust_camera(0, -0.05))

    def apply_theme(self, name):
        t = THEMES[name]
        self.theme_name = name

        p = t["primary"]
        bg = t["bg"]
        p_bg = t["panel_bg"]

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: #000000; }}
            QLabel {{
                color: {p};
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 11px;
            }}
            QFrame {{
                background-color: {p_bg};
                border: 2px solid {p};
                font-family: 'Courier New', monospace;
            }}
            QFrame#sidebar {{
                border: 2px solid {p};
            }}
            QPushButton {{
                background-color: {bg};
                color: {p};
                border: 2px solid {p};
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 11px;
                padding: 5px 12px;
            }}
            QPushButton:hover {{
                background-color: {p};
                color: #000000;
            }}
            QMenu {{
                background-color: {p_bg};
                color: {p};
                border: 2px solid {p};
                font-family: 'Courier New', monospace;
            }}
            QMenu::item {{
                padding: 6px 20px;
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: {p};
                color: #000000;
            }}
        """)

        self.btn_theme.setText(f"THEME: {name}")
        self.set_status_message(f"Palette Switched: {name}")

    def set_status_message(self, message):
        self.lbl_status.setText(f"SYSTEM_STATUS: {message.upper()}")

    def adjust_camera(self, dyaw, dpitch):
        self.canvas.yaw += dyaw
        self.canvas.pitch = max(-0.2, min(1.4, self.canvas.pitch + dpitch))
        self.canvas.update()

    # --- Actions ---

    def action_load_obj(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open 3D OBJ Target", "", "Wavefront OBJ Files (*.obj)"
        )
        if not file_path:
            return

        self.set_status_message(f"Compiling OBJ: {os.path.basename(file_path)}")
        v_count, f_count = self.canvas.load_obj(file_path)
        
        if v_count > 0:
            self.lbl_file_name.setText(os.path.basename(file_path).upper())
            self.lbl_stat_verts.setText(f"Vertices: {v_count}")
            self.lbl_stat_polys.setText(f"Polygons: {f_count}")
            self.set_status_message(f"COMPILED {f_count} POLYGONS OK")
        else:
            self.set_status_message("Parsing Exception encountered")

    def action_reset_camera(self):
        self.canvas.yaw = 3.92
        self.canvas.pitch = 0.40
        self.canvas.update()
        self.set_status_message("CAMERA ROTATION INITIALIZED")

    def action_show_modes_menu(self):
        menu = QMenu(self)
        for idx, name in enumerate(RENDER_MODES):
            action = menu.addAction(f"Mode {idx+1}: {name}")
            action.triggered.connect(lambda checked, idx=idx: self.select_render_mode(idx + 1))
            
        menu.exec_(self.btn_f3.mapToGlobal(QPoint(0, self.btn_f3.height())))

    def select_render_mode(self, idx):
        self.canvas.current_render_mode = idx
        mode_str = RENDER_MODES[idx - 1]
        self.lbl_mode_msg.setText(f"ACTIVE_MODE: {mode_str}")
        self.set_status_message(f"RENDER SHADING: {mode_str}")
        self.canvas.update()

    def action_toggle_edge_bloom(self):
        self.canvas.edge_enhance = not self.canvas.edge_enhance
        status = "ACTIVE" if self.canvas.edge_enhance else "OFF"
        self.btn_f4_sidebar.setText(f"BLOOM: {status}")
        self.set_status_message(f"SILHOUETTE BLOOM ENHANCER: {status}")
        self.canvas.update()

    def action_load_shader_config(self):
        """Loads and parses raw parameters from retro glsl configurations."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Custom Post-Process Shader", "", "Shader Configuration (*.glsl *.txt *.glslp)"
        )
        if not file_path:
            return

        try:
            self.set_status_message(f"PROCESSING SHADER: {os.path.basename(file_path)}")
            self.lbl_shader_name.setText(os.path.basename(file_path).upper())
            
            # Reset Configuration profile values
            config = {"r_scale": 1.0, "g_scale": 1.0, "b_scale": 1.0, "scanlines": False, "scan_interval": 4, "color_invert": False}
            
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip().lower()
                    if "r_scale" in line or "redscale" in line:
                        vals = [float(s) for s in line.split() if s.replace('.', '', 1).isdigit()]
                        if vals: config["r_scale"] = vals[0]
                    if "g_scale" in line or "greenscale" in line:
                        vals = [float(s) for s in line.split() if s.replace('.', '', 1).isdigit()]
                        if vals: config["g_scale"] = vals[0]
                    if "b_scale" in line or "bluescale" in line:
                        vals = [float(s) for s in line.split() if s.replace('.', '', 1).isdigit()]
                        if vals: config["b_scale"] = vals[0]
                    if "scanline" in line or "crt" in line:
                        config["scanlines"] = True
                        if "2" in line: config["scan_interval"] = 2
                    if "invert" in line:
                        config["color_invert"] = True
                        
            self.canvas.shader_config = config
            self.canvas.custom_shader_active = True
            self.canvas.update()
            
            status_desc = "CRT ON" if config["scanlines"] else "RGB MATCH"
            self.set_status_message(f"COMPILED GLSL POST-PASS: {status_desc}")
            
        except Exception as e:
            self.set_status_message(f"Shader Exception: {str(e)}")

    def action_toggle_lens(self):
        self.canvas.lens_active = not self.canvas.lens_active
        status = "ACTIVE" if self.canvas.lens_active else "OFF"
        self.btn_lens_sidebar.setText(f"LENS: {status}")
        self.btn_f6.setText(f"F6 LENS: {status}")
        self.canvas.update()
        self.set_status_message(
            f"LENS ANALYZER: ACTIVE. USE SCROLL WHEEL TO CHANGE FILTERS" if self.canvas.lens_active else "LENS STANDBY"
        )

    def action_cycle_theme(self):
        self.theme_index = (self.theme_index + 1) % len(THEME_ORDER)
        self.apply_theme(THEME_ORDER[self.theme_index])


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = GloriaObjViewer()
    viewer.show()
    sys.exit(app.exec_())