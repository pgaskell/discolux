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
    "ROTATION_SPEED": {
        "default": 0.1,
        "min":    -1.0,
        "max":     1.0,
        "step":   0.01,
        "modulatable": True,
        "mod_mode":   "add",
    },
    "RADIUS_SCALE": {
        "default":     0.8,
        "min":         0.1,
        "max":         2.0,
        "step":        0.01,
        "modulatable": True,
        "mod_mode":   "scale",   # scale the base radius
    },
    "COLOR_SHIFT_SPEED": {
        "default": 0.1,
        "min":     0.0,
        "max":     1.0,
        "step":    0.01,
        "modulatable": True,
        "mod_mode":   "add",
    },
    "COLORMAP": {
        "default": "rainbow",
        "options": list(COLORMAPS.keys())
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta   = PARAMS
        self.frame_count  = 0
        self.angle_offset = 0.0
        self.prev_mags    = None
        self.prev_bins    = int(self.params["BINS"])

    def render(self, lfo_signals=None):
        self.frame_count += 1

        # 0) Grab and possibly update band count
        bins = int(self.params["BINS"])
        if self.prev_mags is None or self.prev_bins != bins:
            # reset any time BINS changes
            self.prev_mags = [0.0] * bins
            self.prev_bins = bins

        # 1) read parameters
        rot_speed    = self.params["ROTATION_SPEED"]
        radius_scale = self.params["RADIUS_SCALE"]
        color_shift  = self.params["COLOR_SHIFT_SPEED"]

        # 2) apply modulation to rot_speed
        m = self.param_meta["ROTATION_SPEED"]
        if m.get("modulatable") and m.get("mod_active", False):
            amt = (lfo_signals or {}).get(m["mod_source"], 0.0)
            rot_speed = apply_modulation(self.params["ROTATION_SPEED"], m, amt)

        # 3) apply modulation to radius_scale
        m2 = self.param_meta["RADIUS_SCALE"]
        if m2.get("modulatable") and m2.get("mod_active", False):
            amt2 = (lfo_signals or {}).get(m2["mod_source"], 0.0)
            radius_scale = apply_modulation(self.params["RADIUS_SCALE"], m2, amt2)

        # 4) apply modulation to color_shift
        m3 = self.param_meta["COLOR_SHIFT_SPEED"]
        if m3.get("modulatable") and m3.get("mod_active", False):
            amt3 = (lfo_signals or {}).get(m3["mod_source"], 0.0)
            color_shift = apply_modulation(self.params["COLOR_SHIFT_SPEED"], m3, amt3)

        # 5) update rotation
        dt = 1/30.0
        self.angle_offset = (self.angle_offset + rot_speed * dt) % 1.0

        # 6) pull & smooth FFT bands
        raw_mags = evaluate_fft_bands(bins)
        # one‐pole smoothing toward new value
        alpha = 0.6
        mags = []
        for i, v in enumerate(raw_mags):
            sm = alpha * self.prev_mags[i] + (1-alpha) * v
            mags.append(sm)
        self.prev_mags = mags[:]

        # 7) prepare LUT and frame
        w, h    = self.width, self.height
        cx, cy  = w/2, h/2
        max_r   = min(cx, cy) * radius_scale
        cmap    = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["rainbow"])
        cmap_n  = len(cmap)
        frame   = []

        color_offset = (self.frame_count * color_shift / 30.0) % 1.0

        for py in range(h):
            for px in range(w):
                dx = px - cx
                dy = py - cy
                r  = math.hypot(dx, dy)
                # normalized radius
                rn = r / max_r
                theta = (math.atan2(dy, dx) / (2*math.pi) + 0.5)
                theta = (theta + self.angle_offset) % 1.0

                band = min(bins-1, int(theta * bins))
                if rn <= mags[band]:
                    # color by rotated theta
                    cf = (theta + color_offset) % 1.0
                    idx = int(cf * (cmap_n-1))
                    rc, gc, bc = cmap[idx]
                    frame.append((rc, gc, bc, 0))
                else:
                    frame.append((0, 0, 0, 0))

        return frame
