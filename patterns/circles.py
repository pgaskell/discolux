import math
import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "NUM_GENERATORS": {
        "default": 4,  "min": 1,   "max": 10,  "step": 1,
        "modulatable": True,
        "mod_mode": "add"
    },
    "MOVE_SPEED": {
        "default": 0.1, "min": 0.01, "max": 0.4, "step": 0.01,
        "modulatable": True,
        "mod_mode": "add"
    },
    "PALETTE_SHIFT": {
        "default": 0.02, "min": 0.0,  "max": 0.2,  "step": 0.001,
        "modulatable": True
    },
    "CIRCLE_THICKNESS": {
        "default": 1.0,  "min": 0.1,  "max": 5.0, "step": 0.1,
        "modulatable": True,
        "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "warm_rainbow",
        "options": list(COLORMAPS.keys())
    },
    "SPRITE": {
        "default": "none",
        "options": []
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        # bypass BasePattern's .params so we can merge defaults + passed
        self.width  = width
        self.height = height
        # start with all defaults
        self.params = {
            k: (v["default"] if isinstance(v, dict) else v)
            for k, v in PARAMS.items()
        }
        # override with any passed values
        if params:
            self.params.update(params)

        self.param_meta  = PARAMS
        self.frame_count = 0
        self.circles     = []  # list of (x, y, age)

    def render(self, lfo_signals=None):
        self.frame_count += 1

        # 1) Read & modulate raw parameters
        num_gen    = self.params["NUM_GENERATORS"]
        move_speed = self.params["MOVE_SPEED"]
        cycle_speed= self.params["PALETTE_SHIFT"]
        thickness  = self.params["CIRCLE_THICKNESS"]

        for key in ("NUM_GENERATORS","MOVE_SPEED","PALETTE_SHIFT","CIRCLE_THICKNESS"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                # 1) pull out the one float (default 0.0 if missing)
                amt = (lfo_signals or {}).get(src, 0.0)
                # 2) scale it via min/max according to mod_mode
                mv = apply_modulation(self.params[key], meta, amt)

                # now override your local variable:
                if key == "NUM_GENERATORS":
                    num_gen = max(1, int(round(mv)))
                elif key == "MOVE_SPEED":
                    move_speed = mv
                elif key == "PALETTE_SHIFT":
                    palette_shift = mv
                elif key == "CIRCLE_THICKNESS":
                    thickness = mv

        # 2) Prepare LUT and global color for this frame
        cmap     = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["jet"])
        cmap_len = len(cmap)
        # advance through the colormap by cycle_speed * frames
        idx = int(self.frame_count * cycle_speed * cmap_len) % cmap_len
        base_r, base_g, base_b = cmap[idx]

        # 3) Spawn new ripples if under limit
        if len(self.circles) < num_gen and random.random() < 0.2:
            x = random.randint(0, self.width-1)
            y = random.randint(0, self.height-1)
            self.circles.append((x, y, 0))

        # 4) Age and cull old circles
        new = []
        for cx, cy, age in self.circles:
            if age < 300:
                new.append((cx, cy, age+1))
        self.circles = new

        # 5) Draw! Black background, then rings in uniform color
        frame = [ (0,0,0,0) ] * (self.width * self.height)

        for cx, cy, age in self.circles:
            radius = age * move_speed
            # for performance, you could restrict y range to [cy-radius-thickness, cy+radius+thickness]
            for y in range(self.height):
                for x in range(self.width):
                    dist = math.hypot(x - cx, y - cy)
                    # within half-thickness of the radius?
                    if abs(dist - radius) <= (thickness/2):
                        idx = y * self.width + x
                        frame[idx] = (base_r, base_g, base_b, 0)

        return frame
