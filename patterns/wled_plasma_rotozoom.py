# WLED "Plasma Rotozoomer" effect — port of mode_2Dplasmarotozoom()
# Original: "Plasma Rotozoomer@Speed,Expand,,,;!;!;2"
# By ldirko — noise buffer rotozoom (rotation + zoom).
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import inoise8, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.0, "max": 2.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "EXPAND": {
        "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
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
        self.angle = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        speed  = self.params["SPEED"]
        expand = self.params["EXPAND"]
        cmap   = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("SPEED", "EXPAND"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED":  speed = v
                else:               expand = v

        self.angle -= dt * (0.03 + speed * 0.1)

        w, h = self.width, self.height
        angle = self.angle

        # Build noise source buffer once per frame (tile space)
        # We sample on-the-fly for memory efficiency
        ms = now * 1000.0

        # Scale factor: 1/(sin(a/2) contribution)
        f = (math.sin(angle / 2.0) + ((0.5 - expand) * 2.0) + 1.1) / 1.5
        f = max(0.1, f)
        cos_a = math.cos(angle) * f
        sin_a = math.sin(angle) * f

        frame = []
        for j in range(h):
            u1 = 0.0
            v1 = 0.0
            # Start offsets for this row (WLED accumulates per column)
            for i in range(w):
                u = int(abs(i * cos_a - j * sin_a)) % w
                v = int(abs(i * sin_a + j * cos_a)) % h
                # Sample noise at (u, v) with time offset
                val = inoise8(u, v, ms / 1000.0, scale=0.08)
                frame.append(palette_color(cmap, val) + (0,))
        return frame
