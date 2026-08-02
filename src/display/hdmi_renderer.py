#!/usr/bin/env python3
"""
HDMI Main Screen Oscilloscope & Interactive Touchscreen Piano Interface
Resolution matched to detected 1024x600 7" LCD screen.
MUST be called from the main thread (Pygame requirement).
"""

import os
import numpy as np

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

COLOR_BG = (10, 12, 22)
COLOR_PANEL = (16, 20, 34)
COLOR_TEXT = (240, 240, 250)
COLOR_CYAN = (0, 230, 255)
COLOR_GREEN = (0, 255, 140)
COLOR_YELLOW = (255, 210, 0)
COLOR_WHITE_KEY = (245, 245, 250)
COLOR_BLACK_KEY = (28, 32, 46)
COLOR_KEY_ACTIVE = (0, 230, 255)

class HDMIRenderer:
    def __init__(self, synth, width=1024, height=600, fullscreen=False):
        self.synth = synth
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        self.screen = None
        self.clock = None
        self.touched_notes = set()

        self.white_notes = [48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72]
        self.black_notes = {49: 0, 51: 1, 54: 3, 56: 4, 58: 5, 61: 7, 63: 8, 66: 10, 68: 11, 70: 12}
        self.key_rects = {}

        if not HAS_PYGAME:
            print("[HDMI] Pygame not installed. HDMI display skipped.")
            return
        self.init_display()

    def init_display(self):
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":0"

        try:
            pygame.init()
            pygame.font.init()
            flags = pygame.FULLSCREEN if self.fullscreen else 0
            self.screen = pygame.display.set_mode((self.width, self.height), flags)
            pygame.display.set_caption("Pi 4 Oscilloscope Studio")
            self.clock = pygame.time.Clock()
            self.font_title = pygame.font.SysFont("sans-serif", 24, bold=True)
            self.font_sub = pygame.font.SysFont("sans-serif", 16)
            driver = pygame.display.get_driver()
            print(f"[HDMI] Display initialized ({driver}): {self.width}x{self.height}")
        except Exception as e:
            print(f"[HDMI ERROR] Could not initialize display: {e}")
            self.screen = None

    def _get_note_at_pos(self, pos):
        px, py = pos
        for note, rect in self.key_rects.items():
            if note in self.black_notes and rect.collidepoint(px, py):
                return note
        for note, rect in self.key_rects.items():
            if note in self.white_notes and rect.collidepoint(px, py):
                return note
        return None

    def render(self, analyzer, synth):
        if not self.screen:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pass
            elif event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                pos = getattr(event, 'pos', (int(getattr(event, 'x', 0) * self.width), int(getattr(event, 'y', 0) * self.height)))
                note = self._get_note_at_pos(pos)
                if note:
                    self.touched_notes.add(note)
                    self.synth.note_on(note)
            elif event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                for note in list(self.touched_notes):
                    self.synth.note_off(note)
                self.touched_notes.clear()

        self.screen.fill(COLOR_BG)

        # Header
        pygame.draw.rect(self.screen, COLOR_PANEL, (0, 0, self.width, 44))
        self.screen.blit(self.font_title.render("REAL-TIME OSCILLOSCOPE", True, COLOR_CYAN), (16, 10))
        info = f"{synth.current_preset}  |  {int(synth.cutoff)} Hz"
        info_s = self.font_sub.render(info, True, COLOR_TEXT)
        self.screen.blit(info_s, (self.width - info_s.get_width() - 16, 14))

        # Oscilloscope
        self._render_oscilloscope(synth, 16, 54, self.width - 32, self.height - 210)

        # Piano
        self._render_piano(synth, 16, self.height - 146, self.width - 32, 130)

        pygame.display.flip()

    def _render_oscilloscope(self, synth, x, y, w, h):
        pygame.draw.rect(self.screen, COLOR_PANEL, (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, (40, 50, 75), (x, y, w, h), width=1, border_radius=8)

        mid_y = y + h // 2
        pygame.draw.line(self.screen, (30, 40, 60), (x + 8, mid_y), (x + w - 8, mid_y), 1)
        for i in range(1, 8):
            gx = x + i * (w // 8)
            pygame.draw.line(self.screen, (22, 30, 48), (gx, y + 8), (gx, y + h - 8), 1)

        buf = synth.last_audio_buffer
        if buf is None or len(buf) == 0:
            return

        # Stretch buffer to fill full screen width using interpolation
        draw_w = w - 20
        stretched = np.interp(
            np.linspace(0, len(buf) - 1, draw_w),
            np.arange(len(buf)),
            buf
        )

        scale = (h // 2) - 20
        points = [(x + 10 + i, int(mid_y - stretched[i] * scale)) for i in range(draw_w)]

        if len(points) > 1:
            pygame.draw.lines(self.screen, (0, 80, 50), False, points, 4)
            pygame.draw.lines(self.screen, COLOR_GREEN, False, points, 2)

    def _render_piano(self, synth, x, y, w, h):
        pygame.draw.rect(self.screen, COLOR_PANEL, (x, y, w, h), border_radius=8)

        self.key_rects.clear()
        nw = len(self.white_notes)
        kw = (w - 16) // nw
        kh = h - 16
        active = getattr(synth, 'active_notes', set())

        for i, note in enumerate(self.white_notes):
            kx = x + 8 + i * kw
            ky = y + 8
            rect = pygame.Rect(kx, ky, kw - 2, kh)
            self.key_rects[note] = rect
            c = COLOR_KEY_ACTIVE if note in (self.touched_notes | active) else COLOR_WHITE_KEY
            pygame.draw.rect(self.screen, c, rect, border_radius=3)
            pygame.draw.rect(self.screen, (180, 185, 200), rect, width=1, border_radius=3)

        bkw = int(kw * 0.6)
        bkh = int(kh * 0.6)
        for note, wi in self.black_notes.items():
            kx = x + 8 + (wi + 1) * kw - bkw // 2
            ky = y + 8
            rect = pygame.Rect(kx, ky, bkw, bkh)
            self.key_rects[note] = rect
            c = COLOR_KEY_ACTIVE if note in (self.touched_notes | active) else COLOR_BLACK_KEY
            pygame.draw.rect(self.screen, c, rect, border_radius=3)
