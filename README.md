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
| **Software Synthesizer Engine** | [synth.py](file:///Users/iniemi/Desktop/pisi/src/audio/synth.py) | 4-voice polyphonic synth with 5 waveforms (Sine, Square, Sawtooth, Triangle, Noise), ADSR envelopes, low-pass filter, and real-time sounddevice audio streaming. |
| **Real-Time FFT Audio Analyzer** | [analyzer.py](file:///Users/iniemi/Desktop/pisi/src/audio/analyzer.py) | Computes Fast Fourier Transform (FFT) across 32 logarithmic frequency bands with peak decay, RMS volume meter, and bass beat impulse detector. |
| **HDMI Main Screen Renderer** | [hdmi_renderer.py](file:///Users/iniemi/Desktop/pisi/src/display/hdmi_renderer.py) | High-resolution Pygame graphics engine driving full-screen visualizer and interactive piano keyboard on the main HDMI display. |
| **ST7789 LCD Display Renderer** | [renderer.py](file:///Users/iniemi/Desktop/pisi/src/display/renderer.py) | High-framerate PIL graphics renderer providing 3 screen modes for the Pimoroni Pirate Audio LCD screen. |
| **Hardware & USB Controller** | [hardware.py](file:///Users/iniemi/Desktop/pisi/src/controls/hardware.py) | Event handler for Pirate Audio HAT buttons (A, B, X, Y), raw USB QWERTY Keyboards (`evdev`), and **USB MIDI Keyboards**. |
| **Main Application Launcher** | [main.py](file:///Users/iniemi/Desktop/pisi/main.py) | Coordinates dual-display rendering (45+ FPS), audio streaming, FFT processing, and keyboard inputs. |

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
cd ~/pisi
source venv/bin/activate
pip install pygame
sudo ~/pisi/venv/bin/python3 main.py
```
