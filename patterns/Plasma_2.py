import time
import math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "SPEED": {
        "default": 0.1,     "min": -1.0,  "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "FREQUENCY": {
        "default": 3.0,     "min": 0.1,   "max": 10.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "AMPLITUDE": {
        "default": 1.0,     "min": 0.1,   "max": 2.0,  "step": 0.1,
        "modulatable": True, "mod_mode": "scale"
    },
    "LUT_SHIFT": {
        "default": 0.0,     "min": 0.0,   "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "rainbow",
        "options": list(COLORMAPS.keys())
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.start_time = time.time()

    def render(self, lfo_signals=None):
        t = time.time() - self.start_time

        # 1) Read raw parameters
        speed     = self.params["SPEED"]
        frequency = self.params["FREQUENCY"]
        amplitude = self.params["AMPLITUDE"]
        shift     = self.params["LUT_SHIFT"]

        # 2) Apply modulation if active
        for key in ("SPEED", "FREQUENCY", "AMPLITUDE", "LUT_SHIFT"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active", False):
                src = meta["mod_source"]
                amt = (lfo_signals or {}).get(src, 0.0)
                val = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED":
                    speed = val
                elif key == "FREQUENCY":
                    frequency = val
                elif key == "AMPLITUDE":
                    amplitude = val
                else:  # LUT_SHIFT
                    shift = val % 1.0

        # 3) Scale time
        t *= speed

        # 4) Pick colormap
        cmap     = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["rainbow"])
        cmap_len = len(cmap)

        w, h = self.width, self.height
        frame = []

        for y in range(h):
            vy = y / h
            for x in range(w):
                vx = x / w

                # classic plasma formula
                v = (
                    math.sin((vx + t) * frequency)
                  + math.sin((vy + t) * frequency)
                  + math.sin(((vx + vy) / 2 + t) * frequency)
                )
                # normalize [-3..3] → [0..1]
                v = (v + 3.0) / 6.0

                # apply amplitude & clamp
                v = max(0.0, min(1.0, v * amplitude))

                # rotate through LUT
                v = (v + shift) % 1.0

                idx = int(v * (cmap_len - 1))
                r, g, b = cmap[idx]
                frame.append((r, g, b, 0))

        return frame
