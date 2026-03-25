import time, math, random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "AXES": {
        "default": 6, "min": 2, "max": 12, "step": 1,
        "modulatable": True
    },
    "ROTATION_SPEED": {
        "default": 0.15, "min": -1.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "COMPLEXITY": {
        "default": 2.0, "min": 0.5, "max": 8.0, "step": 0.1,
        "modulatable": True
    },
    "COLORMAP": {
        "default": "none", "options": ["none"] + list(COLORMAPS.keys()),
        "modulatable": False
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.last_time = time.time()
        self.t = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        self.t += dt

        # Params
        axes = int(self.params["AXES"])
        rotation_speed = self.params["ROTATION_SPEED"]
        color_cycle = self.params["COLOR_CYCLE"]
        complexity = self.params["COMPLEXITY"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "AXES": axes = int(mod)
                elif key == "ROTATION_SPEED": rotation_speed = mod
                elif key == "COLOR_CYCLE": color_cycle = mod
                elif key == "COMPLEXITY": complexity = mod

        w, h = self.width, self.height
        cx, cy = (w-1)/2.0, (h-1)/2.0

        angle_offset = self.t * rotation_speed * math.pi * 2
        color_offset = (self.t * color_cycle) % 1.0
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        frame = []
        for y in range(h):
            for x in range(w):
                dx = x - cx
                dy = y - cy
                r = math.hypot(dx, dy)
                theta = math.atan2(dy, dx) + angle_offset

                # Mirror into sector
                sector_angle = math.pi * 2 / axes
                theta = theta % (sector_angle * 2)
                if theta > sector_angle:
                    theta = sector_angle * 2 - theta

                # Generate pattern in the sector
                # Example: radial + angular waves
                v = math.sin(r * complexity + math.cos(theta * complexity + self.t))
                v = (v + 1) / 2  # Normalize to 0..1

                hue = (theta / (sector_angle * 2) + color_offset) % 1.0

                if lut:
                    lut_idx = int(hue * (len(lut) - 1))
                    r_c, g_c, b_c = lut[lut_idx]
                    r_c = int(r_c * v)
                    g_c = int(g_c * v)
                    b_c = int(b_c * v)
                else:
                    r_c, g_c, b_c = colorsys.hsv_to_rgb(hue, 1.0, v)
                    r_c = int(r_c * 255)
                    g_c = int(g_c * 255)
                    b_c = int(b_c * 255)
                frame.append((r_c, g_c, b_c, 0))
        return frame