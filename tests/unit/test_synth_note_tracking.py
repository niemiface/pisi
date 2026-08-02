"""
Covers the multi-channel note-routing logic added in Phase 1. This is the
single most likely place to introduce stuck notes (per the expansion plan's
own warning), so it gets real tests instead of only manual Pi verification.
"""

import pytest

from src.audio.synth import (
    SynthEngine, LEAD, LAYER, SPLIT_BASS, DRUMS,
    PLAY_MODE_NORMAL, PLAY_MODE_LAYER, PLAY_MODE_SPLIT,
)


@pytest.fixture
def synth():
    return SynthEngine()


def test_normal_mode_single_channel(synth):
    synth.play_note(60)
    assert (LEAD, 60) in synth.active_voices
    assert synth.active_notes == {60}
    synth.release_note(60)
    assert synth.active_voices == set()
    assert synth.active_notes == set()


def test_layer_mode_dual_channel_and_symmetric_release(synth):
    synth.set_play_mode(PLAY_MODE_LAYER)
    synth.play_note(60)
    assert (LEAD, 60) in synth.active_voices
    assert (LAYER, 60) in synth.active_voices
    synth.release_note(60)
    assert (LEAD, 60) not in synth.active_voices
    assert (LAYER, 60) not in synth.active_voices


def test_split_mode_routes_by_split_point(synth):
    synth.set_play_mode(PLAY_MODE_SPLIT)
    low_note = synth.split_point - 1
    high_note = synth.split_point
    synth.play_note(low_note)
    synth.play_note(high_note)
    assert (SPLIT_BASS, low_note) in synth.active_voices
    assert (LEAD, high_note) in synth.active_voices
    synth.release_note(low_note)
    synth.release_note(high_note)
    assert synth.active_voices == set()


def test_mode_switch_mid_note_releases_original_channels_only(synth):
    """The core stuck-note pitfall: a note struck in one mode must release from
    the channels it was ACTUALLY struck on, even if play_mode changes before release."""
    synth.play_note(60)  # struck in NORMAL -> only LEAD
    synth.set_play_mode(PLAY_MODE_LAYER)
    synth.release_note(60)
    assert (LEAD, 60) not in synth.active_voices
    assert (LAYER, 60) not in synth.active_voices
    assert synth._note_channel_map == {}


def test_duplicate_press_does_not_leak_channel_entries(synth):
    synth.play_note(60)
    synth.play_note(60)  # duplicate press while still held
    assert synth._note_channel_map[60] == [LEAD]
    synth.release_note(60)
    assert synth.active_voices == set()


def test_all_notes_off_panic_clears_everything(synth):
    synth.set_play_mode(PLAY_MODE_LAYER)
    synth.play_note(60)
    synth.play_note(64)
    synth.all_notes_off()
    assert synth.active_voices == set()
    assert synth._note_channel_map == {}


def test_drum_notes_do_not_appear_in_performance_active_notes(synth):
    """Drums are struck via the low-level channel-explicit API, not play_note —
    they must not light up the performance piano UI."""
    synth.note_on(38, channel=DRUMS)
    assert synth.active_notes == set()
    synth.note_off(38, channel=DRUMS)
    assert synth.active_voices == set()


def test_sustain_toggle(synth):
    assert synth.sustain_on is False
    synth.toggle_sustain()
    assert synth.sustain_on is True
    synth.toggle_sustain()
    assert synth.sustain_on is False


def test_cycle_play_mode_wraps(synth):
    synth.set_play_mode(PLAY_MODE_NORMAL)
    synth.cycle_play_mode()
    assert synth.play_mode == PLAY_MODE_LAYER
    synth.cycle_play_mode()
    assert synth.play_mode == PLAY_MODE_SPLIT
    synth.cycle_play_mode()
    assert synth.play_mode == PLAY_MODE_NORMAL


def test_tone_clamped_0_127(synth):
    synth.tone = 200
    assert synth.tone == 127
    synth.tone = -10
    assert synth.tone == 0


def test_apply_preset_by_program(synth):
    synth.apply_preset_by_program(LEAD, 0)  # program 0 = Grand Piano
    assert synth.current_preset == "Grand Piano"
    synth.apply_preset_by_program(LEAD, 127)  # not in PRESETS table
    assert synth.current_preset == "Program 127"
