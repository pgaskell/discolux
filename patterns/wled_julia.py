# WLED "Julia" effect — port of mode_2DJulia()
# Original: "Julia@,Max iterations per pixel,X center,Y center,Area size,,Blur;!;!;2;ix=24,c1=128,c2=128,c3=16"
# Animated Julia set fractal (by Andrew Tuline).
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color
from colormaps import COLORMAPS

PARAMS = {
    "MAX_ITER": {
        "default": 24, "min": 5, "max": 60, "step": 1,
        "modulatable": False
    },
    "X_CENTER": {
        "default": 0.0, "min": -1.2, "max": 1.2, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "Y_CENTER": {
        "default": 0.0, "min": -0.8, "max": 1.0, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "AREA": {
        "default": 0.5, "min": 0.01, "max": 1.0, "step": 0.01,
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
        self._last = time.time()
        # Slowly drifting c parameter (real and imaginary parts)
        self.xcen  = 0.0
        self.ycen  = 0.0
        self.xymag = 0.5

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        max_iter = max(5, int(self.params["MAX_ITER"]))
        x_center = self.params["X_CENTER"]
        y_center = self.params["Y_CENTER"]
        area     = self.params["AREA"]
        cmap     = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("X_CENTER", "Y_CENTER", "AREA"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "X_CENTER": x_center = v
                elif key == "Y_CENTER": y_center = v
                else:                   area = v

        # Slowly drift center (WLED drifts c by tiny amounts each frame)
        drift = dt * 0.0001
        self.xcen  += (x_center - self.xcen)  * 0.05 + drift * 0.7
        self.ycen  += (y_center - self.ycen)  * 0.05 + drift * 0.5
        self.xymag += (area - self.xymag) * 0.05

        xcen  = max(-1.2, min(1.2, self.xcen))
        ycen  = max(-0.8, min(1.0, self.ycen))
        xymag = max(0.01, min(1.0, self.xymag))

        reAl = -0.94299   # typical Julia c values (can vary)
        imAg =  0.3162    # same

        xmin = xcen - xymag; xmax = xcen + xymag
        ymin = ycen - xymag; ymax = ycen + xymag
        xmin = max(-1.2, min(1.2, xmin)); xmax = max(-1.2, min(1.2, xmax))
        ymin = max(-0.8, min(0.8, ymin)); ymax = max(-0.8, min(0.8, ymax))

        w, h = self.width, self.height
        dx = (xmax - xmin) / max(w - 1, 1)
        dy = (ymax - ymin) / max(h - 1, 1)
        max_calc = 4.0

        frame = []
        y = ymin
        for _ in range(h):
            x = xmin
            for _ in range(w):
                a, b = x, y
                icount = 0
                while icount < max_iter:
                    aa = a * a
                    bb = b * b
                    if aa + bb > max_calc:
                        break
                    b = 2 * a * b + imAg
                    a = aa - bb + reAl
                    icount += 1
                if icount == max_iter:
                    frame.append((0, 0, 0, 0))
                else:
                    hue = int(icount * 255 / max_iter)
                    frame.append(palette_color(cmap, hue) + (0,))
                x += dx
            y += dy
        return frame
