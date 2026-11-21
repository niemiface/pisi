import os
import time
import numpy as np
import sounddevice as sd
import traceback

from src.config import CONFIG, REPO_ROOT
from src.audio.soundfont_manager import SoundfontManager

try:
    import fluidsynth
    HAS_FLUIDSYNTH = True
except ImportError:
    HAS_FLUIDSYNTH = False

SAMPLE_RATE = CONFIG["audio"]["sample_rate"]
BLOCK_SIZE = CONFIG["audio"]["block_size"]

SOUNDFONT_MANIFEST_PATH = os.path.join(REPO_ROOT, CONFIG["soundfonts"]["manifest_path"])
DEFAULT_SOUNDFONT_ID = CONFIG["soundfonts"]["default_id"]
MAX_RESIDENT_BYTES = CONFIG["soundfonts"]["max_resident_mb"] * 1024 * 1024

LEAD = CONFIG["channels"]["lead"]
LAYER = CONFIG["channels"]["layer"]
SPLIT_BASS = CONFIG["channels"]["split_bass"]
DRUMS = CONFIG["channels"]["drums"]

DRUM_MAP = {int(k): v for k, v in CONFIG["drum_map"].items()}

PLAY_MODE_NORMAL = "normal"
PLAY_MODE_LAYER = "layer"
PLAY_MODE_SPLIT = "split"
PLAY_MODES = [PLAY_MODE_NORMAL, PLAY_MODE_LAYER, PLAY_MODE_SPLIT]


class SynthEngine:
    # Full General MIDI instrument set (128 programs, per the GM1 spec).
    # FluidR3_GM.sf2 (and any GM-compliant soundfont) implements all of these.
    # reverb_send/chorus_send are MIDI CC91/93 (0-127). Hand-tuned values are kept
    # for the original 20 instruments; the rest use the defaults in apply_preset().
    PRESETS = {
        # Piano
        "Acoustic Grand Piano": {"program": 0, "reverb_send": 40, "chorus_send": 10},
        "Bright Acoustic Piano": {"program": 1},
        "Electric Grand Piano": {"program": 2},
        "Honky-tonk Piano": {"program": 3},
        "Electric Piano 1": {"program": 4, "reverb_send": 30, "chorus_send": 20},
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
        "Drawbar Organ": {"program": 16, "reverb_send": 20, "chorus_send": 40},
        "Percussive Organ": {"program": 17},
        "Rock Organ": {"program": 18},
        "Church Organ": {"program": 19, "reverb_send": 90, "chorus_send": 20},
        "Reed Organ": {"program": 20},
        "Accordion": {"program": 21},
        "Harmonica": {"program": 22},
        "Tango Accordion": {"program": 23},
        # Guitar
        "Acoustic Guitar (nylon)": {"program": 24, "reverb_send": 30, "chorus_send": 10},
        "Acoustic Guitar (steel)": {"program": 25},
        "Electric Guitar (jazz)": {"program": 26},
        "Electric Guitar (clean)": {"program": 27},
        "Electric Guitar (muted)": {"program": 28},
        "Overdriven Guitar": {"program": 29},
        "Distortion Guitar": {"program": 30},
        "Guitar Harmonics": {"program": 31},
        # Bass
        "Acoustic Bass": {"program": 32},
        "Electric Bass (finger)": {"program": 33, "reverb_send": 5, "chorus_send": 0},
        "Electric Bass (pick)": {"program": 34},
        "Fretless Bass": {"program": 35},
        "Slap Bass 1": {"program": 36},
        "Slap Bass 2": {"program": 37},
        "Synth Bass 1": {"program": 38, "reverb_send": 5, "chorus_send": 0},
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
        "String Ensemble 1": {"program": 48, "reverb_send": 60, "chorus_send": 40},
        "String Ensemble 2": {"program": 49},
        "Synth Strings 1": {"program": 50, "reverb_send": 60, "chorus_send": 50},
        "Synth Strings 2": {"program": 51},
        "Choir Aahs": {"program": 52, "reverb_send": 70, "chorus_send": 30},
        "Voice Oohs": {"program": 53},
        "Synth Choir": {"program": 54},
        "Orchestra Hit": {"program": 55},
        # Brass
        "Trumpet": {"program": 56, "reverb_send": 40, "chorus_send": 10},
        "Trombone": {"program": 57},
        "Tuba": {"program": 58},
        "Muted Trumpet": {"program": 59},
        "French Horn": {"program": 60},
        "Brass Section": {"program": 61, "reverb_send": 40, "chorus_send": 20},
        "Synth Brass 1": {"program": 62},
        "Synth Brass 2": {"program": 63},
        # Reed
        "Soprano Sax": {"program": 64},
        "Alto Sax": {"program": 65},
        "Tenor Sax": {"program": 66, "reverb_send": 35, "chorus_send": 15},
        "Baritone Sax": {"program": 67},
        "Oboe": {"program": 68},
        "English Horn": {"program": 69},
        "Bassoon": {"program": 70},
        "Clarinet": {"program": 71},
        # Pipe
        "Piccolo": {"program": 72},
        "Flute": {"program": 73, "reverb_send": 45, "chorus_send": 20},
        "Recorder": {"program": 74},
        "Pan Flute": {"program": 75},
        "Blown Bottle": {"program": 76},
        "Shakuhachi": {"program": 77},
        "Whistle": {"program": 78},
        "Ocarina": {"program": 79},
        # Synth Lead
        "Square Lead": {"program": 80, "reverb_send": 20, "chorus_send": 30},
        "Saw Lead": {"program": 81, "reverb_send": 25, "chorus_send": 35},
        "Calliope Lead": {"program": 82},
        "Chiff Lead": {"program": 83, "reverb_send": 20, "chorus_send": 25},
        "Charang Lead": {"program": 84},
        "Voice Lead": {"program": 85},
        "Fifths Lead": {"program": 86},
        "Bass + Lead": {"program": 87},
        # Synth Pad
        "New Age Pad": {"program": 88},
        "Warm Pad": {"program": 89, "reverb_send": 90, "chorus_send": 50},
        "Polysynth Pad": {"program": 90},
        "Choir Pad": {"program": 91, "reverb_send": 90, "chorus_send": 40},
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
        "Sci-Fi FX": {"program": 103, "reverb_send": 60, "chorus_send": 70},
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
        self.xrun_count = 0

        self.fs = None
        self.sfid = None
        self.soundfonts = None
        self.current_soundfont_id = None

        self.play_mode = PLAY_MODE_NORMAL
        self.split_point = CONFIG["performance"]["split_point"]
        self.sustain_on = False
        self._tone = 64

        self.active_voices = set()       # {(channel, note)} every voice currently sounding
        self._note_channel_map = {}      # note -> [channels] struck by the last play_note() for that note

        if HAS_FLUIDSYNTH:
            try:
                # Initialize FluidSynth (no driver started, we fetch samples manually)
                self.fs = fluidsynth.Synth(samplerate=float(self.sample_rate))
                self.soundfonts = SoundfontManager(self.fs, REPO_ROOT, MAX_RESIDENT_BYTES)
                self.soundfonts.load_manifest(SOUNDFONT_MANIFEST_PATH)
                self.sfid = self.soundfonts.ensure_loaded(DEFAULT_SOUNDFONT_ID)
                if self.sfid == -1:
                    self._print_fatal_banner(f"Default soundfont '{DEFAULT_SOUNDFONT_ID}' failed to load")
                else:
                    self.current_soundfont_id = DEFAULT_SOUNDFONT_ID
                    self._init_effects()
                    self._init_performance_channels()
            except Exception as e:
                self._print_fatal_banner(f"FluidSynth init error: {e}")
        else:
            self._print_fatal_banner("pyfluidsynth is not installed (import fluidsynth failed)")

        self.apply_preset(self.current_preset)

    @staticmethod
    def _print_fatal_banner(reason):
        print("=" * 60)
        print("[FATAL] Audio engine unavailable — output will be silence.")
        print(f"[FATAL] Reason: {reason}")
        print("=" * 60)

    def _init_effects(self):
        r = CONFIG["effects"]["reverb"]
        c = CONFIG["effects"]["chorus"]
        self.fs.set_reverb(roomsize=r["roomsize"], damping=r["damping"], width=r["width"], level=r["level"])
        self.fs.set_chorus(nr=c["nr"], level=c["level"], speed=c["speed"], depth=c["depth"])

    def _init_performance_channels(self):
        perf = CONFIG["performance"]
        # GM drum kit lives on bank 128 by convention, always on the drum channel.
        self.fs.program_select(DRUMS, self.sfid, 128, 0)
        # Preload split-bass and layer channels so they sound right the instant a mode is toggled.
        self.fs.program_select(SPLIT_BASS, self.sfid, 0, perf["split_bass_program"])
        self.fs.program_select(LAYER, self.sfid, 0, perf["layer_default_program"])
        vol_cc = max(0, min(127, int(127 * (1 + perf["layer_volume_offset"]))))
        self.fs.cc(LAYER, 7, vol_cc)
        # Cheap detune: bias the layer channel's pitch wheel a few cents off center
        # rather than doing full RPN fine-tune plumbing. Trades away real pitch-bend
        # expressiveness on the layer channel for a one-line "make it chorus-y" effect.
        detune_bend = 8192 + int(perf["layer_detune_cents"] / 200.0 * 8192)
        self.fs.pitch_bend(LAYER, max(0, min(16383, detune_bend)))

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

    # ---- low-level, channel-explicit API ----
    # Always available, always takes an explicit channel. Used directly by
    # drums and (later) the sequencer/looper, and underlies play_note/release_note.

    def program_select(self, channel, sfid, bank, program):
        if self.fs:
            self.fs.program_select(channel, sfid, bank, program)

    def note_on(self, note, velocity=1.0, channel=0):
        if self.fs:
            vel_midi = max(1, min(127, int(velocity * 127)))
            self.fs.noteon(channel, note, vel_midi)
            self.active_voices.add((channel, note))

    def note_off(self, note, channel=0):
        if self.fs:
            self.fs.noteoff(channel, note)
            self.active_voices.discard((channel, note))

    def all_notes_off(self, channel=None):
        """Panic button. Uses All Sound Off (CC120) so it cuts through sustain
        and release tails instead of just queueing a polite note-off."""
        if not self.fs:
            return
        channels = range(16) if channel is None else [channel]
        for ch in channels:
            self.fs.cc(ch, 120, 0)
        if channel is None:
            self.active_voices.clear()
            self._note_channel_map.clear()
        else:
            self.active_voices = {(c, n) for (c, n) in self.active_voices if c != channel}
            self._note_channel_map = {
                n: chs for n, chs in self._note_channel_map.items() if channel not in chs
            }

    def cc(self, channel, control, value):
        if self.fs:
            self.fs.cc(channel, control, int(value))

    def pitch_bend(self, channel, value):
        if self.fs:
            self.fs.pitch_bend(channel, int(value))

    # ---- performance-surface API (mode-aware: normal/layer/split) ----
    # QWERTY, touchscreen, HDMI piano taps, and MIDI-in note events all route
    # through here so layering/splitting is transparent to every input source.
    # Tracking exactly which channels a given note hit (rather than assuming
    # channel 0) is what keeps release symmetric and avoids stuck notes.

    @property
    def active_notes(self):
        """Note numbers currently sounding on the performance channels (for piano UI highlighting)."""
        perf_channels = {LEAD, LAYER, SPLIT_BASS}
        return {n for (c, n) in self.active_voices if c in perf_channels}

    def play_note(self, note, velocity=1.0):
        if note in self._note_channel_map:
            return  # already sounding — don't double-trigger or leak a channel entry
        if self.play_mode == PLAY_MODE_LAYER:
            channels = [LEAD, LAYER]
        elif self.play_mode == PLAY_MODE_SPLIT:
            channels = [SPLIT_BASS] if note < self.split_point else [LEAD]
        else:
            channels = [LEAD]

        for ch in channels:
            self.note_on(note, velocity, channel=ch)
        self._note_channel_map[note] = channels

    def release_note(self, note):
        channels = self._note_channel_map.pop(note, None)
        if channels is None:
            return
        for ch in channels:
            self.note_off(note, channel=ch)

    def set_play_mode(self, mode):
        if mode in PLAY_MODES:
            self.play_mode = mode
            print(f"[SYNTH] Play mode: {mode}")

    def cycle_play_mode(self):
        idx = (PLAY_MODES.index(self.play_mode) + 1) % len(PLAY_MODES)
        self.set_play_mode(PLAY_MODES[idx])

    def set_sustain(self, on):
        self.sustain_on = on
        val = 127 if on else 0
        for ch in (LEAD, LAYER, SPLIT_BASS):
            self.cc(ch, 64, val)

    def toggle_sustain(self):
        self.set_sustain(not self.sustain_on)

    # ---- presets & tone ----

    def apply_preset(self, preset_name, channel=LEAD):
        if preset_name in self.PRESETS:
            data = self.PRESETS[preset_name]
            prog = data["program"]
            if self.fs and self.sfid != -1:
                self.fs.program_select(channel, self.sfid, 0, prog)
                self.fs.cc(channel, 91, data.get("reverb_send", 40))
                self.fs.cc(channel, 93, data.get("chorus_send", 10))
            if channel == LEAD:
                self.current_preset = preset_name
            print(f"[AUDIO] FluidSynth Program: {prog} ({preset_name}) on channel {channel}")

    def apply_preset_by_program(self, channel, program, bank=0):
        """Used for incoming MIDI program_change messages."""
        if self.fs and self.sfid != -1:
            self.fs.program_select(channel, self.sfid, bank, program)
        for name, data in self.PRESETS.items():
            if data.get("program") == program:
                if channel == LEAD:
                    self.current_preset = name
                return
        if channel == LEAD:
            self.current_preset = f"Program {program}"

    def apply_manifest_preset(self, sf_id, preset_name=None, channel=LEAD):
        """Load (if needed) and select a preset from a soundfont-manager-managed
        font. With no preset_name, uses the font's first favorite/preset."""
        if not self.soundfonts:
            return
        sfid = self.soundfonts.ensure_loaded(sf_id)
        if sfid == -1:
            return  # missing/broken file — soundfonts.ensure_loaded already logged why

        presets = self.soundfonts.list_presets(sf_id)
        preset = None
        if preset_name:
            preset = next((p for p in presets if p.name == preset_name), None)
        if preset is None and presets:
            preset = presets[0]
        bank, program, name = (preset.bank, preset.program, preset.name) if preset else (0, 0, sf_id)

        if self.fs:
            self.fs.program_select(channel, sfid, bank, program)
            self.fs.cc(channel, 91, 40)
            self.fs.cc(channel, 93, 10)
        if channel == LEAD:
            self.sfid = sfid
            self.current_soundfont_id = sf_id
            self.current_preset = name
        print(f"[AUDIO] Soundfont '{sf_id}' program {program} ({name}) on channel {channel}")

    def cycle_soundfont(self):
        if not self.soundfonts:
            return
        next_id = self.soundfonts.next_font(self.current_soundfont_id)
        self.apply_manifest_preset(next_id)

    @property
    def reverb_send(self):
        return self.PRESETS.get(self.current_preset, {}).get("reverb_send", 0)

    @property
    def chorus_send(self):
        return self.PRESETS.get(self.current_preset, {}).get("chorus_send", 0)

    @property
    def tone(self):
        """MIDI CC74 (brightness) value, 0-127. Not a frequency — CC74 is a relative
        offset to the soundfont's own filter envelope, so there's no honest Hz to show."""
        return self._tone

    @tone.setter
    def tone(self, value):
        self._tone = max(0, min(127, int(value)))
        self.cc(LEAD, 74, self._tone)

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
        if status:
            self.xrun_count += 1
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
