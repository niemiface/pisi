#!/usr/bin/env python3
"""
Hardware, USB QWERTY Keyboard (evdev), USB Touchscreen Piano, and USB MIDI Controller.
Key-repeat events (event.value==2) are IGNORED so held keys play one continuous note.
Touchscreen auto-reconnects if the USB device cycles.
Touch coordinates (0-4096) are mapped to screen pixels (1024x600).
"""

import time
import threading
import os

try:
    from gpiozero import Button
    HAS_GPIOZERO = True
except ImportError:
    HAS_GPIOZERO = False

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

try:
    import evdev
    from evdev import ecodes, InputDevice
    HAS_EVDEV = True
except ImportError:
    HAS_EVDEV = False

PINS = {'A': 5, 'B': 6, 'X': 16, 'Y': 24}

EVDEV_KEY_NOTE_MAP = {
    'KEY_A': 60, 'KEY_W': 61, 'KEY_S': 62, 'KEY_E': 63,
    'KEY_D': 64, 'KEY_F': 65, 'KEY_T': 66, 'KEY_G': 67,
    'KEY_Y': 68, 'KEY_H': 69, 'KEY_U': 70, 'KEY_J': 71,
    'KEY_K': 72, 'KEY_O': 73, 'KEY_L': 74,
}

# ROADOM LE070-01 touchscreen: coordinates 0-4096, screen 1024x600
TOUCH_MAX_X = 4096
TOUCH_MAX_Y = 4096
SCREEN_W = 1024
SCREEN_H = 600


class HardwareController:
    def __init__(self, synth, renderer, hdmi_renderer=None):
        self.synth = synth
        self.renderer = renderer
        self.hdmi = hdmi_renderer
        self.buttons = {}
        self.presets = list(synth.PRESETS.keys())
        self.preset_idx = 0
        self.test_notes = [60, 64, 67, 72]
        self.note_idx = 0
        self.running = True
        self.pressed_keys = set()  # Tracks held keys to filter OS repeats

        self.setup_buttons()
        self.setup_usb_midi()
        self.setup_keyboard_listener()
        self.setup_touchscreen_listener()

    def setup_buttons(self):
        if not HAS_GPIOZERO:
            print("[WARNING] gpiozero unavailable.")
            return
        for name, pin in PINS.items():
            try:
                btn = Button(pin, pull_up=True, bounce_time=0.05)
                if name == 'A': btn.when_pressed = self.on_button_a
                elif name == 'B': btn.when_pressed = self.on_button_b
                elif name == 'X':
                    btn.when_pressed = self.on_button_x
                    btn.when_released = self.on_button_x_release
                elif name == 'Y': btn.when_pressed = self.on_button_y
                self.buttons[name] = btn
                print(f"[HW] Button {name} on GPIO {pin}")
            except Exception as e:
                print(f"[HW] Button {name} failed: {e}")

    def _find_touchscreen(self):
        """Find the yldzkj touchscreen device path dynamically."""
        if not HAS_EVDEV:
            return None
        for path in evdev.list_devices():
            try:
                dev = InputDevice(path)
                if 'yldzkj' in dev.name or 'CTP' in dev.name.upper():
                    return dev
            except (PermissionError, OSError):
                continue
        return None

    def _find_keyboards(self):
        """Find all USB keyboard devices."""
        if not HAS_EVDEV:
            return []
        keyboards = []
        for path in evdev.list_devices():
            try:
                dev = InputDevice(path)
                if "HDMI" in dev.name or "vc4" in dev.name:
                    continue
                if 'yldzkj' in dev.name or 'CTP' in dev.name.upper():
                    continue  # Skip touchscreen
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps:
                    key_caps = caps[ecodes.EV_KEY]
                    # Must have letter keys (KEY_A = 30)
                    if 30 in key_caps:
                        keyboards.append(dev)
                        print(f"[INPUT] Keyboard: '{dev.name}' at {dev.path}")
            except (PermissionError, OSError):
                continue
        return keyboards

    def setup_keyboard_listener(self):
        """Keyboard listener thread — reads evdev key events."""
        if not HAS_EVDEV:
            print("[INFO] evdev not installed.")
            return

        def keyboard_loop():
            print("[INPUT] Scanning /dev/input/...")
            keyboards = self._find_keyboards()

            if not keyboards:
                print("[INPUT] No USB keyboards found.")

            while self.running:
                for dev in list(keyboards):
                    try:
                        for event in dev.read():
                            if event.type != ecodes.EV_KEY:
                                continue

                            key_code = ecodes.KEY.get(event.code, None)
                            if isinstance(key_code, list):
                                key_code = key_code[0]
                            if not key_code:
                                continue

                            # ONLY handle first press (1), IGNORE repeats (2)
                            if event.value == 1:
                                if key_code not in self.pressed_keys:
                                    self.pressed_keys.add(key_code)
                                    if key_code in EVDEV_KEY_NOTE_MAP:
                                        note = EVDEV_KEY_NOTE_MAP[key_code]
                                        self.synth.note_on(note)
                                    elif key_code == 'KEY_1': self.on_button_a()
                                    elif key_code == 'KEY_2': self.on_button_b()
                                    elif key_code == 'KEY_3': self.on_button_x()
                                    elif key_code == 'KEY_4': self.on_button_y()

                            elif event.value == 0:  # Key release
                                self.pressed_keys.discard(key_code)
                                if key_code in EVDEV_KEY_NOTE_MAP:
                                    note = EVDEV_KEY_NOTE_MAP[key_code]
                                    self.synth.note_off(note)
                            # event.value == 2 (repeat) is intentionally IGNORED
                    except (BlockingIOError, OSError):
                        pass

                time.sleep(0.008)

        threading.Thread(target=keyboard_loop, daemon=True).start()

    def setup_touchscreen_listener(self):
        """Touchscreen listener thread — auto-reconnects on USB disconnect."""
        if not HAS_EVDEV:
            return

        def touch_loop():
            touch_x = 0
            touch_y = 0
            touch_note = None
            connected = False

            while self.running:
                # Try to find touchscreen if not connected
                if not connected:
                    dev = self._find_touchscreen()
                    if dev:
                        print(f"[TOUCH] Connected: '{dev.name}' at {dev.path}")
                        connected = True
                    else:
                        time.sleep(1.0)  # Retry every second
                        continue

                # Read touch events
                try:
                    for event in dev.read():
                        if event.type == ecodes.EV_ABS:
                            if event.code in (ecodes.ABS_X, ecodes.ABS_MT_POSITION_X):
                                touch_x = event.value
                            elif event.code in (ecodes.ABS_Y, ecodes.ABS_MT_POSITION_Y):
                                touch_y = event.value

                        elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                            if event.value == 1:  # Finger down
                                # Map 0-4096 touch coords to screen pixels
                                px = int(touch_x / TOUCH_MAX_X * SCREEN_W)
                                py = int(touch_y / TOUCH_MAX_Y * SCREEN_H)

                                note = self._pos_to_note(px, py)
                                if note is not None:
                                    touch_note = note
                                    self.synth.note_on(note)
                                    if self.hdmi:
                                        self.hdmi.touched_notes.add(note)
                                    print(f"[TOUCH] Tap ({px},{py}) -> Note {note}")

                            elif event.value == 0:  # Finger up
                                if touch_note is not None:
                                    self.synth.note_off(touch_note)
                                    if self.hdmi:
                                        self.hdmi.touched_notes.discard(touch_note)
                                    touch_note = None

                except BlockingIOError:
                    pass
                except OSError:
                    # Device disconnected — will auto-reconnect
                    print("[TOUCH] Disconnected, waiting to reconnect...")
                    connected = False
                    touch_note = None
                    time.sleep(0.5)
                    continue

                time.sleep(0.008)

        threading.Thread(target=touch_loop, daemon=True).start()

    def _pos_to_note(self, px, py):
        """Map screen pixel position to a piano key note number."""
        # Use HDMI renderer's key rectangles if available
        if self.hdmi and self.hdmi.key_rects:
            # Check black keys first (they overlap white keys)
            for note in self.hdmi.black_notes:
                if note in self.hdmi.key_rects:
                    rect = self.hdmi.key_rects[note]
                    if rect.collidepoint(px, py):
                        return note
            for note in self.hdmi.white_notes:
                if note in self.hdmi.key_rects:
                    rect = self.hdmi.key_rects[note]
                    if rect.collidepoint(px, py):
                        return note

        # Fallback: piano is in bottom 146px of screen, 15 white keys
        piano_top = SCREEN_H - 146
        if py < piano_top:
            return None
        white_notes = [48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72]
        key_w = (SCREEN_W - 32) // len(white_notes)
        idx = max(0, min((px - 16) // key_w, len(white_notes) - 1))
        return white_notes[idx]

    def setup_usb_midi(self):
        if not HAS_MIDO:
            return

        def midi_listener():
            opened_ports = []
            try:
                inputs = mido.get_input_names()
                if inputs:
                    for name in inputs:
                        if "Midi Through" in name:
                            continue
                        try:
                            port = mido.open_input(name)
                            opened_ports.append(port)
                            print(f"[MIDI] Connected: {name}")
                        except Exception:
                            pass
                    while self.running:
                        for port in opened_ports:
                            for msg in port.iter_pending():
                                if msg.type == 'note_on':
                                    v = msg.velocity / 127.0
                                    if msg.velocity > 0:
                                        self.synth.note_on(msg.note, v)
                                    else:
                                        self.synth.note_off(msg.note)
                                elif msg.type == 'note_off':
                                    self.synth.note_off(msg.note)
                        time.sleep(0.002)
            except Exception:
                pass
            finally:
                for p in opened_ports:
                    p.close()

        threading.Thread(target=midi_listener, daemon=True).start()

    def on_button_a(self):
        self.renderer.set_mode(self.renderer.mode + 1)
        print(f"[HW] Mode: {self.renderer.mode_names[self.renderer.mode]}")

    def on_button_b(self):
        self.preset_idx = (self.preset_idx + 1) % len(self.presets)
        name = self.presets[self.preset_idx]
        self.synth.apply_preset(name)
        print(f"[HW] Preset: {name}")

    def on_button_x(self):
        note = self.test_notes[self.note_idx]
        self.note_idx = (self.note_idx + 1) % len(self.test_notes)
        self.synth.note_on(note)

    def on_button_x_release(self):
        for note in self.test_notes:
            self.synth.note_off(note)

    def on_button_y(self):
        c = self.synth.cutoff + 1500.0
        if c > 9000.0: c = 800.0
        self.synth.cutoff = c
        print(f"[HW] Cutoff: {c:.0f} Hz")
