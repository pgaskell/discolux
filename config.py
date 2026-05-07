"""
config.py – Central configuration for DiscoLux.

All settings are loaded from ``discolux_settings.yaml`` if it exists,
otherwise sensible defaults are used.  The CONFIG tab in the UI can
write changes back to the YAML file at any time.
"""

import os
import yaml

CONFIG_FILE = "discolux_settings.yaml"

# ─── Defaults ──────────────────────────────────────────────────────────────
_DEFAULTS = {
    # Matrix
    "matrix_width": 24,
    "matrix_height": 24,

    # WLED
    "wled_host": "10.0.0.2",
    "wled_timeout": 0.5,
    "led_protocol": "DRGB",

    # Frame rate
    "frame_rate": 30,

    # UI / runtime
    "cycle_beats": 32,
    "auto_bpm": False,
    "brightness": 1.0,
    "mic_sensitivity": 1.0,
}


def _load_yaml() -> dict:
    """Load the YAML config file, merging with defaults."""
    cfg = dict(_DEFAULTS)
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                saved = yaml.safe_load(f) or {}
            cfg.update(saved)
        except Exception as e:
            print(f"[config] Warning: could not read {CONFIG_FILE}: {e}")
    return cfg


def save_yaml(settings: dict):
    """Write current settings dict to the YAML config file."""
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(settings, f, default_flow_style=False, sort_keys=False)


_cfg = _load_yaml()

# ─── Public module-level attributes (used by other modules) ────────────────
MATRIX_WIDTH = _cfg["matrix_width"]
MATRIX_HEIGHT = _cfg["matrix_height"]

WLED_HOST = _cfg["wled_host"]
WLED_TIMEOUT = _cfg["wled_timeout"]
LED_PROTOCOL = _cfg["led_protocol"]

FRAME_RATE = _cfg["frame_rate"]