# WLED "Plasma Ball" effect — port of mode_2DPlasmaball()
# Original: "Plasma Ball@Speed,,Fade,Blur;;!;2"
# Oscillating cross-hair lines that form a plasma globe.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import blur2d, fade_to_black, beatsin8, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "FADE": {
        "default": 50, "min": 0, "max": 200, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 24, "min": 0, "max": 200, "step": 1,
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
        self._frame = [(0, 0, 0, 0)] * (width * height)
        self.t = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        speed = self.params["SPEED"]
        fade  = self.params["FADE"]
        blur  = self.params["BLUR"]
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("SPEED", "FADE", "BLUR"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED": speed = v
                elif key == "FADE": fade = int(v)
                else:               blur = int(v)

        self.t += dt * speed

        w, h = self.width, self.height
        t = self.t

        fade_to_black(self._frame, w, h, fade)

        # Four sinusoidal lines sweep across the matrix
        bpm = speed * 40.0
        cx  = [int(beatsin8(bpm * (0.7 + i * 0.15), 0, w - 1, t=t)) for i in range(4)]
        cy  = [int(beatsin8(bpm * (0.5 + i * 0.2),  0, h - 1, t=t)) for i in range(4)]

        beat_hue = int(t * 20) & 255
        color = palette_color(cmap, beat_hue)

        # Draw cross-hairs at each {cx,cy}
        for k in range(4):
            x, y = cx[k], cy[k]
            # vertical and horizontal lines
            for ny in range(h):
                i = ny * w + x
                self._frame[i] = (min(255, self._frame[i][0] + color[0]),
                                   min(255, self._frame[i][1] + color[1]),
                                   min(255, self._frame[i][2] + color[2]), 0)
            for nx in range(w):
                i = y * w + nx
                self._frame[i] = (min(255, self._frame[i][0] + color[0]),
                                   min(255, self._frame[i][1] + color[1]),
                                   min(255, self._frame[i][2] + color[2]), 0)

        blur2d(self._frame, w, h, blur)
        return list(self._frame)
