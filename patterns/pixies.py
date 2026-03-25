# patterns/pixies.py
import time, random, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "BLOB_SIZE": {
        "default": 2.0, "min": 1.0, "max": 5.0, "step": 1.0,
        "modulatable": True
    },
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1,
        "modulatable": True
    },
    "TRAIL_DECAY": {
        "default": 0.85, "min": 0.5, "max": 0.99, "step": 0.01,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.2, "min": 0.0, "max": 2.0, "step": 0.01,
        "modulatable": True
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        # State for three pixies:
        self.pixies = []
        for _ in range(5):
            angle = random.random() * 2*math.pi
            self.pixies.append({
                "x": random.uniform(0, width),
                "y": random.uniform(0, height),
                "vx": math.cos(angle),
                "vy": math.sin(angle),
                "hue": random.random()
            })
        # trail buffer: per-pixel [r,g,b] floats in [0..1]
        self.trail = [[0.0,0.0,0.0] for _ in range(width*height)]
        self.last_time = time.time()

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self.last_time
        self.last_time = now

        # 1) raw params
        size       = self.params["BLOB_SIZE"]
        speed      = self.params["SPEED"]
        decay      = self.params["TRAIL_DECAY"]
        color_cycle= self.params["COLOR_CYCLE"]

        # 2) apply modulation properly
        for key in ("BLOB_SIZE","SPEED","TRAIL_DECAY","COLOR_CYCLE"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if   key=="BLOB_SIZE":    size        = mod
                elif key=="SPEED":        speed       = mod
                elif key=="TRAIL_DECAY":  decay       = mod
                elif key=="COLOR_CYCLE":  color_cycle = mod

        w, h = self.width, self.height

        # 3) fade existing trail
        for pix in self.trail:
            pix[0] *= decay
            pix[1] *= decay
            pix[2] *= decay

        # 4) move & draw each pixie
        for p in self.pixies:
            # update color
            p["hue"] = (p["hue"] + color_cycle * dt) % 1.0
            # update pos
            p["x"] += p["vx"] * speed * dt
            p["y"] += p["vy"] * speed * dt
            # bounce off walls
            if p["x"] < 0 or p["x"] >= w:
                p["vx"] *= -1; p["x"] = max(0,min(w-1,p["x"]))
            if p["y"] < 0 or p["y"] >= h:
                p["vy"] *= -1; p["y"] = max(0,min(h-1,p["y"]))

            # draw a little filled circle into the trail buffer
            base_r, base_g, base_b = colorsys.hsv_to_rgb(p["hue"], 1.0, 1.0)
            radius = size
            cx, cy = p["x"], p["y"]
            r_int = int(math.ceil(radius))
            for dy in range(-r_int, r_int+1):
                yy = int(cy+dy)
                if 0 <= yy < h:
                    for dx in range(-r_int, r_int+1):
                        xx = int(cx+dx)
                        if 0 <= xx < w:
                            dist = math.hypot(dx, dy)
                            if dist <= radius:
                                idx = yy*w + xx
                                # simple linear falloff
                                strength = max(0.0, 1 - dist/radius)
                                self.trail[idx][0] += base_r * strength
                                self.trail[idx][1] += base_g * strength
                                self.trail[idx][2] += base_b * strength

        # 5) build output frame
        frame = []
        for r,g,b in self.trail:
            # clamp and convert to 0..255
            rr = int(max(0, min(1, r)) * 255)
            gg = int(max(0, min(1, g)) * 255)
            bb = int(max(0, min(1, b)) * 255)
            frame.append((rr, gg, bb, 0))
        return frame
