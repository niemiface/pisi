"""
Stubs out the hardware-facing modules (fluidsynth, sounddevice) so SynthEngine's
pure logic — channel routing, note tracking, mode switching — can run on any
dev machine, no Pi/audio hardware/soundfont required.
"""

import os
import sys
import types

import numpy as np
import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


class _FakeFluidSynth:
    def __init__(self, *args, **kwargs):
        pass

    def sfload(self, path):
        return 1  # pretend the soundfont loaded fine

    def sfunload(self, sfid):
        pass

    def program_select(self, *args, **kwargs):
        pass

    def set_reverb(self, *args, **kwargs):
        pass

    def set_chorus(self, *args, **kwargs):
        pass

    def cc(self, *args, **kwargs):
        pass

    def pitch_bend(self, *args, **kwargs):
        pass

    def noteon(self, *args, **kwargs):
        pass

    def noteoff(self, *args, **kwargs):
        pass

    def get_samples(self, frames):
        return np.zeros(frames * 2, dtype=np.int16)

    def delete(self):
        pass


if "fluidsynth" not in sys.modules:
    fluidsynth_stub = types.ModuleType("fluidsynth")
    fluidsynth_stub.Synth = _FakeFluidSynth
    sys.modules["fluidsynth"] = fluidsynth_stub

if "sounddevice" not in sys.modules:
    sounddevice_stub = types.ModuleType("sounddevice")
    sounddevice_stub.OutputStream = object
    sounddevice_stub.query_devices = lambda: []
    sounddevice_stub.default = types.SimpleNamespace(device=(None, None))
    sys.modules["sounddevice"] = sounddevice_stub


@pytest.fixture
def synth():
    from src.audio.synth import SynthEngine
    return SynthEngine()
