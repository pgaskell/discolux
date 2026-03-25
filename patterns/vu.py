import time
import math
from .base import Pattern as BasePattern, apply_modulation
from audio_env import evaluate_fft_bands
from colormaps import COLORMAPS

# --- Adjustable Parameters ---
PARAMS = {
    "BINS": {
        "default": 24,
        "valid":   [24, 12, 8, 6, 4, 3],
    },
    "HOLD_TIME": {
        "default": 0.5,
        "min":     0.1,
        "max":     5.0,
        "step":    0.1,
    },
    "GAIN_DB": {
        "default":     0.0,
        "min":       -20.0,
        "max":        20.0,
        "step":       1.0,
        "modulatable": True,
        "mod_mode":   "add",
    },
    # now a slider 0=vu,1=peak,2=both
    "DISPLAY_MODE": {
        "default": 2,
        "min":     0,
        "max":     2,
        "step":    1,
        "modulatable": False
    },
    "COLORMAP": {
        "default": "vu",
        "options": list(COLORMAPS.keys())
    }
}

# map slider value → mode name
_MODE_MAP = {
    0: "vu",
    1: "peak",
    2: "both"
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta  = PARAMS
        self.prev_time   = time.time()
        self.hold_values = [0.0] * int(self.params["BINS"])

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self.prev_time
        self.prev_time = now

        # 1) Read base params
        bins         = int(self.params["BINS"])
        hold_time    = self.params["HOLD_TIME"]
        gain_db      = self.params["GAIN_DB"]
        mode_idx     = int(self.params["DISPLAY_MODE"])
        display_mode = _MODE_MAP.get(mode_idx, "both")

        # 2) Apply modulation to GAIN_DB if active
        meta = self.param_meta["GAIN_DB"]
        if meta.get("modulatable") and meta.get("mod_active", False):
            src = meta.get("mod_source")
            amt = (lfo_signals or {}).get(src, 0.0)
            gain_db = apply_modulation(self.params["GAIN_DB"], meta, amt)

        # 3) Convert gain dB → linear
        gain_lin = 10 ** (gain_db / 20.0)

        # 4) Grab & scale FFT bands
        mags = evaluate_fft_bands(bins)
        for i, m in enumerate(mags):
            mags[i] = min(1.0, m * gain_lin)

        # 5) Ensure hold buffer matches
        if len(self.hold_values) != bins:
            self.hold_values = [0.0] * bins

        # 6) Update peak‐hold
        for i, level in enumerate(mags):
            if level > self.hold_values[i]:
                self.hold_values[i] = level
            else:
                decay = dt / hold_time
                self.hold_values[i] = max(0.0, self.hold_values[i] - decay)

        # 7) Prepare for drawing
        w, h        = self.width, self.height
        cmap        = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["vu_meter"])
        cmap_len    = len(cmap)

        # Build a mirrored band map: low freq in the centre, high freq
        # reflected outward to both edges.
        half_w = w / 2.0
        band_for_col = []
        for x in range(w):
            # distance from centre, 0.0 at mid → 1.0 at edges
            dist = abs(x - half_w + 0.5) / half_w
            band_for_col.append(min(bins - 1, int(dist * bins)))

        frame = []
        for y in range(h):
            # pick color by row
            frac      = 1.0 - (y / (h - 1))
            lut_idx   = int(frac * (cmap_len - 1))
            row_color = cmap[lut_idx]

            for x in range(w):
                band   = band_for_col[x]
                level  = mags[band]
                peak   = self.hold_values[band]
                fill_y = h - int(level * h)
                peak_y = h - int(peak  * h)

                drawn = False
                # bars?
                if display_mode in ("vu", "both") and y >= fill_y:
                    r, g, b = row_color
                    frame.append((r, g, b, 0))
                    drawn = True

                # peaks?
                if not drawn and display_mode in ("peak", "both") and y == peak_y:
                    frame.append((255, 255, 255, 0))
                    drawn = True

                if not drawn:
                    frame.append((0, 0, 0, 0))

        return frame
