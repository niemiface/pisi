"""
Owns which .sf2/.sf3 files are resident in a running FluidSynth instance.

Reads soundfonts/manifest.json, lazy-loads fonts on first use, and evicts the
least-recently-used resident font once total resident bytes cross a
configured cap — so a Pi with a big soundfont library doesn't try to hold
gigabytes of samples in RAM at once. Missing files and load failures degrade
gracefully (log and skip) rather than crashing the audio thread.
"""

import json
import os


class Preset:
    __slots__ = ("bank", "program", "name")

    def __init__(self, bank, program, name):
        self.bank = bank
        self.program = program
        self.name = name

    def __repr__(self):
        return f"Preset(bank={self.bank}, program={self.program}, name={self.name!r})"


class SoundfontManager:
    def __init__(self, fs, repo_root, max_resident_bytes=400 * 1024 * 1024):
        self.fs = fs
        self.repo_root = repo_root
        self.max_resident_bytes = max_resident_bytes
        self.entries = {}         # sf_id -> manifest entry dict
        self.resident = {}        # sf_id -> fluidsynth sfid
        self.resident_bytes = {}  # sf_id -> file size in bytes
        self._lru = []            # sf_id, most-recently-used at the end

    def load_manifest(self, path):
        self.entries = {}
        if not os.path.exists(path):
            print(f"[SOUNDFONT] No manifest at {path}")
            return
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"[SOUNDFONT] Failed to parse manifest {path}: {e}")
            return

        for entry in data.get("soundfonts", []):
            sf_id = entry.get("id")
            if not sf_id:
                continue
            self.entries[sf_id] = entry

        for sf_id, entry in self.entries.items():
            if not entry.get("lazy", True):
                self.ensure_loaded(sf_id)

    def _resolve_path(self, entry):
        p = entry["path"]
        if not os.path.isabs(p):
            p = os.path.join(self.repo_root, p)
        return p

    def ensure_loaded(self, sf_id):
        """Returns the FluidSynth sfid for sf_id, loading it on demand. Returns
        -1 if the id is unknown, the file is missing, or FluidSynth rejects it."""
        if sf_id in self.resident:
            self._touch(sf_id)
            return self.resident[sf_id]

        entry = self.entries.get(sf_id)
        if entry is None:
            print(f"[SOUNDFONT] Unknown id '{sf_id}', skipping")
            return -1

        path = self._resolve_path(entry)
        if not os.path.exists(path):
            print(f"[SOUNDFONT] WARNING: '{sf_id}' missing on disk at {path}, skipping")
            return -1

        if not self.fs:
            return -1

        sfid = self.fs.sfload(path)
        if sfid == -1:
            print(f"[SOUNDFONT] FluidSynth failed to load '{sf_id}' from {path}")
            return -1

        size = os.path.getsize(path)
        self.resident[sf_id] = sfid
        self.resident_bytes[sf_id] = size
        self._touch(sf_id)
        print(f"[SOUNDFONT] Loaded '{sf_id}' ({entry.get('name', sf_id)}), {size / 1e6:.1f} MB")
        self._evict_if_needed(protected=sf_id)
        return sfid

    def _touch(self, sf_id):
        if sf_id in self._lru:
            self._lru.remove(sf_id)
        self._lru.append(sf_id)

    def _evict_if_needed(self, protected=None):
        total = sum(self.resident_bytes.values())
        i = 0
        while total > self.max_resident_bytes and i < len(self._lru):
            candidate = self._lru[i]
            if candidate == protected:
                i += 1
                continue
            total -= self.resident_bytes.get(candidate, 0)
            self.unload(candidate)
            i = 0  # unload() mutated _lru — restart the scan

    def unload(self, sf_id):
        sfid = self.resident.pop(sf_id, None)
        self.resident_bytes.pop(sf_id, None)
        if sf_id in self._lru:
            self._lru.remove(sf_id)
        if sfid is not None and self.fs:
            self.fs.sfunload(sfid)
            print(f"[SOUNDFONT] Unloaded '{sf_id}'")

    def list_presets(self, sf_id):
        """Prefers the manifest's curated 'favorites' list; falls back to
        sf2utils header parsing (if installed) when there are none."""
        entry = self.entries.get(sf_id, {})
        favorites = entry.get("favorites")
        if favorites:
            return [Preset(f.get("bank", 0), f["program"], f["name"]) for f in favorites]

        if not entry:
            return []

        path = self._resolve_path(entry)
        if not os.path.exists(path):
            return []

        try:
            from sf2utils.sf2parse import Sf2File
        except ImportError:
            print("[SOUNDFONT] sf2utils unavailable (not installed, or 'audioop' missing on Python 3.13+ "
                  "without audioop-lts); can't enumerate presets without it")
            return []

        try:
            with open(path, "rb") as fh:
                sf2 = Sf2File(fh)
                presets = [Preset(p.bank, p.preset, p.name) for p in sf2.presets]
                presets.sort(key=lambda pr: (pr.bank, pr.program))
                return presets
        except Exception as e:
            print(f"[SOUNDFONT] Failed to parse {path}: {e}")
            return []

    def next_font(self, current_id):
        """Cycle to the next soundfont id in manifest order, for button/key cycling."""
        ids = list(self.entries.keys())
        if not ids:
            return current_id
        if current_id not in ids:
            return ids[0]
        idx = (ids.index(current_id) + 1) % len(ids)
        return ids[idx]

    @property
    def total_resident_bytes(self):
        return sum(self.resident_bytes.values())
