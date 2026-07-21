"""
audio_engine.py -- live mic I/O and file load/export for SERIF-VOICE.

Live path uses sounddevice (PortAudio) with a duplex callback stream so mic
input is processed through the effect chain and sent straight to the output
device with minimal buffering -- important on a Pentium Dual Core where big
buffers are the only way most apps avoid glitches, but big buffers also mean
big latency. Default block size is kept small (256-512 frames).

File path uses soundfile (libsndfile) for WAV/FLAC/OGG. MP3 is intentionally
not supported -- pulling in an MP3 codec is exactly the kind of "fat" this
suite avoids. Convert with any lightweight tool first if needed.
"""

import numpy as np
import soundfile as sf

try:
    import sounddevice as sd
    SOUNDDEVICE_OK = True
except OSError:
    sd = None
    SOUNDDEVICE_OK = False


class LiveEngine:
    """Duplex mic-in -> effect chain -> speaker-out stream."""

    def __init__(self, chain, samplerate=44100, blocksize=512, channels=1):
        self.chain = chain
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.channels = channels
        self.stream = None
        self.level_in = 0.0
        self.level_out = 0.0
        self.error = None

    @staticmethod
    def list_devices():
        if not SOUNDDEVICE_OK:
            return []
        return sd.query_devices()

    def _callback(self, indata, outdata, frames, time_info, status):
        if status:
            self.error = str(status)
        mono_in = indata[:, 0].astype(np.float32)
        self.level_in = float(np.max(np.abs(mono_in))) if len(mono_in) else 0.0
        processed = self.chain.process(mono_in)
        self.level_out = float(np.max(np.abs(processed))) if len(processed) else 0.0
        outdata[:, 0] = processed
        if self.channels > 1:
            for c in range(1, self.channels):
                outdata[:, c] = processed

    def start(self, input_device=None, output_device=None):
        if not SOUNDDEVICE_OK:
            raise RuntimeError(
                "PortAudio not available on this system. Install libportaudio2 "
                "(e.g. `sudo apt install libportaudio2`) and reinstall sounddevice."
            )
        self.chain.reset()
        self.stream = sd.Stream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            channels=self.channels,
            dtype="float32",
            device=(input_device, output_device),
            callback=self._callback,
        )
        self.stream.start()

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None


class RecordingEngine:
    """Screen-recorder-style audio capture: mic only, system/headset output
    (loopback) only, or both mixed. Independent of LiveEngine's monitor
    pass-through, so recording doesn't require monitoring to be running.

    - "mic" / "system": single InputStream, effects applied live per block
      if `chain` is given and `apply_fx` is True, written straight to an
      in-memory list of blocks.
    - "mixed": two InputStreams run concurrently, each collecting raw
      (unprocessed) audio independently. On stop() they're trimmed to equal
      length, averaged together, and -- if `apply_fx` was set -- the effect
      chain is run once over the full mixed result. Two live streams can't
      be safely summed sample-for-sample inside two separate callbacks
      without risking underrun glitches, so mixing is done after capture
      instead of in real time.
    """

    def __init__(self, chain=None, samplerate=44100, blocksize=512):
        self.chain = chain
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.mode = "mic"
        self.apply_fx = True
        self._streams = []
        self._blocks_a = []
        self._blocks_b = []
        self.recording = False
        self.error = None
        self.level = 0.0

    def _cb_single(self, indata, frames, time_info, status):
        if status:
            self.error = str(status)
        mono = indata[:, 0].astype(np.float32)
        self.level = float(np.max(np.abs(mono))) if len(mono) else 0.0
        if self.apply_fx and self.chain is not None:
            mono = self.chain.process(mono)
        self._blocks_a.append(mono.copy())

    def _cb_a(self, indata, frames, time_info, status):
        if status:
            self.error = str(status)
        self._blocks_a.append(indata[:, 0].astype(np.float32).copy())

    def _cb_b(self, indata, frames, time_info, status):
        self._blocks_b.append(indata[:, 0].astype(np.float32).copy())

    def start(self, mode, mic_device=None, system_device=None, apply_fx=True):
        if not SOUNDDEVICE_OK:
            raise RuntimeError(
                "PortAudio not available on this system. Install libportaudio2 "
                "(e.g. `sudo apt install libportaudio2`) and reinstall sounddevice."
            )
        self.mode = mode
        self.apply_fx = apply_fx
        self._blocks_a = []
        self._blocks_b = []
        self.error = None
        if self.chain is not None:
            self.chain.reset()

        if mode == "mixed":
            s1 = sd.InputStream(
                samplerate=self.samplerate, blocksize=self.blocksize,
                channels=1, dtype="float32", device=mic_device, callback=self._cb_a,
            )
            s2 = sd.InputStream(
                samplerate=self.samplerate, blocksize=self.blocksize,
                channels=1, dtype="float32", device=system_device, callback=self._cb_b,
            )
            self._streams = [s1, s2]
        else:
            device = mic_device if mode == "mic" else system_device
            s1 = sd.InputStream(
                samplerate=self.samplerate, blocksize=self.blocksize,
                channels=1, dtype="float32", device=device, callback=self._cb_single,
            )
            self._streams = [s1]

        for s in self._streams:
            s.start()
        self.recording = True

    def stop(self):
        for s in self._streams:
            s.stop()
            s.close()
        self._streams = []
        self.recording = False

        if self.mode == "mixed":
            a = np.concatenate(self._blocks_a) if self._blocks_a else np.zeros(0, dtype=np.float32)
            b = np.concatenate(self._blocks_b) if self._blocks_b else np.zeros(0, dtype=np.float32)
            n = min(len(a), len(b))
            mixed = (a[:n] * 0.5 + b[:n] * 0.5).astype(np.float32)
            if self.apply_fx and self.chain is not None and n > 0:
                mixed = process_offline(self.chain, mixed, self.samplerate)
            return mixed
        else:
            return np.concatenate(self._blocks_a) if self._blocks_a else np.zeros(0, dtype=np.float32)


def play_preview(data, samplerate, device=None):
    """Fire-and-forget playback for previewing a loaded/processed clip."""
    if not SOUNDDEVICE_OK:
        raise RuntimeError(
            "PortAudio not available on this system. Install libportaudio2 "
            "(e.g. `sudo apt install libportaudio2`) and reinstall sounddevice."
        )
    sd.stop()
    sd.play(data, samplerate, device=device)


def stop_preview():
    if SOUNDDEVICE_OK:
        sd.stop()


def load_file(path):
    """Load an audio file to mono float32 + samplerate."""
    data, sr = sf.read(path, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data.astype(np.float32), sr


def save_file(path, data, samplerate):
    sf.write(path, data, samplerate)


def process_offline(chain, data, samplerate, block_size=4096, progress_cb=None):
    """Run the whole effect chain over a full array, chunked, resetting
    stateful effects first so file processing is reproducible / seek-safe."""
    chain.sr = samplerate
    for fx in chain.effects:
        fx.sr = samplerate
    chain.reset()
    out = np.zeros_like(data)
    n = len(data)
    for i in range(0, n, block_size):
        block = data[i:i + block_size]
        out[i:i + len(block)] = chain.process(block)
        if progress_cb:
            progress_cb(min(1.0, (i + block_size) / n))
    return out
