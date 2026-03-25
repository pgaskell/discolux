import time, math, random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "HEART_COUNT": {
        "default": 3, "min": 1, "max": 8, "step": 1,
        "modulatable": True
    },
    "BEAT_SPEED": {
        "default": 1.0, "min": 0.2, "max": 3.0, "step": 0.01,
        "modulatable": True
    },
    "SIZE": {
        "default": 0.25, "min": 0.05, "max": 0.5, "step": 0.01,
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

def heart_shape(x, y):
    # Improved heart shape: x, y in [-1, 1]
    # (x^2 + y^2 - 1)^3 - x^2 * y^3 <= 0 is "blobby"
    # Use a sharper implicit heart curve:
    return (x**2 + (5/4)*y**2 - 1)**3 - x**2 * y**3 <= 0

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.last_time = time.time()
        self.t = 0.0
        # Randomize heart positions
        self.heart_offsets = []
        self._init_hearts(width, height, PARAMS["HEART_COUNT"]["default"])

    def _init_hearts(self, width, height, count):
        self.heart_offsets = []
        for _ in range(int(count)):
            ox = random.uniform(0.2, 0.8)
            oy = random.uniform(0.2, 0.8)
            self.heart_offsets.append((ox, oy, random.random()))

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        self.t += dt

        heart_count = self.params["HEART_COUNT"]
        beat_speed = self.params["BEAT_SPEED"]
        size = self.params["SIZE"]
        color_cycle = self.params["COLOR_CYCLE"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "HEART_COUNT": heart_count = int(mod)
                elif key == "BEAT_SPEED": beat_speed = mod
                elif key == "SIZE": size = mod
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        # Re-init hearts if count changes
        if len(self.heart_offsets) != int(heart_count):
            self._init_hearts(w, h, heart_count)

        # Animate beating (scale factor oscillates)
        beat = (math.sin(self.t * beat_speed * 2 * math.pi) + 1) / 2  # 0..1
        scale = size * (0.8 + 0.4 * beat)

        frame = []
        for y in range(h):
            for x in range(w):
                val = 0.0
                hue = 0.0
                for i, (ox, oy, h_offset) in enumerate(self.heart_offsets):
                    # Center of heart in pixel coords
                    cx = ox * (w - 1)
                    cy = oy * (h - 1)
                    # Map pixel to [-1,1] heart space
                    hx = (x - cx) / (scale * w)
                    hy = (y - cy) / (scale * h)
                    if heart_shape(hx, hy):
                        # Distance from center for soft edge
                        d = math.hypot(hx, hy)
                        v = max(0.0, 1.0 - d)
                        if v > val:
                            val = v
                            hue = (h_offset + self.t * color_cycle) % 1.0
                if val > 0:
                    if lut:
                        lut_idx = int(hue * (len(lut) - 1))
                        r, g, b = lut[lut_idx]
                        r = int(r * val)
                        g = int(g * val)
                        b = int(b * val)
                    else:
                        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, val)
                        r = int(r * 255)
                        g = int(g * 255)
                        b = int(b * 255)
                    frame.append((r, g, b, 0))
                else:
                    frame.append((0, 0, 0, 0))
        return frame