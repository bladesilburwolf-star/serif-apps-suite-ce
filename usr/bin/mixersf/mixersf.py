import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

# MoviePy v2.0+ Imports
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
import moviepy.video.fx.all as vfx

class SerifMixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("serif-mixer // EDM Video Looper")
        self.root.geometry("580x620")
        self.root.configure(bg="#2e2e2e")
        
        # Apply global dark styling properties to ttk widgets
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure("TProgressbar", thickness=15, troughcolor="#1e1e1e", background="#4caf50")
        self.style.configure("TCombobox", fieldbackground="#1e1e1e", background="#2e2e2e", foreground="#ffffff")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Title
        title_label = tk.Label(self.root, text="SERIF-MIXER", font=("Helvetica", 18, "bold"), fg="#ffffff", bg="#2e2e2e")
        title_label.pack(pady=10)
        
        subtitle_label = tk.Label(self.root, text="Automated Video Loop & Audio Syncer", font=("Helvetica", 10, "italic"), fg="#cccccc", bg="#2e2e2e")
        subtitle_label.pack(pady=2)
        
        # Form Container
        form_frame = tk.Frame(self.root, bg="#2e2e2e")
        form_frame.pack(pady=10, padx=20, fill="x")
        
        # Input Styling Configs
        entry_kwargs = {"bg": "#1e1e1e", "fg": "#ffffff", "insertbackground": "white", "relief": "solid", "bd": 1}
        
        # Inputs
        tk.Label(form_frame, text="Source Video:", fg="#ffffff", bg="#2e2e2e").grid(row=0, column=0, sticky="w", pady=5)
        self.ent_video = tk.Entry(form_frame, width=40, **entry_kwargs)
        self.ent_video.insert(0, "cdance1.mp4")
        self.ent_video.grid(row=0, column=1, pady=5, padx=5)
        
        tk.Label(form_frame, text="EDM Audio Track:", fg="#ffffff", bg="#2e2e2e").grid(row=1, column=0, sticky="w", pady=5)
        self.ent_audio = tk.Entry(form_frame, width=40, **entry_kwargs)
        self.ent_audio.insert(0, "psy.mp3")
        self.grid_audio = self.ent_audio.grid(row=1, column=1, pady=5, padx=5)
        
        tk.Label(form_frame, text="Crossfade (seconds):", fg="#ffffff", bg="#2e2e2e").grid(row=2, column=0, sticky="w", pady=5)
        self.ent_fade = tk.Entry(form_frame, width=10, **entry_kwargs)
        self.ent_fade.insert(0, "0.4")
        self.ent_fade.grid(row=2, column=1, sticky="w", pady=5, padx=5)
        
        tk.Label(form_frame, text="Save Output As:", fg="#ffffff", bg="#2e2e2e").grid(row=3, column=0, sticky="w", pady=5)
        self.ent_output = tk.Entry(form_frame, width=40, **entry_kwargs)
        self.ent_output.insert(0, "itstyle.mp4")
        self.ent_output.grid(row=3, column=1, pady=5, padx=5)

        # --- Handbrake-Style Video Tweaks Section ---
        tweak_frame = tk.LabelFrame(self.root, text=" Handbrake-Style Tweaks ", fg="#ffffff", bg="#2e2e2e", padx=10, pady=10, relief="solid", bd=1)
        tweak_frame.pack(pady=10, padx=20, fill="x")
        
        # Resolution Preset Selector
        res_frame = tk.Frame(tweak_frame, bg="#2e2e2e")
        res_frame.pack(anchor="w", pady=5)
        tk.Label(res_frame, text="Output Resolution Preset:", fg="#ffffff", bg="#2e2e2e").pack(side="left")
        
        self.res_preset = ttk.Combobox(res_frame, values=["Original", "1080x1080 (Square Shorts)", "720x720 (Square Light)", "1080x1920 (Vertical Shorts)", "720x1280 (Vertical Light)"], state="readonly", width=25)
        self.res_preset.set("1080x1080 (Square Shorts)")
        self.res_preset.pack(side="left", padx=5)

        # Max Length Slider Safeguard
        slider_frame = tk.Frame(tweak_frame, bg="#2e2e2e")
        slider_frame.pack(anchor="w", pady=10, fill="x")
        tk.Label(slider_frame, text="Cap Output Length (seconds):", fg="#ffffff", bg="#2e2e2e").pack(side="left")
        
        self.lbl_slider_val = tk.Label(slider_frame, text="15s", fg="#4caf50", bg="#2e2e2e", font=("Helvetica", 10, "bold"))
        self.lbl_slider_val.pack(side="right", padx=5)
        
        self.sld_length = tk.Scale(slider_frame, from_=5, to=60, orient="horizontal", bg="#2e2e2e", fg="#ffffff", highlightthickness=0, troughcolor="#1e1e1e", activebackground="#4caf50", command=self.update_slider_label)
        self.sld_length.set(15)
        self.sld_length.pack(side="right", fill="x", expand=True, padx=5)

        # Performance Enforcements
        self.use_gpu = tk.BooleanVar(value=False) # Switched default off since driver limits it
        self.chk_gpu = tk.Checkbutton(tweak_frame, text="Use GPU Acceleration (h264_nvenc)", variable=self.use_gpu, fg="#ffffff", bg="#2e2e2e", activebackground="#2e2e2e", activeforeground="#ffffff", selectcolor="#1e1e1e")
        self.chk_gpu.pack(anchor="w")
        
        self.use_ultrafast = tk.BooleanVar(value=True)
        self.chk_speed = tk.Checkbutton(tweak_frame, text="Ultrafast Preset (Reduces dual-core stress)", variable=self.use_ultrafast, fg="#ffffff", bg="#2e2e2e", activebackground="#2e2e2e", activeforeground="#ffffff", selectcolor="#1e1e1e")
        self.chk_speed.pack(anchor="w")
        
        thread_frame = tk.Frame(tweak_frame, bg="#2e2e2e")
        thread_frame.pack(anchor="w", pady=5)
        tk.Label(thread_frame, text="Max CPU Threads:", fg="#ffffff", bg="#2e2e2e").pack(side="left")
        self.spin_threads = tk.Spinbox(thread_frame, from_=1, to=4, width=5, bg="#1e1e1e", fg="#ffffff", buttonbackground="#2e2e2e", relief="solid", bd=1)
        self.spin_threads.delete(0, "end")
        self.spin_threads.insert(0, "2")
        self.spin_threads.pack(side="left", padx=5)
        
        # Status
        self.lbl_status = tk.Label(self.root, text="", fg="#ffcc00", bg="#2e2e2e")
        self.lbl_status.pack(pady=5)
        
        # Progress Bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate", style="TProgressbar")
        self.progress.pack(pady=5)
        
        # Start Button
        self.btn_start = tk.Button(self.root, text="START MIXING", bg="#4caf50", fg="#ffffff", font=("Helvetica", 11, "bold"), relief="flat", activebackground="#45a049", activeforeground="#ffffff", command=self.start_mixing_thread)
        self.btn_start.pack(pady=10)

    def update_slider_label(self, val):
        self.lbl_slider_val.config(text=f"{val}s")

    def start_mixing_thread(self):
        self.btn_start.config(state="disabled")
        self.lbl_status.config(text="Status: Adjusting sizes & Rendering...")
        self.progress.start(10)
        
        threading.Thread(target=self.process_video, daemon=True).start()

    def process_video(self):
        try:
            v_name = self.ent_video.get()
            a_name = self.ent_audio.get()
            fade_len = float(self.ent_fade.get())
            o_path = self.ent_output.get()

            codec_choice = "h264_nvenc" if self.use_gpu.get() else "libx264"
            preset_choice = "ultrafast" if self.use_ultrafast.get() else "medium"
            thread_count = int(self.spin_threads.get())
            max_duration_cap = float(self.sld_length.get())

            if not os.path.exists(v_name) or not os.path.exists(a_name):
                raise FileNotFoundError("Source video or audio file missing!")

            # 1. Determine Handbrake-style resolution target first
            preset = self.res_preset.get()
            target_res = None
            if "1080x1080" in preset:
                target_res = (1080, 1080)
            elif "720x720" in preset:
                target_res = (720, 720)
            elif "1080x1920" in preset:
                target_res = (1080, 1920)
            elif "720x1280" in preset:
                target_res = (720, 1280)

            # 2. Load and instantly scale via FFmpeg backend (saves CPU/RAM)
            if target_res:
                # MoviePy v2.x processes target_resolution natively on read
                video_clip = VideoFileClip(v_name, target_resolution=target_res)
            else:
                video_clip = VideoFileClip(v_name)

            audio_clip = AudioFileClip(a_name)

            # 3. Calculate bounded duration caps
            target_duration = min(audio_clip.duration, max_duration_cap)

            clips_to_join = []
            current_duration = 0.0

            while current_duration < target_duration:
                clips_to_join.append(video_clip)
                if len(clips_to_join) == 1:
                    current_duration += video_clip.duration
                else:
                    current_duration += (video_clip.duration - fade_len)

            # 4. Compile the pre-resized loop structure
            final_video = concatenate_videoclips(clips_to_join, method="compose")

            # 5. Apply explicit target caps directly to properties
            final_video.duration = target_duration
            audio_clip.duration = target_duration
            final_video.audio = audio_clip

            # 6. Render the optimized stream
            final_video.write_videofile(
                o_path,
                fps=video_clip.fps,
                codec=codec_choice,
                preset=preset_choice,
                threads=thread_count,
                audio_codec="aac",
                logger=None
            )

            video_clip.close()
            audio_clip.close()
            final_video.close()

            self.root.after(0, self.mixing_done, f"Success! Output generated at {int(target_duration)}s length.")

        except Exception as e:
            self.root.after(0, self.mixing_done, f"Error: {str(e)}", True)

    def mixing_done(self, message, is_error=False):
        self.progress.stop()
        self.btn_start.config(state="normal")
        if is_error:
            self.lbl_status.config(text="Status: Failed.")
            messagebox.showerror("Processing Error", message)
        else:
            self.lbl_status.config(text="Status: Complete!")
            messagebox.showinfo("Success", message)

if __name__ == "__main__":
    root = tk.Tk()
    app = SerifMixerApp(root)
    root.mainloop()
