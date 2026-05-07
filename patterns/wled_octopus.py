# WLED "Octopus" effect — port of mode_2Doctopus()
# Original: "Octopus@!,,Offset X,Offset Y,Legs,fasttan;;!;2"
# Rotating tentacle/leg pattern in polar coordinates.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "OFFSET_X": {
        "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "OFFSET_Y": {
        "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "LEGS": {
        "default": 4, "min": 1, "max": 16, "step": 1,
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

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        speed    = self.params["SPEED"]
        offset_x = self.params["OFFSET_X"]
        offset_y = self.params["OFFSET_Y"]
        legs     = max(1, int(self.params["LEGS"]))
        cmap     = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("SPEED", "OFFSET_X", "OFFSET_Y", "LEGS"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED":    speed = v
                elif key == "OFFSET_X": offset_x = v
                elif key == "OFFSET_Y": offset_y = v
                else:                 legs = max(1, int(v))

        self.t += dt * speed

        w, h = self.width, self.height
        cx = (w - 1) / 2.0 + offset_x * w / 2
        cy = (h - 1) / 2.0 + offset_y * h / 2
        max_r = math.hypot(w / 2, h / 2)
        t = self.t

        frame = []
        for y in range(h):
            for x in range(w):
                dx, dy = x - cx, y - cy
                r   = math.hypot(dx, dy) / max_r       # 0..1
                ang = math.atan2(dy, dx)                # -π..π

                # Tentacle pattern: angular distance to nearest leg
                leg_phase = (ang * legs / (2 * math.pi) + t) % 1.0
                # Distance from centre of nearest tentacle
                leg_dist = abs(leg_phase - round(leg_phase)) * 2.0  # 0..1

                # Glow along tentacle edges, fade with radius
                intensity = max(0.0, 1.0 - leg_dist * 2.5) * (1.0 - r)
                # Colour: step through palette along radius
                hue = int((r * 200 + ang * 128 / math.pi + t * 80)) & 255
                color = palette_color(cmap, hue)
                bri = intensity ** 0.7
                frame.append((int(color[0] * bri), int(color[1] * bri), int(color[2] * bri), 0))
        return frame
