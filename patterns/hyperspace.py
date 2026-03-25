import time, math, random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "STAR_COUNT": {
        "default": 60, "min": 10, "max": 200, "step": 1,
        "modulatable": True
    },
    "SPEED": {
        "default": 0.25, "min": 0.01, "max": 2.0, "step": 0.01,
        "modulatable": True
    },
    "TRAIL": {
        "default": 0.7, "min": 0.1, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.12, "min": 0.0, "max": 1.0, "step": 0.01,
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
        self.stars = []
        self._init_stars(width, height, PARAMS["STAR_COUNT"]["default"])

    def _init_stars(self, width, height, count):
        self.stars = []
        for _ in range(int(count)):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0.1, 0.5)
            self.stars.append({
                "angle": angle,
                "dist": dist,
                "speed": random.uniform(0.8, 1.2),
                "hue": random.random()
            })

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        self.t += dt

        star_count = self.params["STAR_COUNT"]
        speed = self.params["SPEED"]
        trail = self.params["TRAIL"]
        color_cycle = self.params["COLOR_CYCLE"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "STAR_COUNT": star_count = int(mod)
                elif key == "SPEED": speed = mod
                elif key == "TRAIL": trail = mod
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        max_radius = math.hypot(cx, cy)
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        # Re-init stars if count changes
        if len(self.stars) != int(star_count):
            self._init_stars(w, h, star_count)

        # Fading trail buffer
        if not hasattr(self, "trail_buf") or len(self.trail_buf) != w * h:
            self.trail_buf = [(0, 0, 0)] * (w * h)
        else:
            # Fade trail
            faded = []
            for r, g, b in self.trail_buf:
                faded.append((
                    int(r * trail),
                    int(g * trail),
                    int(b * trail)
                ))
            self.trail_buf = faded

        # Move and draw stars
        for star in self.stars:
            # Move star outward
            star["dist"] += dt * speed * star["speed"] * 0.5
            if star["dist"] > 1.0:
                star["angle"] = random.uniform(0, 2 * math.pi)
                star["dist"] = random.uniform(0.1, 0.2)
                star["speed"] = random.uniform(0.8, 1.2)
                star["hue"] = random.random()

            # Star position
            px = int(cx + math.cos(star["angle"]) * star["dist"] * max_radius)
            py = int(cy + math.sin(star["angle"]) * star["dist"] * max_radius)
            if 0 <= px < w and 0 <= py < h:
                hue = (star["hue"] + self.t * color_cycle) % 1.0
                if lut:
                    lut_idx = int(hue * (len(lut) - 1))
                    r, g, b = lut[lut_idx]
                else:
                    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    r = int(r * 255)
                    g = int(g * 255)
                    b = int(b * 255)
                idx = py * w + px
                self.trail_buf[idx] = (r, g, b)

        # Build frame
        frame = []
        for rgb in self.trail_buf:
            frame.append((rgb[0], rgb[1], rgb[2], 0))
        return frame