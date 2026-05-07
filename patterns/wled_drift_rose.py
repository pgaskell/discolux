# WLED "Drift Rose" effect — port of mode_2DDriftRose()
# Original: "Drift Rose@Blur,,,,,Smear;;!;2"
# Rotating rose (rhodonea) curve that slowly drifts, with optional blur/smear.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, fade_to_black, blur2d, move_x, move_y
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 4, "min": 0, "max": 20, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "PETALS": {
        "default": 4, "min": 1, "max": 8, "step": 1,
        "modulatable": False, "mod_mode": "add"
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
        self._last  = time.time()
        self.t      = 0.0
        self._frame = [(0, 0, 0, 0)] * (width * height)

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self._last
        self._last = now

        speed  = self.params["SPEED"]
        blur   = int(self.params["BLUR"])
        k      = int(self.params["PETALS"])
        cmap   = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt * speed

        w, h = self.width, self.height
        t    = self.t

        if len(self._frame) != w * h:
            self._frame = [(0, 0, 0, 0)] * (w * h)

        # Fade previous frame
        fade_to_black(self._frame, w, h, 30)

        # Rose curve: r = cos(k * theta), draw many sample points
        cx = (w - 1) / 2.0
        cy = (h - 1) / 2.0
        radius = min(cx, cy) * 0.95
        steps  = max(200, w * h * 2)
        for i in range(steps):
            theta  = i / steps * 2 * math.pi * k + t
            r      = radius * math.cos(k * (i / steps * math.pi + t * 0.5))
            px = cx + r * math.cos(theta)
            py = cy + r * math.sin(theta)
            xi = int(px + 0.5)
            yi = int(py + 0.5)
            if 0 <= xi < w and 0 <= yi < h:
                hue = int((theta / (2 * math.pi) * 255 + t * 40)) & 255
                color = palette_color(cmap, hue)
                idx = yi * w + xi
                r0, g0, b0, _ = self._frame[idx]
                self._frame[idx] = (
                    min(255, r0 + color[0] // 2),
                    min(255, g0 + color[1] // 2),
                    min(255, b0 + color[2] // 2),
                    0
                )

        if blur:
            blur2d(self._frame, w, h, blur * 2)

        return list(self._frame)
