import time, math, random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "FREQUENCY": {
        "default": 0.15, "min": 0.01, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "JAGGEDNESS": {
        "default": 0.25, "min": 0.05, "max": 0.7, "step": 0.01,
        "modulatable": True
    },
    "THICKNESS": {
        "default": 2, "min": 1, "max": 6, "step": 1,
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
        self.bolts = []

    def spawn_bolt(self, w, h, jaggedness):
        # Start at random top x, end at random bottom x
        x0 = random.randint(0, w-1)
        x1 = random.randint(0, w-1)
        y0, y1 = 0, h-1
        points = [(x0, y0)]
        steps = h
        for i in range(1, steps):
            t = i / steps
            x = int((1-t)*x0 + t*x1 + random.uniform(-jaggedness*w, jaggedness*w))
            y = i
            points.append((max(0, min(w-1, x)), y))
        return {
            "points": points,
            "age": 0.0,
            "max_age": random.uniform(0.12, 0.25)
        }

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        self.t += dt

        freq = self.params["FREQUENCY"]
        jag = self.params["JAGGEDNESS"]
        thick = int(self.params["THICKNESS"])
        color_cycle = self.params["COLOR_CYCLE"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "FREQUENCY": freq = mod
                elif key == "JAGGEDNESS": jag = mod
                elif key == "THICKNESS": thick = int(mod)
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        # Possibly spawn a new bolt
        if random.random() < freq * dt:
            self.bolts.append(self.spawn_bolt(w, h, jag))

        # Age and cull bolts
        new_bolts = []
        for bolt in self.bolts:
            bolt["age"] += dt
            if bolt["age"] < bolt["max_age"]:
                new_bolts.append(bolt)
        self.bolts = new_bolts

        # Draw bolts
        frame = [(0,0,0,0)] * (w*h)
        for bolt in self.bolts:
            alpha = 1.0 - (bolt["age"] / bolt["max_age"])
            hue = (self.t * color_cycle) % 1.0
            if lut:
                lut_idx = int(hue * (len(lut) - 1))
                r, g, b = lut[lut_idx]
            else:
                r, g, b = colorsys.hsv_to_rgb(hue, 0.1 + 0.9*alpha, alpha)
                r = int(r * 255)
                g = int(g * 255)
                b = int(b * 255)
            for i in range(len(bolt["points"])-1):
                x0, y0 = bolt["points"][i]
                x1, y1 = bolt["points"][i+1]
                # Bresenham's line with thickness
                dx = abs(x1 - x0)
                dy = abs(y1 - y0)
                sx = 1 if x0 < x1 else -1
                sy = 1 if y0 < y1 else -1
                err = dx - dy
                x, y = x0, y0
                while True:
                    for tx in range(-thick//2, thick//2+1):
                        for ty in range(-thick//2, thick//2+1):
                            xx = x + tx
                            yy = y + ty
                            if 0 <= xx < w and 0 <= yy < h:
                                idx = yy*w + xx
                                frame[idx] = (r, g, b, 0)
                    if x == x1 and y == y1:
                        break
                    e2 = 2*err
                    if e2 > -dy:
                        err -= dy
                        x += sx
                    if e2 < dx:
                        err += dx
                        y += sy
        return frame