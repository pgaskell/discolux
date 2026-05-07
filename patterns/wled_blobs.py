# WLED "Blobs" effect — port of mode_2Dfloatingblobs()
# Original: "Blobs@!,# blobs,Blur,Trail;!;!;2;c1=8"
# Bouncing colored blobs of varying radius.
import math
import random
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import blur2d, fade_to_black, fill_circle, palette_color
from colormaps import COLORMAPS

MAX_BLOBS = 8

PARAMS = {
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "NUM_BLOBS": {
        "default": 4, "min": 1, "max": MAX_BLOBS, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 20, "min": 0, "max": 200, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "TRAIL": {
        "default": 40, "min": 0, "max": 200, "step": 1,
        "modulatable": True, "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "warm_rainbow", "options": list(COLORMAPS.keys())
    },
    "SPRITE": {"default": "none", "options": []}
}

class _Blob:
    def __init__(self, w, h):
        self.x  = random.uniform(0, w)
        self.y  = random.uniform(0, h)
        self.vx = random.uniform(-1.5, 1.5) or 0.5
        self.vy = random.uniform(-1.5, 1.5) or 0.5
        self.r  = random.uniform(1, max(1, w / 6.0))
        self.color = random.randint(0, 255)
        self.grow  = True

    def update(self, dt, speed, w, h):
        self.x += self.vx * speed * dt * 10.0
        self.y += self.vy * speed * dt * 10.0
        # Bounce
        if self.x < 0.0:   self.vx = abs(self.vx)
        if self.x > w - 1: self.vx = -abs(self.vx)
        if self.y < 0.0:   self.vy = abs(self.vy)
        if self.y > h - 1: self.vy = -abs(self.vy)
        self.color = (self.color + 1) & 255

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self._last = time.time()
        self._frame = [(0, 0, 0, 0)] * (width * height)
        self._blobs = [_Blob(width, height) for _ in range(MAX_BLOBS)]

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        speed      = self.params["SPEED"]
        num_blobs  = max(1, int(self.params["NUM_BLOBS"]))
        blur       = self.params["BLUR"]
        trail      = self.params["TRAIL"]
        cmap       = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("SPEED", "NUM_BLOBS", "BLUR", "TRAIL"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED":     speed = v
                elif key == "NUM_BLOBS": num_blobs = max(1, int(v))
                elif key == "BLUR":    blur = int(v)
                else:                  trail = int(v)

        w, h = self.width, self.height
        fade_to_black(self._frame, w, h, int(trail))

        for blob in self._blobs[:num_blobs]:
            blob.update(dt, speed, w, h)
            color = palette_color(cmap, blob.color)
            fill_circle(self._frame, w, h, blob.x, blob.y, blob.r, color)

        if blur > 0:
            blur2d(self._frame, w, h, int(blur))
        return list(self._frame)
