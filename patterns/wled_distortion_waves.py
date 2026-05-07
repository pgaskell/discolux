# WLED "Distortion Waves" effect — port of mode_2Ddistortionwaves()
# Original: "Distortion Waves@!,Scale;;!;2"
# Sine-based coordinate distortion producing wavy interference patterns.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "SCALE": {
        "default": 0.4, "min": 0.05, "max": 2.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "AMPLITUDE": {
        "default": 0.4, "min": 0.05, "max": 2.0, "step": 0.05,
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

        speed = self.params["SPEED"]
        scale = self.params["SCALE"]
        amp   = self.params["AMPLITUDE"]
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt * speed
        t = self.t

        w, h = self.width, self.height
        frame = []

        # WLED algorithm: sum of four sine waves in distorted coordinates
        for y in range(h):
            for x in range(w):
                nx = x / w * 2 * math.pi * scale
                ny = y / h * 2 * math.pi * scale
                v  = (
                    math.sin(nx       + t) +
                    math.sin(ny       + t * 1.3) +
                    math.sin(nx + ny  + t * 0.7) +
                    math.sin(math.sqrt(nx * nx + ny * ny) + t * 0.9)
                ) * amp
                hue  = int((v / (4 * amp) + 0.5) * 255) & 255
                color = palette_color(cmap, hue)
                frame.append((color[0], color[1], color[2], 0))

        return frame
