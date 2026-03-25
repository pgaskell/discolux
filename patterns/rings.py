import math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "RING_SPACING": {
        "default": 0.2,   "min": 0.05, "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "EXPANSION_SPEED": {
        "default": 0.5,   "min": 0.0,  "max": 5.0,  "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "RING_THICKNESS": {
        "default": 0.05,  "min": 0.01, "max": 0.5,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    },
    "COLOR_SHIFT": {
        "default": 0.0,   "min": 0.0,  "max": 1.0,  "step": 0.01,
        "modulatable": True, "mod_mode": "add"
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta  = PARAMS
        self.frame_count = 0

    def render(self, lfo_signals=None):
        self.frame_count += 1
        w, h = self.width, self.height
        cx, cy = w/2.0, h/2.0
        max_r = math.hypot(cx, cy)

        # 1) Load raw params
        spacing = self.params["RING_SPACING"]
        speed   = self.params["EXPANSION_SPEED"]
        thickness = self.params["RING_THICKNESS"]
        shift     = self.params["COLOR_SHIFT"]

        # 2) Apply modulation
        for key in ("RING_SPACING","EXPANSION_SPEED","RING_THICKNESS","COLOR_SHIFT"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active",False):
                src = meta["mod_source"]
                amt = (lfo_signals or {}).get(src,0.0)
                val = apply_modulation(self.params[key], meta, amt)
                if key=="RING_SPACING":
                    spacing = val
                elif key=="EXPANSION_SPEED":
                    speed = val
                elif key=="RING_THICKNESS":
                    thickness = val
                else:
                    shift = val % 1.0

        # guard ranges
        spacing   = max(0.001, min(1.0, spacing))
        thickness = max(0.001, min(spacing, thickness))
        shift     = shift % 1.0

        # 3) pick colormap
        cmap     = COLORMAPS.get(self.params.get("COLORMAP","rainbow"), COLORMAPS["rainbow"])
        cmap_n   = len(cmap)

        # 4) time offset in “ring units”
        t = (self.frame_count / 30.0) * speed / spacing

        frame = []
        for y in range(h):
            for x in range(w):
                # radial distance normalized 0..1
                dx = x - cx
                dy = y - cy
                r = math.hypot(dx, dy) / max_r

                # position within each ring [0..1)
                pos = (r / spacing - t) % 1.0

                # if we’re within the thickness window, map to color
                if pos < (thickness/spacing):
                    # rotate that position by shift for color cycling
                    cpos = (pos + shift) % 1.0
                    idx = int(cpos * (cmap_n-1))
                    idx = max(0, min(cmap_n-1, idx))
                    r_,g_,b_ = cmap[idx]
                    frame.append((r_, g_, b_, 0))
                else:
                    frame.append((0, 0, 0, 0))

        return frame
