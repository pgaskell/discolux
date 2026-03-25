import time, math, random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "BLOBS": {
        "default": 3, "min": 1, "max": 8, "step": 1,
        "modulatable": True
    },
    "SPEED": {
        "default": 0.13, "min": 0.01, "max": 0.5, "step": 0.01,
        "modulatable": True
    },
    "SIZE": {
        "default": 0.22, "min": 0.05, "max": 0.5, "step": 0.01,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.18, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "COLORMAP": {
        "default": "hot", "options": ["hot"] + list(COLORMAPS.keys()),
        "modulatable": False
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.last_time = time.time()
        self.t = 0.0
        self._init_blobs(width, height, PARAMS["BLOBS"]["default"])

    def _init_blobs(self, width, height, count):
        self.blobs = []
        for _ in range(int(count)):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0.2, 0.45)
            speed = random.uniform(0.5, 1.5)
            phase = random.uniform(0, 2 * math.pi)
            self.blobs.append({
                "angle": angle,
                "radius": radius,
                "speed": speed,
                "phase": phase
            })

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        self.t += dt

        blobs = self.params["BLOBS"]
        speed = self.params["SPEED"]
        size = self.params["SIZE"]
        color_cycle = self.params["COLOR_CYCLE"]
        colormap = self.params.get("COLORMAP", "hot")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "BLOBS": blobs = int(mod)
                elif key == "SPEED": speed = mod
                elif key == "SIZE": size = mod
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        lut = COLORMAPS.get(colormap) if colormap in COLORMAPS else COLORMAPS.get("hot", None)

        # Re-init blobs if count changes
        if not hasattr(self, "blobs") or len(self.blobs) != int(blobs):
            self._init_blobs(w, h, blobs)

        # Animate blobs
        for blob in self.blobs:
            blob["angle"] += dt * speed * blob["speed"]
            blob["angle"] %= 2 * math.pi

        frame = []
        for y in range(h):
            for x in range(w):
                val = 0.0
                for blob in self.blobs:
                    # Blob center moves in a circle
                    bx = cx + math.cos(blob["angle"] + blob["phase"]) * blob["radius"] * cx
                    by = cy + math.sin(blob["angle"] + blob["phase"]) * blob["radius"] * cy
                    dist = math.hypot(x - bx, y - by)
                    v = max(0.0, 1.0 - dist / (size * min(w, h)))
                    val += v
                val = min(val, 1.0)
                hue = (self.t * color_cycle + val * 0.1) % 1.0
                if lut:
                    lut_idx = int(hue * (len(lut) - 1))
                    r_c, g_c, b_c = lut[lut_idx]
                    r_c = int(r_c * val)
                    g_c = int(g_c * val)
                    b_c = int(b_c * val)
                else:
                    r_c, g_c, b_c = colorsys.hsv_to_rgb(hue, 1.0, val)
                    r_c = int(r_c * 255)
                    g_c = int(g_c * 255)
                    b_c = int(b_c * 255)
                frame.append((r_c, g_c, b_c, 0))
        return frame