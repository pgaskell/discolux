# WLED "Polar Lights" effect — port of mode_2DPolarLights()
# Original: "Polar Lights@!,Scale,Phase;!,!;!;2;pal=71"
# By Kostyantyn Matviyevskyy — aurora-like noise curtains.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import inoise8, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "SCALE": {
        "default": 0.1, "min": 0.02, "max": 0.5, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "PHASE": {
        "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "aurora", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._last = time.time()
        self.t = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        speed = self.params["SPEED"]
        scale = self.params["SCALE"]
        phase = self.params["PHASE"]
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        # Fall back to first available colormap if 'aurora' not present
        if not cmap:
            cmap = list(COLORMAPS.values())[0]

        for key in ("SPEED", "SCALE", "PHASE"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED":  speed = v
                elif key == "SCALE": scale = v
                else:                phase = v

        self.t += dt * speed

        w, h = self.width, self.height
        t = self.t

        frame = []
        for y in range(h):
            # Polar-lights "curtain" — noise varies along x, attenuated at top/bottom
            fy = y / h
            # Weight: brightest in the top half, fading towards bottom
            curtain = max(0.0, 1.0 - abs(fy - 0.3) * 3.0)
            for x in range(w):
                # 2D noise gives the aurora shape
                n1 = inoise8(x, y,  t * 10.0, scale=scale)
                n2 = inoise8(x, y, -t * 7.0 + 128, scale=scale * 0.5)
                val = int((n1 * 0.7 + n2 * 0.3) * curtain)
                hue = int(n1 + phase * 255 + t * 30) & 255
                color = palette_color(cmap, hue)
                bri   = val / 255.0
                frame.append((int(color[0] * bri), int(color[1] * bri), int(color[2] * bri), 0))
        return frame
