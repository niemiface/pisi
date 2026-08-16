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
    # Full General MIDI instrument set (128 programs, per the GM1 spec).
    # FluidR3_GM.sf2 (and any GM-compliant soundfont) implements all of these.
    PRESETS = {
        # Piano
        "Acoustic Grand Piano": {"program": 0},
        "Bright Acoustic Piano": {"program": 1},
        "Electric Grand Piano": {"program": 2},
        "Honky-tonk Piano": {"program": 3},
        "Electric Piano 1": {"program": 4},
        "Electric Piano 2": {"program": 5},
        "Harpsichord": {"program": 6},
        "Clavinet": {"program": 7},
        # Chromatic Percussion
        "Celesta": {"program": 8},
        "Glockenspiel": {"program": 9},
        "Music Box": {"program": 10},
        "Vibraphone": {"program": 11},
        "Marimba": {"program": 12},
        "Xylophone": {"program": 13},
        "Tubular Bells": {"program": 14},
        "Dulcimer": {"program": 15},
        # Organ
        "Drawbar Organ": {"program": 16},
        "Percussive Organ": {"program": 17},
        "Rock Organ": {"program": 18},
        "Church Organ": {"program": 19},
        "Reed Organ": {"program": 20},
        "Accordion": {"program": 21},
        "Harmonica": {"program": 22},
        "Tango Accordion": {"program": 23},
        # Guitar
        "Acoustic Guitar (nylon)": {"program": 24},
        "Acoustic Guitar (steel)": {"program": 25},
        "Electric Guitar (jazz)": {"program": 26},
        "Electric Guitar (clean)": {"program": 27},
        "Electric Guitar (muted)": {"program": 28},
        "Overdriven Guitar": {"program": 29},
        "Distortion Guitar": {"program": 30},
        "Guitar Harmonics": {"program": 31},
        # Bass
        "Acoustic Bass": {"program": 32},
        "Electric Bass (finger)": {"program": 33},
        "Electric Bass (pick)": {"program": 34},
        "Fretless Bass": {"program": 35},
        "Slap Bass 1": {"program": 36},
        "Slap Bass 2": {"program": 37},
        "Synth Bass 1": {"program": 38},
        "Synth Bass 2": {"program": 39},
        # Strings
        "Violin": {"program": 40},
        "Viola": {"program": 41},
        "Cello": {"program": 42},
        "Contrabass": {"program": 43},
        "Tremolo Strings": {"program": 44},
        "Pizzicato Strings": {"program": 45},
        "Orchestral Harp": {"program": 46},
        "Timpani": {"program": 47},
        "String Ensemble 1": {"program": 48},
        "String Ensemble 2": {"program": 49},
        "Synth Strings 1": {"program": 50},
        "Synth Strings 2": {"program": 51},
        "Choir Aahs": {"program": 52},
        "Voice Oohs": {"program": 53},
        "Synth Choir": {"program": 54},
        "Orchestra Hit": {"program": 55},
        # Brass
        "Trumpet": {"program": 56},
        "Trombone": {"program": 57},
        "Tuba": {"program": 58},
        "Muted Trumpet": {"program": 59},
        "French Horn": {"program": 60},
        "Brass Section": {"program": 61},
        "Synth Brass 1": {"program": 62},
        "Synth Brass 2": {"program": 63},
        # Reed
        "Soprano Sax": {"program": 64},
        "Alto Sax": {"program": 65},
        "Tenor Sax": {"program": 66},
        "Baritone Sax": {"program": 67},
        "Oboe": {"program": 68},
        "English Horn": {"program": 69},
        "Bassoon": {"program": 70},
        "Clarinet": {"program": 71},
        # Pipe
        "Piccolo": {"program": 72},
        "Flute": {"program": 73},
        "Recorder": {"program": 74},
        "Pan Flute": {"program": 75},
        "Blown Bottle": {"program": 76},
        "Shakuhachi": {"program": 77},
        "Whistle": {"program": 78},
        "Ocarina": {"program": 79},
        # Synth Lead
        "Square Lead": {"program": 80},
        "Saw Lead": {"program": 81},
        "Calliope Lead": {"program": 82},
        "Chiff Lead": {"program": 83},
        "Charang Lead": {"program": 84},
        "Voice Lead": {"program": 85},
        "Fifths Lead": {"program": 86},
        "Bass + Lead": {"program": 87},
        # Synth Pad
        "New Age Pad": {"program": 88},
        "Warm Pad": {"program": 89},
        "Polysynth Pad": {"program": 90},
        "Choir Pad": {"program": 91},
        "Bowed Pad": {"program": 92},
        "Metallic Pad": {"program": 93},
        "Halo Pad": {"program": 94},
        "Sweep Pad": {"program": 95},
        # Synth Effects
        "Rain FX": {"program": 96},
        "Soundtrack FX": {"program": 97},
        "Crystal FX": {"program": 98},
        "Atmosphere FX": {"program": 99},
        "Brightness FX": {"program": 100},
        "Goblins FX": {"program": 101},
        "Echoes FX": {"program": 102},
        "Sci-Fi FX": {"program": 103},
        # Ethnic
        "Sitar": {"program": 104},
        "Banjo": {"program": 105},
        "Shamisen": {"program": 106},
        "Koto": {"program": 107},
        "Kalimba": {"program": 108},
        "Bagpipe": {"program": 109},
        "Fiddle": {"program": 110},
        "Shanai": {"program": 111},
        # Percussive
        "Tinkle Bell": {"program": 112},
        "Agogo": {"program": 113},
        "Steel Drums": {"program": 114},
        "Woodblock": {"program": 115},
        "Taiko Drum": {"program": 116},
        "Melodic Tom": {"program": 117},
        "Synth Drum": {"program": 118},
        "Reverse Cymbal": {"program": 119},
        # Sound Effects
        "Guitar Fret Noise": {"program": 120},
        "Breath Noise": {"program": 121},
        "Seashore": {"program": 122},
        "Bird Tweet": {"program": 123},
        "Telephone Ring": {"program": 124},
        "Helicopter": {"program": 125},
        "Applause": {"program": 126},
        "Gunshot": {"program": 127},
    }

    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.current_preset = "Acoustic Grand Piano"
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
