import math
import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "SPAWN_RATE": {
        "default": 0.1,   "min": 0.0,  "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "SWIRL_STRENGTH": {
        "default": 0.2,   "min": 0.0,  "max": 2.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "RADIAL_SPEED": {
        "default": 0.3,   "min": -1.0, "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "LIFESPAN": {
        "default": 2.0,   "min": 0.1,  "max": 10.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "HUE_SHIFT": {
        "default": 0.0,   "min": -1.0, "max": 1.0,  "step": 0.01,
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
        self.param_meta = PARAMS
        self.particles  = []   # each is dict: {r_norm, theta, age}
        self.frame_count = 0

    def render(self, lfo_signals=None):
        self.frame_count += 1
        w, h = self.width, self.height
        cx, cy = w/2.0, h/2.0
        radius_max = min(cx, cy)
        dt = 1.0 / 30.0  # assume 30 FPS

        # 1) read parameters
        spawn_rate   = self.params["SPAWN_RATE"]
        swirl_strength = self.params["SWIRL_STRENGTH"]
        radial_speed   = self.params["RADIAL_SPEED"]
        lifespan       = self.params["LIFESPAN"]
        hue_shift      = self.params["HUE_SHIFT"]

        # 2) apply modulation if active
        for key in ("SPAWN_RATE", "SWIRL_STRENGTH", 
                    "RADIAL_SPEED", "LIFESPAN", "HUE_SHIFT"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active", False):
                src = meta["mod_source"]
                amt = (lfo_signals or {}).get(src, 0.0)
                val = apply_modulation(self.params[key], meta, amt)
                if key == "SPAWN_RATE":
                    spawn_rate = val
                elif key == "SWIRL_STRENGTH":
                    swirl_strength = val
                elif key == "RADIAL_SPEED":
                    radial_speed = val
                elif key == "LIFESPAN":
                    lifespan = val
                else:  # HUE_SHIFT
                    hue_shift = val

        # 3) spawn new particle?
        if random.random() < spawn_rate:
            self.particles.append({
                "r_norm": 0.0,
                "theta": random.random() * 2*math.pi,
                "age": 0.0
            })

        # 4) update existing particles
        new_parts = []
        for p in self.particles:
            p["age"]   += dt
            p["r_norm"] += radial_speed * dt
            p["theta"] += swirl_strength * 2*math.pi * dt

            if p["age"] <= lifespan and 0.0 <= p["r_norm"] <= 1.0:
                new_parts.append(p)
        self.particles = new_parts

        # 5) prepare colormap
        cmap = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["rainbow"])
        cmap_n = len(cmap)

        # 6) draw background
        frame = [(0,0,0,0)] * (w*h)

        # 7) render particles
        for p in self.particles:
            # convert polar → x,y
            rpx = p["r_norm"] * radius_max
            x = int(round(cx + math.cos(p["theta"]) * rpx))
            y = int(round(cy + math.sin(p["theta"]) * rpx))
            if 0 <= x < w and 0 <= y < h:
                # hue based on age fraction + global shift
                hf = (p["age"]/lifespan + hue_shift * self.frame_count*dt) % 1.0
                idx = int(hf * (cmap_n-1))
                r, g, b = cmap[idx]
                frame[y*w + x] = (r, g, b, 0)

        return frame
