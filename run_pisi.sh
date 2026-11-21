#!/bin/bash
# Launcher for the pisi synth/visualizer project
# Kills any previous running instance first so audio device isn't double-claimed.

pkill -9 -f "python3 main.py" 2>/dev/null
sleep 1

cd /home/niemiface/pisi
source venv/bin/activate
export DISPLAY=:0
python3 main.py
