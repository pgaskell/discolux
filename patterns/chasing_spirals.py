import time, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "SPIRALS": {
        "default": 3, "min": 1, "max": 8, "step": 1,
        "modulatable": True
    },
    "SPEED": {
        "default": 0.18, "min": 0.01, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "TWIST": {
        "default": 2.0, "min": 0.5, "max": 8.0, "step": 0.1,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.15, "min": 0.0, "max": 1.0, "step": 0.01,
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

        spirals = self.params["SPIRALS"]
        speed = self.params["SPEED"]
        twist = self.params["TWIST"]
        color_cycle = self.params["COLOR_CYCLE"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "SPIRALS": spirals = int(mod)
                elif key == "SPEED": speed = mod
                elif key == "TWIST": twist = mod
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        # Animation phase
        phase = self.t * speed * 2 * math.pi

        frame = []
        for y in range(h):
            for x in range(w):
                dx = x - cx
                dy = y - cy
                r = math.hypot(dx, dy)
                theta = math.atan2(dy, dx)
                # Spiral pattern: sum several rotating spirals
                v = 0.0
                for s in range(spirals):
                    angle = theta + phase + s * (2 * math.pi / spirals)
                    spiral = math.sin(angle + r * twist)
                    v += (spiral + 1) / 2
                v /= spirals
                v = v ** 2  # sharpen
                v *= 5.0    # increase brightness (try 1.5, 2.0, or higher if needed)
                v = min(v, 1.0)
                # Color
                hue = (theta / (2 * math.pi) + self.t * color_cycle) % 1.0

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