#!/usr/bin/env python3
"""
SERIF OS // AUTOMATED SPECTRAL MIXER
High-performance, streamlined video/filter engine optimized for low-resource hardware.
"""

import os
import sys
import time
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
from threading import Thread
from PIL import Image, ImageTk  # C-optimized image conversion block

THEME = {"primary": "#00ff80", "bg": "#001100", "panel_bg": "#001a0f", "dim": "#005522"}
SCREEN_TYPES = ["VINTAGE TV", "COMPUTER LCD", "COMPUTER LED", "THEATER MODE"]
COLOR_MODES = ["FULL COLOR", "MONOCHROME", "SEPIA", "MONO GREEN", "AMBER", "VIRTUAL BOY"]

class StreamlinedMixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SERIF OS // SPECTRAL MIXER")
        self.root.geometry("960x600")
        self.root.configure(bg="#000000")
        
        self.cap = None
        self.playing = False
        self.screen_type = 0
        self.color_mode = 0
        self.prev_frame = None

        self.build_flat_ui()

    def build_flat_ui(self):
        # Base container layout
        self.main_frame = tk.Frame(self.root, bg="#000000")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left control deck
        self.left_panel = tk.Frame(self.main_frame, width=180, bg=THEME["panel_bg"], bd=1, relief="flat")
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))
        self.left_panel.pack_propagate(False)

        tk.Label(self.left_panel, text="[ SCREEN TYPE ]", fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 9, "bold")).pack(pady=(10, 5))
        for idx, name in enumerate(SCREEN_TYPES):
            btn = tk.Button(self.left_panel, text=name, bg=THEME["bg"], fg=THEME["primary"], relief="flat", bd=1,
                            command=lambda i=idx: self.set_screen(i), font=("Courier", 8, "bold"))
            btn.pack(fill="x", padx=10, pady=2)

        tk.Label(self.left_panel, text="[ COLOR MATRIX ]", fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 9, "bold")).pack(pady=(15, 5))
        for idx, name in enumerate(COLOR_MODES):
            btn = tk.Button(self.left_panel, text=name, bg=THEME["bg"], fg=THEME["primary"], relief="flat", bd=1,
                            command=lambda i=idx: self.set_color(i), font=("Courier", 8, "bold"))
            btn.pack(fill="x", padx=10, pady=2)

        # Right control matrix
        self.right_panel = tk.Frame(self.main_frame, width=180, bg=THEME["panel_bg"], bd=1, relief="flat")
        self.right_panel.pack(side="right", fill="y", padx=(10, 0))
        self.right_panel.pack_propagate(False)

        tk.Label(self.right_panel, text="[ ADJUSTMENTS ]", fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 9, "bold")).pack(pady=10)
        
        self.sld_scanlines = self.create_flat_slider(self.right_panel, "SCANLINES")
        self.sld_ghosting = self.create_flat_slider(self.right_panel, "GHOSTING")

        # Center Video Canvas
        self.canvas = tk.Canvas(self.main_frame, bg=THEME["bg"], highlightthickness=0, bd=1, relief="flat")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bottom Transport panel
        self.bottom_bar = tk.Frame(self.root, bg=THEME["panel_bg"], height=50, bd=1, relief="flat")
        self.bottom_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        
        self.btn_load = tk.Button(self.bottom_bar, text="LOAD VIDEO VECTOR", bg=THEME["bg"], fg=THEME["primary"], 
                                  relief="flat", bd=1, command=self.load_video, font=("Courier", 9, "bold"))
        self.btn_load.pack(side="left", padx=10, pady=10)

        self.btn_play = tk.Button(self.bottom_bar, text="PLAY", bg=THEME["bg"], fg=THEME["primary"], 
                                  relief="flat", bd=1, command=self.toggle_play, font=("Courier", 9, "bold"))
        self.btn_play.pack(side="left", padx=5, pady=10)

        self.lbl_status = tk.Label(self.bottom_bar, text="STATUS: SYSTEM READY", fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 9, "bold"))
        self.lbl_status.pack(side="right", padx=15)

    def create_flat_slider(self, parent, label_text):
        tk.Label(parent, text=label_text, fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 8)).pack(anchor="w", padx=10)
        slider = tk.Scale(parent, from_=0, to=100, orient="horizontal", bg=THEME["panel_bg"], fg=THEME["primary"],
                          highlightthickness=0, troughcolor=THEME["bg"], bd=0, activebackground=THEME["primary"])
        slider.pack(fill="x", padx=10, pady=(0, 10))
        return slider

    def set_screen(self, idx): self.screen_type = idx
    def set_color(self, idx): self.color_mode = idx

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mkv")])
        if path:
            self.cap = cv2.VideoCapture(path)
            self.lbl_status.config(text=f"STAGED: {os.path.basename(path).upper()}")
            self.playing = False
            self.btn_play.config(text="PLAY")

    def toggle_play(self):
        if not self.cap: return
        self.playing = not self.playing
        self.btn_play.config(text="PAUSE" if self.playing else "PLAY")
        if self.playing:
            Thread(target=self.video_loop, daemon=True).start()

    def video_loop(self):
        target_width = 480
        while self.playing and self.cap.isOpened():
            start_time = time.time()
            ret, frame = self.cap.read()
            if not ret:
                break

            h, w, _ = frame.shape
            scale = target_width / w
            if scale < 1.0:
                frame = cv2.resize(frame, (target_width, int(h * scale)), interpolation=cv2.INTER_NEAREST)

            processed = self.apply_fast_filters(frame)
            
            # C-Optimized conversion path using Pillow to avoid rendering blocks
            img_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_tk = ImageTk.PhotoImage(image=img_pil)
            
            # Safely render image directly over the frame center line
            self.canvas.create_image(self.canvas.winfo_width()//2, self.canvas.winfo_height()//2, image=img_tk, anchor="center")
            self.canvas.image = img_tk
            
            # Accurate frame delivery pacing tracking
            elapsed = time.time() - start_time
            sleep_time = max(0.001, (1.0 / 30.0) - elapsed)
            time.sleep(sleep_time)

    def apply_fast_filters(self, frame):
        h, w, c = frame.shape
        img = frame.astype(np.float32) / 255.0

        if self.screen_type == 1: img[:, 0::2, :] *= 0.9
        elif self.screen_type == 2: img[0::2, 0::2, :] *= 0.85

        luma = 0.299 * img[:, :, 2] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 0]
        if self.color_mode == 1:
            img = np.stack([luma, luma, luma], axis=-1)
        elif self.color_mode == 3: # Mono Green
            img[:, :, 2] = luma * 0.1; img[:, :, 1] = luma; img[:, :, 0] = luma * 0.2
        elif self.color_mode == 4: # Amber
            img[:, :, 2] = luma; img[:, :, 1] = luma * 0.6; img[:, :, 0] = 0.0
        elif self.color_mode == 5: # Virtual Boy
            img[:, :, 2] = luma * 1.1; img[:, :, 1] = 0.0; img[:, :, 0] = 0.0

        # FIXED: Converted from PyQt .value() to native Tkinter .get() method
        s_val = self.sld_scanlines.get() / 100.0
        if s_val > 0.0: img[0::2, :, :] *= (1.0 - s_val * 0.5)

        g_val = self.sld_ghosting.get() / 100.0
        if g_val > 0.0 and self.prev_frame is not None and self.prev_frame.shape == img.shape:
            img = img * (1.0 - g_val) + self.prev_frame * g_val
        self.prev_frame = img.copy()

        return (np.clip(img, 0.0, 1.0) * 255.0).astype(np.uint8)

if __name__ == "__main__":
    root = tk.Tk()
    app = StreamlinedMixerApp(root)
    root.mainloop()