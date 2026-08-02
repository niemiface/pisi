#!/usr/bin/env python3
"""
Real-time Audio Analyzer & FFT Spectrum Processor
Computes frequency spectrum bands, peak hold, RMS volume, and beat detection.
"""

import numpy as np

class AudioAnalyzer:
    def __init__(self, num_bands=16, sample_rate=44100, smoothing=0.7):
        self.num_bands = num_bands
        self.sample_rate = sample_rate
        self.smoothing = smoothing
        
        self.bands = np.zeros(num_bands, dtype=np.float32)
        self.peaks = np.zeros(num_bands, dtype=np.float32)
        self.rms = 0.0
        self.beat_detected = False
        
        # Precompute band frequency boundaries (logarithmically spaced from 40 Hz to 12000 Hz)
        self.freq_boundaries = np.logspace(
            np.log10(40.0), np.log10(12000.0), num_bands + 1
        )

    def process(self, audio_buffer):
        """Processes a 1D float32 numpy audio buffer and updates FFT band levels."""
        if audio_buffer is None or len(audio_buffer) == 0:
            return self.bands

        buffer_len = len(audio_buffer)
        
        # 1. Compute RMS Volume
        self.rms = np.sqrt(np.mean(audio_buffer ** 2)) if len(audio_buffer) > 0 else 0.0
        
        # 2. Windowing & FFT
        windowed = audio_buffer * np.hanning(buffer_len)
        fft_vals = np.abs(np.fft.rfft(windowed))
        fft_freqs = np.fft.rfftfreq(buffer_len, 1.0 / self.sample_rate)
        
        # 3. Bin FFT into frequency bands
        raw_bands = np.zeros(self.num_bands, dtype=np.float32)
        for i in range(self.num_bands):
            f_low = self.freq_boundaries[i]
            f_high = self.freq_boundaries[i + 1]
            idx = np.where((fft_freqs >= f_low) & (fft_freqs < f_high))[0]
            if len(idx) > 0:
                raw_bands[i] = np.mean(fft_vals[idx])
            else:
                raw_bands[i] = 0.0

        # Scale and log-compress for visually pleasing dynamic range
        raw_bands = np.log1p(raw_bands * 10.0) / 3.0
        raw_bands = np.clip(raw_bands, 0.0, 1.0)
        
        # 4. Temporal Smoothing & Peak Decay
        self.bands = self.smoothing * self.bands + (1.0 - self.smoothing) * raw_bands
        self.peaks = np.maximum(self.peaks * 0.92, self.bands)
        
        # 5. Simple Bass Beat Detection
        bass_energy = np.mean(self.bands[:3])
        if bass_energy > 0.6 and not self.beat_detected:
            self.beat_detected = True
        else:
            self.beat_detected = False

        return self.bands
