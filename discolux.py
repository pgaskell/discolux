#!/usr/bin/env python3
"""
discolux.py – Main entry point for the DiscoLux LED controller.

Initialises the Wall (WLED network output), optional gamma correction,
and launches the Pygame touch UI.
"""

from config import WLED_HOST, MULTI_WLED_MODE, EXTEND_DIRECTION, WLED_DEVICES
from gamma import init_gamma
from wall import MultiWall
from touch_ui import launch_ui


def main():
    # ── Gamma / white-balance calibration ───────────────────────────────
    init_gamma(
        gammas={"r": 0.65, "g": 0.65, "b": 0.65, "w": 0.65},
        scales={"r": 1.25, "g": 1.25, "b": 1.25, "w": 1.25},
    )

    # ── Create multi-device wall output ─────────────────────────────────
    if not WLED_DEVICES or not WLED_DEVICES[0].get("host"):
        wall = None
        print("[discolux] No WLED host configured – running in simulator-only mode.")
    else:
        wall = MultiWall(
            devices=WLED_DEVICES,
            mode=MULTI_WLED_MODE,
            extend_direction=EXTEND_DIRECTION,
        )
        print(f"[discolux] Output mode={MULTI_WLED_MODE}, "
              f"devices={[d['host'] for d in WLED_DEVICES]}")

    # ── Launch the touch UI (blocks until the window is closed) ─────────
    launch_ui(wall=wall)


if __name__ == "__main__":
    main()
