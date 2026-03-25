#!/bin/bash
# start_discolux.sh – Launch DiscoLux with proper environment.
# Called from labwc autostart on login.

# Minimal wait for display server to be ready
sleep 0.5

# Ensure we can talk to the Wayland/X display
export DISPLAY=:0
export SDL_VIDEODRIVER=x11

# Audio: make sure PulseAudio / PipeWire is up (for sounddevice)
# Timeout after 10 seconds if audio server isn't starting
for i in $(seq 1 20); do
    if command -v pactl &>/dev/null && pactl info &>/dev/null; then
        break
    fi
    sleep 0.5
done

cd /home/rpi/discolux_ctrl
exec python3 discolux.py >> /tmp/discolux.log 2>&1
