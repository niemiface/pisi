"""
Covers SynthEngine's integration with SoundfontManager: apply_manifest_preset
and cycle_soundfont. Builds an isolated manifest/SoundfontManager pointed at
temp files rather than the real soundfonts/manifest.json, since that one
references absolute Pi paths (e.g. /usr/share/sounds/sf2/...) that won't
exist on a dev machine — keeping this hermetic either way.
"""

import json

from src.audio.synth import LEAD
from src.audio.soundfont_manager import SoundfontManager


def _make_font(tmp_path, name):
    p = tmp_path / name
    p.write_bytes(b"\0" * 256)
    return str(p)


def _swap_in_isolated_manifest(synth, tmp_path, entries):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"soundfonts": entries}))
    mgr = SoundfontManager(synth.fs, str(tmp_path), max_resident_bytes=10 * 1024 * 1024)
    mgr.load_manifest(str(manifest_path))
    synth.soundfonts = mgr
    return mgr


def test_apply_manifest_preset_updates_current_preset(synth, tmp_path):
    font_path = _make_font(tmp_path, "a.sf2")
    _swap_in_isolated_manifest(synth, tmp_path, [
        {
            "id": "font-a", "name": "Font A", "path": font_path, "lazy": True,
            "favorites": [{"name": "Custom Lead", "bank": 0, "program": 81}],
        },
    ])
    synth.apply_manifest_preset("font-a")
    assert synth.current_soundfont_id == "font-a"
    assert synth.current_preset == "Custom Lead"


def test_cycle_soundfont_advances_through_manifest_order(synth, tmp_path):
    paths = {n: _make_font(tmp_path, f"{n}.sf2") for n in ("font-a", "font-b", "font-c")}
    _swap_in_isolated_manifest(synth, tmp_path, [
        {"id": n, "name": n, "path": p, "lazy": True, "favorites": [{"name": n, "bank": 0, "program": 0}]}
        for n, p in paths.items()
    ])
    synth.apply_manifest_preset("font-a")
    assert synth.current_soundfont_id == "font-a"

    synth.cycle_soundfont()
    assert synth.current_soundfont_id == "font-b"

    synth.cycle_soundfont()
    assert synth.current_soundfont_id == "font-c"

    synth.cycle_soundfont()  # wraps back around
    assert synth.current_soundfont_id == "font-a"


def test_apply_manifest_preset_with_missing_font_does_not_change_state(synth, tmp_path):
    _swap_in_isolated_manifest(synth, tmp_path, [
        {"id": "ghost", "name": "Ghost", "path": str(tmp_path / "missing.sf2"), "lazy": True},
    ])
    before_id = synth.current_soundfont_id
    before_preset = synth.current_preset
    synth.apply_manifest_preset("ghost")
    assert synth.current_soundfont_id == before_id
    assert synth.current_preset == before_preset


def test_apply_manifest_preset_only_updates_current_preset_on_lead_channel(synth, tmp_path):
    font_path = _make_font(tmp_path, "a.sf2")
    _swap_in_isolated_manifest(synth, tmp_path, [
        {
            "id": "font-a", "name": "Font A", "path": font_path, "lazy": True,
            "favorites": [{"name": "Custom Lead", "bank": 0, "program": 81}],
        },
    ])
    before_preset = synth.current_preset
    synth.apply_manifest_preset("font-a", channel=5)
    assert synth.current_preset == before_preset  # unaffected — not the LEAD channel
