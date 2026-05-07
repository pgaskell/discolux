# WLED "Spaceships" effect — port of mode_2Dspaceships()
# Original: "Spaceships@!,Blur;;!;2;c2=128"
# Ships bounce around the matrix, leaving fading trails.
import math
import time
import random
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, fade_to_black, blur2d
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "NUM_SHIPS": {
        "default": 4, "min": 1, "max": 12, "step": 1,
        "modulatable": False, "mod_mode": "add"
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

MAX_SHIPS = 12

class _Ship:
    def __init__(self, w, h, hue):
        self.x  = random.uniform(0, w - 1)
        self.y  = random.uniform(0, h - 1)
        self.ax = random.uniform(0, w - 1)   # aim X
        self.ay = random.uniform(0, h - 1)   # aim Y
        self.dx = 0.0
        self.dy = 0.0
        self.hue = hue
        self.w = w
        self.h = h

    def update(self, speed):
        # move toward aim
        self.dx += (self.ax - self.x) * 0.004 * speed
        self.dy += (self.ay - self.y) * 0.004 * speed
        # damping
        self.dx *= 0.97
        self.dy *= 0.97
        self.x = max(0, min(self.w - 1, self.x + self.dx))
        self.y = max(0, min(self.h - 1, self.y + self.dy))
        # pick new aim when close
        if abs(self.x - self.ax) < 0.5 and abs(self.y - self.ay) < 0.5:
            self.ax = random.uniform(0, self.w - 1)
            self.ay = random.uniform(0, self.h - 1)


class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._frame  = [(0, 0, 0, 0)] * (width * height)
        self._ships  = []
        self._last   = time.time()
        n = int(self.params.get("NUM_SHIPS", PARAMS["NUM_SHIPS"]["default"]))
        for i in range(min(n, MAX_SHIPS)):
            hue = (i * 256 // MAX_SHIPS) & 255
            self._ships.append(_Ship(width, height, hue))

    def _ensure_ships(self, n, cmap):
        w, h = self.width, self.height
        while len(self._ships) < n:
            hue = random.randint(0, 255)
            self._ships.append(_Ship(w, h, hue))
        while len(self._ships) > n:
            self._ships.pop()

    def render(self, lfo_signals=None):
        now  = time.time()
        dt   = now - self._last
        self._last = now

        speed = self.params["SPEED"]
        n     = max(1, min(MAX_SHIPS, int(self.params["NUM_SHIPS"])))
        blur  = int(self.params["BLUR"])
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self._ensure_ships(n, cmap)
        w, h = self.width, self.height

        # Resize frame if needed
        if len(self._frame) != w * h:
            self._frame = [(0, 0, 0, 0)] * (w * h)

        fade_to_black(self._frame, w, h, 40)

        for ship in self._ships[:n]:
            ship.w = w
            ship.h = h
            ship.update(speed)
            xi = int(ship.x + 0.5)
            yi = int(ship.y + 0.5)
            xi = max(0, min(w - 1, xi))
            yi = max(0, min(h - 1, yi))
            color = palette_color(cmap, ship.hue)
            idx = yi * w + xi
            self._frame[idx] = (color[0], color[1], color[2], 0)

        if blur:
            blur2d(self._frame, w, h, blur * 2)

        return list(self._frame)
