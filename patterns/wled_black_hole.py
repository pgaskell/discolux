# WLED "Black Hole" effect — port of mode_2DBlackHole()
# Original: "Black Hole@Fade rate,Outer Y freq.,Outer X freq.,Inner X freq.,Inner Y freq.,Solid,,Blur;!;!;2;pal=11"
# 8 outer stars + 4 inner stars bounce via beatsin8 with phase spread, additive palette colouring,
# constant medium fade & blur, white centre dot.
# Controls: outer X/Y frequency and inner X/Y frequency.
import math, time
import lfo as _lfo
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, fade_to_black, blur2d, add_color, beatsin8
from colormaps import COLORMAPS

PARAMS = {
    "OUTER_X": {
        "default": 7, "min": 1, "max": 30, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "OUTER_Y": {
        "default": 9, "min": 1, "max": 30, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "INNER_X": {
        "default": 13, "min": 1, "max": 60, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "INNER_Y": {
        "default": 11, "min": 1, "max": 60, "step": 1,
        "modulatable": True, "mod_mode": "add"
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
        self._start = time.time()

    def render(self, lfo_signals=None):
        outer_x = self.params["OUTER_X"]
        outer_y = self.params["OUTER_Y"]
        inner_x = self.params["INNER_X"]
        inner_y = self.params["INNER_Y"]
        cmap    = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key, local in (("OUTER_X", "outer_x"), ("OUTER_Y", "outer_y"),
                           ("INNER_X", "inner_x"), ("INNER_Y", "inner_y")):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "OUTER_X":   outer_x = v
                elif key == "OUTER_Y": outer_y = v
                elif key == "INNER_X": inner_x = v
                elif key == "INNER_Y": inner_y = v

        outer_x = max(0.1, outer_x)
        outer_y = max(0.1, outer_y)
        inner_x = max(0.1, inner_x)
        inner_y = max(0.1, inner_y)

        w, h = self.width, self.height
        if len(self._frame) != w * h:
            self._frame = [(0, 0, 0, 0)] * (w * h)
            self._start  = time.time()

        t = time.time() - self._start

        # Much slower fade
        fade_to_black(self._frame, w, h, 6)

        def paint_star(sx, sy, col):
            """Paint a faded + with bright centre and dimmer arms."""
            # centre — full brightness
            if 0 <= sx < w and 0 <= sy < h:
                self._frame[sy * w + sx] = add_color(self._frame[sy * w + sx][:3], col) + (0,)
            # arm pixels — 40% brightness
            dim = (col[0] * 2 // 5, col[1] * 2 // 5, col[2] * 2 // 5)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                px2, py2 = sx + dx, sy + dy
                if 0 <= px2 < w and 0 <= py2 < h:
                    self._frame[py2 * w + px2] = add_color(self._frame[py2 * w + px2][:3], dim) + (0,)

        # ── 8 outer stars ─────────────────────────────────────────────────
        px = 60.0 / outer_x   # period in seconds for X
        py = 60.0 / outer_y
        for i in range(8):
            off_x = px * ((i % 2) * 0.5 + i * 0.125)
            off_y = py * ((i % 2) * 0.75 + i * 0.125)
            x = beatsin8(outer_x, 0, w - 1, t=t + off_x)
            y = beatsin8(outer_y, 0, h - 1, t=t + off_y)
            hue = (i * 32) & 255
            paint_star(x, y, palette_color(cmap, hue))

        # ── 4 inner stars (constrained to middle half) ─────────────────────
        ix_lo, ix_hi = w // 4, w - 1 - w // 4
        iy_lo, iy_hi = h // 4, h - 1 - h // 4
        px2 = 60.0 / inner_x
        py2 = 60.0 / inner_y
        for i in range(4):
            off_x = px2 * ((i % 2) * 0.5 + i * 0.25)
            off_y = py2 * ((i % 2) * 0.75 + i * 0.25)
            x = beatsin8(inner_x, ix_lo, ix_hi, t=t + off_x)
            y = beatsin8(inner_y, iy_lo, iy_hi, t=t + off_y)
            hue = (255 - i * 64) & 255
            paint_star(x, y, palette_color(cmap, hue))

        # ── central dot — blinks white on each beat, drawn as a + ─────────
        beat_phase = (time.time() * _lfo.BPM / 60.0) % 1.0
        dot_bright = 255 if beat_phase < 0.15 else max(0, int(255 * (1.0 - beat_phase) * 0.5))
        dot_dim = dot_bright * 2 // 5
        cx, cy = w // 2, h // 2
        self._frame[cy * w + cx] = (dot_bright, dot_bright, dot_bright, 0)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            px2, py2 = cx + dx, cy + dy
            if 0 <= px2 < w and 0 <= py2 < h:
                self._frame[py2 * w + px2] = (dot_dim, dot_dim, dot_dim, 0)

        # Heavy blur
        blur2d(self._frame, w, h, 80)

        return list(self._frame)
