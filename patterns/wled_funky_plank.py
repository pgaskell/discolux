# WLED "Funky Plank" effect — port of mode_2DFunkyPlank()
# Original: "Funky Plank@Scroll speed,,# of bands;;;2f;si=0"  (audio)
# Audio replaced by simulated beat — beatsin8 at several BPMs drives column heights.
# 2 original sliders (scroll speed + # bands) + 2 non-audio additions = 4 params.
import math, time, random
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, beatsin8, beat8
from colormaps import COLORMAPS

PARAMS = {
    "SCROLL_SPEED": {
        "default": 0.5, "min": 0.0, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "NUM_BANDS": {
        "default": 8, "min": 1, "max": 16, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "AMPLITUDE": {
        "default": 0.7, "min": 0.1, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "warm_rainbow", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

# Different BPMs for each simulated FFT band — creates organic independent motion
_BAND_BPMS = [7, 9, 11, 13, 15, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        # Column shift offsets so each band's column scrolls independently
        self._col_offsets = [random.random() for _ in range(16)]
        self._last = time.time()
        self.t     = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self._last
        self._last = now

        scroll_speed = self.params["SCROLL_SPEED"]
        num_bands    = max(1, min(16, int(self.params["NUM_BANDS"])))
        amplitude    = self.params["AMPLITUDE"]
        beat_speed   = self.params["SPEED"]
        cmap         = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt * beat_speed

        w, h = self.width, self.height
        t    = self.t

        frame = [(0, 0, 0, 0)] * (w * h)

        # Each "band" fills a slice of columns
        band_w = max(1, w // num_bands)

        for b in range(num_bands):
            bpm      = _BAND_BPMS[b % len(_BAND_BPMS)]
            # Simulate a "volume" level for this band using beatsin8
            vol_norm = beatsin8(bpm, 0, 255, t=t + b * 0.3) / 255.0 * amplitude

            # Bar height
            bar_h = int(vol_norm * h)

            # Column range for this band
            x_start = b * band_w
            x_end   = min(w, x_start + band_w)

            # Colour — scroll horizontally with scroll_speed
            hue = int((b / num_bands) * 255 + t * scroll_speed * 50) & 255
            color = palette_color(cmap, hue)

            # Fill from bottom upward
            for x in range(x_start, x_end):
                for y in range(h - bar_h, h):
                    row_hue = int(hue + (h - y) * 3) & 255
                    c = palette_color(cmap, row_hue)
                    frame[y * w + x] = (c[0], c[1], c[2], 0)

        return frame
