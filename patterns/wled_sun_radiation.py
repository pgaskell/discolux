# WLED "Sun Radiation" effect — port of mode_2DSunradiation()
# Original: "Sun Radiation@Variance,Brightness;;;2"
# By ldirko. Bump map of a sphere mapped onto the canvas.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

PARAMS = {
    "VARIANCE": {
        "default": 0.5, "min": 0.01, "max": 2.0, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "BRIGHTNESS": {
        "default": 0.8, "min": 0.1, "max": 1.0, "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "fire", "options": list(COLORMAPS.keys())
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
        self.t += dt

        variance   = self.params["VARIANCE"]
        brightness = self.params["BRIGHTNESS"]
        cmap = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("VARIANCE", "BRIGHTNESS"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "VARIANCE":   variance   = v
                else:                   brightness = v

        w, h = self.width, self.height
        # Build a bump map: small random offsets give a "solar" texture
        # We use a time-varying combination of sines to mimic the bump map.
        t = self.t
        frame = []
        for y in range(h):
            vy = (y - h / 2.0) / (h / 2.0)
            for x in range(w):
                vx = (x - w / 2.0) / (w / 2.0)
                # Radial distance from center
                r = math.sqrt(vx * vx + vy * vy + 1e-9)
                # Spherical bump field
                s1 = math.sin(vx * 4.0 * variance + t * 1.1)
                s2 = math.sin(vy * 4.0 * variance - t * 0.9)
                s3 = math.cos((vx + vy) * 3.0 * variance + t * 0.7)
                bump = (s1 + s2 + s3) / 3.0  # -1..1
                # Add radial glow
                glow = max(0.0, 1.0 - r * 1.2)
                intensity = (bump * 0.5 + 0.5) * glow * brightness
                val = int(max(0, min(255, intensity * 255)))
                frame.append(self._sample_cmap(cmap, val) + (0,))
        return frame

    @staticmethod
    def _sample_cmap(cmap, pos):
        if not cmap:
            return (0, 0, 0)
        idx = pos * (len(cmap) - 1) / 255.0
        lo  = int(idx)
        hi  = min(lo + 1, len(cmap) - 1)
        f   = idx - lo
        a, b = cmap[lo], cmap[hi]
        return (int(a[0]+f*(b[0]-a[0])), int(a[1]+f*(b[1]-a[1])), int(a[2]+f*(b[2]-a[2])))
