"""
Covers SoundfontManager's pure logic: manifest parsing, lazy loading,
LRU eviction under a byte cap, and graceful handling of missing files —
the pitfalls Phase 2 of the expansion plan calls out explicitly.
"""

import json
import os

import pytest

from src.audio.soundfont_manager import SoundfontManager, Preset


class _FakeFluidSynth:
    """Records sfload/sfunload calls; assigns an incrementing fake sfid per file."""

    def __init__(self):
        self.loaded_paths = []
        self.unloaded_sfids = []
        self._next_sfid = 1

    def sfload(self, path):
        if "BROKEN" in path:
            return -1
        sfid = self._next_sfid
        self._next_sfid += 1
        self.loaded_paths.append(path)
        return sfid

    def sfunload(self, sfid):
        self.unloaded_sfids.append(sfid)


def _write_manifest(tmp_path, entries):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"soundfonts": entries}))
    return str(manifest_path)


def _make_font_file(tmp_path, name, size_bytes):
    p = tmp_path / name
    p.write_bytes(b"\0" * size_bytes)
    return str(p)


def test_lazy_font_not_loaded_until_requested(tmp_path):
    font_path = _make_font_file(tmp_path, "a.sf2", 1024)
    manifest_path = _write_manifest(tmp_path, [
        {"id": "a", "name": "A", "path": font_path, "lazy": True},
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    assert "a" not in mgr.resident
    assert mgr.ensure_loaded("a") == 1
    assert "a" in mgr.resident


def test_non_lazy_font_loaded_eagerly_by_manifest(tmp_path):
    font_path = _make_font_file(tmp_path, "a.sf2", 1024)
    manifest_path = _write_manifest(tmp_path, [
        {"id": "a", "name": "A", "path": font_path, "lazy": False},
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    assert "a" in mgr.resident


def test_unknown_id_degrades_gracefully(tmp_path):
    manifest_path = _write_manifest(tmp_path, [])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    assert mgr.ensure_loaded("nonexistent") == -1


def test_missing_file_on_disk_degrades_gracefully(tmp_path):
    manifest_path = _write_manifest(tmp_path, [
        {"id": "ghost", "name": "Ghost", "path": str(tmp_path / "does-not-exist.sf2"), "lazy": True},
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    assert mgr.ensure_loaded("ghost") == -1
    assert "ghost" not in mgr.resident


def test_sfload_failure_returns_minus_one_and_does_not_register(tmp_path):
    font_path = _make_font_file(tmp_path, "BROKEN.sf2", 1024)
    manifest_path = _write_manifest(tmp_path, [
        {"id": "broken", "name": "Broken", "path": font_path, "lazy": True},
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    assert mgr.ensure_loaded("broken") == -1
    assert "broken" not in mgr.resident


def test_relative_path_resolved_against_repo_root(tmp_path):
    (tmp_path / "soundfonts").mkdir()
    font_path = tmp_path / "soundfonts" / "rel.sf2"
    font_path.write_bytes(b"\0" * 512)
    manifest_path = _write_manifest(tmp_path, [
        {"id": "rel", "name": "Rel", "path": "soundfonts/rel.sf2", "lazy": True},
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    assert mgr.ensure_loaded("rel") != -1


def test_lru_eviction_when_over_byte_cap(tmp_path):
    size = 100
    paths = {name: _make_font_file(tmp_path, f"{name}.sf2", size) for name in "abc"}
    manifest_path = _write_manifest(tmp_path, [
        {"id": n, "name": n, "path": p, "lazy": True} for n, p in paths.items()
    ])
    fs = _FakeFluidSynth()
    # Cap fits two fonts but not three.
    mgr = SoundfontManager(fs, str(tmp_path), max_resident_bytes=size * 2)
    mgr.load_manifest(manifest_path)

    mgr.ensure_loaded("a")
    mgr.ensure_loaded("b")
    assert set(mgr.resident) == {"a", "b"}

    mgr.ensure_loaded("c")  # should evict LRU ('a') to stay under the cap
    assert "a" not in mgr.resident
    assert set(mgr.resident) == {"b", "c"}
    assert mgr.total_resident_bytes <= size * 2


def test_touching_a_font_protects_it_from_eviction(tmp_path):
    size = 100
    paths = {name: _make_font_file(tmp_path, f"{name}.sf2", size) for name in "abc"}
    manifest_path = _write_manifest(tmp_path, [
        {"id": n, "name": n, "path": p, "lazy": True} for n, p in paths.items()
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path), max_resident_bytes=size * 2)
    mgr.load_manifest(manifest_path)

    mgr.ensure_loaded("a")
    mgr.ensure_loaded("b")
    mgr.ensure_loaded("a")  # re-touch 'a' -> 'b' is now the LRU one
    mgr.ensure_loaded("c")
    assert "b" not in mgr.resident
    assert set(mgr.resident) == {"a", "c"}


def test_next_font_cycles_and_wraps(tmp_path):
    manifest_path = _write_manifest(tmp_path, [
        {"id": "a", "name": "A", "path": "a.sf2", "lazy": True},
        {"id": "b", "name": "B", "path": "b.sf2", "lazy": True},
        {"id": "c", "name": "C", "path": "c.sf2", "lazy": True},
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    assert mgr.next_font("a") == "b"
    assert mgr.next_font("b") == "c"
    assert mgr.next_font("c") == "a"
    assert mgr.next_font("unknown-id") == "a"


def test_list_presets_prefers_manifest_favorites(tmp_path):
    manifest_path = _write_manifest(tmp_path, [
        {
            "id": "a", "name": "A", "path": "a.sf2", "lazy": True,
            "favorites": [{"name": "Grand Piano", "bank": 0, "program": 0}],
        },
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    presets = mgr.list_presets("a")
    assert len(presets) == 1
    assert isinstance(presets[0], Preset)
    assert presets[0].name == "Grand Piano"


def test_list_presets_empty_without_favorites_or_sf2utils(tmp_path):
    font_path = _make_font_file(tmp_path, "noname.sf2", 64)
    manifest_path = _write_manifest(tmp_path, [
        {"id": "a", "name": "A", "path": font_path, "lazy": True},
    ])
    fs = _FakeFluidSynth()
    mgr = SoundfontManager(fs, str(tmp_path))
    mgr.load_manifest(manifest_path)
    # noname.sf2 isn't a real soundfont, so sf2utils (if present) will fail to
    # parse it too — either way this must degrade to an empty list, not raise.
    assert mgr.list_presets("a") == []
