# main.py
import os
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw

import pipeline

THEMES = {
    "FORENSIC CYAN": {
        "bg": "#00080B",
        "panel_bg": "#001217",
        "hot": "#00E6FF",
        "dim": "#005F73",
        "text": "#E0FAFF",
        "grid": "#00181F"
    },
    "SARIF AMBER": {
        "bg": "#0B0600",
        "panel_bg": "#1C1100",
        "hot": "#FFB300",
        "dim": "#805000",
        "text": "#FFE6B3",
        "grid": "#241600"
    }
}

MAX_RESOLUTION = (1280, 720)


class CyanMicroscope:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SERIF GRAPHICS // PORTABLE SPECTRAL SUITE v5.7")
        self.root.geometry("1340x880")

        self.current_theme_name = "SARIF AMBER"
        self.theme = THEMES[self.current_theme_name]
        self.root.configure(bg=self.theme["bg"])

        self.raw_image = None
        self.overlay_image = None  
        self.photo = None
        self.file_path = None
        self.gallery_assets = []
        self.asset_idx = 0

        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start = None

        self.cursor_x = 0
        self.cursor_y = 0
        self.pixel_under_lens = (0, 0, 0, 0)
        self.is_drafting = False
        
        # Tool Configuration States
        self.active_tool = "NAVIGATION"  
        self.flood_tolerance = 20
        self.brush_size = 15
        
        # Render Cache layer
        self.cached_processed_base = None

        self.filters = {
            "monochrome": 0,  # Pre-pass order of operations trigger
            "aug_lens": 0,
            "threat_detect": 0,
            "thermal": 0,
            "high_pass": 0,
            "chromatic_sep": 0,
            "color_r": 100,
            "color_g": 100,
            "color_b": 100
        }

        self.setup_styles()
        self.build_layout()
        
        # Canvas Interaction Hooks
        self.canvas.bind("<ButtonPress-1>", self.handle_left_press)
        self.canvas.bind("<B1-Motion>", self.handle_left_motion)
        self.canvas.bind("<ButtonRelease-1>", self.handle_left_release)
        self.canvas.bind("<Motion>", self.track_cursor)
        self.canvas.bind("<MouseWheel>", self.mouse_zoom)
        self.canvas.bind("<Configure>", lambda e: self.redraw_canvas())

        # Keyboard Navigation Matrix (Zoom & IO Hotkeys)
        self.root.bind("<Control-o>", lambda e: self.open_image())
        self.root.bind("<plus>", lambda e: self.adjust_zoom(1.15))
        self.root.bind("<equal>", lambda e: self.adjust_zoom(1.15))       
        self.root.bind("<Control-equal>", lambda e: self.adjust_zoom(1.15)) 
        self.root.bind("<minus>", lambda e: self.adjust_zoom(0.85))
        self.root.bind("<Control-minus>", lambda e: self.adjust_zoom(0.85))

    def setup_styles(self):
        theme = self.theme
        self.root.option_add("*Font", "Courier 10 bold")
        self.root.option_add("*Background", theme["panel_bg"])
        self.root.option_add("*Foreground", theme["hot"])
        self.root.option_add("*activeBackground", theme["hot"])
        self.root.option_add("*activeForeground", theme["bg"])

    def build_layout(self):
        theme = self.theme
        self.header = tk.Frame(self.root, bg=theme["bg"])
        self.header.pack(fill="x", side="top", padx=15, pady=8)
        
        self.lbl_title = tk.Label(self.header, text="SERIF GRAPHICS // PORTABLE SPECTRAL SUITE", fg=theme["hot"], bg=theme["bg"])
        self.lbl_title.pack(side="left")
        
        self.lbl_status = tk.Label(self.header, text="MODE: NAVIGATE", fg=theme["dim"], bg=theme["bg"])
        self.lbl_status.pack(side="right")

        self.left_panel = tk.Frame(self.root, width=230, bg=theme["panel_bg"], bd=1, relief="flat")
        self.left_panel.pack(fill="y", side="left", padx=10, pady=5)
        self.left_panel.pack_propagate(False)

        tk.Label(self.left_panel, text="[ NAV MODULE ]", fg=theme["hot"]).pack(pady=3)
        self.btn_load = self.create_btn("LOAD IMAGE", self.open_image)
        self.btn_load.pack(fill="x", padx=12, pady=2)
        
        self.btn_overlay = self.create_btn("LOAD OVERLAY", self.open_overlay)
        self.btn_overlay.pack(fill="x", padx=12, pady=2)

        self.btn_reset = self.create_btn("RESET VIEW", self.reset_view)
        self.btn_reset.pack(fill="x", padx=12, pady=2)

        self.divider1 = tk.Frame(self.left_panel, height=2, bg=theme["dim"])
        self.divider1.pack(fill="x", padx=12, pady=6)

        tk.Label(self.left_panel, text="[ EDITING UTILS ]", fg=theme["hot"]).pack(pady=3)
        
        self.btn_tool_nav = self.create_btn("MODE: NAVIGATE", lambda: self.set_tool("NAVIGATION"))
        self.btn_tool_nav.pack(fill="x", padx=12, pady=2)
        
        self.btn_tool_flood = self.create_btn("MODE: FLOOD CUT", lambda: self.set_tool("FLOOD_CUT"))
        self.btn_tool_flood.pack(fill="x", padx=12, pady=2)
        
        self.btn_tool_erase = self.create_btn("MODE: ERASER", lambda: self.set_tool("ERASER"))
        self.btn_tool_erase.pack(fill="x", padx=12, pady=2)
        
        # Dynamic Multi-Option Utility Slider
        self.frame_edit_slider = tk.Frame(self.left_panel, bg=theme["panel_bg"])
        self.frame_edit_slider.pack(fill="x", padx=12, pady=2)
        self.lbl_edit_slider = tk.Label(self.frame_edit_slider, text="FLOOD TOLERANCE", font=("Courier", 8, "bold"), fg=theme["dim"])
        self.lbl_edit_slider.pack(anchor="w")
        self.slider_edit_ctrl = tk.Scale(
            self.frame_edit_slider, from_=0, to=150, orient="horizontal", bd=0,
            bg=theme["panel_bg"], fg=theme["hot"], highlightthickness=0,
            troughcolor=theme["bg"], command=self.handle_edit_slider_change
        )
        self.slider_edit_ctrl.set(self.flood_tolerance)
        self.slider_edit_ctrl.pack(fill="x")

        self.divider_edit = tk.Frame(self.left_panel, height=2, bg=theme["dim"])
        self.divider_edit.pack(fill="x", padx=12, pady=6)

        self.lbl_queue = tk.Label(self.left_panel, text="ASSET QUEUE", fg=theme["dim"])
        self.lbl_queue.pack()
        self.btn_prev = self.create_btn("PREV ASSET", self.prev_asset)
        self.btn_prev.pack(fill="x", padx=12, pady=2)
        self.btn_next = self.create_btn("NEXT ASSET", self.next_asset)
        self.btn_next.pack(fill="x", padx=12, pady=2)
        self.lbl_index = tk.Label(self.left_panel, text="INDEX: 00/00", fg=theme["dim"])
        self.lbl_index.pack(pady=2)

        self.divider2 = tk.Frame(self.left_panel, height=2, bg=theme["dim"])
        self.divider2.pack(fill="x", padx=12, pady=6)

        tk.Label(self.left_panel, text="INTERFACE MATRIX", fg=theme["dim"]).pack()
        self.btn_swap_theme = self.create_btn(f"STYLE: {self.current_theme_name}", self.toggle_theme)
        self.btn_swap_theme.pack(fill="x", padx=12, pady=2)

        # Right Filters Panel Layout
        self.right_panel = tk.Frame(self.root, width=250, bg=theme["panel_bg"], bd=1, relief="flat")
        self.right_panel.pack(fill="y", side="right", padx=10, pady=5)
        self.right_panel.pack_propagate(False)

        tk.Label(self.right_panel, text="[ AUGMENT MATRIX ]", fg=theme["hot"]).pack(pady=5)

        # PRE-FILTER BUTTON: Monochrome base switch
        self.btn_mono = tk.Button(
            self.right_panel, text="BASE: COLOR SOURCE", command=self.toggle_monochrome, relief="flat", bd=1,
            bg=theme["panel_bg"], fg=theme["dim"], font=("Courier", 9, "bold")
        )
        self.btn_mono.pack(fill="x", padx=12, pady=6)

        self.sliders = {}
        filters_to_build = [
            ("aug_lens", "AUG HUD LENS", 0, 100, 0),
            ("threat_detect", "THREAT DETECT", 0, 100, 0),
            ("thermal", "THERMAL SCAN", 0, 100, 0),
            ("high_pass", "HIGH-PASS (SHARP)", 0, 100, 0),
            ("chromatic_sep", "CHROMATIC SEP", 0, 100, 0),
            ("color_r", "COLOR BAL: RED", 0, 200, 100),
            ("color_g", "COLOR BAL: GREEN", 0, 200, 100),
            ("color_b", "COLOR BAL: BLUE", 0, 200, 100)
        ]

        for f_key, f_label, start_v, end_v, def_v in filters_to_build:
            frame_slider = tk.Frame(self.right_panel, bg=theme["panel_bg"])
            frame_slider.pack(fill="x", padx=12, pady=4)
            
            lbl = tk.Label(frame_slider, text=f_label, font=("Courier", 8, "bold"), fg=theme["dim"], anchor="w")
            lbl.pack(fill="x")
            
            slider = tk.Scale(
                frame_slider, from_=start_v, to=end_v, orient="horizontal", bd=0,
                bg=theme["panel_bg"], fg=theme["hot"], highlightthickness=0,
                troughcolor=theme["bg"], activebackground=theme["hot"],
                command=lambda val, k=f_key: self.update_slider_param(k, val)
            )
            slider.set(def_v)
            slider.pack(fill="x")
            self.sliders[f_key] = (slider, lbl)

        self.canvas_container = tk.Frame(self.root, bg=theme["bg"], bd=1, relief="flat")
        self.canvas_container.pack(fill="both", expand=True, padx=2, pady=5)
        self.canvas = tk.Canvas(self.canvas_container, bg=theme["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.update_tool_ui_indicators()

    def create_btn(self, text, command):
        return tk.Button(
            self.left_panel, text=text, command=command, relief="flat", bd=1,
            bg=self.theme["panel_bg"], fg=self.theme["hot"],
            activebackground=self.theme["hot"], activeforeground=self.theme["bg"],
            font=("Courier", 9, "bold")
        )

    def toggle_monochrome(self):
        if self.filters["monochrome"] == 0:
            self.filters["monochrome"] = 1
            self.btn_mono.config(text="BASE: MONOCHROME", fg=self.theme["bg"], bg=self.theme["hot"])
        else:
            self.filters["monochrome"] = 0
            self.btn_mono.config(text="BASE: COLOR SOURCE", fg=self.theme["dim"], bg=self.theme["panel_bg"])
        self.update_pipeline_cache()
        self.redraw_canvas()

    def set_tool(self, tool_name):
        self.active_tool = tool_name
        self.update_tool_ui_indicators()
        self.redraw_canvas()

    def update_tool_ui_indicators(self):
        theme = self.theme
        for b in [self.btn_tool_nav, self.btn_tool_flood, self.btn_tool_erase]:
            b.config(fg=theme["hot"], bg=theme["panel_bg"])
            
        if self.active_tool == "NAVIGATION":
            self.btn_tool_nav.config(fg=theme["bg"], bg=theme["hot"])
            self.lbl_status.config(text="MODE: NAVIGATE", fg=theme["dim"])
            self.lbl_edit_slider.config(text="NAV MODE ACTIVE")
            self.slider_edit_ctrl.pack_forget()
        elif self.active_tool == "FLOOD_CUT":
            self.btn_tool_flood.config(fg=theme["bg"], bg=theme["hot"])
            self.lbl_status.config(text="MODE: FLOOD CUT", fg=theme["hot"])
            self.lbl_edit_slider.config(text="FLOOD TOLERANCE")
            self.slider_edit_ctrl.pack(fill="x")
            self.slider_edit_ctrl.config(from_=0, to=150)
            self.slider_edit_ctrl.set(self.flood_tolerance)
        elif self.active_tool == "ERASER":
            self.btn_tool_erase.config(fg=theme["bg"], bg=theme["hot"])
            self.lbl_status.config(text="MODE: MANUAL ERASER", fg=theme["hot"])
            self.lbl_edit_slider.config(text="BRUSH RADIUS")
            self.slider_edit_ctrl.pack(fill="x")
            self.slider_edit_ctrl.config(from_=2, to=100)
            self.slider_edit_ctrl.set(self.brush_size)

    def handle_edit_slider_change(self, val):
        if self.active_tool == "FLOOD_CUT":
            self.flood_tolerance = int(val)
        elif self.active_tool == "ERASER":
            self.brush_size = int(val)

    def handle_left_press(self, event):
        if self.raw_image is None: return
        if self.active_tool == "NAVIGATION":
            self.start_pan(event)
        elif self.active_tool == "FLOOD_CUT":
            self.execute_flood_cut(event)
        elif self.active_tool == "ERASER":
            self.is_drafting = True  
            self.execute_manual_erase(event)

    def handle_left_motion(self, event):
        if self.raw_image is None: return
        if self.active_tool == "NAVIGATION":
            self.do_pan(event)
        elif self.active_tool == "ERASER":
            self.execute_manual_erase(event)

    def handle_left_release(self, event):
        if self.active_tool == "NAVIGATION":
            self.stop_pan(event)
        elif self.active_tool in ["FLOOD_CUT", "ERASER"]:
            self.is_drafting = False
            self.update_pipeline_cache()
            self.redraw_canvas()

    def execute_flood_cut(self, event):
        w = self.canvas.winfo_width() or 1280
        h = self.canvas.winfo_height() or 800
        img_x = int((event.x - (w // 2 + self.pan_x)) / self.zoom + self.raw_image.width / 2)
        img_y = int((event.y - (h // 2 + self.pan_y)) / self.zoom + self.raw_image.height / 2)
        
        if 0 <= img_x < self.raw_image.width and 0 <= img_y < self.raw_image.height:
            rgba_working = self.raw_image.convert("RGBA")
            ImageDraw.floodfill(rgba_working, xy=(img_x, img_y), value=(0, 0, 0, 0), thresh=self.flood_tolerance)
            self.raw_image = rgba_working
            self.update_pipeline_cache()
            self.redraw_canvas()

    def execute_manual_erase(self, event):
        w = self.canvas.winfo_width() or 1280
        h = self.canvas.winfo_height() or 800
        img_x = int((event.x - (w // 2 + self.pan_x)) / self.zoom + self.raw_image.width / 2)
        img_y = int((event.y - (h // 2 + self.pan_y)) / self.zoom + self.raw_image.height / 2)
        
        if 0 <= img_x < self.raw_image.width and 0 <= img_y < self.raw_image.height:
            draw = ImageDraw.Draw(self.raw_image)
            r = self.brush_size
            draw.ellipse([img_x - r, img_y - r, img_x + r, img_y + r], fill=(0, 0, 0, 0))
            
            if self.cached_processed_base is not None:
                cache_draw = ImageDraw.Draw(self.cached_processed_base)
                cache_draw.ellipse([img_x - r, img_y - r, img_x + r, img_y + r], fill=(0, 0, 0, 0))

            self.redraw_canvas()

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp *.gif")])
        if not path:
            return
        self.load_target_path(path)
        self.scan_directory(Path(path).parent)

    def open_overlay(self):
        path = filedialog.askopenfilename(filetypes=[("Images/Overlays", "*.png *.jpg *.jpeg *.bmp *.webp *.gif")])
        if not path:
            return
        self.overlay_image = Image.open(path).convert("RGBA")
        self.update_pipeline_cache()
        self.redraw_canvas()

    def load_target_path(self, path):
        self.file_path = path
        img = Image.open(path)
        img.thumbnail(MAX_RESOLUTION, Image.Resampling.BILINEAR)
        self.raw_image = img.convert("RGBA")
        self.reset_view()

    def scan_directory(self, folder_path):
        valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
        try:
            p = Path(folder_path)
            self.gallery_assets = sorted([p / f for f in os.listdir(p) if Path(f).suffix.lower() in valid_exts])
            if p / Path(self.file_path).name in self.gallery_assets:
                self.asset_idx = self.gallery_assets.index(p / Path(self.file_path).name)
            self.update_queue_label()
        except Exception:
            pass

    def next_asset(self):
        if not self.gallery_assets: return
        self.asset_idx = (self.asset_idx + 1) % len(self.gallery_assets)
        self.load_target_path(str(self.gallery_assets[self.asset_idx]))

    def prev_asset(self):
        if not self.gallery_assets: return
        self.asset_idx = (self.asset_idx - 1) % len(self.gallery_assets)
        self.load_target_path(str(self.gallery_assets[self.asset_idx]))

    def update_queue_label(self):
        total = len(self.gallery_assets)
        curr = self.asset_idx + 1 if total > 0 else 0
        self.lbl_index.config(text=f"INDEX: {curr:02d}/{total:02d}")

    def reset_view(self):
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update_pipeline_cache()
        self.redraw_canvas()

    def start_pan(self, event):
        self.drag_start = (event.x, event.y)
        self.is_drafting = True

    def do_pan(self, event):
        if self.active_tool != "NAVIGATION": return
        if not self.drag_start or self.raw_image is None: return
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        self.pan_x += dx
        self.pan_y += dy
        self.drag_start = (event.x, event.y)
        self.redraw_canvas()

    def stop_pan(self, event):
        self.is_drafting = False
        self.redraw_canvas()

    def update_pipeline_cache(self):
        if self.raw_image is not None:
            self.cached_processed_base = pipeline.process_filters(self.raw_image, self.filters, self.theme)

    def track_cursor(self, event):
        self.cursor_x = event.x
        self.cursor_y = event.y
        if self.raw_image:
            w = self.canvas.winfo_width() or 1280
            h = self.canvas.winfo_height() or 800
            img_x = int((self.cursor_x - (w // 2 + self.pan_x)) / self.zoom + self.raw_image.width / 2)
            img_y = int((self.cursor_y - (h // 2 + self.pan_y)) / self.zoom + self.raw_image.height / 2)
            if 0 <= img_x < self.raw_image.width and 0 <= img_y < self.raw_image.height:
                self.pixel_under_lens = self.raw_image.getpixel((img_x, img_y))
            else:
                self.pixel_under_lens = (0, 0, 0, 0)
            
            self.redraw_canvas(only_hud=True)

    def mouse_zoom(self, event):
        factor = 1.15 if event.delta > 0 else 0.85
        self.adjust_zoom(factor)

    def adjust_zoom(self, factor):
        if self.raw_image is None: return
        self.zoom *= factor
        self.zoom = max(0.1, min(10.0, self.zoom))
        self.is_drafting = True
        self.redraw_canvas()
        self.root.after(100, self._stop_zoom_draft)

    def _stop_zoom_draft(self):
        self.is_drafting = False
        self.redraw_canvas()

    def update_slider_param(self, filter_key, value):
        val_int = int(value)
        self.filters[filter_key] = val_int
        slider_widget, label_widget = self.sliders[filter_key]
        
        is_modified = (filter_key in ["color_r", "color_g", "color_b"] and val_int != 100) or \
                      (filter_key not in ["color_r", "color_g", "color_b"] and val_int > 0)

        if is_modified:
            label_widget.config(fg=self.theme["hot"])
        else:
            label_widget.config(fg=self.theme["dim"])
            
        self.update_pipeline_cache()
        self.redraw_canvas()

    def toggle_theme(self):
        self.current_theme_name = "FORENSIC CYAN" if self.current_theme_name == "SARIF AMBER" else "SARIF AMBER"
        self.theme = THEMES[self.current_theme_name]
        self.apply_theme_colors()
        self.update_pipeline_cache()
        self.redraw_canvas()

    def apply_theme_colors(self):
        theme = self.theme
        self.root.configure(bg=theme["bg"])
        self.header.configure(bg=theme["bg"])
        self.lbl_title.configure(fg=theme["hot"], bg=theme["bg"])
        self.lbl_status.configure(fg=theme["dim"], bg=theme["bg"])
        
        self.left_panel.configure(bg=theme["panel_bg"])
        self.lbl_queue.configure(fg=theme["dim"], bg=theme["panel_bg"])
        self.lbl_index.configure(fg=theme["dim"], bg=theme["panel_bg"])
        self.divider1.configure(bg=theme["dim"])
        self.divider2.configure(bg=theme["dim"])
        self.divider_edit.configure(bg=theme["dim"])
        
        self.slider_edit_ctrl.configure(bg=theme["panel_bg"], fg=theme["hot"], troughcolor=theme["bg"])
        self.lbl_edit_slider.configure(fg=theme["dim"], bg=theme["panel_bg"])
        self.right_panel.configure(bg=theme["panel_bg"])
        self.canvas_container.configure(bg=theme["bg"])
        self.canvas.configure(bg=theme["bg"])

        for btn in [self.btn_load, self.btn_overlay, self.btn_reset, self.btn_prev, self.btn_next]:
            btn.configure(bg=theme["panel_bg"], fg=theme["hot"])
            
        self.update_tool_ui_indicators()
        self.btn_swap_theme.configure(text=f"STYLE: {self.current_theme_name}", bg=theme["panel_bg"], fg=theme["hot"])

        if self.filters["monochrome"] == 1:
            self.btn_mono.configure(bg=theme["hot"], fg=theme["bg"])
        else:
            self.btn_mono.configure(bg=theme["panel_bg"], fg=theme["dim"])

        for f_key, (slider_widget, label_widget) in self.sliders.items():
            slider_widget.configure(bg=theme["panel_bg"], fg=theme["hot"], troughcolor=theme["bg"])
            val_int = self.filters[f_key]
            is_modified = (f_key in ["color_r", "color_g", "color_b"] and val_int != 100) or \
                          (f_key not in ["color_r", "color_g", "color_b"] and val_int > 0)
            if is_modified:
                label_widget.configure(fg=theme["hot"], bg=theme["panel_bg"])
            else:
                label_widget.configure(fg=theme["dim"], bg=theme["panel_bg"])

    def draw_grid(self, w, h):
        spacing = 64
        grid_color = self.theme["grid"]
        for x in range(0, w, spacing):
            self.canvas.create_line(x, 0, x, h, fill=grid_color, width=1, tags="grid")
        for y in range(0, h, spacing):
            self.canvas.create_line(0, y, w, y, fill=grid_color, width=1, tags="grid")

    def draw_image(self, w, h):
        if self.raw_image is None:
            self.canvas.create_text(
                w // 2, h // 2,
                text="[ SYSTEM: STANDBY ]\n\nMOUNT SPECTRAL PATH TO START FORENSIC SWEEP",
                fill=self.theme["dim"], font=("Courier", 13, "bold"), justify="center", tags="ui"
            )
            return

        iw = max(1, int(self.raw_image.width * self.zoom))
        ih = max(1, int(self.raw_image.height * self.zoom))

        if self.is_drafting or self.cached_processed_base is None:
            processed = self.raw_image
            resized = processed.resize((iw, ih), Image.NEAREST)
        else:
            if self.overlay_image:
                overlay_resized = self.overlay_image.resize((self.raw_image.width, self.raw_image.height), Image.Resampling.BILINEAR)
                processed = Image.alpha_composite(self.cached_processed_base, overlay_resized)
            else:
                processed = self.cached_processed_base

            resized = processed.resize((iw, ih), Image.Resampling.BILINEAR)
        
        self.photo = ImageTk.PhotoImage(resized)
        self.canvas.create_image(w // 2 + self.pan_x, h // 2 + self.pan_y, image=self.photo, tags="img")

    def draw_hud(self, w, h):
        theme = self.theme
        
        if self.active_tool == "ERASER" and self.raw_image is not None:
            scaled_brush_radius = int(self.brush_size * self.zoom)
            self.canvas.create_oval(
                self.cursor_x - scaled_brush_radius, self.cursor_y - scaled_brush_radius,
                self.cursor_x + scaled_brush_radius, self.cursor_y + scaled_brush_radius,
                outline=theme["hot"], width=1, dash=(4, 4), tags="hud"
            )
            
        if self.filters["aug_lens"] > 0 and self.raw_image is not None:
            radius = int(50 + (self.filters["aug_lens"] * 0.8))
            cx, cy = self.cursor_x, self.cursor_y
            self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=theme["hot"], width=2, tags="hud")
            self.canvas.create_line(cx - 15, cy, cx - 4, cy, fill=theme["hot"], width=1.5, tags="hud")
            self.canvas.create_line(cx + 4, cy, cx + 15, cy, fill=theme["hot"], width=1.5, tags="hud")
            self.canvas.create_line(cx, cy - 15, cx, cy - 4, fill=theme["hot"], width=1.5, tags="hud")
            self.canvas.create_line(cx, cy + 4, cx, cy + 15, fill=theme["hot"], width=1.5, tags="hud")

            r, g, b = self.pixel_under_lens[:3]
            a = self.pixel_under_lens[3] if len(self.pixel_under_lens) > 3 else 255
            hex_val = f"#{r:02X}{g:02X}{b:02X}"
            self.canvas.create_text(
                cx + radius + 12, cy - 35, anchor="nw", fill=theme["hot"], font=("Courier", 8, "bold"), tags="hud",
                text=f"AUG LENS STATS:\nCOORDS: {cx:04d}, {cy:04d}\nRGB: [{r:03d},{g:03d},{b:03d}]\nHEX: {hex_val}\nALPHA: {a:03d}"
            )

        self.canvas.create_rectangle(8, 8, w - 8, h - 8, outline=theme["dim"], width=1, tags="hud")
        cb = 24
        corners = [
            (8, 8, 8+cb, 8, 8, 8, 8, 8+cb),
            (w-8-cb, 8, w-8, 8, w-8, 8, w-8, 8+cb),
            (8, h-8-cb, 8, h-8, 8, h-8, 8+cb, h-8),
            (w-8-cb, h-8, w-8, h-8, w-8, h-8, w-8, h-8-cb)
        ]
        for c in corners:
            self.canvas.create_line(c[:4], fill=theme["hot"], width=2, tags="hud")
            self.canvas.create_line(c[4:], fill=theme["hot"], width=2, tags="hud")

    def redraw_canvas(self, only_hud=False):
        w = self.canvas.winfo_width() or 1280
        h = self.canvas.winfo_height() or 800
        
        if only_hud:
            self.canvas.delete("hud")
            self.draw_hud(w, h)
        else:
            self.canvas.delete("all")
            self.draw_grid(w, h)
            self.draw_image(w, h)
            self.draw_hud(w, h)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = CyanMicroscope()
    app.run()
