import time, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "WAVES": {
        "default": 4, "min": 1, "max": 12, "step": 1,
        "modulatable": True
    },
    "SPEED": {
        "default": 0.20, "min": 0.01, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "TWIST": {
        "default": 1.5, "min": 0.1, "max": 6.0, "step": 0.1,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.16, "min": 0.0, "max": 1.0, "step": 0.01,
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

        waves = self.params["WAVES"]
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
                if key == "WAVES": waves = int(mod)
                elif key == "SPEED": speed = mod
                elif key == "TWIST": twist = mod
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        phase = self.t * speed * 2 * math.pi

        frame = []
        for y in range(h):
            for x in range(w):
                dx = x - cx
                dy = y - cy
                r = math.hypot(dx, dy)
                theta = math.atan2(dy, dx)
                # Polar_Waves: radiating and twisting waves in polar coordinates
                angle = r * waves + theta * twist + phase
                v = (math.sin(angle) + 1) / 2
                v = v ** 1.6  # contrast

                hue = (r / max(cx, cy) + self.t * color_cycle) % 1.0

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