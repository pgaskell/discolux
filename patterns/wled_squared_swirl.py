# WLED "Squared Swirl" effect — port of mode_2Dsquaredswirl()
# Original: "Squared Swirl@,Fade,,,Blur;;!;2"
# By Mark Kriegsman — four rotating squares generating a swirl.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import blur2d, fade_to_black, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "FADE": {
        "default": 30, "min": 0, "max": 200, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 20, "min": 0, "max": 200, "step": 1,
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
        self.t   = 0.0
        self._last = time.time()
        self._frame = [(0, 0, 0, 0)] * (width * height)

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now
        self.t += dt

        fade = self.params["FADE"]
        blur = self.params["BLUR"]
        cmap = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("FADE", "BLUR"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "FADE": fade = int(v)
                else:             blur = int(v)

        w, h = self.width, self.height
        t = self.t

        fade_to_black(self._frame, w, h, fade)

        # Four rotating "point" sources tracing squares
        for k in range(4):
            angle   = t * (0.7 + k * 0.15) + k * math.pi / 2
            radius  = min(w, h) * 0.35
            cx      = w / 2.0 + math.cos(angle) * radius
            cy      = h / 2.0 + math.sin(angle) * radius

            xi = int(cx) % w
            yi = int(cy) % h
            hue = int((angle * 128 / math.pi + k * 64 + t * 30)) & 255
            color = palette_color(cmap, hue)
            self._frame[yi * w + xi] = color + (0,)

        blur2d(self._frame, w, h, blur)
        return list(self._frame)
