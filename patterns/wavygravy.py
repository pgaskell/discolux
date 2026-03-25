import math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# ─── Adjustable Parameters ────────────────────────────────────────────────
PARAMS = {
    "NUM_WAVES": {
        "default": 3, "min": 1, "max": 10, "step": 1,
        "modulatable": True
    },
    "WAVE_SPEED": {
        "default": 0.1, "min": 0.0, "max": 0.2, "step": 0.01,
        "modulatable": True
    },
    "WAVE_SCALE": {
        "default": 0.5, "min": 0.1, "max": 2.0, "step": 0.01,
        "modulatable": True
    },
    "COLOR_SHIFT": {
        "default": 0.01, "min": 0.0, "max": 0.1, "step": 0.001,
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

        # read raw params
        num_waves   = self.params["NUM_WAVES"]
        speed       = self.params["WAVE_SPEED"]
        scale       = self.params["WAVE_SCALE"]
        color_shift = self.params["COLOR_SHIFT"]

        # apply modulation
        for key in ("NUM_WAVES", "WAVE_SPEED", "WAVE_SCALE", "COLOR_SHIFT"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mv = apply_modulation(self.params[key], meta, amt)
                if key == "NUM_WAVES":
                    num_waves = max(1, int(round(mv)))
                elif key == "WAVE_SPEED":
                    speed = mv
                elif key == "WAVE_SCALE":
                    scale = mv
                elif key == "COLOR_SHIFT":
                    color_shift = mv

        # fetch colormap
        cmap     = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["jet"])
        cmap_len = len(cmap)

        w, h = self.width, self.height
        t = self.frame_count * speed
        frame = []

        for y in range(h):
            for x in range(w):
                acc = 0.0
                # sum a few sin waves with different multipliers
                for i in range(num_waves):
                    freq = scale * (i + 1)
                    phase = 2 * math.pi * ( (x / w) * freq + (y / h) * freq - t )
                    acc += math.sin(phase)
                # normalize into [0,1]
                val = (acc / num_waves) * 0.5 + 0.5
                # color shift over time
                hue = (val + self.frame_count * color_shift) % 1.0
                idx = int(hue * (cmap_len - 1))
                r, g, b = cmap[idx]
                frame.append((r, g, b, 0))

        return frame
