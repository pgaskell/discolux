# WLED "Black Hole" effect — port of mode_2DBlackHole()
# Original: "Black Hole@Fade rate,Outer Y freq.,Outer X freq.,Inner X freq.,Inner Y freq.,Solid,,Blur;!;!;2;pal=11"
# 5 sliders reduced to 4 by merging all 4 frequency sliders into a single SCALE parameter.
# BLUR is kept as an explicit toggle-like slider (0 = off, >0 = on).
# move_x / move_y shifts are driven by beatsin8 at two independent BPMs derived from SCALE,
# matching the outer/inner ring behaviour of the original.
import math, time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, fade_to_black, blur2d, move_x, move_y, beatsin8
from colormaps import COLORMAPS

PARAMS = {
    "FADE_RATE": {
        "default": 0.25, "min": 0.05, "max": 2.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "SCALE": {
        "default": 0.4, "min": 0.05, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 4, "min": 0, "max": 20, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "warm_rainbow", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._frame = [(0, 0, 0, 0)] * (width * height)
        self._last  = time.time()
        self.t      = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self._last
        self._last = now

        fade_rate = self.params["FADE_RATE"]
        scale     = self.params["SCALE"]
        speed     = self.params["SPEED"]
        blur      = int(self.params["BLUR"])
        cmap      = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt * speed
        t = self.t

        w, h = self.width, self.height
        if len(self._frame) != w * h:
            self._frame = [(0, 0, 0, 0)] * (w * h)

        # ---- fade previous content ----
        fade_amt = int(fade_rate * 60)
        fade_to_black(self._frame, w, h, fade_amt)

        # ---- Outer ring: two slow beatsin8 shifts (like WLED move direction 1 & 2) ----
        outer_bpm_x = max(1, int(scale * 7))
        outer_bpm_y = max(1, int(scale * 9))
        dx_outer = int(beatsin8(outer_bpm_x, 0, 3, t=t)) - 1   # -1 .. 2
        dy_outer = int(beatsin8(outer_bpm_y, 0, 3, t=t + 0.5)) - 1

        # ---- Inner ring: faster shifts (like WLED move direction 3 & 4) ----
        inner_bpm_x = max(1, int(scale * 13))
        inner_bpm_y = max(1, int(scale * 11))
        dx_inner = int(beatsin8(inner_bpm_x, 0, 5, t=t + 1.0)) - 2
        dy_inner = int(beatsin8(inner_bpm_y, 0, 5, t=t + 1.7)) - 2

        # Apply outer moves then inner moves (net effect: swirling pull toward centre)
        if dx_outer != 0: move_x(self._frame, w, h, dx_outer)
        if dy_outer != 0: move_y(self._frame, w, h, dy_outer)
        if dx_inner != 0: move_x(self._frame, w, h, dx_inner)
        if dy_inner != 0: move_y(self._frame, w, h, dy_inner)

        # ---- Draw palette-coloured ring and white centre ----
        cx, cy = w // 2, h // 2
        hue = int(t * 40) & 255
        ring_color = palette_color(cmap, hue)
        # ring one pixel out from centre
        for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
            xi, yi = cx + dx, cy + dy
            if 0 <= xi < w and 0 <= yi < h:
                ci = yi * w + xi
                r = min(255, self._frame[ci][0] + ring_color[0] // 3)
                g = min(255, self._frame[ci][1] + ring_color[1] // 3)
                b = min(255, self._frame[ci][2] + ring_color[2] // 3)
                self._frame[ci] = (r, g, b, 0)
        # white centre
        self._frame[cy * w + cx] = (255, 255, 255, 0)

        if blur:
            blur2d(self._frame, w, h, blur * 2)

        return list(self._frame)
