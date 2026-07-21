#!/usr/bin/env python3
"""
SERIF-VOICE -- lightweight voice changer / vocal FX rack
Streamlined Tkinter Port matching the unified Serif OS ecosystem.
"""

import sys
import os
import time
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk
from threading import Thread

# Preserving internal core suite logic hooks
from effects import EffectChain
from theme import THEMES
import audio_engine

SAMPLERATE = 44100
THEME = {"primary": "#00ff80", "bg": "#001100", "panel_bg": "#001a0f", "dim": "#005522"}

class TkVUMeter(tk.Canvas):
    """Port of the retro LED-bar level meter into flat Tkinter space."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=18, width=140, bg=THEME["bg"], highlightthickness=0, **kwargs)
        self.level = 0.0

    def set_level(self, level):
        self.level = max(0.0, min(1.0, level))
        self.draw_meter()

    def draw_meter(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1: w = 140 
        segments = 24
        gap = 2
        seg_w = (w - gap * segments) / segments
        lit = int(self.level * segments)

        for i in range(segments):
            frac = i / segments
            if frac < 0.7: color = THEME["primary"]
            elif frac < 0.9: color = "#ffaa33"
            else: color = "#ff3333"

            if i >= lit:
                color = THEME["dim"]

            x1 = i * (seg_w + gap)
            self.create_rectangle(x1, 0, x1 + seg_w, h, fill=color, outline="")

class TkWaveformView(tk.Canvas):
    """Flat math representation of Claude's downsampled vector display."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=120, bg=THEME["panel_bg"], highlightthickness=0, **kwargs)
        self.peaks = None
        self.playhead = 0.0

    def set_data(self, data, target_cols=800):
        if data is None or len(data) == 0:
            self.peaks = None
            self.draw_wave()
            return
        n = len(data)
        cols = min(target_cols, n)
        chunk = max(1, n // cols)
        trimmed = data[: cols * chunk]
        reshaped = trimmed.reshape(cols, chunk)
        self.peaks = (reshaped.min(axis=1), reshaped.max(axis=1))
        self.draw_wave()

    def set_playhead(self, frac):
        self.playhead = frac
        self.draw_wave()

    def draw_wave(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1: return
        mid = h / 2

        self.create_line(0, mid, w, mid, fill=THEME["dim"])

        if self.peaks is not None:
            mins, maxs = self.peaks
            cols = len(mins)
            col_w = w / cols
            for i in range(cols):
                x = int(i * col_w)
                y1 = int(mid - maxs[i] * mid)
                y2 = int(mid - mins[i] * mid)
                self.create_line(x, y1, x, max(y2, y1 + 1), fill=THEME["primary"])

            px = int(self.playhead * w)
            self.create_line(px, 0, px, h, fill="#ffaa33")
        else:
            self.create_text(w//2, h//2, text="NO VECTOR LOADED", fill=THEME["dim"], font=("Courier", 10, "bold"))

class SerifVoiceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SERIF-VOICE // Cyberdeck Vocal Matrix")
        self.root.geometry("960x700")
        self.root.configure(bg="#000000")

        self.live_chain = EffectChain(SAMPLERATE)
        self.studio_chain = EffectChain(SAMPLERATE)
        self.live_engine = audio_engine.LiveEngine(self.live_chain, SAMPLERATE)
        self.record_engine = audio_engine.RecordingEngine(self.live_chain, SAMPLERATE)

        self.file_data = None
        self.file_samplerate = SAMPLERATE
        self.processed_data = None

        self.build_ui_layout()
        self.start_monitoring_loops()

    def build_ui_layout(self):
        self.main_frame = tk.Frame(self.root, bg="#000000")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Column: Hardware Interfacing Deck
        self.left_panel = tk.Frame(self.main_frame, width=220, bg=THEME["panel_bg"])
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))
        self.left_panel.pack_propagate(False)

        tk.Label(self.left_panel, text="[ HARWARE CHANNELS ]", fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 9, "bold")).pack(pady=10)
        self.btn_live = tk.Button(self.left_panel, text="START LIVE MONITOR", bg=THEME["bg"], fg=THEME["primary"],
                                  relief="flat", bd=1, command=self.toggle_live_stream, font=("Courier", 9, "bold"))
        self.btn_live.pack(fill="x", padx=10, pady=5)

        tk.Label(self.left_panel, text="INPUT LEVEL:", fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 8)).pack(anchor="w", padx=10, pady=(10, 0))
        self.vu_in = TkVUMeter(self.left_panel)
        self.vu_in.pack(fill="x", padx=10, pady=2)

        tk.Label(self.left_panel, text="OUTPUT LEVEL:", fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 8)).pack(anchor="w", padx=10, pady=(5, 0))
        self.vu_out = TkVUMeter(self.left_panel)
        self.vu_out.pack(fill="x", padx=10, pady=2)

        # Offline Workspace Deck (Studio Rendering)
        tk.Label(self.left_panel, text="[ STUDIO RENDER ]", fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 9, "bold")).pack(pady=(20, 5))
        self.btn_load = tk.Button(self.left_panel, text="LOAD AUDIO FILE", bg=THEME["bg"], fg=THEME["primary"],
                                  relief="flat", bd=1, command=self.load_audio_vector, font=("Courier", 8, "bold"))
        self.btn_load.pack(fill="x", padx=10, pady=2)

        self.btn_process = tk.Button(self.left_panel, text="PROCESS MATRIX", bg=THEME["bg"], fg=THEME["primary"],
                                     relief="flat", bd=1, command=self.process_audio_vector, font=("Courier", 8, "bold"))
        self.btn_process.pack(fill="x", padx=10, pady=2)

        self.btn_preview = tk.Button(self.left_panel, text="PREVIEW PROCESSED", bg=THEME["bg"], fg=THEME["dim"],
                                     relief="flat", bd=1, command=self.playback_processed_vector, font=("Courier", 8, "bold"), state="disabled")
        self.btn_preview.pack(fill="x", padx=10, pady=2)

        # RESTORED: Export button to save processed matrices to file system
        self.btn_export = tk.Button(self.left_panel, text="EXPORT MATRIX", bg=THEME["bg"], fg=THEME["dim"],
                                     relief="flat", bd=1, command=self.export_audio_file, font=("Courier", 8, "bold"), state="disabled")
        self.btn_export.pack(fill="x", padx=10, pady=2)

        self.autoplay_var = tk.BooleanVar(value=True)
        self.chk_autoplay = tk.Checkbutton(self.left_panel, text="AUTO-PLAY PREVIEW", variable=self.autoplay_var,
                                           bg=THEME["panel_bg"], fg=THEME["primary"], selectcolor=THEME["bg"],
                                           activebackground=THEME["panel_bg"], activeforeground=THEME["primary"],
                                           font=("Courier", 8))
        self.chk_autoplay.pack(anchor="w", padx=10, pady=5)

        # Right Column: Main Graphic Visualizer Deck
        self.right_panel = tk.Frame(self.main_frame, bg="#000000")
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.waveform = TkWaveformView(self.right_panel)
        self.waveform.pack(fill="x", pady=(0, 10))

        # Dynamic Rack Scroll Matrix
        self.rack_canvas = tk.Canvas(self.right_panel, bg=THEME["bg"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.right_panel, orient="vertical", command=self.rack_canvas.yview)
        self.scroll_frame = tk.Frame(self.rack_canvas, bg=THEME["bg"])

        self.scroll_frame.bind("<Configure>", lambda e: self.rack_canvas.configure(scrollregion=self.rack_canvas.bbox("all")))

        self.canvas_window = self.rack_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.rack_canvas.bind("<Configure>", lambda event: self.rack_canvas.itemconfig(self.canvas_window, width=event.width) if event.width > 10 else None)

        self.rack_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.rack_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.populate_effects_rack()

    def populate_effects_rack(self):
        """Builds flat parameter adjustment arrays into the scroll container with dedicated bypass triggers."""
        for fx in self.live_chain.effects:
            # FIX: Initialize BOTH chains to be active by default
            fx.enabled = True
            self.studio_chain.by_name(fx.name).enabled = True
            
            fx_frame = tk.LabelFrame(self.scroll_frame, bg=THEME["panel_bg"], bd=1, relief="flat")
            fx_frame.pack(fill="x", padx=10, pady=5, ipadx=5, ipady=5)

            # RESTORED: Dynamic per-effect bypass checkbutton header
            enable_var = tk.BooleanVar(value=True)
            def toggle_fx(f_name=fx.name, var=enable_var):
                self.live_chain.by_name(f_name).enabled = var.get()
                self.studio_chain.by_name(f_name).enabled = var.get()

            header_row = tk.Frame(fx_frame, bg=THEME["panel_bg"])
            header_row.pack(fill="x", padx=5, pady=(0, 5))

            chk = tk.Checkbutton(header_row, text=f" {fx.name.upper()} ", variable=enable_var, command=toggle_fx,
                                 bg=THEME["panel_bg"], fg=THEME["primary"], selectcolor=THEME["bg"],
                                 activebackground=THEME["panel_bg"], activeforeground=THEME["primary"],
                                 font=("Courier", 9, "bold"))
            chk.pack(side="left")

            for pname, (lo, hi, default, step) in fx.params.items():
                row = tk.Frame(fx_frame, bg=THEME["panel_bg"])
                row.pack(fill="x", padx=5, pady=2)

                tk.Label(row, text=pname.replace("_", " ").upper(), fg=THEME["primary"], bg=THEME["panel_bg"], font=("Courier", 8), width=15, anchor="w").pack(side="left")
                
                slider = tk.Scale(row, from_=lo, to=hi, resolution=step, orient="horizontal", bg=THEME["panel_bg"], fg=THEME["primary"], highlightthickness=0, troughcolor=THEME["bg"], bd=0)
                slider.set(default)
                slider.pack(side="left", fill="x", expand=True, padx=5)
                
                # FIX: Explicit parameter setting synchronized mirror
                def update_param(val, f_name=fx.name, p_name=pname):
                    self.live_chain.by_name(f_name).set_param(p_name, float(val))
                    self.studio_chain.by_name(f_name).set_param(p_name, float(val))

                slider.configure(command=update_param)

    def toggle_live_stream(self):
        if not self.live_engine.stream:
            try:
                self.live_engine.start(None, None)
                self.btn_live.config(text="STOP LIVE MONITOR", fg="#ff3333")
            except Exception as e:
                print(f"I/O Error opening device loops: {e}")
        else:
            self.live_engine.stop()
            self.btn_live.config(text="START LIVE MONITOR", fg=THEME["primary"])

    def load_audio_vector(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Base Vector", "*.wav *.flac *.ogg *.mp3")])
        if path:
            if path.lower().endswith(".mp3"):
                try:
                    from pydub import AudioSegment
                    song = AudioSegment.from_mp3(path)
                    song = song.set_frame_rate(SAMPLERATE).set_channels(1)
                    data = np.array(song.get_array_of_samples(), dtype=np.float32) / (2**15)
                    sr = SAMPLERATE
                except ImportError:
                    print("[SYSTEM ERROR] Run 'pip install pydub' for native system MP3 translation vectors.")
                    return
            else:
                data, sr = audio_engine.load_file(path)
                
            self.file_data = data
            self.file_samplerate = sr
            self.waveform.set_data(data)
            self.btn_preview.config(state="disabled", fg=THEME["dim"])
            self.btn_export.config(state="disabled", fg=THEME["dim"])

    def process_audio_vector(self):
        if self.file_data is None: return
        self.btn_process.config(text="PROCESSING...", state="disabled")
        
        def run_async():
            self.processed_data = audio_engine.process_offline(self.studio_chain, self.file_data, self.file_samplerate)
            
            def finalize_ui():
                self.waveform.set_data(self.processed_data)
                self.btn_process.config(text="PROCESS MATRIX", state="normal")
                self.btn_preview.config(state="normal", fg=THEME["primary"])
                self.btn_export.config(state="normal", fg=THEME["primary"])
                
                if self.autoplay_var.get():
                    self.playback_processed_vector()
                    
            self.root.after(0, finalize_ui)
        Thread(target=run_async, daemon=True).start()

    def playback_processed_vector(self):
        """Invoke underlying SoundDevice loop structures safely via fire-and-forget hooks."""
        if self.processed_data is not None:
            try:
                # FIX: Removed the stray system citation syntax crash hazard '[cite: 3]'
                audio_engine.play_preview(self.processed_data, self.file_samplerate)
            except Exception as e:
                print(f"[PREVIEW ERROR] Failed to output vector stream: {e}")

    def export_audio_file(self):
        """Export processed matrix buffer data to filesystem."""
        if self.processed_data is None: return
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Audio", "*.wav"), ("FLAC Audio", "*.flac")])
        if path:
            try:
                audio_engine.save_file(path, self.processed_data, self.file_samplerate)
                print(f"[SYSTEM MATRIX] Successfully exported voice render: {path}")
            except Exception as e:
                print(f"[SYSTEM ERROR] Failed to save file asset: {e}")

    def start_monitoring_loops(self):
        def check_vitals():
            if self.live_engine.stream:
                self.vu_in.set_level(self.live_engine.level_in)
                self.vu_out.set_level(self.live_engine.level_out)
            self.root.after(60, check_vitals)
        self.root.after(60, check_vitals)

if __name__ == "__main__":
    root = tk.Tk()
    app = SerifVoiceApp(root)
    root.mainloop()