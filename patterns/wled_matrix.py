# WLED "2D Matrix" effect — port of mode_2Dmatrix()
# Original: "Matrix@Spawn rate,Luma fade,Custom color,Trail;!,Spawn,Custom;!;2;c1=0,c2=0"
# Digital rain / Matrix effect.
import math
import random
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import fade_to_black, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPAWN_RATE": {
        "default": 0.3, "min": 0.05, "max": 1.0, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "FADE": {
        "default": 30, "min": 1, "max": 200, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "matrix_green", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._last = time.time()
        self._frame = [(0, 0, 0, 0)] * (width * height)
        # Column states: (active, y_pos, speed)
        self._cols = [{"active": False, "y": -1, "speed": 1.0} for _ in range(width)]
        self._tick = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        spawn_rate = self.params["SPAWN_RATE"]
        fade       = self.params["FADE"]
        speed      = self.params["SPEED"]
        cmap_name  = self.params["COLORMAP"]
        cmap       = COLORMAPS.get(cmap_name, list(COLORMAPS.values())[0])

        for key in ("SPAWN_RATE", "FADE", "SPEED"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPAWN_RATE": spawn_rate = v
                elif key == "FADE":     fade = int(v)
                else:                   speed = v

        self._tick += dt * speed * 10.0
        w, h = self.width, self.height

        # Fade all pixels
        fade_to_black(self._frame, w, h, fade)

        # Advance active columns
        for x, col in enumerate(self._cols):
            if col["active"]:
                col["y"] += col["speed"] * speed * dt * 10.0
                yi = int(col["y"])
                if yi >= h:
                    col["active"] = False
                    col["y"] = -1
                else:
                    # Bright leading pixel
                    head_color = (200, 255, 200)  # bright white-green
                    self._frame[yi * w + x] = head_color + (0,)
                    # Trail (slightly dimmer) already handled by fade
            else:
                # Possibly spawn
                if random.random() < spawn_rate * dt:
                    col["active"] = True
                    col["y"] = 0.0
                    col["speed"] = random.uniform(0.5, 2.0)

        # Re-color non-faded pixels from palette
        frame = []
        for i, p in enumerate(self._frame):
            lum = max(p[0], p[1], p[2])
            if lum > 0:
                hue = int(i * 256 / (w * h) + self._tick) & 255
                c = palette_color(cmap, hue)
                scale = lum / 255.0
                frame.append((int(c[0] * scale), int(c[1] * scale), int(c[2] * scale), 0))
            else:
                frame.append((0, 0, 0, 0))
        return frame
