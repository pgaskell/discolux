# WLED "Waverly" effect — port of mode_2DWaverly()
# Original: "Waverly@!,Amplitude;!,!;!;2v;ix=64,si=0"  (audio reactive, volumeRaw)
# Audio (volumeRaw) replaced by beatsin8 — sine waves dance autonomously.
# Original 2 sliders kept (SPEED, AMPLITUDE); BLUR added as 3rd param (≤4).
import math, time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, blur2d, beatsin8, beat8, sin8
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "AMPLITUDE": {
        "default": 0.6, "min": 0.1, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add",
        "note": "Height of the waves"
    },
    "BLUR": {
        "default": 8, "min": 0, "max": 24, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "ocean", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

# Phase offsets per column so waves ripple rather than all moving in unison
_COL_PHASE = [i * 11 for i in range(256)]

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._frame = [(0, 0, 0, 0)] * (width * height)
        self._last  = time.time()
        self.t      = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = min(now - self._last, 0.1)
        self._last = now

        p = dict(self.params)
        if lfo_signals:
            for k in ("SPEED", "AMPLITUDE"):
                if k in lfo_signals:
                    p[k] = apply_modulation(p[k], lfo_signals[k], PARAMS[k])

        speed     = float(p.get("SPEED",     0.5))
        amplitude = float(p.get("AMPLITUDE", 0.6))
        blur_amt  = int(p.get("BLUR",        8))
        cmap      = COLORMAPS.get(p.get("COLORMAP", "ocean"), list(COLORMAPS.values())[0])

        self.t += dt * speed

        w, h = self.width, self.height

        # Simulated volume: slow beat so waves swell and recede
        vol_norm = beatsin8(11, 0, 255, t=self.t) / 255.0 * amplitude

        # Colour hue advances with time
        hue_base = int(self.t * 30) & 255

        frame = [(0, 0, 0, 0)] * (w * h)

        for x in range(w):
            # Each column gets an independent sine phase → ripple effect
            col_phase = _COL_PHASE[x % 256]

            # bar height: sine envelope shaped by vol_norm
            # The original WLED Waverly draws vertical bars whose height is
            # sinusoidally modulated across columns.
            col_frac = x / max(w - 1, 1)  # 0..1
            envelope = 0.5 + 0.5 * math.sin(col_frac * math.pi)  # taper edges
            raw_h = int(vol_norm * envelope * h)
            bar_h = max(1, min(h, raw_h))

            # Colour for this column (position in palette shifts per column)
            col_hue = (hue_base + col_phase + int(self.t * 18)) & 255
            c = palette_color(cmap, col_hue)

            # Fill from the bottom up
            for y in range(bar_h):
                row = h - 1 - y  # y=0 → bottom row
                # Fade upper pixels so bars have a gradient tip
                bright = 1.0 - (y / bar_h) * 0.5
                pixel  = (int(c[0] * bright), int(c[1] * bright), int(c[2] * bright), 0)
                frame[row * w + x] = pixel

        if blur_amt > 0:
            blur2d(frame, w, h, blur_amt)

        self._frame = frame
        return list(frame)
