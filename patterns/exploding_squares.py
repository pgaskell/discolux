import math
import colorsys
from .base import Pattern as BasePattern, apply_modulation

PARAMS = {
    "speed": {
        "default": 1.0,
        "min": 0.1,
        "max": 1.0,
        "step": 0.01,
        "modulatable": True
    },
    "size": {
        "default": 3.0,
        "min": 1.0,
        "max": 16.0,
        "step": 0.1,
        "modulatable": True
    },
    "color_shift": {
        "default": 0.0,
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "modulatable": True
    },
    "fade": {
        "default": 0.8,
        "min": 0.1,
        "max": 1.0,
        "step": 0.01,
        "modulatable": True
    }
}

def clamp(val, minv, maxv):
    return max(minv, min(maxv, val))

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.frame_count = 0

    def update_params(self, params):
        self.params.update(params)

    def render(self, lfo_signals=None):
        lfo_signals = lfo_signals or {}

        # For each parameter, check if modulation is active and apply if so
        def get_modulated(param):
            meta = self.param_meta[param]
            base = self.params[param]
            if meta.get("modulatable") and meta.get("mod_active", False):
                src = meta.get("mod_source")
                amt = lfo_signals.get(src, 0.0)
                return apply_modulation(base, meta, amt)
            else:
                return base

        speed = get_modulated("speed")
        size = get_modulated("size")
        color_shift = get_modulated("color_shift") % 1.0
        fade = get_modulated("fade")
        self.frame_count += 1

        frame = [(0, 0, 0, 0)] * (self.width * self.height)
        cx, cy = self.width / 2, self.height / 2
        t = (self.frame_count * speed / 10.0) % 1.0  # normalized time in [0,1)

        max_dist = math.hypot(cx, cy)
        for y in range(self.height):
            for x in range(self.width):
                dx = x + 0.5 - cx
                dy = y + 0.5 - cy
                dist = math.hypot(dx, dy)
                wave = (dist / (max_dist + 0.1) - t) % 1.0
                if wave < size / self.width:
                    hue = (wave + color_shift) % 1.0
                    r, g, b = [int(fade * c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
                    frame[y * self.width + x] = (r, g, b, 0)
        return frame