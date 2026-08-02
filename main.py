#!/usr/bin/env python3
"""
Raspberry Pi 4 Pirate Audio Synth & Oscilloscope Studio
Architecture: Pygame runs on MAIN thread (SDL requirement).
             ST7789 SPI rendering runs on background thread.
             Audio runs on sounddevice's own thread.
"""

import sys
import os
import time
import signal
import threading
import traceback
import numpy as np

# Set display environment BEFORE any pygame import
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"

from src.config import CONFIG
from src.audio.synth import SynthEngine, HAS_FLUIDSYNTH, SOUNDFONT_PATH
from src.audio.analyzer import AudioAnalyzer
from src.display.renderer import DisplayRenderer
from src.display.hdmi_renderer import HDMIRenderer
from src.controls.hardware import HardwareController

try:
    import st7789 as ST7789
except ImportError:
    try:
        import ST7789
    except ImportError:
        ST7789 = None

ROTATION = CONFIG["display"]["st7789"]["rotation"]
HDMI_WIDTH = CONFIG["display"]["hdmi"]["width"]
HDMI_HEIGHT = CONFIG["display"]["hdmi"]["height"]


def preflight_check():
    """Fail fast with a clear message instead of limping along silently broken."""
    problems = []
    if not HAS_FLUIDSYNTH:
        problems.append("pyfluidsynth is not importable (pip install pyfluidsynth)")
    elif not os.path.exists(SOUNDFONT_PATH):
        problems.append(f"No soundfont found at {SOUNDFONT_PATH}")
    if not os.path.exists("/dev/spidev0.0") and not os.path.exists("/dev/spidev0.1"):
        problems.append("No SPI device found at /dev/spidev0.* (ST7789 needs SPI enabled)")

    if problems:
        print("=" * 60)
        print("[PREFLIGHT] Problems detected before startup:")
        for p in problems:
            print(f"[PREFLIGHT]   - {p}")
        print("=" * 60)
    return problems

def init_st7789():
    if ST7789 is None:
        print("[INFO] ST7789 module not found.")
        return None
    for cs in [1, 0]:
        try:
            disp = ST7789.ST7789(port=0, cs=cs, dc=9, backlight=13,
                                 rotation=ROTATION, spi_speed_hz=52_000_000)
            disp.begin()
            print(f"[INFO] ST7789 LCD initialized on CS={cs} (Rotation={ROTATION}°)")
            return disp
        except Exception:
            continue
    print("[WARNING] ST7789 LCD not available.")
    return None


def main():
    print("=========================================================")
    print("  Pi 4 Oscilloscope Studio & Touchscreen Synth")
    print("=========================================================")

    preflight_check()

    # 1. Init ST7789 small LCD
    disp_st7789 = init_st7789()

    # 2. Init Audio Synth Engine
    print("[INIT] Starting Synth Engine...")
    synth = SynthEngine()
    try:
        synth.start()
        print("[INIT] Audio stream started.")
    except Exception as e:
        print(f"[ERROR] Audio init failed: {e}")

    # 3. Init HDMI Oscilloscope (MUST be on main thread for Pygame)
    print("[INIT] Initializing HDMI Oscilloscope Studio...")
    hdmi = None
    try:
        hdmi = HDMIRenderer(synth, width=HDMI_WIDTH, height=HDMI_HEIGHT)
    except Exception as e:
        print(f"[HDMI] Skipped: {e}")

    # 4. Init analyzers and controllers
    analyzer = AudioAnalyzer(num_bands=16)
    renderer_st7789 = DisplayRenderer()
    hw = HardwareController(synth, renderer_st7789, hdmi_renderer=hdmi)

    running = True
    def on_signal(sig, frame):
        nonlocal running
        print("\n[SHUTDOWN] Exiting...")
        running = False
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    print("\n[READY] Running.")
    print("  Keys [A,W,S,E,D,F,T,G,Y,H,U,J,K] -> Play Notes")
    print("  Keys [Z,X,C,V,B,N,M] -> Drums   [Space] -> Sustain (hold)")
    print("  [1] Mode  [2] Patch  [3] Note  [4] Tone  [5] Play Mode (Normal/Layer/Split)")
    print("  HW buttons: A/B long-press -> Sustain / Play Mode")
    print("  Ctrl+C to stop.\n")

    # Welcome chime
    def chime():
        time.sleep(0.3)
        for n in [60, 64, 67, 72]:
            synth.note_on(n)
            time.sleep(0.12)
            synth.note_off(n)
    threading.Thread(target=chime, daemon=True).start()

    # Background thread: ST7789 SPI LCD rendering (thread-safe PIL + SPI)
    def st7789_loop():
        t0 = time.time()
        frames = 0
        while running:
            try:
                elapsed = time.time() - t0
                fps = frames / max(elapsed, 0.001)
                audio_buf = synth.last_audio_buffer
                analyzer.process(audio_buf)
                img = renderer_st7789.render(analyzer, synth, fps=fps)
                if disp_st7789:
                    disp_st7789.display(img)
                frames += 1
                time.sleep(0.04)  # ~25 FPS for SPI LCD
            except Exception as e:
                print(f"[ST7789 ERROR] {e}")
                time.sleep(0.1)

    st7789_thread = threading.Thread(target=st7789_loop, daemon=True)
    st7789_thread.start()

    # MAIN THREAD: Pygame HDMI rendering (SDL requires main thread)
    try:
        while running:
            if hdmi and hdmi.screen:
                try:
                    hdmi.render(analyzer, synth)
                except Exception as e:
                    print(f"[HDMI ERROR] {e}")
                    traceback.print_exc()
                    hdmi.screen = None  # disable after error
                time.sleep(0.016)  # ~60 FPS
            else:
                time.sleep(0.1)
    finally:
        print("[CLEANUP] Stopping audio engine...")
        synth.stop()
        print("[CLEANUP] Done.")


if __name__ == "__main__":
    main()
