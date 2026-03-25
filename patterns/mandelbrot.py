import time, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "ZOOM_SPEED": {
        "default": 0.15, "min": 0.01, "max": 0.5, "step": 0.01,
        "modulatable": True
    },
    "PAN_SPEED": {
        "default": 0.08, "min": 0.0, "max": 0.5, "step": 0.01,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.12, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "ITERATIONS": {
        "default": 24, "min": 8, "max": 64, "step": 1,
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
        self.last_time = time.time()
        self.t = 0.0

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        self.t += dt

        # Params
        zoom_speed = self.params["ZOOM_SPEED"]
        pan_speed = self.params["PAN_SPEED"]
        color_cycle = self.params["COLOR_CYCLE"]
        iterations = int(self.params["ITERATIONS"])
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "ZOOM_SPEED": zoom_speed = mod
                elif key == "PAN_SPEED": pan_speed = mod
                elif key == "COLOR_CYCLE": color_cycle = mod
                elif key == "ITERATIONS": iterations = int(mod)

        w, h = self.width, self.height

        # Animate zoom and pan
        zoom = 1.5 * math.exp(self.t * zoom_speed)
       
        target_cx, target_cy = -0.088, 0.654
        pan_amt = 0.02 / zoom
        pan_x = math.sin(self.t * pan_speed) * pan_amt
        pan_y = math.cos(self.t * pan_speed) * pan_amt
        cx = target_cx + pan_x
        cy = target_cy + pan_y

        # Color cycling
        color_offset = (self.t * color_cycle) % 1.0

        # Prepare LUT if needed
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        frame = []
        for y in range(h):
            for x in range(w):
                # Map pixel to complex plane
                zx = (x - w/2) / (0.5 * zoom * w) + cx
                zy = (y - h/2) / (0.5 * zoom * h) + cy
                c = complex(zx, zy)
                z = 0
                n = 0
                while abs(z) <= 2 and n < iterations:
                    z = z*z + c
                    n += 1
                if n == iterations:
                    # Inside Mandelbrot set: black
                    frame.append((0, 0, 0, 0))
                else:
                    # Smooth coloring
                    v = n - math.log2(math.log2(abs(z) + 1e-8))
                    v = v / iterations
                    hue = (v + color_offset) % 1.0
                    if lut:
                        lut_idx = int(hue * (len(lut) - 1))
                        r, g, b = lut[lut_idx]
                        r = int(r)
                        g = int(g)
                        b = int(b)
                    else:
                        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                        r = int(r * 255)
                        g = int(g * 255)
                        b = int(b * 255)
                    frame.append((r, g, b, 0))
        return frame