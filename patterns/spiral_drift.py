import math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "SPIRAL_SPEED": {
        "default": 0.01,  "min": -0.2, "max": 0.2, "step": 0.01,
        "modulatable": True,
        "mod_mode": "add"
    },
    "NUM_ARMS": {
        "default": 4,    "min": 1,    "max": 8,   "step": 1,
        "modulatable": True,
        "mod_mode": "replace"
    },
    "ARM_THICKNESS": {
        "default": 0.1,  "min": 0.01, "max": 0.5, "step": 0.01,
        "modulatable": True,
        "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "jet",
        "options": list(COLORMAPS.keys())
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        # keep a handle to our metadata for modulation
        self.param_meta  = PARAMS
        self.frame_count = 0

    def render(self, lfo_signals=None):
        self.frame_count += 1

        # --- pull raw params ---
        speed     = self.params["SPIRAL_SPEED"]
        num_arms  = self.params["NUM_ARMS"]
        thickness = self.params["ARM_THICKNESS"]

        # --- apply any active modulations ---
        if lfo_signals:
            for key in ("SPIRAL_SPEED", "NUM_ARMS", "ARM_THICKNESS"):
                meta = self.param_meta[key]
                if meta.get("modulatable") and meta.get("mod_active"):
                    src = meta.get("mod_source")
                    if src and src in lfo_signals:
                        val = lfo_signals[src]
                        # produce the new, modulated parameter
                        mod_val = apply_modulation(self.params[key], meta, val)

                        if key == "SPIRAL_SPEED":
                            speed = mod_val
                        elif key == "NUM_ARMS":
                            num_arms = max(1, int(round(mod_val)))
                        elif key == "ARM_THICKNESS":
                            thickness = mod_val

        # --- now draw the spiral ---
        cmap     = COLORMAPS.get(self.params.get("COLORMAP","jet"), COLORMAPS["jet"])
        cmap_len = len(cmap)

        cx = self.width  / 2
        cy = self.height / 2
        to = self.frame_count * speed

        frame = []
        for y in range(self.height):
            for x in range(self.width):
                dx = x - cx
                dy = y - cy
                r = math.hypot(dx, dy)

                theta = (math.atan2(dy, dx) + math.pi) / (2*math.pi)
                spin  = (theta + r * 0.05 - to) * num_arms

                # sharpen edges by raising to 1/thickness
                v = 0.5 + 0.5 * math.cos(spin * 2*math.pi)
                v = max(0.0, min(1.0, v ** (1.0/thickness)))

                idx = int(v * (cmap_len-1))
                r_col, g_col, b_col = cmap[idx]
                frame.append((r_col, g_col, b_col, 0))

        return frame
