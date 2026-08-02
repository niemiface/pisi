#!/usr/bin/env python3
"""
Audio Hardware Verification Script for Pirate Audio DAC / HiFiBerry
Generates test tones (Sine wave, Chord sweep) to verify sound output.
"""

import time
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100
DURATION = 3.0  # seconds per test tone

def generate_sine_wave(freq, duration, sample_rate=SAMPLE_RATE, amplitude=0.3):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Generate stereo sine wave
    wave = amplitude * np.sin(2 * np.pi * freq * t)
    stereo_wave = np.column_stack((wave, wave)).astype(np.float32)
    return stereo_wave

def generate_chord(freqs, duration, sample_rate=SAMPLE_RATE, amplitude=0.2):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.zeros_like(t)
    for f in freqs:
        wave += np.sin(2 * np.pi * f * t)
    wave = amplitude * (wave / len(freqs))
    stereo_wave = np.column_stack((wave, wave)).astype(np.float32)
    return stereo_wave

def main():
    print("=== Sound Device Audio Test ===")
    print("Querying available audio devices:")
    print(sd.query_devices())
    default_out = sd.default.device[1]
    print(f"\nUsing default output device ID: {default_out}")
    
    print("\n1. Playing 440Hz Sine Wave (A4) for 3 seconds...")
    tone1 = generate_sine_wave(440.0, DURATION)
    sd.play(tone1, SAMPLE_RATE)
    sd.wait()
    
    time.sleep(0.5)
    
    print("2. Playing A-Major Triad Chord (440Hz, 554.37Hz, 659.25Hz) for 3 seconds...")
    chord = generate_chord([440.0, 554.37, 659.25], DURATION)
    sd.play(chord, SAMPLE_RATE)
    sd.wait()
    
    print("\nAudio test completed successfully!")

if __name__ == "__main__":
    main()
