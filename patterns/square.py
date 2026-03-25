import math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "SIZE": {
        "default": 0.5,   # fraction of the smaller dimension
        "min": 0.1,
        "max": 1.0,
        "step": 0.01,
        "modulatable": True,
        "mod_mode": "add"
    },
    "COLOR_POS": {
        "default": 0.5,   # fraction along the colormap
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "modulatable": True,
        "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "jet",
        "options": list(COLORMAPS.keys())
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        # keep metadata for modulation
        self.param_meta = PARAMS

    def render(self, lfo_signals=None):
        # 1) Read raw parameters
        size_frac   = self.params["SIZE"]
        color_frac  = self.params["COLOR_POS"]
        cmap_name   = self.params.get("COLORMAP", "jet")
        cmap        = COLORMAPS.get(cmap_name, COLORMAPS["jet"])
        cmap_len    = len(cmap)

        # 2) Apply any active modulation
        if lfo_signals:
            for key in ("SIZE", "COLOR_POS"):
                meta = self.param_meta[key]
                if meta.get("modulatable") and meta.get("mod_active"):
                    src = meta.get("mod_source")
                    amt = (lfo_signals or {}).get(src, 0.0)
                    mod_val = apply_modulation(self.params[key], meta, amt)
                    if key == "SIZE":
                        size_frac = mod_val
                    else:  # COLOR_POS
                        color_frac = mod_val

        # 3) Compute pixel bounds
        w, h = self.width, self.height
        side = max(w, h)
        half = side * size_frac / 2.0
        cx, cy = w / 2.0, h / 2.0

        # pick color from the LUT
        idx = int(color_frac * (cmap_len - 1))
        r_col, g_col, b_col = cmap[idx]

        # 4) Build frame
        frame = []
        for y in range(h):
            for x in range(w):
                # inside square?
                if (abs(x - cx) <= half) and (abs(y - cy) <= half):
                    frame.append((r_col, g_col, b_col, 0))
                else:
                    frame.append((0, 0, 0, 0))
        return frame
