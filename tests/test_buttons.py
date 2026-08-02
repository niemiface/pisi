#!/usr/bin/env python3
"""
Pirate Audio Tactile Buttons Test
Button GPIO pins:
  Button A: GPIO 5
  Button B: GPIO 6
  Button X: GPIO 16
  Button Y: GPIO 24
"""

import time
import sys

try:
    from gpiozero import Button
    HAS_GPIOZERO = True
except ImportError:
    HAS_GPIOZERO = False

PINS = {
    'A': 5,
    'B': 6,
    'X': 16,
    'Y': 24
}

def main():
    print("=== Pirate Audio Button Hardware Test ===")
    print("Mapping: Button A=GPIO5, B=GPIO6, X=GPIO16, Y=GPIO24")
    
    if not HAS_GPIOZERO:
        print("[ERROR] gpiozero is not installed. Please install gpiozero / rpi-lgpio.")
        sys.exit(1)

    buttons = {}
    for name, pin in PINS.items():
        try:
            btn = Button(pin, pull_up=True)
            btn.when_pressed = lambda b=name: print(f"[EVENT] Button {b} PRESSED!")
            btn.when_released = lambda b=name: print(f"[EVENT] Button {b} RELEASED!")
            buttons[name] = btn
            print(f"Initialized Button {name} on GPIO {pin}")
        except Exception as e:
            print(f"Failed to initialize Button {name} on GPIO {pin}: {e}")

    print("\nPress buttons A, B, X, or Y on your Pirate Audio HAT (Ctrl+C to quit)...")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nButton test finished.")

if __name__ == "__main__":
    main()
