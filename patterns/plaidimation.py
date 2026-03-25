# patterns/plaidimation.py
import time, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "BANDS": {
        "default": 6, "min": 2, "max": 16, "step": 1,
        "modulatable": True
    },
    "SPEED": {
        "default": 0.18, "min": 0.01, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "BAND_WIDTH": {
        "default": 0.5, "min": 0.1, "max": 2.0, "step": 0.01,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.12, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "COLORMAP": {
        "default": "none", "options": ["none"] + list(COLORMAPS.keys()),
        "modulatable": False
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.last_time = time.time()
        self.t = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        self.t += dt

        bands = int(self.params["BANDS"])
        speed = self.params["SPEED"]
        band_width = self.params["BAND_WIDTH"]
        color_cycle = self.params["COLOR_CYCLE"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "BANDS": bands = int(mod)
                elif key == "SPEED": speed = mod
                elif key == "BAND_WIDTH": band_width = mod
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        # Animation phase
        phase = self.t * speed

        frame = []
        for y in range(h):
            for x in range(w):
                # Horizontal and vertical band values
                fx = (x / w) * bands + phase
                fy = (y / h) * bands - phase

                # Use a smooth band shape (cosine)
                band_x = (math.cos(fx * math.pi * band_width) + 1) / 2
                band_y = (math.cos(fy * math.pi * band_width) + 1) / 2

                # Plaid: combine bands (multiply for more contrast, add for softer)
                v = band_x * band_y

                # Color
                hue = (fx * 0.1 + fy * 0.13 + self.t * color_cycle) % 1.0

                if lut:
                    lut_idx = int(hue * (len(lut) - 1))
                    r, g, b = lut[lut_idx]
                    r = int(r * v)
                    g = int(g * v)
                    b = int(b * v)
                else:
                    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, v)
                    r = int(r * 255)
                    g = int(g * 255)
                    b = int(b * 255)
                frame.append((r, g, b, 0))
        return frame
