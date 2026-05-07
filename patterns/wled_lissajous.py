# WLED "Lissajous" effect — port of mode_2DLissajous()
# Original: "Lissajous@X frequency,Fade rate,Blur,,Speed,Smear;!;!;2;c1=0"
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import blur2d, fade_to_black, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "X_FREQUENCY": {
        "default": 3.0, "min": 1.0, "max": 10.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "FADE_RATE": {
        "default": 30, "min": 0, "max": 200, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 0, "min": 0, "max": 200, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1,
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
        self.t = 0.0
        self._frame = [(0, 0, 0, 0)] * (width * height)

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        x_freq = self.params["X_FREQUENCY"]
        fade   = self.params["FADE_RATE"]
        blur   = self.params["BLUR"]
        speed  = self.params["SPEED"]
        cmap   = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("X_FREQUENCY", "FADE_RATE", "BLUR", "SPEED"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "X_FREQUENCY": x_freq = v
                elif key == "FADE_RATE": fade = int(v)
                elif key == "BLUR":      blur = int(v)
                else:                    speed = v

        self.t += dt * speed

        w, h = self.width, self.height
        t = self.t

        fade_to_black(self._frame, w, h, fade)

        # Draw the Lissajous figure
        steps = 256
        for i in range(steps):
            phase = i * 2.0 * math.pi / steps
            xlocn = (1.0 + math.sin(x_freq * phase + t)) * (w - 1) / 2.0
            ylocn = (1.0 + math.sin(phase + t))          * (h - 1) / 2.0
            xi, yi = int(xlocn), int(ylocn)
            if 0 <= xi < w and 0 <= yi < h:
                hue = int(t * 50 + i) & 255
                color = palette_color(cmap, hue)
                self._frame[yi * w + xi] = color + (0,)

        if blur > 0:
            blur2d(self._frame, w, h, blur)
        return list(self._frame)
