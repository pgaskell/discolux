"""
wled_helpers.py
Python equivalents of WLED's FX_2Dfcn.cpp helper functions.
Used by wled_*.py pattern files.
"""
import math
import time

# ---------------------------------------------------------------------------
# Permutation table for value-noise (built once at import)
# ---------------------------------------------------------------------------
import random as _rnd

_P = list(range(256))
_rnd.shuffle(_P)
_P = _P + _P  # duplicate so _P[i+1] never wraps

def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

def _lerp(t, a, b):
    return a + t * (b - a)

def _grad2(h, x, y):
    h = h & 3
    if h == 0: return  x + y
    if h == 1: return -x + y
    if h == 2: return  x - y
    return -x - y

def pnoise2(x, y):
    """2D Perlin noise, returns –1…1."""
    xi = int(math.floor(x)) & 255
    yi = int(math.floor(y)) & 255
    xf = x - math.floor(x)
    yf = y - math.floor(y)
    u, v = _fade(xf), _fade(yf)
    aa = _P[_P[xi    ] + yi    ]
    ab = _P[_P[xi    ] + yi + 1]
    ba = _P[_P[xi + 1] + yi    ]
    bb = _P[_P[xi + 1] + yi + 1]
    x1 = _lerp(u, _grad2(aa, xf,     yf    ), _grad2(ba, xf - 1,     yf    ))
    x2 = _lerp(u, _grad2(ab, xf,     yf - 1), _grad2(bb, xf - 1,     yf - 1))
    return _lerp(v, x1, x2)

def inoise8(x, y, z=0.0, scale=0.04):
    """
    WLED inoise8 analogue: returns 0…255.
    x, y are pixel coords; z is time offset.
    """
    n = pnoise2(x * scale + z * 0.1, y * scale + z * 0.07)
    return int(max(0, min(255, (n + 1.0) * 127.5)))

# ---------------------------------------------------------------------------
# 8-bit trig helpers (matching WLED's sin8 / cos8)
# sin8(0…255) → 0…255  (0 → 0, 128 → 255, 255 → 0 roughly)
# ---------------------------------------------------------------------------
_SIN8 = [int(128 + 127.5 * math.sin(i * math.pi / 128.0)) for i in range(256)]
_COS8 = [int(128 + 127.5 * math.cos(i * math.pi / 128.0)) for i in range(256)]

def sin8(x: int) -> int:
    return _SIN8[int(x) & 255]

def cos8(x: int) -> int:
    return _COS8[int(x) & 255]

# ---------------------------------------------------------------------------
# Beat / timing helpers
# ---------------------------------------------------------------------------
def beat8(bpm: float, t: float = None) -> int:
    """Sawtooth 0…255 cycling at bpm beats-per-minute."""
    if t is None:
        t = time.time()
    period = 60.0 / max(bpm, 0.001)
    return int((t % period) / period * 255) & 255

def beatsin8(bpm: float, low: int = 0, high: int = 255, t: float = None) -> int:
    """Sine wave at bpm mapped to [low, high]."""
    if t is None:
        t = time.time()
    period = 60.0 / max(bpm, 0.001)
    s = 0.5 + 0.5 * math.sin(2.0 * math.pi * t / period)
    return int(low + s * (high - low))

def time_ms() -> float:
    return time.time() * 1000.0

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
def blend_color(a, b, frac: float):
    """Linear blend between color tuples a and b. frac 0→a, 1→b."""
    r = int(a[0] + frac * (b[0] - a[0]))
    g = int(a[1] + frac * (b[1] - a[1]))
    bl = int(a[2] + frac * (b[2] - a[2]))
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, bl)))

def add_color(a, b):
    return (min(255, a[0] + b[0]), min(255, a[1] + b[1]), min(255, a[2] + b[2]))

def scale_color(c, amount: float):
    """Multiply all channels by amount (0…1)."""
    return (int(c[0] * amount), int(c[1] * amount), int(c[2] * amount))

def palette_color(cmap: list, pos: int) -> tuple:
    """
    Sample a colormap (list of (R,G,B)) at byte position 0…255.
    Returns (R, G, B).
    """
    if not cmap:
        return (0, 0, 0)
    idx = (int(pos) & 255) * (len(cmap) - 1) / 255.0
    lo = int(idx)
    hi = min(lo + 1, len(cmap) - 1)
    frac = idx - lo
    return blend_color(cmap[lo], cmap[hi], frac)

# ---------------------------------------------------------------------------
# 2D frame operations  (frame is a flat list of (R,G,B,0) of length w*h)
# ---------------------------------------------------------------------------
def fade_to_black(frame: list, w: int, h: int, amount: int):
    """
    Dim every pixel in-place.  amount 0=no fade, 255=full black immediately.
    Equivalent to WLED's fadeToBlackBy.
    """
    scale = (255 - amount) / 255.0
    for i in range(w * h):
        r, g, b, _ = frame[i]
        frame[i] = (int(r * scale), int(g * scale), int(b * scale), 0)

def blur2d(frame: list, w: int, h: int, amount: int = 64, smear: bool = False):
    """
    Equivalent to WLED blur2D.
    A simple 3×3 box-blur scaled by amount (0=no blur, 255=max).
    """
    if amount == 0:
        return
    keep = 255 - amount
    spread = amount >> 1

    # horizontal pass
    temp = list(frame)
    for y in range(h):
        for x in range(w):
            i = y * w + x
            r0, g0, b0, _ = frame[i]
            r = r0 * keep
            g = g0 * keep
            b = b0 * keep
            if x > 0:
                rp, gp, bp, _ = frame[i - 1]
                r += rp * spread; g += gp * spread; b += bp * spread
            if x < w - 1:
                rn, gn, bn, _ = frame[i + 1]
                r += rn * spread; g += gn * spread; b += bn * spread
            temp[i] = (min(255, r >> 8), min(255, g >> 8), min(255, b >> 8), 0)

    # vertical pass
    for x in range(w):
        for y in range(h):
            i = y * w + x
            r0, g0, b0, _ = temp[i]
            r = r0 * keep
            g = g0 * keep
            b = b0 * keep
            if y > 0:
                rp, gp, bp, _ = temp[(y-1)*w + x]
                r += rp * spread; g += gp * spread; b += bp * spread
            if y < h - 1:
                rn, gn, bn, _ = temp[(y+1)*w + x]
                r += rn * spread; g += gn * spread; b += bn * spread
            frame[i] = (min(255, r >> 8), min(255, g >> 8), min(255, b >> 8), 0)

def move_x(frame: list, w: int, h: int, delta: int):
    """Shift frame horizontally by delta pixels (positive = right)."""
    result = [(0, 0, 0, 0)] * (w * h)
    for y in range(h):
        for x in range(w):
            src_x = (x - delta) % w
            result[y * w + x] = frame[y * w + src_x]
    frame[:] = result

def move_y(frame: list, w: int, h: int, delta: int):
    """Shift frame vertically by delta pixels (positive = down)."""
    result = [(0, 0, 0, 0)] * (w * h)
    for y in range(h):
        src_y = (y - delta) % h
        for x in range(w):
            result[y * w + x] = frame[src_y * w + x]
    frame[:] = result

def draw_line(frame: list, w: int, h: int, x0: int, y0: int, x1: int, y1: int,
              color: tuple):
    """Bresenham line draw into frame."""
    dx = abs(x1 - x0); dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            frame[y0 * w + x0] = color + (0,)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; x0 += sx
        if e2 < dx:
            err += dx; y0 += sy

def draw_circle(frame: list, w: int, h: int, cx: int, cy: int, r: int, color: tuple):
    """Bresenham circle (outline only)."""
    x, y = 0, r
    d = 3 - 2 * r
    while y >= x:
        for px, py in [(cx+x, cy+y),(cx-x, cy+y),(cx+x, cy-y),(cx-x, cy-y),
                       (cx+y, cy+x),(cx-y, cy+x),(cx+y, cy-x),(cx-y, cy-x)]:
            if 0 <= px < w and 0 <= py < h:
                frame[py * w + px] = color + (0,)
        x += 1
        if d > 0:
            y -= 1; d += 4 * (x - y) + 10
        else:
            d += 4 * x + 6

def fill_circle(frame: list, w: int, h: int, cx: float, cy: float, r: float,
                color: tuple):
    """Filled circle."""
    r2 = r * r
    x0 = max(0, int(cx - r))
    x1 = min(w - 1, int(cx + r))
    y0 = max(0, int(cy - r))
    y1 = min(h - 1, int(cy + r))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                frame[y * w + x] = color + (0,)
