# WLED "Swirl" effect — port of mode_2DSwirl()
# Original: "Swirl@!,Sensitivity,Blur;,Bg Swirl;!;2v;ix=64,si=0"  (audio reactive)
# Audio (volumeRaw used for colour weight) replaced by beatsin8 — creates an autonomous
# swirling vortex whose intensity pulses with an internal beat.
# 3 original sliders kept: SPEED, BLUR, TWIST (= Sensitivity).
import math, time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import palette_color, blur2d, beatsin8, sin8, cos8
from colormaps import COLORMAPS

PARAMS = {
    "SPEED": {
        "default": 0.5, "min": 0.05, "max": 3.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add"
    },
    "TWIST": {
        "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05,
        "modulatable": True, "mod_mode": "add",
        "note": "Equivalent to Sensitivity in original"
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

        speed = self.params["SPEED"]
        twist = self.params["TWIST"]
        blur  = int(self.params["BLUR"])
        cmap  = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        self.t += dt * speed
        t      = self.t

        w, h = self.width, self.height
        if len(self._frame) != w * h:
            self._frame = [(0, 0, 0, 0)] * (w * h)

        cx = (w - 1) / 2.0
        cy = (h - 1) / 2.0

        # Simulated "volume" — pulsing beat replaces audio input
        # WLED: colour weight = volumeRaw * intensity / 64
        # Here: same idea but driven by beatsin8
        vol_norm = beatsin8(13, 0, 255, t=t) / 255.0  # 0..1

        # WLED original: for each pixel rotate its position toward a swirl attractor
        # We copy that by doing an angular shear on the persistent frame every tick.

        # Time-varying twist amount (in radians per unit distance)
        twist_amt = twist * vol_norm * 0.5 * math.pi / max(cx, cy)

        new_frame = [(0, 0, 0, 0)] * (w * h)
        for y in range(h):
            for x in range(w):
                dx = x - cx
                dy = y - cy
                r  = math.sqrt(dx * dx + dy * dy) + 0.001
                # rotate by twist_amt * r radians
                angle = math.atan2(dy, dx) + twist_amt * r
                # fade slightly inward (black hole style pull)
                src_r  = r * (1.0 + 0.015)
                sx     = cx + src_r * math.cos(angle)
                sy     = cy + src_r * math.sin(angle)
                xi = int(sx + 0.5)
                yi = int(sy + 0.5)
                if 0 <= xi < w and 0 <= yi < h:
                    new_frame[y * w + x] = self._frame[yi * w + xi]

        # Fade
        fade = 20
        for i in range(len(new_frame)):
            r2, g2, b2, _ = new_frame[i]
            new_frame[i] = (max(0, r2 - fade), max(0, g2 - fade), max(0, b2 - fade), 0)

        # Draw new energy at random positions — scaled by simulated volume
        num_sparks = max(1, int(vol_norm * 8))
        import random
        for _ in range(num_sparks):
            # Spawn near centre, angle driven by time
            angle   = t * 3.7 + random.random() * math.pi * 2
            r_spawn = random.gauss(0, (w + h) * 0.15)
            sx = int(cx + r_spawn * math.cos(angle))
            sy = int(cy + r_spawn * math.sin(angle))
            if 0 <= sx < w and 0 <= sy < h:
                hue = int(t * 60 + angle * 40) & 255
                color = palette_color(cmap, hue)
                idx = sy * w + sx
                r2 = min(255, new_frame[idx][0] + color[0])
                g2 = min(255, new_frame[idx][1] + color[1])
                b2 = min(255, new_frame[idx][2] + color[2])
                new_frame[idx] = (r2, g2, b2, 0)

        self._frame = new_frame

        if blur:
            blur2d(self._frame, w, h, blur * 2)

        return list(self._frame)
