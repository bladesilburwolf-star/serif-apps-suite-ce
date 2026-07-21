# serif-apps-suite-ce
Serif Apps Suite Complete Edition! It now features a video mixer, screen recorder, voice changer, and arcade!
1. Core System Dependencies
These are binary libraries required at the OS level (via apt) for your audio processing engines to interface with your system hardware:

libportaudio2: Required by sounddevice to map the duplex microphone and speaker streams.

libsndfile1: Required by soundfile to handle hardware-accelerated reading and writing of uncompressed audio vectors.

ffmpeg: Required by pydub and moviepy as the underlying backend pipeline for rendering, converting, and slicing audio/video frames.

2. Python Packages (pip)
Depending on which application you are packaging (such as your video processing utility or this vocal matrix), you can split your requirements manifests using these specific targets:

SERIF-VOICE (Vocal Matrix)
numpy: Powering all vector mathematics and block-based buffer arrays.

scipy: Specifically utilizing scipy.signal for C-optimized audio filtering.

sounddevice: Binding Python to PortAudio for live audio monitor streaming.

soundfile: Managing low-overhead file saving and loading workflows.

pydub: Handling the downmixing and decoding parsing of MP3 streams into unified float32 arrays.

SERIF-MIXER (Video / Audio Automator)
moviepy: The primary rendering library used by your script to automate video mixing workflows.

3. Built-in Standard Libraries
These do not need to be listed in your package dependency files since they ship natively with your Python runtime, but they are critical to your application architectures:

tkinter / ttk: Driving your unified graphic interfaces. (Note: On some minimal Linux environments like Lubuntu, you may need to explicitly include python3-tk as an OS-level package requirement).

threading: Handling async rendering loops and background matrix processing to keep the UI responsive.

os, sys, time: Managing file-pathing pipelines and internal clock vitals.
