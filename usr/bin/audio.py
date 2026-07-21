# audio.py
import os
import subprocess
import threading

_active_processes = {}  # sound_type -> subprocess.Popen of its currently-playing instance
_lock = threading.Lock()


def play_sound(sound_type: str):
    """Launches non-blocking sub-processes to play sound effects on Linux Mint.

    Two defensive changes vs. the original:
    - Tracks the in-flight process per sound_type and terminates any prior
      instance before starting a new one, so a rapid re-trigger (e.g. a
      quick double toggle) can't stack overlapping playback of the same
      clip - that stacking is what tends to read as "looping" even though
      neither playback is actually looping.
    - Caps playback with a timeout so a hung player process (e.g. from a
      malformed WAV header with an unknown/streaming length) gets killed
      rather than running indefinitely.
    """
    sound_files = {
        "click": "click.wav",
        "sweep": "sweep.wav",
        "toggle": "toggle.wav",
        "theme": "theme.wav"
    }
    sound_file = sound_files.get(sound_type)
    if not sound_file or not os.path.exists(sound_file):
        return  # Fails silently to prevent terminal spam

    def _execute():
        with _lock:
            prev = _active_processes.get(sound_type)
        if prev and prev.poll() is None:
            try:
                prev.terminate()
                prev.wait(timeout=1)
            except Exception:
                try:
                    prev.kill()
                except Exception:
                    pass

        proc = None
        try:
            # PulseAudio play
            proc = subprocess.Popen(["paplay", sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            try:
                # Fallback to ALSA
                proc = subprocess.Popen(["aplay", sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                return

        with _lock:
            _active_processes[sound_type] = proc

        try:
            proc.wait(timeout=10)  # hard cap - see docstring
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass

    threading.Thread(target=_execute, daemon=True).start()
