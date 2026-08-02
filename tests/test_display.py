#!/usr/bin/env python3
"""
ST7789 LCD Display Test for Pimoroni Pirate Audio (240x240 SPI Display)
Renders dynamic test pattern, text info, and FPS counter.
"""

import time
import math
from PIL import Image, ImageDraw, ImageFont

try:
    import ST7789
except ImportError:
    try:
        import st7789 as ST7789
    except ImportError:
        ST7789 = None

WIDTH = 240
HEIGHT = 240
ROTATION = 180  # 180 degree rotation as required for upside-down cabling layout

def init_display():
    if ST7789 is None:
        print("[WARNING] ST7789 module not installed. Running in simulation mode.")
        return None

    # Pimoroni Pirate Audio LCD pin configuration:
    # SPI Port: 0, CS: 1 (GPIO 7) or 0 (GPIO 8), DC: GPIO 9, Backlight: GPIO 13
    try:
        disp = ST7789.ST7789(
            port=0,
            cs=1,
            dc=9,
            backlight=13,
            rotation=ROTATION,
            spi_speed_hz=52_000_000
        )
        disp.begin()
        return disp
    except Exception as e:
        print(f"[ERROR] Display initialization failed with CS=1: {e}")
        try:
            disp = ST7789.ST7789(
                port=0,
                cs=0,
                dc=9,
                backlight=13,
                rotation=ROTATION,
                spi_speed_hz=52_000_000
            )
            disp.begin()
            return disp
        except Exception as e2:
            print(f"[ERROR] Display initialization failed with CS=0: {e2}")
            return None

def main():
    print("=== ST7789 Display Test ===")
    disp = init_display()
    
    font = ImageFont.load_default()
    
    start_time = time.time()
    frames = 0
    
    print("Rendering animation loop for 10 seconds...")
    try:
        while time.time() - start_time < 10:
            elapsed = time.time() - start_time
            img = Image.new("RGB", (WIDTH, HEIGHT), color=(15, 18, 28))
            draw = ImageDraw.Draw(img)
            
            # Draw glowing gradient background circles
            cx, cy = WIDTH // 2, HEIGHT // 2
            r = 60 + int(30 * math.sin(elapsed * 4))
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(0, 220, 255), width=3)
            
            r2 = 40 + int(20 * math.cos(elapsed * 4))
            draw.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), outline=(255, 0, 128), width=2)
            
            # Header text
            draw.text((20, 20), "PIRATE AUDIO ST7789", fill=(255, 255, 255), font=font)
            draw.text((20, 35), f"Rotation: {ROTATION}°", fill=(180, 180, 180), font=font)
            
            # Calculate & display FPS
            fps = frames / max(elapsed, 0.001)
            draw.text((20, HEIGHT - 30), f"FPS: {fps:.1f}", fill=(0, 255, 120), font=font)
            draw.text((20, HEIGHT - 15), "Press Ctrl+C to exit", fill=(100, 100, 100), font=font)
            
            if disp:
                disp.display(img)
            
            frames += 1
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\nDisplay test interrupted by user.")
        
    print(f"Test completed. Rendered {frames} frames at {frames / max(time.time() - start_time, 0.001):.1f} FPS.")

if __name__ == "__main__":
    main()
