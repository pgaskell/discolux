# WLED "Crazy Bees" effect — port of mode_2Dcrazybees()
# Original: "Crazy Bees@!,Blur;;!;2;pal=11,sx=64"
# Bees buzz between random target points, drawing with motion-blur trails.
import math
import time
import random
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, fade_to_black, blur2d
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.4, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "NUM_BEES": {
        "default": 6, "min": 1, "max": 16, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "BLUR": {
        "default": 6, "min": 0, "max": 20, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "warm_rainbow", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

MAX_BEES = 16

class _Bee:
    def __init__(self, w, h, hue):
        self.x   = random.uniform(0, w - 1)
        self.y   = random.uniform(0, h - 1)
        self.tx  = random.uniform(0, w - 1)
        self.ty  = random.uniform(0, h - 1)
        self.hue = hue
        self.w   = w
        self.h   = h
        self._buzz_counter = 0

    def update(self, speed):
        # Buzz toward target with oscillation
        dist = math.hypot(self.tx - self.x, self.ty - self.y)
        if dist < 0.5:
            self.tx = random.uniform(0, self.w - 1)
            self.ty = random.uniform(0, self.h - 1)
        else:
            step = min(dist, 0.3 * speed)
            ang  = math.atan2(self.ty - self.y, self.tx - self.x)
            # Add oscillation perpendicular to motion
            self._buzz_counter += 1
            wagg = math.sin(self._buzz_counter * 0.4) * 0.6
            self.x += math.cos(ang + wagg) * step
            self.y += math.sin(ang + wagg) * step
            self.x  = max(0, min(self.w - 1, self.x))
            self.y  = max(0, min(self.h - 1, self.y))


class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._frame = [(0, 0, 0, 0)] * (width * height)
        self._bees  = []
        self._last  = time.time()
        n = int(self.params.get("NUM_BEES", PARAMS["NUM_BEES"]["default"]))
        for i in range(min(n, MAX_BEES)):
            hue = (i * 256 // MAX_BEES) & 255
            self._bees.append(_Bee(width, height, hue))

    def _ensure_bees(self, n):
        w, h = self.width, self.height
        while len(self._bees) < n:
            hue = random.randint(0, 255)
            self._bees.append(_Bee(w, h, hue))
        while len(self._bees) > n:
            self._bees.pop()

    def render(self, lfo_signals=None):
        now  = time.time()
        dt   = now - self._last
        self._last = now

        speed = self.params["SPEED"]
        n     = max(1, min(MAX_BEES, int(self.params["NUM_BEES"])))
        blur  = int(self.params["BLUR"])
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self._ensure_bees(n)
        w, h = self.width, self.height

        if len(self._frame) != w * h:
            self._frame = [(0, 0, 0, 0)] * (w * h)

        fade_to_black(self._frame, w, h, 50)

        for bee in self._bees[:n]:
            bee.w = w
            bee.h = h
            bee.update(speed)
            xi = max(0, min(w - 1, int(bee.x + 0.5)))
            yi = max(0, min(h - 1, int(bee.y + 0.5)))
            color = palette_color(cmap, bee.hue)
            bee.hue = (bee.hue + 1) & 255
            idx = yi * w + xi
            r = min(255, self._frame[idx][0] + color[0])
            g = min(255, self._frame[idx][1] + color[1])
            b = min(255, self._frame[idx][2] + color[2])
            self._frame[idx] = (r, g, b, 0)

        if blur:
            blur2d(self._frame, w, h, blur * 2)

        return list(self._frame)
