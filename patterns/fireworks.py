import random, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters (4 sliders) ---
PARAMS = {
    "EXPLOSION_RATE": {
        "default": 0.02, "min": 0.0,  "max": 0.5,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "PARTICLE_COUNT": {
        "default": 30,   "min": 5,    "max": 100,  "step": 1,
        "modulatable": True, "mod_mode": "replace"
    },
    "PARTICLE_SPEED": {
        "default": 5.0,  "min": 1.0,  "max": 20.0, "step": 0.5,
        "modulatable": True, "mod_mode": "add"
    },
    "FADE_TIME": {
        "default": 1.0,  "min": 0.1,  "max": 3.0,  "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.particles  = []       # list of dicts: x,y,vx,vy,age,lifespan,hue
        self.dt         = 1.0 / 30 # assume 30 FPS for motion

    def render(self, lfo_signals=None):
        w, h = self.width, self.height

        # 1) Read raw parameters
        rate   = self.params["EXPLOSION_RATE"]
        count  = int(self.params["PARTICLE_COUNT"])
        speed  = self.params["PARTICLE_SPEED"]
        fade   = self.params["FADE_TIME"]
        cmap_name = self.params.get("COLORMAP", "rainbow")
        cmap      = COLORMAPS.get(cmap_name, COLORMAPS["rainbow"])
        Ncol      = len(cmap)

        # 2) Apply modulation if active
        for key in ("EXPLOSION_RATE","PARTICLE_COUNT","PARTICLE_SPEED","FADE_TIME"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active", False):
                src = meta["mod_source"]
                amt = (lfo_signals or {}).get(src, 0.0)
                val = apply_modulation(self.params[key], meta, amt)
                if key == "EXPLOSION_RATE":
                    rate = val
                elif key == "PARTICLE_COUNT":
                    count = int(round(val))
                elif key == "PARTICLE_SPEED":
                    speed = val
                else:  # FADE_TIME
                    fade = val

        # clamp sensible ranges
        rate  = max(0.0, min(1.0, rate))
        count = max(1, count)
        speed = max(0.0, speed)
        fade  = max(0.01, fade)

        # 3) Possibly trigger a new explosion this frame
        if random.random() < rate:
            cx = random.uniform(0, w)
            cy = random.uniform(0, h)
            for _ in range(count):
                angle = random.random() * 2 * math.pi
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                hue = random.random()
                self.particles.append({
                    "x": cx, "y": cy,
                    "vx": vx, "vy": vy,
                    "age": 0.0,
                    "lifespan": fade,
                    "hue": hue
                })

        # 4) Update & cull particles
        new_parts = []
        for p in self.particles:
            p["age"] += self.dt
            if p["age"] < p["lifespan"]:
                p["x"] += p["vx"] * self.dt
                p["y"] += p["vy"] * self.dt
                new_parts.append(p)
        self.particles = new_parts

        # 5) Draw frame
        frame = [(0,0,0,0)] * (w * h)
        for p in self.particles:
            t = p["age"] / p["lifespan"]
            # color ramp: hue + fade-out
            u = (p["hue"] + (1 - t)) % 1.0
            idx = int(u * (Ncol - 1))
            idx = max(0, min(Ncol - 1, idx))
            r, g, b = cmap[idx]

            ix = int(p["x"])
            iy = int(p["y"])
            if 0 <= ix < w and 0 <= iy < h:
                frame[iy * w + ix] = (r, g, b, 0)

        return frame
