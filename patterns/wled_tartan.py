# WLED "Tartan" effect — port of mode_2Dtartan()
# Original: "Tartan@X scale,Y scale,,,Sharpness;;!;2"
# By Elliott Kember — plaid / tartan colour pattern.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color
from colormaps import COLORMAPS

PARAMS = {
    "X_SCALE": {
        "default": 3, "min": 1, "max": 20, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "Y_SCALE": {
        "default": 3, "min": 1, "max": 20, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "SHARPNESS": {
        "default": 3.0, "min": 0.5, "max": 10.0, "step": 0.5,
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
        self.t += dt

        x_scale   = self.params["X_SCALE"]
        y_scale   = self.params["Y_SCALE"]
        sharpness = self.params["SHARPNESS"]
        cmap = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("X_SCALE", "Y_SCALE", "SHARPNESS"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "X_SCALE": x_scale = v
                elif key == "Y_SCALE": y_scale = v
                else: sharpness = v

        w, h = self.width, self.height
        t = self.t

        frame = []
        for y in range(h):
            for x in range(w):
                # Two sets of stripes (horizontal & vertical) multiplied
                sx = (math.sin(x * x_scale * math.pi / w + t * 0.5) + 1.0) * 0.5
                sy = (math.sin(y * y_scale * math.pi / h - t * 0.4) + 1.0) * 0.5
                # Raise to power for sharpness
                cx = sx ** sharpness
                cy = sy ** sharpness
                # Combine and map to hue
                combined = (cx + cy) * 0.5
                hue_x = int(x * 256 / w * x_scale) & 255
                hue_y = int(y * 256 / h * y_scale + 128) & 255
                hue   = int((hue_x + hue_y) / 2 * combined) & 255
                bri   = combined
                color = palette_color(cmap, hue)
                frame.append((int(color[0]*bri), int(color[1]*bri), int(color[2]*bri), 0))
        return frame
