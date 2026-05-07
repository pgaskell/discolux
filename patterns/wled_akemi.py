# WLED "Akemi" effect — port of mode_2DAkemi()
# Original: "Akemi@Color speed,Dance;Head palette,Arms & Legs,Eyes & Mouth;Face palette;2f;si=0"
#   (audio reactive, FFT)
# Audio (FFT dance) replaced by beatsin8 — character dances autonomously.
# Original 2 sliders kept (SPEED, DANCE_SPEED); COLORMAP added as 3rd param (≤4).
#
# Drawing mirrors the WLED convention:
#   - Only the top half of the matrix is used (rows 0 … rows//2-1)
#   - The akemi sprite is a 32×32 array (0=bg, 1=face, 2=arms/legs, 3=eyes/hair)
#   - x-axis is mirrored (setPixelXY at cols-1-x to create symmetric character)
import math, time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, beatsin8, sin8
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add",
        "note": "Color cycling speed (hue advance rate)"
    },
    "DANCE_SPEED": {
        "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add",
        "note": "Animation speed of arms/dance motion"
    },
    "COLORMAP": {
        "default": "warm_rainbow", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

# ---------------------------------------------------------------------------
# Akemi 32×32 sprite
# Encoding: 0 = background, 1 = face/skin, 2 = arms/body/legs, 3 = dark (eyes/hair)
# The right-half character — WLED renders at cols-1-x so this appears on the
# right side, and the mirrored column fills the left side.
# ---------------------------------------------------------------------------
_AKEMI = [
    # Row  0 – top of head
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    # Row  1
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    # Row  2 – hair crown
    [0,0,0,0,0,0,0,0,0,0,0,0,3,3,3,3,3,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0],
    # Row  3 – hair
    [0,0,0,0,0,0,0,0,0,0,3,3,3,3,3,3,3,3,3,3,3,3,0,0,0,0,0,0,0,0,0,0],
    # Row  4 – cat ear
    [0,0,0,0,0,0,0,0,0,3,3,0,3,3,3,3,3,3,3,0,3,3,3,0,0,0,0,0,0,0,0,0],
    # Row  5 – forehead
    [0,0,0,0,0,0,0,0,3,3,1,1,1,1,1,1,1,1,1,1,1,3,3,0,0,0,0,0,0,0,0,0],
    # Row  6 – face
    [0,0,0,0,0,0,0,3,3,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,0,0,0,0,0,0,0,0],
    # Row  7 – eyes (brow)
    [0,0,0,0,0,0,3,3,1,1,1,3,3,3,1,1,1,1,3,3,3,1,1,3,3,0,0,0,0,0,0,0],
    # Row  8 – eyes (pupil)
    [0,0,0,0,0,0,3,3,1,1,1,3,3,3,1,1,1,1,3,3,3,1,1,3,3,0,0,0,0,0,0,0],
    # Row  9 – nose
    [0,0,0,0,0,0,3,3,1,1,1,1,1,1,1,3,1,3,1,1,1,1,1,3,3,0,0,0,0,0,0,0],
    # Row 10 – smile
    [0,0,0,0,0,0,3,1,1,1,1,1,3,1,1,1,1,1,1,1,3,1,1,1,3,0,0,0,0,0,0,0],
    # Row 11 – chin
    [0,0,0,0,0,0,0,3,3,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,0,0,0,0,0,0,0,0],
    # Row 12 – neck
    [0,0,0,0,0,0,0,0,3,3,1,1,1,1,1,1,1,1,1,1,1,3,3,0,0,0,0,0,0,0,0,0],
    # Row 13 – shoulders
    [0,0,2,2,2,2,2,2,2,3,1,1,1,1,1,1,1,1,1,1,3,2,2,2,2,2,2,2,0,0,0,0],
    # Row 14 – upper body
    [0,0,2,2,2,2,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,2,2,2,0,0,0,0,0],
    # Row 15 – body
    [0,0,0,2,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,2,0,0,0,0,0,0],
    # Row 16 – body
    [0,0,0,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,0,0,0,0,0,0,0],
    # Row 17 – arms out (static base; dance offset applied at render time)
    [0,2,2,2,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,2,2,2,0,0,0,0],
    # Row 18 – hands
    [3,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,3,0,0,0],
    # Row 19 – gap
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    # Row 20 – hips
    [0,0,0,0,0,0,2,2,2,1,1,1,0,0,0,0,0,0,0,0,1,1,2,2,2,0,0,0,0,0,0,0],
    # Row 21 – upper legs
    [0,0,0,0,0,0,0,2,2,1,1,0,0,0,0,0,0,0,0,0,0,1,1,2,2,0,0,0,0,0,0,0],
    # Row 22 – legs
    [0,0,0,0,0,0,0,0,2,2,1,1,0,0,0,0,0,0,0,0,1,1,2,2,0,0,0,0,0,0,0,0],
    # Row 23 – legs (bend)
    [0,0,0,0,0,0,0,0,2,2,2,1,1,0,0,0,0,0,0,1,1,2,2,2,0,0,0,0,0,0,0,0],
    # Row 24 – knees
    [0,0,0,0,0,0,0,0,0,2,2,2,1,1,0,0,0,0,1,1,2,2,2,0,0,0,0,0,0,0,0,0],
    # Row 25 – lower legs
    [0,0,0,0,0,0,0,0,0,2,2,1,1,1,0,0,0,0,1,1,2,2,2,0,0,0,0,0,0,0,0,0],
    # Row 26 – ankles
    [0,0,0,0,0,0,0,0,0,0,2,2,2,1,1,0,0,1,1,2,2,2,0,0,0,0,0,0,0,0,0,0],
    # Row 27 – feet
    [0,0,0,0,0,0,0,0,0,0,2,2,2,2,1,1,1,1,2,2,2,0,0,0,0,0,0,0,0,0,0,0],
    # Row 28 – shoe
    [0,0,0,0,0,0,0,0,0,0,0,2,2,2,2,2,2,2,2,2,0,0,0,0,0,0,0,0,0,0,0,0],
    # Row 29 – shoe lower
    [0,0,0,0,0,0,0,0,0,0,0,0,2,2,2,2,2,2,2,0,0,0,0,0,0,0,0,0,0,0,0,0],
    # Row 30 – shoe tips
    [0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,2,2,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    # Row 31 – last row (matches WLED source: pos 13→3, pos 14→2)
    [0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

# Flatten to 1D for fast index access (matches WLED's linear akemi[] array)
_AKEMI_FLAT = [v for row in _AKEMI for v in row]


class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._last   = time.time()
        self.t       = 0.0
        self._blink  = False  # eye blink state
        self._blink_timer = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = min(now - self._last, 0.1)
        self._last = now

        p = dict(self.params)
        if lfo_signals:
            for k in ("SPEED", "DANCE_SPEED"):
                if k in lfo_signals:
                    p[k] = apply_modulation(p[k], lfo_signals[k], PARAMS[k])

        speed       = float(p.get("SPEED",      0.5))
        dance_speed = float(p.get("DANCE_SPEED", 0.4))
        cmap        = COLORMAPS.get(p.get("COLORMAP", "warm_rainbow"), list(COLORMAPS.values())[0])

        self.t += dt * speed

        w, h = self.width, self.height

        # Colour cycle counter (0…255), used for face palette
        counter = int(self.t * 40) & 255

        # Face colour from palette
        face_color   = palette_color(cmap, counter)
        body_color   = (80, 80, 200)   # blue-ish arms/legs (WLED SEGCOLOR(1) default: Arms & Legs)
        dark_color   = (200, 100,  20)  # warm dark for eyes/hair (WLED SEGCOLOR(2) default: Eyes & Mouth)

        # Blink timer: open for ~2s, closed for ~0.1s
        self._blink_timer += dt
        if self._blink_timer > (0.1 if self._blink else 2.0):
            self._blink = not self._blink
            self._blink_timer = 0.0

        # Dance offset: arms bob slightly using beatsin8
        # dance_vol simulates the beat/dance stimulus
        dance_vol = beatsin8(60 * dance_speed + 4, 0, 255, t=self.t) / 255.0

        frame = [(0, 0, 0, 0)] * (w * h)

        # WLED draws akemi in the TOP HALF only (rows 0..h//2-1)
        # Coordinate transform from WLED:
        #   screen_y = rows//2 - y   (y=0 → middle row, y=rows//2 → top row)
        #   screen_x = cols-1-x      (x-mirrored)
        # We iterate y from 0..h//2 inclusive, x from 0..w-1
        half_h = max(1, h // 2)

        for y in range(half_h + 1):
            sy = half_h - y  # screen row: 0 (top) to half_h (center)
            if sy < 0 or sy >= h:
                continue

            ak_row = min(31, (y * 32) // max(1, half_h))

            for x in range(w):
                ak_col = min(31, (x * 32) // max(1, w))
                ak = _AKEMI_FLAT[ak_row * 32 + ak_col]

                if ak == 0:
                    color = (0, 0, 0, 0)
                elif ak == 1:
                    color = (*face_color, 0)
                elif ak == 2:
                    # Dance: shift body brightness using dance_vol
                    bright = 0.6 + 0.4 * dance_vol
                    color = (int(body_color[0] * bright),
                             int(body_color[1] * bright),
                             int(body_color[2] * bright), 0)
                else:  # ak == 3
                    if self._blink:
                        # Blink: eyes become face color
                        color = (*face_color, 0)
                    else:
                        color = (*dark_color, 0)

                # Mirror: draw at both (cols-1-x) and the original x
                sx = (w - 1 - x)
                if 0 <= sx < w:
                    frame[sy * w + sx] = color

        return frame
