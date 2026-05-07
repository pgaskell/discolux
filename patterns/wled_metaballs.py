# WLED "Metaballs" effect — port of mode_2Dmetaballs()
# Original: "Metaballs@!,,Blur;;!;2"
# Classic metaball field: charge sum thresholded into smooth organic blobs.
import math
import time
import random
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, blur2d, beatsin8
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "NUM_BALLS": {
        "default": 4, "min": 2, "max": 8, "step": 1,
        "modulatable": False, "mod_mode": "add"
    },
    "BLUR": {
        "default": 5, "min": 0, "max": 20, "step": 1,
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
        self._last  = time.time()
        self.t      = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt  = now - self._last
        self._last = now

        speed    = self.params["SPEED"]
        n_balls  = max(2, min(8, int(self.params["NUM_BALLS"])))
        blur     = int(self.params["BLUR"])
        cmap     = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt * speed

        w, h = self.width, self.height
        t    = self.t

        # Animate ball positions using beatsin8 at slightly different BPMs
        bpms   = [7, 9, 11, 13, 17, 19, 23, 29]
        balls  = []
        for i in range(n_balls):
            bx = beatsin8(bpms[i]     , 0, w - 1, t=t)
            by = beatsin8(bpms[i] + 4 , 0, h - 1, t=t + i * 0.31)
            balls.append((bx, by))

        frame = []
        for y in range(h):
            for x in range(w):
                total = 0.0
                for (bx, by) in balls:
                    dx   = x - bx
                    dy   = y - by
                    dsq  = dx * dx + dy * dy + 0.001
                    total += 100.0 / dsq
                # Map field value to brightness and colour
                val   = min(255, int(total))
                color = palette_color(cmap, val)
                frame.append((color[0], color[1], color[2], 0))

        if blur:
            blur2d(frame, w, h, blur * 2)

        return frame
