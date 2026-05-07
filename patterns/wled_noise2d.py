# WLED "Noise2D" effect — port of mode_2Dnoise()
# Original: "Noise2D@!,Scale;;!;2"
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import inoise8, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.0, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "SCALE": {
        "default": 0.10, "min": 0.01, "max": 0.5, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "warm_rainbow", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.t = 0.0
        self._last = time.time()

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        speed = self.params["SPEED"]
        scale = self.params["SCALE"]
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("SPEED", "SCALE"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED": speed = v
                else: scale = v

        self.t += dt * speed * 20.0

        w, h = self.width, self.height
        frame = []
        for y in range(h):
            for x in range(w):
                val = inoise8(x, y, self.t, scale=scale)
                frame.append(palette_color(cmap, val) + (0,))
        return frame
