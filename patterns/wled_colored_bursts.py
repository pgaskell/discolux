# WLED "Colored Bursts" effect — port of mode_2DColoredBursts()
# Original: "Colored Bursts@Speed,Blur,,,Lines;!,!;!;2;c2=8"
# Lines radiate from a pulsing centre point, coloured per palette.
import math
import time
import random
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, fade_to_black, blur2d, draw_line, beatsin8
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.4, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 4, "min": 0, "max": 20, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "NUM_LINES": {
        "default": 8, "min": 2, "max": 20, "step": 1,
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
        self._frame = [(0, 0, 0, 0)] * (width * height)
        self._last  = time.time()
        self.t      = 0.0
        self._hue_offset = 0

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self._last
        self._last = now

        speed     = self.params["SPEED"]
        blur      = int(self.params["BLUR"])
        num_lines = max(2, min(20, int(self.params["NUM_LINES"])))
        cmap      = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t    += dt * speed
        t          = self.t

        w, h = self.width, self.height
        if len(self._frame) != w * h:
            self._frame = [(0, 0, 0, 0)] * (w * h)

        fade_to_black(self._frame, w, h, 60)

        # Hub centre oscillates
        cx = beatsin8(7,  0, w - 1, t=t)
        cy = beatsin8(9,  0, h - 1, t=t)

        for i in range(num_lines):
            # Each line: angle and length vary with time and index
            angle = (i / num_lines) * 2 * math.pi + t * 0.7
            length = (w + h) * 0.5 * 0.9
            ex = int(cx + length * math.cos(angle))
            ey = int(cy + length * math.sin(angle))
            hue = (self._hue_offset + i * 256 // num_lines) & 255
            color = palette_color(cmap, hue)
            draw_line(self._frame, w, h, cx, cy, ex, ey, color)

        self._hue_offset = (self._hue_offset + 1) & 255

        if blur:
            blur2d(self._frame, w, h, blur * 2)

        return list(self._frame)
