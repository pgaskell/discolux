# WLED "Firenoise" effect — port of mode_2Dfirenoise()
# Original: "Firenoise@X scale,Y scale;;!;2"
# 2D Perlin-noise-based fire.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import inoise8, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "X_SCALE": {
        "default": 0.08, "min": 0.02, "max": 0.4, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "Y_SCALE": {
        "default": 0.12, "min": 0.02, "max": 0.4, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "fire", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._last = time.time()
        self.t = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        speed  = self.params["SPEED"]
        xs     = self.params["X_SCALE"]
        ys     = self.params["Y_SCALE"]
        cmap   = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt * speed

        w, h = self.width, self.height
        t = self.t
        frame = []
        for y in range(h):
            for x in range(w):
                # Combine two noise octaves; scroll upward over time
                ny = (h - 1 - y) / h   # flip so fire rises
                n1 = inoise8(x, y, t * 15.0, scale=xs)
                n2 = inoise8(x + 64, y + 64, t * 9.0, scale=ys)
                # Attenuate near the top
                heat = int(((n1 * 0.6 + n2 * 0.4) * (ny ** 0.5)))
                heat = max(0, min(255, heat))
                color = palette_color(cmap, heat)
                frame.append((color[0], color[1], color[2], 0))
        return frame
