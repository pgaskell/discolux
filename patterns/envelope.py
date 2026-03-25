import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "SCROLL_SPEED": {
        "default": 1.0,    "min": 0.1,  "max": 10.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "Y_SCALE": {
        "default": 0.5,    "min": 0.1,  "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "scale"
    },
    "THICKNESS": {
        "default": 2,      "min": 1,    "max": 10,   "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "COLOR_OFFSET": {
        "default": 0.0,    "min": 0.0,  "max": 1.0,  "step": 0.01,
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
        self.buffer = []          # rolling history of sum(envl+envh)
    
    def render(self, lfo_signals=None):
        w, h = self.width, self.height
        mid_y = h // 2

        # 1) read & modulate parameters
        spd = self.params["SCROLL_SPEED"]
        y_scale = self.params["Y_SCALE"]
        thickness = int(self.params["THICKNESS"])
        col_off = self.params["COLOR_OFFSET"]

        for key in ("SCROLL_SPEED", "Y_SCALE", "THICKNESS", "COLOR_OFFSET"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active", False):
                src = meta["mod_source"]
                amt = (lfo_signals or {}).get(src, 0.0)
                val = apply_modulation(self.params[key], meta, amt)
                if key == "SCROLL_SPEED":
                    spd = val
                elif key == "Y_SCALE":
                    y_scale = val
                elif key == "THICKNESS":
                    thickness = int(round(val))
                else:
                    col_off = val % 1.0

        # clamp thickness
        thickness = max(1, min(thickness, h//2))

        # 2) compute the next sample: sum of envl+envh
        envl = (lfo_signals or {}).get("envl", 0.0)
        envh = (lfo_signals or {}).get("envh", 0.0)
        sample = envl + envh
        sample = max(0.0, min(1.0, sample))

        # 3) scroll the buffer by spd samples/frame
        #    allow fractional by probabilistic extra step
        n = int(spd)
        if (spd - n) > random.random():
            n += 1
        for _ in range(n):
            self.buffer.insert(0, sample)
        # keep only last w entries
        if len(self.buffer) > w:
            self.buffer = self.buffer[:w]

        # 4) pick colormap
        cmap = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["rainbow"])
        N = len(cmap)

        # 5) draw frame
        frame = [(0,0,0,0)] * (w*h)
        half_th = thickness // 2

        for x in range(w):
            val = self.buffer[x] if x < len(self.buffer) else 0.0
            # vertical offset from center
            dy = int(val * (h/2) * y_scale)
            # color lookup
            u = (val + col_off) % 1.0
            idx = int(u * (N-1))
            idx = max(0, min(N-1, idx))
            col = cmap[idx]

            # draw a vertical line of height=thickness at y = mid_y ± dy
            for dt in range(-half_th, half_th+1):
                y1 = mid_y + dy + dt
                y2 = mid_y - dy + dt
                if 0 <= y1 < h:
                    frame[y1*w + x] = (*col, 0)
                if 0 <= y2 < h:
                    frame[y2*w + x] = (*col, 0)

        return frame
