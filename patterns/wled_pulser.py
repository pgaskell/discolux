# WLED "Pulser" effect — port of mode_2DPulser()
# Original: "Pulser@!,Blur;;!;2"
# Pulsing rings emanating from center.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import blur2d, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 32, "min": 0, "max": 200, "step": 1,
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
        self.t = 0.0
        self._last = time.time()

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        speed = self.params["SPEED"]
        blur  = self.params["BLUR"]
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("SPEED", "BLUR"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED": speed = v
                else:              blur  = int(v)

        self.t += dt * speed

        w, h = self.width, self.height
        cx, cy  = (w - 1) / 2.0, (h - 1) / 2.0
        max_r   = math.hypot(cx, cy)
        t       = self.t

        frame = []
        for y in range(h):
            for x in range(w):
                r   = math.hypot(x - cx, y - cy) / max_r  # 0..1
                # Pulsating wave: multiple concentric rings
                wave = math.sin(r * 12.0 - t * 6.0)
                # Add a second harmonic for complexity
                wave += 0.5 * math.sin(r * 6.0 - t * 3.5 + 0.8)
                wave /= 1.5
                hue = int((wave * 0.5 + 0.5) * 200 + t * 30) & 255
                bri = max(0.0, (wave * 0.5 + 0.5) ** 1.5)
                color = palette_color(cmap, hue)
                r_ = int(color[0] * bri)
                g_ = int(color[1] * bri)
                b_ = int(color[2] * bri)
                frame.append((r_, g_, b_, 0))

        blur2d(frame, w, h, blur)
        return frame
