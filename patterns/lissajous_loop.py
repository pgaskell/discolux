import math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "X_FREQ": {
        "default": 3.0,   "min": 0.1,  "max": 10.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "Y_FREQ": {
        "default": 2.0,   "min": 0.1,  "max": 10.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "PHASE": {
        "default": 0.0,   "min": 0.0,  "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "COLOR_CENTER": {
        "default": 0.5,   "min": 0.0,  "max": 1.0,  "step": 0.01,
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

    def render(self, lfo_signals=None):
        w, h = self.width, self.height
        cx, cy = w/2, h/2

        # 1) Base parameter values
        xf = self.params["X_FREQ"]
        yf = self.params["Y_FREQ"]
        ph = self.params["PHASE"] * 2 * math.pi   # map [0..1]→[0..2π]
        cc = self.params["COLOR_CENTER"]

        # 2) Apply modulation to xf, yf, ph
        for key in ("X_FREQ", "Y_FREQ", "PHASE", "COLOR_CENTER"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active", False):
                src = meta["mod_source"]
                amt = (lfo_signals or {}).get(src, 0.0)
                modv = apply_modulation(self.params[key], meta, amt)
                if key == "X_FREQ":
                    xf = modv
                elif key == "Y_FREQ":
                    yf = modv
                elif key == "PHASE":
                    ph = modv * 2 * math.pi
                else:
                    cc = modv

        # 3) Choose color from colormap
        cmap = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["rainbow"])
        idx = int(cc * (len(cmap)-1))
        color = cmap[idx]

        # 4) Prepare empty frame
        frame = [(0,0,0,0)] * (w * h)

        # 5) Sample N points along t=[0..1), draw 2×2 pixel “line”
        N = max(w, h) * 8  # enough resolution
        for i in range(N):
            t = i / N * 2*math.pi
            x = cx + cx * math.sin(xf * t + ph)
            y = cy + cy * math.sin(yf * t)
            ix = int(round(x))
            iy = int(round(y))
            # draw a 2×2 square centered
            for dx in (0,1):
                for dy in (0,1):
                    px = ix + dx
                    py = iy + dy
                    if 0 <= px < w and 0 <= py < h:
                        frame[py*w + px] = (*color, 0)

        return frame
