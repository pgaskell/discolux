# WLED "Game Of Life" effect — port of mode_2Dgameoflife()
# Original: "Game Of Life@!,,Blur,,,,,Mutation;!,!;!;2;pal=11,sx=128"
# Conway's Game of Life with palette colouring.
import math
import time
import random
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, blur2d
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 5.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 0, "min": 0, "max": 10, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "matrix_green", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._cells = None
        self._age   = None   # how many generations each alive cell has lived
        self._last_step = time.time()
        self._last_render = time.time()
        self._stagnant = 0
        self._prev_count = -1
        self._frame = []
        self._init_grid()

    def _init_grid(self):
        w, h = self.width, self.height
        self._cells = [[random.random() > 0.55 for _ in range(w)] for _ in range(h)]
        self._age   = [[0] * w for _ in range(h)]
        count = sum(sum(row) for row in self._cells)
        self._prev_count = count
        self._stagnant = 0

    def _step(self):
        w, h = self.width, self.height
        old = self._cells
        new = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                # count live neighbours (wrapped)
                n = sum(
                    old[(y + dy) % h][(x + dx) % w]
                    for dy in (-1, 0, 1)
                    for dx in (-1, 0, 1)
                    if not (dy == 0 and dx == 0)
                )
                alive = old[y][x]
                new[y][x] = (alive and n in (2, 3)) or (not alive and n == 3)
        # update age
        for y in range(h):
            for x in range(w):
                if new[y][x]:
                    self._age[y][x] = min(255, self._age[y][x] + 1)
                else:
                    self._age[y][x] = 0
        self._cells = new
        count = sum(sum(row) for row in new)
        if count == self._prev_count:
            self._stagnant += 1
        else:
            self._stagnant = 0
        self._prev_count = count
        # reset if stuck / dead
        if self._stagnant > 30 or count == 0:
            self._init_grid()

    def render(self, lfo_signals=None):
        now = time.time()
        speed  = self.params["SPEED"]
        blur   = int(self.params["BLUR"])
        cmap   = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        step_interval = 1.0 / max(0.1, speed)
        if now - self._last_step >= step_interval:
            self._step()
            self._last_step = now

        w, h = self.width, self.height
        frame = []
        for y in range(h):
            for x in range(w):
                if self._cells[y][x]:
                    age = self._age[y][x]
                    color = palette_color(cmap, age)
                    frame.append((color[0], color[1], color[2], 0))
                else:
                    frame.append((0, 0, 0, 0))

        if blur:
            blur2d(frame, w, h, blur * 3)

        return frame
