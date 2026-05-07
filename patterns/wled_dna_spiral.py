# WLED "DNA Spiral" effect — port of mode_2DDNASpiral()
# Original: "DNA Spiral@Scroll speed,Y frequency,Blur,,,Smear;;!;2;c1=0"
# Scrolling double-helix DNA animation.
import math
import time
from .base import Pattern as BasePattern, apply_modulation
from .wled_helpers import blur2d, palette_color
from colormaps import COLORMAPS

PARAMS = {
    "SCROLL_SPEED": {
        "default": 1.0, "min": -5.0, "max": 5.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "Y_FREQUENCY": {
        "default": 2.0, "min": 0.5, "max": 8.0, "step": 0.1,
        "modulatable": True, "mod_mode": "add"
    },
    "BLUR": {
        "default": 0, "min": 0, "max": 200, "step": 1,
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
        self._last = time.time()
        self.scroll = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self._last
        self._last = now

        scroll_speed = self.params["SCROLL_SPEED"]
        y_freq       = self.params["Y_FREQUENCY"]
        blur         = self.params["BLUR"]
        cmap         = COLORMAPS.get(self.params["COLORMAP"], list(COLORMAPS.values())[0])

        for key in ("SCROLL_SPEED", "Y_FREQUENCY", "BLUR"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                amt = (lfo_signals or {}).get(meta.get("mod_source"), 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "SCROLL_SPEED": scroll_speed = v
                elif key == "Y_FREQUENCY": y_freq = v
                else:                      blur = int(v)

        self.scroll += dt * scroll_speed * 20.0

        w, h = self.width, self.height
        scroll = self.scroll

        frame = [(0, 0, 0, 0)] * (w * h)

        cx = (w - 1) / 2.0
        freq = y_freq * math.pi / h

        for y in range(h):
            phase = y * freq + scroll * 0.2
            # Strand 1: x1 = center + amplitude * sin(phase)
            # Strand 2: x2 = center + amplitude * sin(phase + pi)
            amp = cx * 0.7
            x1 = cx + amp * math.sin(phase)
            x2 = cx + amp * math.sin(phase + math.pi)

            for strand, x in enumerate([x1, x2]):
                xi = int(x)
                if 0 <= xi < w:
                    hue = int(y * 256 / h + scroll + strand * 128) & 255
                    color = palette_color(cmap, hue)
                    frame[y * w + xi] = color + (0,)

                # Cross-link every few pixels
                if (int(y) % max(1, int(h / (y_freq * 2)))) == 0:
                    for xi2 in range(min(w, int(min(x1, x2))), min(w, int(max(x1, x2)) + 1)):
                        if 0 <= xi2 < w:
                            hue = int(y * 256 / h + scroll + 64) & 255
                            color = palette_color(cmap, hue)
                            frame[y * w + xi2] = color + (0,)

        if blur > 0:
            blur2d(frame, w, h, blur)
        return frame
