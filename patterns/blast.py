# patterns/star_explosions.py
import math
import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# ─── Adjustable Parameters ─────────────────────────────────────────────────
PARAMS = {
    "RATE": {
        "default": 0.1, "min": 0.05, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "NUM_STARS": {
        "default": 3, "min": 1, "max": 10, "step": 1,
        "modulatable": True, "mod_mode": "replace"
    },
    "SPEED": {
        "default": 0.2, "min": 0.05, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "SLICE_WIDTH": {
        "default": 0.1, "min": 0.05, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "replace"
    },
    "COLORMAP": {
        "default": "jet",
        "options": list(COLORMAPS.keys())
    },
    "SPRITE": {
        "default": "none",
        "options": []
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        # Each explosion holds: x0, y0, radius, sub-colormap slice
        self.explosions = []

    def render(self, lfo_signals=None):
        w, h = self.width, self.height
        max_radius = math.hypot(w, h)

       # ─── Read & clamp parameters ────────────────────────────────────────────
        rate        = self.params["RATE"]
        num_stars   = int(self.params["NUM_STARS"])
        speed       = self.params["SPEED"]
        slice_width = self.params["SLICE_WIDTH"]

        # ─── Apply modulation ───────────────────────────────────────────────────
        # Only if meta["mod_active"] and meta["mod_source"] is in the signals map
        for key in ("RATE","NUM_STARS","SPEED","SLICE_WIDTH"):
            meta = self.param_meta[key]
            if not meta.get("modulatable") or not meta.get("mod_active"):
                continue

            src = meta.get("mod_source")
            # make sure you actually have a numeric signal for this source
            if not src or src not in lfo_signals:
                continue
            amt = (lfo_signals or {}).get(src, 0.0)
            # apply_modulation(base_value, meta_dict, signals_dict) → float
            mod_val = apply_modulation(self.params[key], meta, amt)

            # store back into the local variable
            if key == "RATE":
                rate = mod_val
            elif key == "NUM_STARS":
                num_stars = max(1, int(round(mod_val)))
            elif key == "SPEED":
                speed = mod_val
            elif key == "SLICE_WIDTH":
                slice_width = mod_val


        # ─── Possibly Spawn a New Explosion ─────────────────────────────────
        if len(self.explosions) < num_stars and random.random() < rate:
            # pick a random origin
            x0 = random.uniform(0, w-1)
            y0 = random.uniform(0, h-1)
            # pick a random contiguous slice of the LUT
            full_cmap = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["jet"])
            L = len(full_cmap)
            sw = max(1, int(slice_width * L))
            start = random.randint(0, L - sw)
            subcmap = full_cmap[start:start+sw]
            self.explosions.append({
                "x0": x0, "y0": y0,
                "radius": 0.0,
                "cmap": subcmap
            })

        # ─── Advance & Remove Finished Explosions ───────────────────────────
        alive = []
        for e in self.explosions:
            e["radius"] += speed
            if e["radius"] <= max_radius:
                alive.append(e)
        self.explosions = alive

        # ─── Render All Explosions ───────────────────────────────────────────
        frame = [(0,0,0,0)] * (w * h)
        arms = 8
        for e in self.explosions:
            x0, y0, r = e["x0"], e["y0"], e["radius"]
            cmap = e["cmap"]
            L    = len(cmap)
            # for each arm
            for a in range(arms):
                ang = a * (2*math.pi/arms)
                # draw every step from 0..r to persist the trail
                steps = int(r) + 1
                for s in range(steps):
                    frac = s / max_radius
                    idx  = min(L-1, int(frac * (L-1)))
                    col  = cmap[idx]
                    xi = int(round(x0 + s * math.cos(ang)))
                    yi = int(round(y0 + s * math.sin(ang)))
                    if 0 <= xi < w and 0 <= yi < h:
                        frame[yi*w + xi] = (*col, 0)

        return frame
