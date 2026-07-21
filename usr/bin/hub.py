#!/usr/bin/env python3
"""
SERIF OS // AUGMENTED SYSTEM CONTROL HUB v2.1
Unified, vector-styled tactical desktop portal with animated cyber-optic framing.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
from pathlib import Path

# --- Retro Color Matrices ---
THEMES = {
    "SARIF AMBER": {
        "bg": "#0B0600",
        "panel_bg": "#1C1100",
        "hot": "#FFB300",
        "dim": "#805000",
        "text": "#FFE6B3",
        "grid": "#241600",
        "terminal": "#140C00"
    },
    "FORENSIC CYAN": {
        "bg": "#00080B",
        "panel_bg": "#001217",
        "hot": "#00E6FF",
        "dim": "#005F73",
        "text": "#E0FAFF",
        "grid": "#00181F",
        "terminal": "#000D12"
    }
}


class AugmentedSerifHub:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SERIF OS // SYSTEM CONTROL HUB")
        self.root.geometry("1100x700")
        self.root.resizable(False, False)

        self.current_theme_name = "SARIF AMBER"
        self.theme = THEMES[self.current_theme_name]
        self.root.configure(bg=self.theme["bg"])

        self.running_processes = {}
        self.detected_apps = []

        self.setup_styles()
        self.build_layout()
        self.scan_workspace()
        
        # Start the Scanline Shader Loop
        self.run_shader_loop()

    def play_sound(self, sound_type):
        """Uses existing audio backend to play click, sweep, and toggle sound files."""
        sound_files = {
            "click": "click.wav",
            "toggle": "toggle.wav",
            "launch": "sweep.wav"
        }
        sound_file = sound_files.get(sound_type)
        if not sound_file:
            return
        
        # Check adjacent directory for assets
        hub_dir = Path(__file__).parent.resolve()
        asset_path = hub_dir / sound_file
        if not asset_path.exists():
            return
        
        def _execute():
            try:
                subprocess.run(["paplay", str(asset_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                try:
                    subprocess.run(["aplay", str(asset_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

        threading.Thread(target=_execute, daemon=True).start()

    def setup_styles(self):
        theme = self.theme
        self.root.option_add("*Font", "Courier 10 bold")
        self.root.option_add("*Background", theme["bg"])
        self.root.option_add("*Foreground", theme["hot"])
        self.root.option_add("*activeBackground", theme["hot"])
        self.root.option_add("*activeForeground", theme["bg"])

    def build_layout(self):
        theme = self.theme

        # --- Base Interactive Canvas (The Cybernetic Eye Layer) ---
        self.hud_canvas = tk.Canvas(self.root, bg=theme["bg"], highlightthickness=0)
        self.hud_canvas.pack(fill="both", expand=True)

        # Draw the static and dynamic ocular lines
        self.draw_cyber_eye()

        # --- Foreground Interface Containers (Placed over Canvas) ---
        self.hud_frame = tk.Frame(self.hud_canvas, bg=theme["bg"])
        # Centered exactly inside the HUD viewport
        self.hud_canvas.create_window(550, 350, window=self.hud_frame, anchor="center", tags="ui_content")

        # --- Header Deck ---
        self.header = tk.Frame(self.hud_frame, bg=theme["bg"])
        self.header.pack(fill="x", side="top", padx=15, pady=(5, 15))
        
        self.lbl_title = tk.Label(
            self.header, 
            text="SERIF OS // MULTI-MODULE LAUNCH DECK", 
            fg=theme["hot"], bg=theme["bg"], font=("Courier", 12, "bold")
        )
        self.lbl_title.pack(side="left")

        self.btn_theme = tk.Button(
            self.header, text=f"INTERFACE: {self.current_theme_name}", 
            command=self.toggle_theme, relief="flat", bd=1,
            bg=theme["panel_bg"], fg=theme["hot"]
        )
        self.btn_theme.pack(side="right")

        # --- Split Body ---
        self.body_frame = tk.Frame(self.hud_frame, bg=theme["bg"])
        self.body_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # Left Panel: Controller (Optimized to pure flat terminal look)
        self.left_panel = tk.Frame(self.body_frame, width=380, height=440, bg=theme["panel_bg"], bd=1, relief="flat")
        self.left_panel.pack(fill="both", side="left", padx=(0, 15))
        self.left_panel.pack_propagate(False)

        self.lbl_modules_hdr = tk.Label(self.left_panel, text="[ SYSTEM CONTROL INDEX ]", fg=theme["hot"], bg=theme["panel_bg"])
        self.lbl_modules_hdr.pack(pady=10)

        self.app_listbox = tk.Listbox(
            self.left_panel, bg=theme["bg"], fg=theme["hot"], 
            selectbackground=theme["hot"], selectforeground=theme["bg"],
            bd=1, highlightthickness=0, font=("Courier", 9, "bold")
        )
        self.app_listbox.pack(fill="both", expand=True, padx=12, pady=5)

        self.btn_launch = tk.Button(
            self.left_panel, text="BOOT SYSTEM VECTOR", command=self.launch_selected,
            relief="flat", bd=1, bg=theme["bg"], fg=theme["hot"], font=("Courier", 10, "bold")
        )
        self.btn_launch.pack(fill="x", padx=12, pady=12)

        # Right Panel: Output Terminal Log (Optimized to pure flat terminal look)
        self.right_panel = tk.Frame(self.body_frame, width=440, height=440, bg=theme["panel_bg"], bd=1, relief="flat")
        self.right_panel.pack(fill="both", side="right")
        self.right_panel.pack_propagate(False)

        self.lbl_console_hdr = tk.Label(self.right_panel, text="[ LIVE DIAGNOSTIC STREAM ]", fg=theme["hot"], bg=theme["panel_bg"])
        self.lbl_console_hdr.pack(pady=10)

        self.console_text = tk.Text(
            self.right_panel, bg=theme["terminal"], fg=theme["text"],
            state="disabled", wrap="word", font=("Courier", 9), bd=0, highlightthickness=0
        )
        self.console_text.pack(fill="both", expand=True, padx=12, pady=(5, 12))

    def draw_cyber_eye(self):
        """Draws the augmented eye overlay frame and technical alignment brackets."""
        self.hud_canvas.delete("eye_element")
        
        w, h = 1100, 700
        cx, cy = w // 2, h // 2
        
        hot = self.theme["hot"]
        dim = self.theme["dim"]
        grid = self.theme["grid"]

        # 1. Technical Gridlines & Concentric Circles
        for r in [180, 320, 480]:
            self.hud_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r, 
                outline=grid, width=1, dash=(4, 8), tags="eye_element"
            )

        # 2. Main Augmented Eye Eyelid Curves
        # Upper Arch
        self.hud_canvas.create_arc(
            cx - 520, cy - 380, cx + 520, cy + 280,
            start=18, extent=144, style=tk.ARC,
            outline=hot, width=2, tags="eye_element"
        )
        # Lower Arch
        self.hud_canvas.create_arc(
            cx - 520, cy - 280, cx + 520, cy + 380,
            start=198, extent=144, style=tk.ARC,
            outline=hot, width=2, tags="eye_element"
        )

        # Reticle Iris Rings
        self.hud_canvas.create_oval(
            cx - 90, cy - 90, cx + 90, cy + 90, 
            outline=dim, width=1, dash=(3, 3), tags="eye_element"
        )
        self.hud_canvas.create_oval(
            cx - 110, cy - 110, cx + 110, cy + 110, 
            outline=hot, width=1.5, tags="eye_element"
        )

        # Technical ticks and HUD framing brackets
        b_len = 25
        self.hud_canvas.create_line(15, 15, 15 + b_len, 15, fill=hot, width=2, tags="eye_element")
        self.hud_canvas.create_line(15, 15, 15, 15 + b_len, fill=hot, width=2, tags="eye_element")

        self.hud_canvas.create_line(w - 15, 15, w - (15 + b_len), 15, fill=hot, width=2, tags="eye_element")
        self.hud_canvas.create_line(w - 15, 15, w - 15, 15 + b_len, fill=hot, width=2, tags="eye_element")

        self.hud_canvas.create_line(15, h - 15, 15 + b_len, h - 15, fill=hot, width=2, tags="eye_element")
        self.hud_canvas.create_line(15, h - 15, 15, h - (15 + b_len), fill=hot, width=2, tags="eye_element")

        self.hud_canvas.create_line(w - 15, h - 15, w - (15 + b_len), h - 15, fill=hot, width=2, tags="eye_element")
        self.hud_canvas.create_line(w - 15, h - 15, w - 15, h - (15 + b_len), fill=hot, width=2, tags="eye_element")

    def run_shader_loop(self, sweep_y=0):
        """Pulsing scanline shader scrolling vertically across the terminal."""
        self.hud_canvas.delete("shader_sweep")
        w, h = 1100, 700
        
        # Subtle glowing tracking bar
        self.hud_canvas.create_line(
            0, sweep_y, w, sweep_y,
            fill=self.theme["grid"], width=3, tags="shader_sweep"
        )
        
        next_y = (sweep_y + 3) % h
        self.root.after(35, self.run_shader_loop, next_y)

    def scan_workspace(self):
        """Flat scan targeting decoupled subfolders and verifying corresponding .py binaries inside."""
        # 1. ALWAYS CLEAR BOTH DATA SOURCES TO PREVENT DUPLICATION
        self.app_listbox.delete(0, tk.END)
        self.detected_apps.clear()  # Ensure this is clearing out old references cleanly

        hub_dir = Path(__file__).parent.resolve()
        self.log_message(f"SYSTEM: Scanning vector layout in {hub_dir.name}...")

        # Decoupled targets mapping subdirectories to their target binary executions
        suite_targets = {
            "editorsf/editorsf.py": "[MODULE] GRAPHICS SUITE",
            "arcadesf/arcadesf.py": "[MODULE] ARCADE DECK",
            "desksf/desksf.py":     "[MODULE] OVERLAY LENS",
            "moviesf/moviesf.py":   "[MODULE] VIDEO MIXER",
            "objsf/objsf.py":       "[MODULE] 3D SCANNER",
            "docsf/docsf.py":       "[MODULE] TEXT READER",
            "voicesf/voicesf.py":     "[MODULE] VOICE CHANGER",
            "mixersf/mixersf.py":   "[MODULE] AUDIO MIXER",
            "recordsf/recordsf.py": "[MODULE] SCREEN RECORDER"
        }

        try:
            for relative_path, display_name in suite_targets.items():
                target_path = hub_dir / relative_path
                if target_path.exists():
                    self.detected_apps.append({
                        "path": target_path,
                        "display": display_name
                    })
        except Exception as e:
            self.log_message(f"SYSTEM ERROR during sweep: {str(e)}")

        for app in self.detected_apps:
            self.app_listbox.insert(tk.END, f"  {app['display']}")

        self.log_message(f"SYSTEM: Sweep complete. Connected to {len(self.detected_apps)} standalone subsystems.")

    def log_message(self, message):
        self.console_text.config(state="normal")
        self.console_text.insert(tk.END, f"{message}\n")
        self.console_text.see(tk.END)
        self.console_text.config(state="disabled")

    def launch_selected(self):
        """Safely boots the isolated module payload inside its localized directory path."""
        try:
            sel_idx = self.app_listbox.curselection()[0]
        except IndexError:
            self.log_message("ERROR: No bootable hardware target selected.")
            return

        app = self.detected_apps[sel_idx]
        app_path = app["path"]
        app_name = app["display"]

        self.play_sound("launch")
        self.log_message(f"BOOT: Initializing stream payload for {app_name}...")

        def _runner():
            try:
                cmd = [sys.executable or "python3", app_path.name]

                process = subprocess.Popen(
                    cmd,
                    cwd=str(app_path.parent),  # Locks execution directory environment context strictly inside its folder
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                self.running_processes[app_name] = process
                self.log_message(f"ONLINE: {app_name} active on PID {process.pid}")

                # Realtime diagnostic back-piping to central hub console logs
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.log_message(f"[{app_path.name.upper()}] {line.strip()}")
                
                process.stdout.close()
                return_code = process.wait()
                self.log_message(f"OFFLINE: {app_name} closed (Return Code {return_code})")
                self.running_processes.pop(app_name, None)
            except Exception as e:
                self.log_message(f"CRITICAL ERROR: {str(e)}")

        threading.Thread(target=_runner, daemon=True).start()

    def toggle_theme(self):
        """Swaps UI configurations between Amber and Cyan profiles on the fly."""
        self.play_sound("toggle")
        
        self.current_theme_name = "FORENSIC CYAN" if self.current_theme_name == "SARIF AMBER" else "SARIF AMBER"
        self.theme = THEMES[self.current_theme_name]
        
        # Apply fresh base frame colors
        theme = self.theme
        self.root.configure(bg=theme["bg"])
        self.hud_canvas.configure(bg=theme["bg"])
        self.hud_frame.configure(bg=theme["bg"])
        
        # Redraw ocular layers
        self.draw_cyber_eye()
        
        # Propagate changes to child frames recursively
        for widget in self.hud_frame.winfo_children():
            self.recolor_widget_tree(widget)
            
        self.log_message(f"SYSTEM: Color matrix re-routed to {self.current_theme_name} profile.")

    def recolor_widget_tree(self, widget):
        theme = self.theme
        try:
            widget.configure(bg=theme["bg"])
        except tk.TclError:
            pass

        if isinstance(widget, tk.Label):
            if widget == self.lbl_title:
                widget.configure(fg=theme["hot"], bg=theme["bg"])
            else:
                widget.configure(fg=theme["hot"], bg=theme["panel_bg"])
                
        elif isinstance(widget, tk.Button):
            if widget == self.btn_theme:
                widget.configure(text=f"INTERFACE: {self.current_theme_name}", bg=theme["panel_bg"], fg=theme["hot"])
            else:
                widget.configure(bg=theme["bg"], fg=theme["hot"])
                
        elif isinstance(widget, tk.Listbox):
            widget.configure(
                bg=theme["bg"], fg=theme["hot"], 
                selectbackground=theme["hot"], selectforeground=theme["bg"]
            )
        elif isinstance(widget, tk.Text):
            widget.configure(bg=theme["terminal"], fg=theme["text"])
        elif isinstance(widget, tk.Frame):
            if widget in (self.left_panel, self.right_panel):
                widget.configure(bg=theme["panel_bg"])
            else:
                widget.configure(bg=theme["bg"])

        for child in widget.winfo_children():
            self.recolor_widget_tree(child)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = AugmentedSerifHub()
    app.run()
