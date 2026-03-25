import random, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "STAR_COUNT": {
        "default": 200,   "min":  20,   "max": 500,  "step": 10,
        "modulatable": True, "mod_mode": "replace"
    },
    "SPEED": {
        "default": 0.2,   "min": 0.01,  "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "FOV": {
        "default": 200.0, "min":  50.0, "max": 500.0,"step": 10.0,
        "modulatable": True, "mod_mode": "add"
    },
    "TWINKLE": {
        "default": 0.5,   "min":   0.0, "max":   1.0,"step": 0.01,
        "modulatable": True, "mod_mode": "scale"
    },
    "COLOR_SHIFT": {
        "default": 0.0,   "min":   0.0, "max":   1.0,"step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "rainbow",
        "options": list(COLORMAPS.keys())
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta   = PARAMS
        self.width        = width
        self.height       = height
        self.cx           = width  / 2.0
        self.cy           = height / 2.0
        self.frame_count  = 0
        # star list: each is [x, y, z]
        self._init_stars(int(self.params["STAR_COUNT"]), self.params["FOV"])

    def _init_stars(self, count, fov):
        self.stars = []
        for _ in range(count):
            x = random.uniform(-self.cx, self.cx)
            y = random.uniform(-self.cy, self.cy)
            z = random.uniform(1.0, fov)
            self.stars.append([x, y, z])
        self.prev_star_count = count

    def render(self, lfo_signals=None):
        self.frame_count += 1

        # --- 1) Read & modulate parameters ---
        # raw values
        star_count = int(self.params["STAR_COUNT"])
        speed      = self.params["SPEED"]
        fov        = self.params["FOV"]
        twinkle    = self.params["TWINKLE"]
        cshift     = self.params["COLOR_SHIFT"]

        # modulatable ones:
        for key in ("STAR_COUNT", "SPEED", "FOV", "TWINKLE", "COLOR_SHIFT"):
            meta = self.param_meta[key]
            if meta.get("modulatable", False) and meta.get("mod_active", False):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                val = apply_modulation(self.params[key], meta, amt)
                if key == "STAR_COUNT":
                    star_count = int(val)
                elif key == "SPEED":
                    speed = val
                elif key == "FOV":
                    fov = val
                elif key == "TWINKLE":
                    twinkle = val
                elif key == "COLOR_SHIFT":
                    cshift = val

        # if STAR_COUNT changed, re-init
        if star_count != self.prev_star_count:
            self._init_stars(star_count, fov)

        # pick colormap
        cmap     = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["rainbow"])
        cmap_n   = len(cmap)
        color_off = (self.frame_count * cshift / 30.0) % 1.0

        # blank frame
        w, h = self.width, self.height
        frame = [(0,0,0,0)] * (w*h)

        # --- 2) Update & draw each star ---
        for s in self.stars:
            # move forward
            s[2] -= speed
            if s[2] <= 1.0:
                # respawn at far plane
                s[0] = random.uniform(-self.cx, self.cx)
                s[1] = random.uniform(-self.cy, self.cy)
                s[2] = fov

            # project
            px = int(self.cx + (s[0] / s[2]) * fov)
            py = int(self.cy + (s[1] / s[2]) * fov)

            if 0 <= px < w and 0 <= py < h:
                # brightness by depth
                bri = max(0.0, 1.0 - (s[2] / fov))
                # twinkle variation
                bri *= (1 - twinkle) + random.random()*twinkle
                # color lookup with shift
                cidx = int(((bri + color_off) % 1.0) * (cmap_n-1))
                r, g, b = cmap[cidx]
                frame[py*w + px] = (r, g, b, 0)

        return frame
