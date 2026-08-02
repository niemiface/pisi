#!/usr/bin/env bash
# Raspberry Pi 4 Pirate Audio DAC & ST7789 Setup Script
# Run with sudo: sudo ./setup_pi.sh

set -e

echo "=== 1. Updating System Packages ==="
apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    python3-pil \
    python3-numpy \
    python3-spidev \
    python3-scipy \
    python3-gpiozero \
    python3-evdev \
    alsa-utils \
    portaudio19-dev \
    libopenblas-dev \
    git \
    rsync

echo "=== 2. Configuring Boot Firmware Overlays ==="
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

echo "Targeting config file: $CONFIG_FILE"

# Backup config file
cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
echo "Backed up config file."

# Helper function to append line if not present
append_if_missing() {
    local line="$1"
    if ! grep -qF "$line" "$CONFIG_FILE"; then
        echo "$line" >> "$CONFIG_FILE"
        echo "Added: $line"
    else
        echo "Already present: $line"
    fi
}

echo "Applying Pirate Audio hardware overlays..."
append_if_missing "dtoverlay=hifiberry-dac"
append_if_missing "dtparam=spi=on"
append_if_missing "gpio=25=op,dh"

# Disable onboard headphone audio to make HiFiBerry default card (optional, comment out if unwanted)
# sed -i 's/dtparam=audio=on/#dtparam=audio=on/' "$CONFIG_FILE"

echo "=== 3. Setting Up Python Environment ==="
VENV_DIR="/home/niemiface/pisi/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
    echo "Created venv at $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install st7789 pillow numpy sounddevice scipy gpiozero rpi-lgpio evdev mido python-rtmidi

echo "=== Setup Completed Successfully! ==="
echo "Please reboot your Raspberry Pi using 'sudo reboot' for device tree overlays to take effect."
