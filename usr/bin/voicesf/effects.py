"""
effects.py -- SERIF-VOICE DSP core

All effects are block-based and stateful, so the exact same objects can be
used for real-time streaming (small blocks, called repeatedly from an audio
callback) or offline file processing (one big block, or chunked - same call).

Design goals (fat-trimmed / lightweight):
  - numpy + scipy only, no heavy DSP frameworks
  - scipy.signal.lfilter (C-optimized) used for recursive filters instead of
    hand-rolled Python sample loops
  - everything vectorized per block -- no per-sample Python loops anywhere
  - safe on a Pentium Dual Core: each effect costs O(n) with small constants
"""

import numpy as np
from scipy.signal import lfilter, butter


def _interp_circular(buf: np.ndarray, positions: np.ndarray) -> np.ndarray:
    """Linear interpolation into a circular buffer at fractional positions."""
    size = len(buf)
    idx0 = np.floor(positions).astype(np.int64) % size
    idx1 = (idx0 + 1) % size
    frac = positions - np.floor(positions)
    return buf[idx0] * (1.0 - frac) + buf[idx1] * frac


class Effect:
    """Base class for all voice effects."""
    name = "Effect"
    params = {}  # {param_name: (min, max, default, step)}

    def __init__(self, samplerate: int):
        self.sr = samplerate
        self.enabled = False
        self.values = {k: v[2] for k, v in self.params.items()}
        self.reset()

    def reset(self):
        """Clear internal state (call when starting a stream or seeking)."""
        pass

    def process(self, block: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def set_param(self, name: str, value: float):
        if name in self.values:
            lo, hi, _, _ = self.params[name]
            self.values[name] = float(np.clip(value, lo, hi))


class PitchShift(Effect):
    """Dual-read-head granular pitch shifter (classic lightweight algorithm).

    Writes into a circular buffer at normal rate, reads back with two
    read heads spaced half a buffer apart, running at `factor` speed, and
    crossfades between them with a triangular window so neither head ever
    has to jump discontinuously past the write pointer.
    """
    name = "Pitch Shift"
    params = {"semitones": (-12.0, 12.0, 0.0, 0.5)}

    def reset(self):
        self.buf_size = max(2048, int(self.sr * 0.09))  # ~90ms buffer
        self.buffer = np.zeros(self.buf_size)
        self.write_pos = 0
        self.read_phase = 0.0

    def process(self, block: np.ndarray) -> np.ndarray:
        st = self.values["semitones"]
        if st == 0.0:
            return block
        factor = 2.0 ** (st / 12.0)
        n = len(block)
        size = self.buf_size
        half = size / 2.0

        # write incoming samples into circular buffer
        idx_write = (self.write_pos + np.arange(n)) % size
        self.buffer[idx_write] = block
        self.write_pos = (self.write_pos + n) % size

        # head A / head B positions
        pos_a = self.read_phase + np.arange(n) * factor
        pos_b = pos_a + half

        sample_a = _interp_circular(self.buffer, pos_a)
        sample_b = _interp_circular(self.buffer, pos_b)

        cycle_a = (pos_a % size) / size
        weight_a = 1.0 - np.abs(2.0 * cycle_a - 1.0)  # triangular 0..1..0
        weight_b = 1.0 - weight_a

        out = sample_a * weight_a + sample_b * weight_b
        self.read_phase = (self.read_phase + n * factor) % size
        return out.astype(np.float32)


class RobotVoice(Effect):
    """Ring modulation against a fixed carrier -- the classic robot-voice effect."""
    name = "Robot Voice"
    params = {"carrier_hz": (30.0, 400.0, 90.0, 5.0), "mix": (0.0, 1.0, 1.0, 0.05)}

    def reset(self):
        self.phase = 0.0

    def process(self, block: np.ndarray) -> np.ndarray:
        freq = self.values["carrier_hz"]
        mix = self.values["mix"]
        n = len(block)
        t = (self.phase + np.arange(n)) / self.sr
        carrier = np.sin(2.0 * np.pi * freq * t)
        self.phase = (self.phase + n) % self.sr
        wet = block * carrier
        return (block * (1 - mix) + wet * mix).astype(np.float32)


class RadioVoice(Effect):
    """Bandpass filter + soft clipping -- old speaker / walkie-talkie tone."""
    name = "Radio Voice"
    params = {
        "low_hz": (300.0, 1200.0, 500.0, 50.0),
        "high_hz": (1500.0, 4000.0, 2800.0, 100.0),
        "drive": (1.0, 8.0, 3.0, 0.5),
    }

    def reset(self):
        self._zi = None
        self._coeffs_key = None

    def _design(self):
        low = self.values["low_hz"]
        high = self.values["high_hz"]
        nyq = self.sr / 2.0
        low = min(low, nyq - 100)
        high = min(high, nyq - 10)
        if high <= low:
            high = low + 200
        b, a = butter(2, [low / nyq, high / nyq], btype="band")
        return b, a

    def process(self, block: np.ndarray) -> np.ndarray:
        key = (round(self.values["low_hz"]), round(self.values["high_hz"]))
        if self._coeffs_key != key:
            self.b, self.a = self._design()
            self._coeffs_key = key
            self._zi = np.zeros(max(len(self.a), len(self.b)) - 1)
        filtered, self._zi = lfilter(self.b, self.a, block, zi=self._zi)
        drive = self.values["drive"]
        distorted = np.tanh(filtered * drive) / np.tanh(drive)
        return distorted.astype(np.float32)


class Echo(Effect):
    """Discrete feedback delay -- a comb filter implemented via lfilter+state."""
    name = "Echo"
    params = {
        "delay_ms": (80.0, 600.0, 250.0, 10.0),
        "feedback": (0.0, 0.85, 0.35, 0.05),
        "mix": (0.0, 1.0, 0.35, 0.05),
    }

    def reset(self):
        self._zi = None
        self._delay_samples = None

    def process(self, block: np.ndarray) -> np.ndarray:
        d = max(1, int(self.sr * self.values["delay_ms"] / 1000.0))
        if self._delay_samples != d:
            self._delay_samples = d
            a = np.zeros(d + 1)
            a[0] = 1.0
            a[d] = -self.values["feedback"]
            self.a = a
            self.b = np.array([1.0])
            self._zi = np.zeros(d)
        else:
            self.a[-1] = -self.values["feedback"]
        wet, self._zi = lfilter(self.b, self.a, block, zi=self._zi)
        mix = self.values["mix"]
        return (block * (1 - mix) + wet * mix).astype(np.float32)


class Reverb(Effect):
    """Small Schroeder reverb: parallel combs + series allpasses."""
    name = "Reverb"
    params = {"decay": (0.0, 0.95, 0.5, 0.05), "mix": (0.0, 1.0, 0.3, 0.05)}

    _comb_ms = (29.7, 37.1, 41.1, 43.7)
    _allpass_ms = (5.0, 1.7)

    def reset(self):
        self._built = False

    def _build(self):
        self._comb_zi = []
        self._comb_ab = []
        for ms in self._comb_ms:
            d = max(1, int(self.sr * ms / 1000.0))
            a = np.zeros(d + 1)
            a[0] = 1.0
            self._comb_ab.append([np.array([1.0]), a, d])
            self._comb_zi.append(np.zeros(d))
        self._ap_zi = []
        self._ap_ab = []
        g = 0.5
        for ms in self._allpass_ms:
            d = max(1, int(self.sr * ms / 1000.0))
            b = np.zeros(d + 1)
            b[0] = -g
            b[d] = 1.0
            a = np.zeros(d + 1)
            a[0] = 1.0
            a[d] = -g
            self._ap_ab.append([b, a, d])
            self._ap_zi.append(np.zeros(d))
        self._built = True

    def process(self, block: np.ndarray) -> np.ndarray:
        if not self._built:
            self._build()
        decay = self.values["decay"]
        mix = self.values["mix"]

        comb_sum = np.zeros_like(block, dtype=np.float64)
        for i, (b, a, d) in enumerate(self._comb_ab):
            a[d] = -decay
            out, self._comb_zi[i] = lfilter(b, a, block, zi=self._comb_zi[i])
            comb_sum += out
        comb_sum /= len(self._comb_ab)

        signal = comb_sum
        for i, (b, a, d) in enumerate(self._ap_ab):
            signal, self._ap_zi[i] = lfilter(b, a, signal, zi=self._ap_zi[i])

        return (block * (1 - mix) + signal * mix).astype(np.float32)


class ChorusFlanger(Effect):
    """Single modulated delay line -- LFO-swept for chorus/flanger character."""
    name = "Chorus / Flanger"
    params = {
        "rate_hz": (0.05, 5.0, 0.8, 0.05),
        "depth_ms": (0.5, 15.0, 4.0, 0.5),
        "base_ms": (2.0, 25.0, 8.0, 0.5),
        "mix": (0.0, 1.0, 0.4, 0.05),
    }

    def reset(self):
        self.buf_size = max(2048, int(self.sr * 0.06))
        self.buffer = np.zeros(self.buf_size)
        self.write_pos = 0
        self.lfo_phase = 0.0

    def process(self, block: np.ndarray) -> np.ndarray:
        n = len(block)
        size = self.buf_size
        rate = self.values["rate_hz"]
        depth = self.values["depth_ms"] * self.sr / 1000.0
        base = self.values["base_ms"] * self.sr / 1000.0

        idx_write = (self.write_pos + np.arange(n)) % size
        self.buffer[idx_write] = block
        self.write_pos = (self.write_pos + n) % size

        t = (self.lfo_phase + np.arange(n)) / self.sr
        lfo = np.sin(2.0 * np.pi * rate * t)
        self.lfo_phase = (self.lfo_phase + n) % self.sr

        delay = base + depth * lfo
        read_pos = idx_write - delay
        wet = _interp_circular(self.buffer, read_pos)

        mix = self.values["mix"]
        return (block * (1 - mix) + wet * mix).astype(np.float32)


EFFECT_CLASSES = [PitchShift, RobotVoice, RadioVoice, Echo, Reverb, ChorusFlanger]


class EffectChain:
    """Ordered chain of effects applied in sequence to each audio block."""

    def __init__(self, samplerate: int):
        self.sr = samplerate
        self.effects = [cls(samplerate) for cls in EFFECT_CLASSES]

    def reset(self):
        for fx in self.effects:
            fx.reset()

    def process(self, block: np.ndarray) -> np.ndarray:
        out = block
        for fx in self.effects:
            if fx.enabled:
                out = fx.process(out)
        return out

    def by_name(self, name: str) -> Effect:
        for fx in self.effects:
            if fx.name == name:
                return fx
        raise KeyError(name)
