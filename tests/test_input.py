#!/usr/bin/env python3
"""
USB Input Device Diagnostic Tool
Lists all connected keyboards, touchscreens, and mice under /dev/input/
and monitors keypress events in real-time.
"""

import sys
import evdev

def main():
    print("=== USB Input Devices Diagnostic ===")
    
    try:
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    except Exception as e:
        print(f"[ERROR] Could not list /dev/input devices: {e}")
        print("Try running with sudo: sudo python3 tests/test_input.py")
        sys.exit(1)

    if not devices:
        print("[WARNING] No input devices found under /dev/input/. Check USB physical connections.")
        sys.exit(0)

    print(f"Found {len(devices)} input device(s):")
    for dev in devices:
        print(f"  - [{dev.path}] Name: '{dev.name}' | Phys: '{dev.phys}'")

    print("\nListening for live keypresses from all input devices...")
    print("Press any keys on your plugged-in USB keyboard (Press Ctrl+C to stop)...\n")

    try:
        from select import select
        dev_map = {dev.fd: dev for dev in devices}
        
        while True:
            r, w, x = select(dev_map, [], [])
            for fd in r:
                dev = dev_map[fd]
                for event in dev.read():
                    if event.type == evdev.ecodes.EV_KEY:
                        key_event = evdev.categorize(event)
                        print(f"[EVENT] Device '{dev.name}' -> Key: {key_event.keycode} | State: {key_event.keystate}")

    except KeyboardInterrupt:
        print("\nDiagnostic test stopped.")
    except PermissionError:
        print("\n[PERMISSION ERROR] Permission denied reading /dev/input/.")
        print("Run with sudo: sudo ~/pisi/venv/bin/python3 tests/test_input.py")

if __name__ == "__main__":
    main()
