# WLED "Sindots" effect — port of mode_2DSindots()
# Original: "Sindots@!,Dot distance,Fade rate,Blur,,Smear;;!;2"
# By ldirko — dots arranged by intersecting sine waves.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import blur2d, fade_to_black, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "DOT_DISTANCE": {
        "default": 4.0, "min": 1.0, "max": 16.0, "step": 0.5,
        "modulatable": True, "mod_mode": "add"
    },
    "FADE_RATE": {
        "default": 40, "min": 0, "max": 200, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 16, "min": 0, "max": 200, "step": 1,
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

        speed    = self.params["SPEED"]
        dot_dist = self.params["DOT_DISTANCE"]
        fade     = self.params["FADE_RATE"]
        blur     = self.params["BLUR"]
        cmap     = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("SPEED", "DOT_DISTANCE", "FADE_RATE", "BLUR"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED":        speed = v
                elif key == "DOT_DISTANCE": dot_dist = v
                elif key == "FADE_RATE":  fade = int(v)
                else:                     blur = int(v)

        self.t += dt * speed

        w, h = self.width, self.height
        t = self.t

        fade_to_black(self._frame, w, h, fade)

        # Place dots where sine waves intersect
        freq = 2.0 * math.pi / max(dot_dist, 0.5)
        for y in range(h):
            for x in range(w):
                sx = math.sin(x * freq + t * 2.0)
                sy = math.sin(y * freq - t * 1.5)
                # Both close to peak → dot
                dot = sx * sy
                if dot > 0.6:
                    hue = int((x + y) * 255 / (w + h) + t * 60) & 255
                    color = palette_color(cmap, hue)
                    bri = (dot - 0.6) / 0.4
                    i = y * w + x
                    self._frame[i] = (
                        min(255, self._frame[i][0] + int(color[0] * bri)),
                        min(255, self._frame[i][1] + int(color[1] * bri)),
                        min(255, self._frame[i][2] + int(color[2] * bri)),
                        0)

        if blur > 0:
            blur2d(self._frame, w, h, blur)
        return list(self._frame)
