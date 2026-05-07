# WLED "Frizzles" effect — port of mode_2DFrizzles()
# Original: "Frizzles@X freq,Y freq;;!;2"
# Curly lines drawn across the matrix, palette coloured.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, draw_line, sin8, cos8, beatsin8
from colormaps import COLORMAPS

PARAMS = {
    "X_FREQ": {
        "default": 0.4, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "Y_FREQ": {
        "default": 0.3, "min": 0.05, "max": 3.0, "step": 0.05,
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
        self.t     = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self._last
        self._last = now

        xfreq = self.params["X_FREQ"]
        yfreq = self.params["Y_FREQ"]
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt
        t = self.t

        w, h = self.width, self.height
        frame = [(0, 0, 0, 0)] * (w * h)

        # WLED draws horizontal lines where Y is driven by sin(x * xfreq + t)
        # and vertical lines where X is driven by sin(y * yfreq + t)
        # They are overlaid with palette colours keyed to position.
        for x in range(w):
            y = int((sin8(int(x * xfreq * 16 + t * 48) & 255) / 255.0) * (h - 1))
            y = max(0, min(h - 1, y))
            hue = int(x * 256 / w + t * 60) & 255
            color = palette_color(cmap, hue)
            idx = y * w + x
            frame[idx] = (color[0], color[1], color[2], 0)

        for y in range(h):
            x = int((cos8(int(y * yfreq * 16 + t * 40) & 255) / 255.0) * (w - 1))
            x = max(0, min(w - 1, x))
            hue = int(y * 256 / h + t * 80) & 255
            color = palette_color(cmap, hue)
            idx = y * w + x
            r = min(255, frame[idx][0] + color[0])
            g = min(255, frame[idx][1] + color[1])
            b = min(255, frame[idx][2] + color[2])
            frame[idx] = (r, g, b, 0)

        return frame
