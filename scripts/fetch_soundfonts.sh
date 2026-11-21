#!/usr/bin/env bash
# Downloads a curated set of redistributable soundfonts into soundfonts/.
# Never commit the .sf2/.sf3 files themselves — soundfonts/.gitignore already
# excludes them. After downloading, run scripts/scan_soundfonts.py to add
# whatever you fetched to the manifest.
set -e

SOUNDFONT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/soundfonts"
mkdir -p "$SOUNDFONT_DIR"
cd "$SOUNDFONT_DIR"

fetch() {
    local name="$1" url="$2" out="$3"
    if [ -f "$out" ]; then
        echo "Already have $out, skipping."
        return
    fi
    echo "Fetching $name -> $out ..."
    curl -L --fail --progress-bar -o "$out.part" "$url"
    mv "$out.part" "$out"
}

echo "Available soundfonts:"
echo "  1) GeneralUser GS      (~31 MB)  - best default, permissive license"
echo "  2) MuseScore General   (~36 MB)  - .sf3, decent GM, Ogg-compressed"
echo "  3) Arachno GM          (~148 MB) - richer leads/brass"
echo "  4) SGM-v2.01           (~236 MB) - strong pianos/strings"
echo
read -p "Which to fetch? [1-4, space-separated, or 'all']: " CHOICE

want() {
    [ "$CHOICE" = "all" ] && return 0
    case " $CHOICE " in *" $1 "*) return 0 ;; esac
    return 1
}

want 1 && fetch "GeneralUser GS" \
    "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2" \
    "GeneralUser-GS.sf2"

want 2 && fetch "MuseScore General" \
    "https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf3" \
    "MuseScore_General.sf3"

want 3 && fetch "Arachno GM" \
    "https://archive.org/download/free-soundfonts-sf2-2019-04/Arachno%20SoundFont%20-%20Version%201.0.sf2" \
    "Arachno-SoundFont-1.0.sf2"

want 4 && fetch "SGM-v2.01" \
    "https://archive.org/download/SGM-V2.01/SGM-V2.01.sf2" \
    "SGM-V2.01.sf2"

echo
echo "Done. Run scripts/scan_soundfonts.py to add these to soundfonts/manifest.json."
