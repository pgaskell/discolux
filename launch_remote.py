#!/usr/bin/env python3
"""
launch_remote.py – Launch DiscoLux on the Pi's local display from a
remote VS Code / SSH session.

Usage:
    python3 launch_remote.py          # launch
    python3 launch_remote.py --kill   # kill running instance
"""

import subprocess
import sys
import os
import signal
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = "/tmp/discolux.log"

# Environment needed to target the Pi's physical display
DISPLAY_ENV = {
    **os.environ,
    "DISPLAY": ":0",
    "WAYLAND_DISPLAY": "wayland-0",
    "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
    "SDL_VIDEODRIVER": "x11",
}


def kill_existing():
    """Kill any running discolux.py processes."""
    result = subprocess.run(
        ["pgrep", "-f", "python3 discolux.py"],
        capture_output=True, text=True,
    )
    pids = result.stdout.strip().split()
    if pids:
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"[launch] Sent SIGTERM to PID {pid}")
            except ProcessLookupError:
                pass
        time.sleep(0.5)
        print("[launch] Existing instance stopped.")
    else:
        print("[launch] No running instance found.")


def launch():
    """Launch discolux.py on the Pi's physical display."""
    kill_existing()

    with open(LOG_FILE, "a") as log:
        log.write(f"\n--- launch_remote.py at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    proc = subprocess.Popen(
        [sys.executable, "discolux.py"],
        cwd=SCRIPT_DIR,
        env=DISPLAY_ENV,
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,  # detach from this terminal
    )
    print(f"[launch] DiscoLux started (PID {proc.pid})")
    print(f"[launch] Log: {LOG_FILE}")
    print(f"[launch] Use:  python3 launch_remote.py --kill  to stop")


if __name__ == "__main__":
    if "--kill" in sys.argv:
        kill_existing()
    else:
        launch()
