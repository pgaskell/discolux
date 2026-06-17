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

    # WLED (single-device legacy keys, kept for backward compat)
    "wled_host": "10.0.0.2",
    "wled_timeout": 0.5,
    "led_protocol": "DRGB",

    # Multi-device output
    "multi_wled_mode": "single",   # "single" | "mirror" | "extend"
    "extend_direction": "right",   # "right" | "left" | "below" | "above"
    # wled_devices is intentionally absent from defaults; it is derived from
    # the legacy wled_host / matrix_width / matrix_height keys when missing.

    # Frame rate
    "frame_rate": 30,

    # UI / runtime
    "cycle_beats": 32,
    "auto_bpm": False,
    "brightness": 1.0,
    "mic_sensitivity": 1.0,
    "orientation": "normal",
    "display_mode": "Fill",
    "render_sprites": True,
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

MULTI_WLED_MODE = _cfg.get("multi_wled_mode", "single")
EXTEND_DIRECTION = _cfg.get("extend_direction", "right")

# Derive WLED_DEVICES: prefer saved list; fall back to legacy single-device keys.
# Always provide 3 device slots so the UI can show all three panels.
_primary = {
    "host":        _cfg["wled_host"],
    "width":       _cfg["matrix_width"],
    "height":      _cfg["matrix_height"],
    "protocol":    _cfg["led_protocol"],
    "wiring_mode": _cfg.get("wiring_mode", "COLUMN_MAJOR"),
    "x": 0, "y": 0, "active": True,
}
_device_preset = {
    "host":        "10.0.0.3",
    "width":       _cfg["matrix_width"],
    "height":      _cfg["matrix_height"],
    "protocol":    _cfg["led_protocol"],
    "wiring_mode": _cfg.get("wiring_mode", "COLUMN_MAJOR"),
    "x": 0, "y": 0, "active": False,
}
WLED_DEVICES = _cfg.get("wled_devices") or [_primary, dict(_device_preset), dict(_device_preset)]
# Ensure there are always at least 3 device slots
while len(WLED_DEVICES) < 3:
    WLED_DEVICES = list(WLED_DEVICES) + [dict(_device_preset)]

FRAME_RATE = _cfg["frame_rate"]