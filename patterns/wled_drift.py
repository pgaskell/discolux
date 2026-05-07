# WLED "Drift" effect — port of mode_2DDrift()
# Original: "Drift@Rotation speed,Blur,,,,Twin,Smear;;!;2;ix=0"
# By Stepko — concentric polar-coordinate rings that rotate.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import blur2d, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "ROTATION_SPEED": {
        "default": 1.0, "min": -5.0, "max": 5.0, "step": 0.1,
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
        self.step = 0
        self._last = time.time()

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        rot_speed = self.params["ROTATION_SPEED"]
        blur      = self.params["BLUR"]
        cmap = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("ROTATION_SPEED", "BLUR"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "ROTATION_SPEED": rot_speed = v
                else:                       blur = int(v)

        self.step += dt * rot_speed * 50.0
        step = self.step

        w, h = self.width, self.height
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        cr = math.hypot(cx, cy) + 1.0

        frame = []
        for y in range(h):
            for x in range(w):
                # hue = angle/π*128 + step*speed + 16*distance/CR
                angle = math.atan2(y - cy, x - cx)
                dist  = math.hypot(x - cx, y - cy)
                hue   = int(128.0 * angle / math.pi + step + 16.0 * dist / cr) & 255
                frame.append(palette_color(cmap, hue) + (0,))

        blur2d(frame, w, h, blur)
        return frame
