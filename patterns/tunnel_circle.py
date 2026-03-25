import time, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "ZOOM_SPEED": {
        "default": 0.25, "min": 0.01, "max": 2.0, "step": 0.01,
        "modulatable": True
    },
    "SPACING": {
        "default": 3.0, "min": 1.0, "max": 10.0, "step": 0.1,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.18, "min": 0.0, "max": 1.0, "step": 0.01,
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
        zoom_speed = self.params["ZOOM_SPEED"]
        spacing = self.params["SPACING"]
        color_cycle = self.params["COLOR_CYCLE"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "ZOOM_SPEED": zoom_speed = mod
                elif key == "SPACING": spacing = mod
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        # Animate tunnel
        phase = (self.t * zoom_speed) % spacing

        frame = []
        for y in range(h):
            for x in range(w):
                dx = x - cx
                dy = y - cy
                dist = math.hypot(dx, dy)

                # Tunnel rings (circles)
                ring = (dist - phase) / spacing
                ring_idx = int(ring)
                fade = 1.0 - abs(ring - ring_idx)
                fade = max(0.0, min(1.0, fade))

                # Color
                hue = (ring_idx * 0.08 + self.t * color_cycle) % 1.0

                if fade > 0.05:
                    if lut:
                        lut_idx = int(hue * (len(lut) - 1))
                        r_c, g_c, b_c = lut[lut_idx]
                        r_c = int(r_c * fade)
                        g_c = int(g_c * fade)
                        b_c = int(b_c * fade)
                    else:
                        r_c, g_c, b_c = colorsys.hsv_to_rgb(hue, 1.0, fade)
                        r_c = int(r_c * 255)
                        g_c = int(g_c * 255)
                        b_c = int(b_c * 255)
                    frame.append((r_c, g_c, b_c, 0))
                else:
                    frame.append((0, 0, 0, 0))
        return frame