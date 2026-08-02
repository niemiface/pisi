#!/usr/bin/env python3
"""
Scans soundfonts/ for .sf2/.sf3 files and updates soundfonts/manifest.json.

This is the whole workflow for adding a new sound: drop a file in soundfonts/,
run this script. Existing entries (e.g. system fonts living outside this
directory, like FluidR3 under /usr/share/sounds/sf2/) are left untouched;
entries for files found under soundfonts/ are added or refreshed.
"""

import json
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOUNDFONT_DIR = os.path.join(REPO_ROOT, "soundfonts")
MANIFEST_PATH = os.path.join(SOUNDFONT_DIR, "manifest.json")

try:
    from sf2utils.sf2parse import Sf2File
    HAS_SF2UTILS = True
except ImportError:
    HAS_SF2UTILS = False


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {"soundfonts": []}


def id_from_filename(filename):
    base = os.path.splitext(filename)[0]
    return base.lower().replace(" ", "-").replace("_", "-")


def read_favorites(path):
    """Pull a short curated list of bank-0 presets via sf2utils, if installed."""
    if not HAS_SF2UTILS:
        return []
    try:
        with open(path, "rb") as fh:
            sf2 = Sf2File(fh)
            presets = [p for p in sf2.presets if getattr(p, "bank", 0) == 0]
            presets.sort(key=lambda p: p.preset)
            return [{"name": p.name.strip(), "bank": 0, "program": p.preset} for p in presets[:20]]
    except Exception as e:
        print(f"[SCAN] Warning: couldn't parse {path}: {e}")
        return []


def main():
    os.makedirs(SOUNDFONT_DIR, exist_ok=True)

    manifest = load_manifest()
    existing_by_id = {e["id"]: e for e in manifest.get("soundfonts", []) if e.get("id")}

    found_files = sorted(
        f for f in os.listdir(SOUNDFONT_DIR) if f.lower().endswith((".sf2", ".sf3"))
    )

    if not found_files:
        print(f"[SCAN] No .sf2/.sf3 files found in {SOUNDFONT_DIR}")

    for filename in found_files:
        sf_id = id_from_filename(filename)
        rel_path = os.path.join("soundfonts", filename)
        entry = existing_by_id.get(sf_id, {})
        entry["id"] = sf_id
        entry.setdefault("name", os.path.splitext(filename)[0])
        entry["path"] = rel_path
        entry.setdefault("type", "gm")
        entry.setdefault("lazy", True)
        entry.setdefault("license", "UNKNOWN - fill this in")
        if not entry.get("favorites"):
            favorites = read_favorites(os.path.join(SOUNDFONT_DIR, filename))
            if favorites:
                entry["favorites"] = favorites
        existing_by_id[sf_id] = entry
        print(f"[SCAN] {sf_id} -> {rel_path} ({len(entry.get('favorites', []))} favorites)")

    manifest["soundfonts"] = list(existing_by_id.values())
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"[SCAN] Wrote {MANIFEST_PATH} ({len(manifest['soundfonts'])} soundfonts total)")

    if found_files and not HAS_SF2UTILS:
        print("[SCAN] Note: sf2utils unavailable, so new entries got no auto-detected favorites.")
        print("[SCAN]       pip install sf2utils (and audioop-lts on Python 3.13+), or hand-edit")
        print("[SCAN]       the manifest's favorites list.")


if __name__ == "__main__":
    main()
