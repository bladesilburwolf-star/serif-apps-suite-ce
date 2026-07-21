#!/usr/bin/env python3
"""
SERIF OS // SPECTRAL AUDIO-VISUAL RECORDER v0.6
Auto-detect resolution + improved diagnostics.
"""

import os
import sys
import subprocess
import signal
import tkinter as tk
from datetime import datetime
import re

THEME = {"primary": "#00ff80", "bg": "#001100", "panel_bg": "#001a0f"}

# Configurable output (change here or via env var)
OUTPUT_DIR = os.getenv("SERIF_RECORDER_DIR", os.path.expanduser("~/Videos"))

class StreamlinedRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SERIF OS // SYSTEM CAPTURE")
        self.root.geometry("520x340")
        self.root.configure(bg=THEME["bg"])
        self.root.resizable(False, False)

        self.proc = None
        self.recording = False
        self.paused = False
        self.screen_size = self.get_screen_size()

        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        self.build_flat_ui()

    def get_screen_size(self):
        """Auto-detect primary display resolution."""
        try:
            output = subprocess.check_output(["xrandr"], stderr=subprocess.DEVNULL).decode()
            match = re.search(r'(\d+)x(\d+)\s+\d+\.\d+\*', output)
            if match:
                return f"{match.group(1)}x{match.group(2)}"
        except:
            pass
        return "1920x1080"  # safe fallback

    def build_flat_ui(self):
        header = tk.Label(self.root, text="NEON-REC v0.6 // SYSTEM RECORD matrix",
                          fg=THEME["primary"], bg=THEME["bg"], font=("Courier", 11, "bold"))
        header.pack(pady=15)

        self.status_frame = tk.Frame(self.root, bg=THEME["panel_bg"], bd=1, relief="flat")
        self.status_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.lbl_status = tk.Label(self.status_frame, text="STATUS: CORE IDLE",
                                   fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 10, "bold"))
        self.lbl_status.pack(pady=10)

        self.lbl_info = tk.Label(self.status_frame,
                                 text=f"RES: {self.screen_size} | OUT: {OUTPUT_DIR}",
                                 fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 8))
        self.lbl_info.pack()

        btn_deck = tk.Frame(self.root, bg=THEME["bg"])
        btn_deck.pack(fill="x", side="bottom", pady=20, padx=20)

        self.btn_record = tk.Button(btn_deck, text="RECORD", bg=THEME["panel_bg"], fg=THEME["primary"],
                                    relief="flat", bd=1, command=self.toggle_record, font=("Courier", 9, "bold"))
        self.btn_record.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_pause = tk.Button(btn_deck, text="PAUSE", bg=THEME["panel_bg"], fg=THEME["primary"],
                                   relief="flat", bd=1, command=self.toggle_pause, font=("Courier", 9, "bold"))
        self.btn_pause.pack(side="right", fill="x", expand=True, padx=5)

    def toggle_record(self):
        if not self.recording:
            output_filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            full_path = os.path.join(OUTPUT_DIR, output_filename)

            cmd = [
                'ffmpeg', '-y', '-f', 'x11grab',
                '-framerate', '30',
                '-video_size', self.screen_size,
                '-i', ':0.0',
                '-f', 'pulse', '-ac', '2', '-i', 'default',
                '-c:v', 'libx264', '-crf', '23',
                '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k',
                full_path
            ]
            try:
                self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.recording = True
                self.paused = False
                self.lbl_status.config(text=f"RECORDING → {output_filename}")
                self.btn_record.config(text="STOP", fg="#ff3333")
            except Exception as e:
                self.lbl_status.config(text=f"ERROR: {str(e)[:50]}")
        else:
            if self.proc:
                self.proc.send_signal(signal.SIGINT)
                self.proc.wait()
                self.proc = None
            self.recording = False
            self.paused = False
            self.lbl_status.config(text="STREAM CAPTURE SAVED")
            self.btn_record.config(text="RECORD", fg=THEME["primary"])

    def toggle_pause(self):
        if not self.recording or not self.proc:
            return
        if not self.paused:
            self.proc.send_signal(signal.SIGSTOP)
            self.paused = True
            self.lbl_status.config(text="PROCESS SUSPENDED (PAUSED)")
            self.btn_pause.config(text="RESUME", fg="#ffff33")
        else:
            self.proc.send_signal(signal.SIGCONT)
            self.paused = False
            self.lbl_status.config(text="RECORDING ACTIVE...")
            self.btn_pause.config(text="PAUSE", fg=THEME["primary"])

if __name__ == "__main__":
    root = tk.Tk()
    app = StreamlinedRecorderApp(root)
    root.mainloop()
