# Raspberry Pi 4 Synth & Audio-Reactive Studio (Dual-Display Edition)

A portable Raspberry Pi 4 synthesizer engine and real-time studio visualizer driving dual displays:
1. **Pimoroni Pirate Audio DAC** (ST7789 240x240 LCD, I2S DAC sound card, 4 tactile buttons).
2. **HDMI Main Screen Display** (Full-Screen 32-band Spectrum Analyzer, Oscilloscope, Interactive Piano Keyboard).

---

## 📺 Dual-Display System Architecture

```
                               ┌───────────────────────────────────────────────┐
                               │             RASPBERRY PI 4 WORKSPACE          │
                               └───────────────────────┬───────────────────────┘
                                                       │
                           ┌───────────────────────────┴───────────────────────────┐
                           │                                                       │
                           ▼                                                       ▼
            ┌─────────────────────────────┐                         ┌─────────────────────────────┐
            │   PIMORONI ST7789 LCD (SPI) │                         │   HDMI MAIN SCREEN DISPLAY  │
            │          (240x240)          │                         │     (1280x720 / 1920x1080)  │
            ├─────────────────────────────┤                         ├─────────────────────────────┤
            │  • Compact 16-Band Spectrum │                         │  • Full 32-Band Neon FFT    │
            │  • Real-Time Oscilloscope   │                         │  • High-Res Oscilloscope    │
            │  • Synth Parameters Badge   │                         │  • Interactive Piano Keys   │
            └─────────────────────────────┘                         └─────────────────────────────┘
```

---

## 📦 Installed Software Stack Overview

| Software Component | File Location | Description & Functionality |
|---|---|---|
| **Software Synthesizer Engine** | [synth.py](file:///Users/iniemi/Desktop/pisi/src/audio/synth.py) | **FluidSynth (pyFluidSynth)** engine utilizing General MIDI SoundFonts (`.sf2`) for realistic instrument samples (Grand Piano, Guitars, Synths, Brass), polyphony, and perfectly smooth C-optimized audio buffers bridged to the visualizers. |
| **Real-Time FFT Audio Analyzer** | [analyzer.py](file:///Users/iniemi/Desktop/pisi/src/audio/analyzer.py) | Computes Fast Fourier Transform (FFT) across 16-32 logarithmic frequency bands with peak decay, RMS volume meter, and bass beat impulse detector based on the raw FluidSynth audio stream. |
| **HDMI Main Screen Renderer** | [hdmi_renderer.py](file:///Users/iniemi/Desktop/pisi/src/display/hdmi_renderer.py) | High-resolution Pygame graphics engine driving full-screen oscilloscope and interactive touch-capable piano keyboard on the main HDMI display. |
| **ST7789 LCD Display Renderer** | [renderer.py](file:///Users/iniemi/Desktop/pisi/src/display/renderer.py) | High-framerate PIL graphics renderer providing 3 screen modes (Spectrum, Scope, Dash) for the Pimoroni Pirate Audio LCD screen. |
| **Hardware & Touch Controller** | [hardware.py](file:///Users/iniemi/Desktop/pisi/src/controls/hardware.py) | Thread-safe `evdev` event handler for Pirate Audio HAT buttons (A, B, X, Y), raw USB QWERTY Keyboards, and **USB Touchscreens** with auto-reconnection. |
| **Main Application Launcher** | [main.py](file:///Users/iniemi/Desktop/pisi/main.py) | Coordinates dual-display rendering, audio streaming, FFT processing, and hardware inputs. |

---

## ⌨️ How to Plug In & Use Keyboards

### USB QWERTY Keyboard
Plug any USB computer keyboard into one of the Pi's USB ports. Play notes directly using the QWERTY keys:

| Key | Piano Note | Note Name |
|---|---|---|
| **A** | Note 60 | C4 (Middle C) |
| **W** | Note 61 | C#4 |
| **S** | Note 62 | D4 |
| **E** | Note 63 | D#4 |
| **D** | Note 64 | E4 |
| **F** | Note 65 | F4 |
| **T** | Note 66 | F#4 |
| **G** | Note 67 | G4 |
| **Y** | Note 68 | G#4 |
| **H** | Note 69 | A4 |
| **U** | Note 70 | A#4 |
| **J** | Note 71 | B4 |
| **K** | Note 72 | C5 |

### USB MIDI Keyboard
Plug your USB MIDI Keyboard into any USB port on the Pi. Launch `main.py` — it auto-detects hot-plugged MIDI devices with velocity sensitivity!

---

## 🚀 Quick Launch Guide

On your Raspberry Pi over SSH or terminal:

```bash
# 1. Install FluidSynth Audio Dependencies
sudo apt-get update
sudo apt-get install -y fluidsynth fluid-soundfont-gm

# 2. Setup Python Environment
cd ~/pisi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Grant Input Permissions (for Touch/Keyboard) and Run
sudo chmod 666 /dev/input/event*
DISPLAY=:0 python3 main.py
```

### ⚡ Hybrid USB Boot Mode (For Fast SSDs)
If you are using a high-speed external SSD (like the SanDisk Extreme) and experiencing `Firmware not found` or `Timeout: 25 seconds` errors from the Pi 4 bootloader, you can use **Hybrid Boot**:
1. Clone your SD Card to the SSD (e.g., using `rpi-clone`).
2. Boot from the SD card.
3. Edit `/boot/firmware/cmdline.txt` on the SD card to point to the SSD's PARTUUID (`root=PARTUUID=xxxxxxxx-02`).
4. (Optional) Add USB storage quirks for incompatible drives like SanDisk Extreme: `usb-storage.quirks=0781:55ae:u`.
5. Reboot, and the Pi will use the SD card to load the kernel and immediately hand off the OS to the high-speed SSD!
