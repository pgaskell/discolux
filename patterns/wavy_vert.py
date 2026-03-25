import math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# ─── Adjustable Parameters ────────────────────────────────────────────────
PARAMS = {
    "STRIPES": {
        "default": 2, "min": 2,  "max": 8,  "step": 1,
        "modulatable": True
    },
    "AMPLITUDE": {
        "default": 0.2, "min": 0.0,  "max": 0.2,  "step": 0.02,
        "modulatable": True
    },
    "WAVE_SPEED": {
        "default": 0.05, "min": 0.0,  "max": 0.1,  "step": 0.005,
        "modulatable": True
    },
    "COLOR_SHIFT": {
        "default": 0.01, "min": 0.0,  "max": 0.1,  "step": 0.001,
        "modulatable": True
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
        self.param_meta  = PARAMS
        self.frame_count = 0

    def render(self, lfo_signals=None):
        self.frame_count += 1

        # ── 1) Read raw parameters ─────────────────────────────────
        stripes     = self.params["STRIPES"]
        amplitude   = self.params["AMPLITUDE"]
        wave_speed  = self.params["WAVE_SPEED"]
        color_shift = self.params["COLOR_SHIFT"]

        # ── 2) Apply any modulation ────────────────────────────────
        for key in ("STRIPES", "AMPLITUDE", "WAVE_SPEED", "COLOR_SHIFT"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mv  = apply_modulation(self.params[key], meta, amt)
                if key == "STRIPES":
                    stripes = max(1, int(round(mv)))
                elif key == "AMPLITUDE":
                    amplitude = mv
                elif key == "WAVE_SPEED":
                    wave_speed = mv
                elif key == "COLOR_SHIFT":
                    color_shift = mv

        # ── 3) Prepare color lookup ─────────────────────────────────
        cmap     = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["jet"])
        cmap_len = len(cmap)

        w, h = self.width, self.height
        t    = self.frame_count * wave_speed

        frame = []
        for y in range(h):
            y_norm = y / h
            # how far to offset this row (in pixels)
            offset = amplitude * w * math.sin(2 * math.pi * (y_norm + t))

            for x in range(w):
                # shifted X (wraps naturally)
                x_off = (x + offset) / w

                # stripe pattern
                val = math.sin(2 * math.pi * (x_off * stripes))

                # normalize [–1…1] → [0…1]
                v_norm = 0.5 * val + 0.5

                # add a slow hue shift
                hue = (v_norm + self.frame_count * color_shift) % 1.0
                idx = int(hue * (cmap_len - 1))
                r, g, b = cmap[idx]
                frame.append((r, g, b, 0))

        return frame
