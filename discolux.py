#!/usr/bin/env python3
"""
discolux.py – Main entry point for the DiscoLux LED controller.

Initialises the Wall (WLED network output), optional gamma correction,
and launches the Pygame touch UI.
"""

from config import WLED_HOST
from gamma import init_gamma
from wall import Wall
from touch_ui import launch_ui


def main():
    # ── Gamma / white-balance calibration ───────────────────────────────
    init_gamma(
        gammas={"r": 0.65, "g": 0.65, "b": 0.65, "w": 0.65},
        scales={"r": 1.25, "g": 1.25, "b": 1.25, "w": 1.25},
    )

    # ── Create the Wall output (talks to WLED over the network) ─────────
    wall = Wall() if WLED_HOST else None
    if wall is None:
        print("[discolux] No WLED_HOST configured – running in simulator-only mode.")
    else:
        print(f"[discolux] Sending frames to WLED at {WLED_HOST}")

    # ── Launch the touch UI (blocks until the window is closed) ─────────
    launch_ui(wall=wall)


if __name__ == "__main__":
    main()
