# WLED "Waving Cell" effect — port of mode_2Dwavingcell()
# Original: "Waving Cell@!,Blur,Amplitude 1,Amplitude 2,Amplitude 3,,Flow;;!;2;ix=0"
# 5 sliders reduced to 4 by merging Amplitude 1+2 into AMPLITUDE_X and Amplitude 3 into AMPLITUDE_Y.
# The 3 original amplitudes control how far each sine-distortion axis bends the coordinates.
import math, time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, sin8, cos8, blur2d
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 0, "min": 0, "max": 20, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "AMPLITUDE_X": {
        "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "AMPLITUDE_Y": {
        "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.05,
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

        speed  = self.params["SPEED"]
        blur   = int(self.params["BLUR"])
        ax     = self.params["AMPLITUDE_X"]
        ay     = self.params["AMPLITUDE_Y"]
        cmap   = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt * speed
        t = self.t

        w, h = self.width, self.height
        # WLED uses: t = (strip.now * (speed+1)) >> 3
        # Per-pixel: cell value = sin8(x*amp1 + t) + sin8(y*amp2 + t) + sin8(...)
        # We use amplitude_x to scale the x contribution, amplitude_y for y.
        ax_scale = ax * 8.0
        ay_scale = ay * 8.0
        frame = []
        for y in range(h):
            for x in range(w):
                # Three sine components as in original:
                # sin8(x * c1 + t), sin8(y * c2 + t), sin8((x+y) * c3 + t)
                ti = int(t * 64) & 255
                v1 = sin8(int(x * ax_scale + ti) & 255)
                v2 = sin8(int(y * ay_scale + ti + 85) & 255)
                v3 = sin8(int((x + y) * (ax_scale + ay_scale) * 0.5 + ti + 170) & 255)
                val = (v1 + v2 + v3) // 3
                color = palette_color(cmap, val)
                frame.append((color[0], color[1], color[2], 0))

        if blur:
            blur2d(frame, w, h, blur * 2)

        return frame
