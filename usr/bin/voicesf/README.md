# SERIF-VOICE

Cyberpunk-retro voice changer / vocal FX rack for the Serif Graphics Suite.
Fat-trimmed on purpose: pure numpy/scipy DSP, no shader passes, no bloated
audio frameworks. Designed to run comfortably on a Pentium Dual Core
E6700/E5800 with a Radeon HD 6450.

## What it does

- **LIVE MONITOR tab** -- mic in -> effect chain -> speaker out, in real
  time, with input/output device selection and LED-style level meters.
- **STUDIO tab** -- load a WAV/FLAC/OGG file, dial in effects, process
  offline (runs on a background thread so the UI stays responsive), preview
  the waveform, export a new WAV.

Both tabs share the same six effects, each with its own independent chain
instance (so you can, say, run a light Chorus live but a heavier Reverb +
Pitch combo in the Studio without them fighting over state):

| Effect | What it's doing |
|---|---|
| Pitch Shift | Dual-read-head granular resampler (classic lightweight pitch-shift algorithm, no phase vocoder) |
| Robot Voice | Ring modulation against a tunable carrier tone |
| Radio Voice | Bandpass filter + soft-clip distortion (walkie-talkie / old-speaker tone) |
| Echo | Feedback delay (comb filter via `scipy.signal.lfilter` with persistent state) |
| Reverb | Small Schroeder reverb -- 4 parallel combs + 2 series allpasses |
| Chorus / Flanger | Single LFO-modulated delay line |

Every effect is block-based and stateful, so the exact same classes drive
both the real-time callback and the offline file processor -- no duplicated
DSP code.

### Recording (screen-recorder style)

The Live Monitor tab has a RECORD panel, separate from the monitor
pass-through above it. Pick a source:

- **Microphone** -- your headset/mic input
- **System Output (Loopback)** -- captures what's playing out of your
  speakers/headset. On Linux with PulseAudio or PipeWire this is normally a
  "Monitor of ..." entry in the same device list; pick it in the
  System/Loopback Device dropdown.
- **Mic + System (Mixed)** -- both at once. Two input streams run
  concurrently and get averaged together after you stop recording. The
  effect chain (if "Apply effect chain" is checked) runs as one offline
  pass over the mixed result rather than live, since safely summing two
  independent audio callback threads sample-for-sample in real time isn't
  reliable on this kind of hardware -- this way nothing glitches.

Recording and live monitoring are mutually exclusive while running, since
both would otherwise be pushing audio through the same effect chain objects
from two different callback threads at once. Stop one before starting the
other -- the UI enforces this for you.

Export format for recordings is WAV, OGG (Vorbis), or FLAC, picked before
you hit stop; you'll get a Save dialog once the recording finishes.

## Install

```bash
pip install -r requirements.txt --break-system-packages
sudo apt install libportaudio2   # needed for live mic monitoring
```

## Run

```bash
python3 serif_voice.py
```

## Notes / limitations

- File support is WAV / FLAC / OGG only (via libsndfile). No MP3 codec is
  bundled on purpose -- keeps the dependency footprint small. Convert MP3s
  with any lightweight tool first if you need to bring one in.
- Live latency depends on your soundcard's buffer; default block size is
  512 frames. If you hear glitches/crackle on the dual-core box, that's the
  CPU falling behind -- try disabling Reverb (the priciest effect, 6 filter
  stages) while live, and save it for offline Studio processing instead.
- Theming matches the rest of the suite: Green / Amber / Cyan / Mono,
  selectable from the top bar. Cyan is the default here.
