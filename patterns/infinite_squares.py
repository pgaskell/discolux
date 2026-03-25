import time, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 12.0, "step": 0.05,
        "modulatable": True
    },
    "THICKNESS": {
        "default": 1.0, "min": 0.5, "max": 4.0, "step": 0.1,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.15, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "SPACING": {
        "default": 3.0, "min": 1.0, "max": 10.0, "step": 0.1,
        "modulatable": True
    },
    "COLORMAP": {
        "default": "none", "options": ["none"] + list(COLORMAPS.keys()),
        "modulatable": False
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.squares = []
        self.last_time = time.time()
        self.base_hue = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        # Params
        speed = self.params["SPEED"]
        thickness = self.params["THICKNESS"]
        color_cycle = self.params["COLOR_CYCLE"]
        spacing = self.params["SPACING"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "SPEED": speed = mod
                elif key == "THICKNESS": thickness = mod
                elif key == "COLOR_CYCLE": color_cycle = mod
                elif key == "SPACING": spacing = mod

        w, h = self.width, self.height
        cx, cy = (w-1)/2.0, (h-1)/2.0
        
        max_radius = max(
            abs(cx - 0), abs(cx - (w - 1)),
            abs(cy - 0), abs(cy - (h - 1))
        )

        # Update base hue
        self.base_hue = (self.base_hue + color_cycle * dt) % 1.0

        # Spawn new square if needed
        if not self.squares or (self.squares and self.squares[-1]["radius"] > spacing):
            self.squares.append({"radius": 0.0, "hue": self.base_hue})

        # Update squares
        for sq in self.squares:
            sq["radius"] += speed * dt

        # Remove squares that are out of bounds
        self.squares = [sq for sq in self.squares if sq["radius"] < max_radius + thickness]

        # Prepare frame
        frame = []
        lut = COLORMAPS.get(colormap) if colormap != "none" else None
        for y in range(h):
            for x in range(w):
                dx, dy = abs(x - cx), abs(y - cy)
                dist = max(dx, dy)
                val = 0.0
                hue = 0.0
                for sq in self.squares:
                    edge = abs(dist - sq["radius"])
                    if edge < thickness:
                        fade = max(0.0, 1.0 - edge / thickness)
                        if fade > val:
                            val = fade
                            hue = sq["hue"]
                if val > 0:
                    if lut:
                        # Use LUT: hue is 0..1, val is brightness
                        lut_idx = int(hue * (len(lut) - 1))
                        r, g, b = lut[lut_idx]
                        r = int(r * val)
                        g = int(g * val)
                        b = int(b * val)
                    else:
                        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, val)
                        r = int(r * 255)
                        g = int(g * 255)
                        b = int(b * 255)
                    frame.append((r, g, b, 0))
                else:
                    frame.append((0, 0, 0, 0))
        return frame