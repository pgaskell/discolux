# WLED "Akemi" effect — port of mode_2DAkemi()
# Original: "Akemi@Color speed,Dance;Head palette,Arms & Legs,Eyes & Mouth;Face palette;2f;si=0"
#   (audio reactive, FFT)
# Audio (fftResult base) replaced by beatsin8 for standalone operation.
# Parameters reduced to 4: SPEED, DANCE_SPEED, COLORMAP (face), SPRITE (unused).
#
# Faithful WLED rendering:
#   - Full matrix covered by scaled 32×32 sprite
#   - Values 0-8: bg, arms/legs (3 shades), face (3 shades), eyes/mouth, ears
#   - Dancing: frame shifts down 1 row when beat is strong
import math, time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, beatsin8
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add",
        "note": "Face color cycling speed"
    },
    "DANCE_SPEED": {
        "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add",
        "note": "Dance bounce speed (0=static, >0.5=dancing)"
    },
    "COLORMAP": {
        "default": "warm_rainbow", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

# ---------------------------------------------------------------------------
# Akemi 32×32 sprite — exact copy from WLED FX.cpp
# Values:
#   0 = background (black)
#   1 = arms/legs colour, full brightness
#   2 = arms/legs colour × 0.4  (normal)
#   3 = arms/legs colour × 0.15 (light/shadow)
#   4 = face colour, full brightness
#   5 = face colour × 0.4  (normal)
#   6 = face colour × 0.15 (light)
#   7 = eyes/mouth (white)
#   8 = ears (orange, sound-reactive → beatsin)
# WLED renders the full matrix: pixel (x,y) → akemi[(y*32)//rows][(x*32)//cols]
# ---------------------------------------------------------------------------
_AKEMI = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,2,2,2,2,2,2,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,2,2,3,3,3,3,3,3,2,2,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,2,3,3,0,0,0,0,0,0,3,3,2,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,2,3,0,0,0,6,5,5,4,0,0,0,3,2,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,2,3,0,0,6,6,5,5,5,5,4,4,0,0,3,2,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,2,3,0,6,5,5,5,5,5,5,5,5,4,0,3,2,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,2,3,0,6,5,5,5,5,5,5,5,5,5,5,4,0,3,2,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,3,2,0,6,5,5,5,5,5,5,5,5,5,5,4,0,2,3,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,3,2,3,6,5,5,7,7,5,5,5,5,7,7,5,5,4,3,2,3,0,0,0,0,0,0],
    [0,0,0,0,0,2,3,1,3,6,5,1,7,7,7,5,5,1,7,7,7,5,4,3,1,3,2,0,0,0,0,0],
    [0,0,0,0,0,8,3,1,3,6,5,1,7,7,7,5,5,1,7,7,7,5,4,3,1,3,8,0,0,0,0,0],
    [0,0,0,0,0,8,3,1,3,6,5,5,1,1,5,5,5,5,1,1,5,5,4,3,1,3,8,0,0,0,0,0],
    [0,0,0,0,0,2,3,1,3,6,5,5,5,5,5,5,5,5,5,5,5,5,4,3,1,3,2,0,0,0,0,0],
    [0,0,0,0,0,0,3,2,3,6,5,5,5,5,5,5,5,5,5,5,5,5,4,3,2,3,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,6,5,5,5,5,5,7,7,5,5,5,5,5,4,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,6,5,5,5,5,5,5,5,5,5,5,5,5,4,0,0,0,0,0,0,0,0,0],
    [1,0,0,0,0,0,0,0,0,6,5,5,5,5,5,5,5,5,5,5,5,5,4,0,0,0,0,0,0,0,0,2],
    [0,2,2,2,0,0,0,0,0,6,5,5,5,5,5,5,5,5,5,5,5,5,4,0,0,0,0,0,2,2,2,0],
    [0,0,0,3,2,0,0,0,6,5,4,4,4,4,4,4,4,4,4,4,4,4,4,4,0,0,0,2,2,0,0,0],
    [0,0,0,3,2,0,0,0,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,4,0,0,0,2,3,0,0,0],
    [0,0,0,0,3,2,0,0,0,0,3,3,0,3,3,0,0,3,3,0,3,3,0,0,0,0,2,2,0,0,0,0],
    [0,0,0,0,3,2,0,0,0,0,3,2,0,3,2,0,0,3,2,0,3,2,0,0,0,0,2,3,0,0,0,0],
    [0,0,0,0,0,3,2,0,0,3,2,0,0,3,2,0,0,3,2,0,0,3,2,0,0,2,3,0,0,0,0,0],
    [0,0,0,0,0,3,2,2,2,2,0,0,0,3,2,0,0,3,2,0,0,0,3,2,2,2,3,0,0,0,0,0],
    [0,0,0,0,0,0,3,3,3,0,0,0,0,3,2,0,0,3,2,0,0,0,0,3,3,3,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,0,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,0,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,0,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,0,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

_LIGHT  = 0.15   # WLED lightFactor
_NORMAL = 0.40   # WLED normalFactor
_ARMS_LEGS = (255, 224, 160)   # 0xFFE0A0 warm white default
_EYES      = (255, 255, 255)   # white
_EARS_BASE = (255, 165,   0)   # orange


def _apply_ak(ak, face_r, face_g, face_b, base):
    """Map sprite value 0-8 to (R, G, B)."""
    if ak == 0:
        return (0, 0, 0)
    elif ak == 1:
        return _ARMS_LEGS
    elif ak == 2:
        return (int(_ARMS_LEGS[0] * _NORMAL), int(_ARMS_LEGS[1] * _NORMAL), int(_ARMS_LEGS[2] * _NORMAL))
    elif ak == 3:
        return (int(_ARMS_LEGS[0] * _LIGHT),  int(_ARMS_LEGS[1] * _LIGHT),  int(_ARMS_LEGS[2] * _LIGHT))
    elif ak == 4:
        return (face_r, face_g, face_b)
    elif ak == 5:
        return (int(face_r * _NORMAL), int(face_g * _NORMAL), int(face_b * _NORMAL))
    elif ak == 6:
        return (int(face_r * _LIGHT),  int(face_g * _LIGHT),  int(face_b * _LIGHT))
    elif ak == 7:
        return _EYES
    elif ak == 8:
        # ears: orange modulated by beat; stay dim arms colour when quiet
        if base > 0.4:
            s = base
            return (int(_EARS_BASE[0] * s), int(_EARS_BASE[1] * s), 0)
        else:
            return (int(_ARMS_LEGS[0] * _LIGHT), int(_ARMS_LEGS[1] * _LIGHT), int(_ARMS_LEGS[2] * _LIGHT))
    return (0, 0, 0)


class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._last = time.time()
        self.t     = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = min(now - self._last, 0.1)
        self._last = now

        p = dict(self.params)
        if lfo_signals:
            for k in ("SPEED", "DANCE_SPEED"):
                if k in lfo_signals:
                    p[k] = apply_modulation(p[k], lfo_signals[k], PARAMS[k])

        speed       = float(p.get("SPEED",       0.5))
        dance_speed = float(p.get("DANCE_SPEED",  0.4))
        cmap        = COLORMAPS.get(p.get("COLORMAP", "warm_rainbow"), list(COLORMAPS.values())[0])

        self.t += dt
        t = self.t

        w, h = self.width, self.height

        # Face colour cycles via palette (mirrors WLED's color_wheel(counter)).
        # WLED: counter = (ms * ((speed>>2)+2)) >> 8
        # Map our SPEED (0.05-3.0) → WLED speed (0-255).
        speed_wled = int(speed * 85)          # 0-255 approx
        rate = (speed_wled >> 2) + 2          # 2-65, hue ticks per 256ms
        hue  = int(t * rate * (1000.0 / 256)) & 255
        fr, fg, fb = palette_color(cmap, hue)

        # Beat / dance base  (replaces fftResult[0]/255.0)
        dance_bpm = dance_speed * 120.0 + 4.0
        base = beatsin8(dance_bpm, 0, 255, t=t) / 255.0
        dancing = (dance_speed > 0.5 and base > 0.4)

        # Build full frame — WLED maps sprite to entire matrix dimensions.
        frame = [(0, 0, 0, 0)] * (w * h)
        for y in range(h):
            for x in range(w):
                sr = (y * 32) // h
                sc = (x * 32) // w
                ak = _AKEMI[sr][sc]
                rgb = _apply_ak(ak, fr, fg, fb, base)
                frame[y * w + x] = (rgb[0], rgb[1], rgb[2], 0)

        # Dancing: shift entire frame down one row, clear top.
        if dancing:
            shifted = [(0, 0, 0, 0)] * (w * h)
            for y in range(h - 1):
                for x in range(w):
                    shifted[(y + 1) * w + x] = frame[y * w + x]
            frame = shifted

        return frame
