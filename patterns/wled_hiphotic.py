# WLED "Hiphotic" effect — port of mode_2DHiphotic()
# Original: "Hiphotic@X scale,Y scale,,,Speed;!;!;2"
# By ldirko — sin(x*scale) + cos(y*scale + a) plasma.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color
from colormaps import COLORMAPS

PARAMS = {
    "X_SCALE": {
        "default": 4.0, "min": 0.5, "max": 20.0, "step": 0.5,
        "modulatable": True, "mod_mode": "add"
    },
    "Y_SCALE": {
        "default": 4.0, "min": 0.5, "max": 20.0, "step": 0.5,
        "modulatable": True, "mod_mode": "add"
    },
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1,
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

        x_scale = self.params["X_SCALE"]
        y_scale = self.params["Y_SCALE"]
        speed   = self.params["SPEED"]
        cmap    = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("X_SCALE", "Y_SCALE", "SPEED"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "X_SCALE": x_scale = v
                elif key == "Y_SCALE": y_scale = v
                else: speed = v

        self.t += dt * speed

        w, h = self.width, self.height
        # Normalise scale so frequency feels consistent on matrices of different sizes
        sx = x_scale * math.pi / w
        sy = y_scale * math.pi / h
        t = self.t

        frame = []
        for y in range(h):
            for x in range(w):
                a = math.sin(x * sx + t)
                b = math.cos(y * sy + t + a)
                val = int((a + b) * 64 + 128) & 255
                frame.append(palette_color(cmap, val) + (0,))
        return frame
