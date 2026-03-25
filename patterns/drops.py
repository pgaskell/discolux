import random, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "DROP_RATE": {            # average drops spawned per frame
        "default": 0.05, "min": 0.0,  "max": 1.0, "step": 0.01,
        "modulatable": True,  "mod_mode": "add"
    },
    "MIN_SIZE": {             # smallest drop radius in pixels
        "default": 1.0,  "min": 0.5, "max": 5.0, "step": 0.1,
        "modulatable": True,  "mod_mode": "scale"
    },
    "MAX_SIZE": {             # largest drop radius in pixels
        "default": 2.5,  "min": 1.0, "max": 8.0, "step": 0.1,
        "modulatable": True,  "mod_mode": "scale"
    },
    "DROP_SPEED": {           # pixels per frame
        "default": 0.5,  "min": 0.1, "max": 5.0, "step": 0.1,
        "modulatable": True,  "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "rainbow",
        "options": list(COLORMAPS.keys())
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        # each drop is [x:float, y:float, size:float]
        self.drops = []

    def render(self, lfo_signals=None):
        w, h = self.width, self.height

        # 1) Read raw parameters
        drop_rate = self.params["DROP_RATE"]
        min_s     = self.params["MIN_SIZE"]
        max_s     = self.params["MAX_SIZE"]
        speed     = self.params["DROP_SPEED"]

        # 2) Apply modulation if active
        for key in ("DROP_RATE", "MIN_SIZE", "MAX_SIZE", "DROP_SPEED"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active", False):
                src = meta["mod_source"]
                amt = (lfo_signals or {}).get(src, 0.0)
                val = apply_modulation(self.params[key], meta, amt)
                if key == "DROP_RATE":
                    drop_rate = val
                elif key == "MIN_SIZE":
                    min_s = val
                elif key == "MAX_SIZE":
                    max_s = val
                else:
                    speed = val

        # ensure size window is valid
        min_s, max_s = min(min_s, max_s), max(min_s, max_s)

        # 3) Spawn new drops
        # allow >1 spawn if drop_rate > 1.0
        cnt = int(drop_rate)
        if random.random() < (drop_rate - cnt):
            cnt += 1
        for _ in range(cnt):
            size = random.uniform(min_s, max_s)
            x = random.uniform(0, w - 1)
            y = -size  # start just above top
            self.drops.append([x, y, size])

        # 4) Update and cull drops
        new = []
        for x, y, size in self.drops:
            y += speed
            # keep if still visible
            if y - size < h:
                new.append([x, y, size])
        self.drops = new

        # 5) Prepare colormap lookup by drop size
        cmap = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["rainbow"])
        N    = len(cmap)

        # 6) Build an empty frame
        frame = [(0,0,0,0)] * (w * h)

        # 7) Draw each drop as a filled circle
        for x, y, size in self.drops:
            # color index from size between min_s→max_s
            t = 0.0 if max_s==min_s else (size - min_s) / (max_s - min_s)
            idx = int(t * (N - 1)) % 255
            r, g, b = cmap[idx]

            r2 = size * size
            x0 = int(math.floor(x - size))
            x1 = int(math.ceil (x + size))
            y0 = int(math.floor(y - size))
            y1 = int(math.ceil (y + size))
            for py in range(y0, y1+1):
                for px in range(x0, x1+1):
                    dx = px - x
                    dy = py - y
                    if 0 <= px < w and 0 <= py < h and (dx*dx + dy*dy) <= r2:
                        frame[py*w + px] = (r, g, b, 0)

        return frame
