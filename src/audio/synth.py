import time
import numpy as np
import sounddevice as sd
import traceback

try:
    import fluidsynth
    HAS_FLUIDSYNTH = True
except ImportError:
    HAS_FLUIDSYNTH = False

SAMPLE_RATE = 44100
BLOCK_SIZE = 1024

class SynthEngine:
    # Map our preset names to General MIDI Program Numbers
    # (FluidR3_GM contains 128 standard instruments)
    PRESETS = {
        "Grand Piano": {"program": 0},
        "Electric Piano": {"program": 4},
        "Drawbar Organ": {"program": 16},
        "Church Organ": {"program": 19},
        "Acoustic Guitar": {"program": 24},
        "Electric Bass": {"program": 33},
        "Synth Bass": {"program": 38},
        "String Ensemble": {"program": 48},
        "Synth Strings": {"program": 50},
        "Choir Aahs": {"program": 52},
        "Trumpet": {"program": 56},
        "Brass Section": {"program": 61},
        "Tenor Sax": {"program": 66},
        "Flute": {"program": 73},
        "Square Lead": {"program": 80},
        "Saw Lead": {"program": 81},
        "Chiff Lead": {"program": 83},
        "Warm Pad": {"program": 89},
        "Choir Pad": {"program": 91},
        "Sci-Fi": {"program": 103},
    }

    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.current_preset = "Grand Piano"
        self.volume = 0.8
        self.stream = None
        self.last_audio_buffer = np.zeros(BLOCK_SIZE, dtype=np.float32)
        
        self.fs = None
        self.sfid = None
        
        if HAS_FLUIDSYNTH:
            try:
                # Initialize FluidSynth (no driver started, we fetch samples manually)
                self.fs = fluidsynth.Synth(samplerate=float(self.sample_rate))
                # Load the standard GM soundfont installed via apt-get
                sf_path = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
                self.sfid = self.fs.sfload(sf_path)
                if self.sfid == -1:
                    print(f"[AUDIO] WARNING: SoundFont not found at {sf_path}")
            except Exception as e:
                print(f"[AUDIO] FluidSynth init error: {e}")

        self.apply_preset(self.current_preset)

    def find_audio_device(self):
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                name = dev['name'].lower()
                if dev['max_output_channels'] > 0:
                    if 'hifiberry' in name or 'pcm5102a' in name or 'sndrpihifiberry' in name:
                        print(f"[AUDIO] Bound to Pirate Audio DAC [{idx}]: {dev['name']}")
                        return idx
            for idx, dev in enumerate(devices):
                if dev['max_output_channels'] > 0 and 'default' in dev['name'].lower():
                    return idx
        except Exception as e:
            print(f"[AUDIO WARNING] {e}")
        return None

    def apply_preset(self, preset_name):
        if preset_name in self.PRESETS:
            self.current_preset = preset_name
            prog = self.PRESETS[preset_name]["program"]
            if self.fs and self.sfid != -1:
                self.fs.program_select(0, self.sfid, 0, prog)
            print(f"[AUDIO] FluidSynth Program: {prog} ({preset_name})")

    def set_cutoff(self, value_0_to_127):
        """Send MIDI CC 74 (Brightness/Cutoff) to FluidSynth"""
        if self.fs:
            self.fs.cc(0, 74, int(value_0_to_127))

    @property
    def cutoff(self):
        return getattr(self, '_cutoff', 9000.0)

    @cutoff.setter
    def cutoff(self, value):
        self._cutoff = value
        # Map old cutoff Hz (800-9000) to MIDI CC (0-127)
        cc_val = max(0, min(127, int((value - 800) / (9000 - 800) * 127)))
        self.set_cutoff(cc_val)

    def note_on(self, note, velocity=1.0):
        if self.fs:
            # Map 0.0-1.0 to 0-127
            vel_midi = max(1, min(127, int(velocity * 127)))
            self.fs.noteon(0, note, vel_midi)

    def note_off(self, note):
        if self.fs:
            self.fs.noteoff(0, note)

    def process_block(self, frames):
        if self.fs:
            # Get 16-bit interleaved stereo samples from FluidSynth
            # Returns flat array: [L0, R0, L1, R1, ...]
            raw = self.fs.get_samples(frames)
            
            # Convert to float32 in range [-1.0, 1.0] and reshape to (frames, 2)
            block = raw.astype(np.float32) / 32768.0
            block = block.reshape((frames, 2))
            
            block *= self.volume
            
            # Store mono mixdown for visualizers
            self.last_audio_buffer = (block[:, 0] + block[:, 1]) * 0.5
            return block
        else:
            return np.zeros((frames, 2), dtype=np.float32)

    def audio_callback(self, outdata, frames, time_info, status):
        try:
            block = self.process_block(frames)
            outdata[:] = block
        except Exception as e:
            traceback.print_exc()
            outdata[:] = np.zeros((frames, 2), dtype=np.float32)

    def start(self):
        if self.stream is None:
            dev = self.find_audio_device()
            self.stream = sd.OutputStream(
                device=dev, channels=2, samplerate=self.sample_rate,
                blocksize=BLOCK_SIZE, callback=self.audio_callback,
                latency='high'
            )
            self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.fs:
            self.fs.delete()
            self.fs = None
