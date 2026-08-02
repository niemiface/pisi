#!/usr/bin/env python3
"""
ST7789 Display Renderer for Pirate Audio Synth & Visualizer
Renders Spectrum Analyzer, Waveform Oscilloscope, and Synth Dashboard screens using PIL.
"""

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH = 240
HEIGHT = 240

# Color Palette Definitions (RGB)
COLOR_BG = (12, 14, 24)
COLOR_CARD = (20, 25, 42)
COLOR_TEXT = (240, 240, 245)
COLOR_MUTED = (120, 130, 155)
COLOR_CYAN = (0, 225, 255)
COLOR_MAGENTA = (255, 0, 150)
COLOR_YELLOW = (255, 210, 0)
COLOR_GREEN = (0, 255, 130)

class DisplayRenderer:
    MODE_SPECTRUM = 0
    MODE_OSCILLOSCOPE = 1
    MODE_SYNTH_DASH = 2

    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width = width
        self.height = height
        self.mode = self.MODE_SPECTRUM
        self.font = ImageFont.load_default()
        self.mode_names = ["Spectrum Analyzer", "Oscilloscope", "Synth Dashboard"]

    def set_mode(self, mode):
        self.mode = mode % len(self.mode_names)

    def render(self, analyzer, synth, fps=0.0):
        img = Image.new("RGB", (self.width, self.height), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Header bar
        draw.rectangle((0, 0, self.width, 24), fill=COLOR_CARD)
        draw.text((8, 6), self.mode_names[self.mode], fill=COLOR_CYAN, font=self.font)
        draw.text((self.width - 55, 6), f"{fps:.0f} FPS", fill=COLOR_MUTED, font=self.font)

        if self.mode == self.MODE_SPECTRUM:
            self._render_spectrum(draw, analyzer, synth)
        elif self.mode == self.MODE_OSCILLOSCOPE:
            self._render_oscilloscope(draw, analyzer, synth)
        elif self.mode == self.MODE_SYNTH_DASH:
            self._render_synth_dashboard(draw, synth)

        # Footer button guide
        draw.line((0, self.height - 18, self.width, self.height - 18), fill=COLOR_CARD)
        draw.text((8, self.height - 14), "A:Mode  B:Preset  X:Tone  Y:Cutoff", fill=COLOR_MUTED, font=self.font)

        return img

    def _render_spectrum(self, draw, analyzer, synth):
        """Renders 16-band Spectrum Analyzer with gradient bars and peak indicators."""
        bands = analyzer.bands
        peaks = analyzer.peaks
        num_bands = len(bands)
        
        bar_margin = 3
        total_width = self.width - 24
        bar_width = max(1, (total_width // num_bands) - bar_margin)
        max_bar_height = 140
        bottom_y = 190

        # Draw Beat pulse ring if detected
        if analyzer.beat_detected:
            draw.ellipse((self.width - 30, 30, self.width - 10, 50), outline=COLOR_MAGENTA, width=2)
            draw.ellipse((self.width - 26, 34, self.width - 14, 46), fill=COLOR_MAGENTA)

        # Draw spectrum bars
        for i in range(num_bands):
            x = 12 + i * (bar_width + bar_margin)
            h = int(bands[i] * max_bar_height)
            p_h = int(peaks[i] * max_bar_height)
            
            top_y = bottom_y - h
            peak_y = bottom_y - p_h

            # Dynamic hue gradient based on frequency band index
            ratio = i / float(num_bands)
            r = int(COLOR_CYAN[0] * (1 - ratio) + COLOR_MAGENTA[0] * ratio)
            g = int(COLOR_CYAN[1] * (1 - ratio) + COLOR_MAGENTA[1] * ratio)
            b = int(COLOR_CYAN[2] * (1 - ratio) + COLOR_MAGENTA[2] * ratio)

            # Draw bar
            if h > 0:
                draw.rectangle((x, top_y, x + bar_width, bottom_y), fill=(r, g, b))
            
            # Draw peak dot
            draw.line((x, peak_y, x + bar_width, peak_y), fill=COLOR_YELLOW, width=2)

        # Draw Active Preset name
        draw.text((12, 32), f"Patch: {synth.current_preset}", fill=COLOR_TEXT, font=self.font)

    def _render_oscilloscope(self, draw, analyzer, synth):
        """Renders real-time waveform scope trace."""
        buffer = synth.last_audio_buffer
        if buffer is None or len(buffer) == 0:
            return

        mid_y = 110
        amplitude_scale = 70.0
        
        # Center grid line
        draw.line((10, mid_y, self.width - 10, mid_y), fill=(30, 40, 60), width=1)
        
        points = []
        step = max(1, len(buffer) // (self.width - 20))
        for i in range(0, min(len(buffer), self.width - 20), step):
            x = 10 + i
            y = int(mid_y - buffer[i] * amplitude_scale)
            points.append((x, y))

        if len(points) > 1:
            draw.line(points, fill=COLOR_GREEN, width=2)

        # Waveform stats
        draw.text((12, 32), f"Waveform: SoundFont (SF2)", fill=COLOR_CYAN, font=self.font)
        draw.text((12, 48), f"Volume RMS: {analyzer.rms:.2f}", fill=COLOR_TEXT, font=self.font)

    def _render_synth_dashboard(self, draw, synth):
        """Renders synth parameters, active patch info, and filter cutoff dial."""
        draw.text((12, 34), "SYNTH PARAMETERS", fill=COLOR_YELLOW, font=self.font)
        
        # Patch Info
        draw.rectangle((12, 52, self.width - 12, 95), fill=COLOR_CARD, outline=(40, 50, 80))
        draw.text((20, 60), f"Patch: {synth.current_preset}", fill=COLOR_TEXT, font=self.font)
        draw.text((20, 75), f"Mode: SF2", fill=COLOR_CYAN, font=self.font)

        # Filter Cutoff Bar
        draw.text((12, 108), f"Cutoff: {int(synth.cutoff)} Hz", fill=COLOR_TEXT, font=self.font)
        cutoff_ratio = min(1.0, max(0.0, synth.cutoff / 10000.0))
        bar_w = int(cutoff_ratio * (self.width - 24))
        draw.rectangle((12, 125, self.width - 12, 138), fill=(25, 30, 50))
        draw.rectangle((12, 125, 12 + bar_w, 138), fill=COLOR_GREEN)

        # Volume Bar
        draw.text((12, 148), f"Volume: {int(synth.volume * 100)}%", fill=COLOR_TEXT, font=self.font)
        vol_w = int(synth.volume * (self.width - 24))
        draw.rectangle((12, 165, self.width - 12, 178), fill=(25, 30, 50))
        draw.rectangle((12, 165, 12 + vol_w, 178), fill=COLOR_CYAN)
