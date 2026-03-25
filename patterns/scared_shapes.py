# patterns/scared_shapes.py
import time
import math
import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
from lfo import BPM

# — Adjustable, modulatable parameters —
PARAMS = {
    "speed": {
        "default": 0.5,  "min": 0.0,  "max": 5.0,  "step": 0.01,
        "modulatable": True
    },
    "max_size": {
        "default": 8.0,  "min": 1.0,  "max": 32.0, "step": 0.5,
        "modulatable": True
    },
    "center": {
        "default": 0.5,  "min": 0.0,  "max": 1.0,  "step": 0.01,
        "modulatable": True
    },
    "spread": {
        "default": 0.5,  "min": 0.0,  "max": 1.0,  "step": 0.01,
        "modulatable": True
    },
    "COLORMAP": {
        "default": "jet",
        "options": list(COLORMAPS.keys())
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.shapes     = []       # list of active shapes
        self.last_time  = time.time()

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self.last_time
        self.last_time = now

        # — 1) Read & (optionally) modulate parameters —
        speed    = self.params["speed"]
        max_size = self.params["max_size"]
        center   = self.params["center"]
        spread   = self.params["spread"]

        for key in ("speed","max_size","center","spread"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src     = meta.get("mod_source")
                amt     = (lfo_signals or {}).get(src, 0.0)
                mval    = apply_modulation(self.params[key], meta, amt)
                if   key=="speed":    speed    = mval
                elif key=="max_size": max_size = mval
                elif key=="center":   center   = mval
                else:                 spread   = mval

        # — 2) Possibly spawn a new shape (≈1 per beat) —
        beat_rate = BPM/60.0
        if random.random() < dt * beat_rate:
            # random type, size, position, lifetime, color
            typ = random.choice(("rect","tri"))
            size = random.uniform(1.0, max_size)
            cx   = random.uniform(0, self.width  - 1)
            cy   = random.uniform(0, self.height - 1)
            life_beats = random.uniform(8.0, 32.0)
            life_secs  = life_beats * (60.0 / BPM)
            # pick a color fraction around [center±spread/2]
            cfrac = center + (random.random()*2.0 - 1.0)*(spread/2.0)
            cfrac = max(0.0, min(1.0, cfrac))
            self.shapes.append({
                "type": typ,
                "cx":   cx,    "cy": cy,
                "size": size,
                "col":  cfrac,
                "t0":   now,   "life": life_secs
            })

        # — 3) Remove expired shapes —
        self.shapes = [s for s in self.shapes if now - s["t0"] < s["life"]]

        # — 4) Draw all shapes onto the frame buffer —
        cmap = COLORMAPS.get(self.params.get("COLORMAP","jet"), COLORMAPS["jet"])
        N    = len(cmap)
        frame = [(0,0,0,0)] * (self.width * self.height)

        for s in self.shapes:
            age   = now - s["t0"]
            angle = age * speed * 2 * math.pi
            half  = s["size"] / 2.0
            ca, sa = math.cos(angle), math.sin(angle)
            # convert color fraction → index
            idx = int(s["col"] * (N-1))
            r, g, b = cmap[idx]

            # bounding box in pixel coords
            x0 = max(0, int(math.floor(s["cx"] - half)))
            x1 = min(self.width-1,  int(math.ceil (s["cx"] + half)))
            y0 = max(0, int(math.floor(s["cy"] - half)))
            y1 = min(self.height-1, int(math.ceil (s["cy"] + half)))

            for y in range(y0, y1+1):
                for x in range(x0, x1+1):
                    # transform into shape‐centered coords and rotate
                    dx = x - s["cx"]
                    dy = y - s["cy"]
                    rx = dx*ca + dy*sa
                    ry = -dx*sa + dy*ca

                    if s["type"] == "rect":
                        # filled square
                        if abs(rx) <= half and abs(ry) <= half:
                            frame[y*self.width + x] = (r, g, b, 0)

                    else:  # triangle
                        # normalized vertical position t in [0..1]
                        tpos = (ry + half) / (2*half)
                        if 0.0 <= tpos <= 1.0:
                            # half‐width at this row
                            hwidth = tpos * half
                            if abs(rx) <= hwidth:
                                frame[y*self.width + x] = (r, g, b, 0)

        return frame
