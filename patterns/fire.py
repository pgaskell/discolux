import time, random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

PARAMS = {
    "COOLING": {
        "default": 55, "min": 10, "max": 120, "step": 1,
        "modulatable": True
    },
    "SPARKING": {
        "default": 120, "min": 10, "max": 200, "step": 1,
        "modulatable": True
    },
    "SPEED": {
        "default": 0.25, "min": 0.01, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "COLORMAP": {
        "default": "fire", "options": ["fire"] + list(COLORMAPS.keys()),
        "modulatable": False
    }
}

def get_fire_palette():
    # Use a classic fire palette or fallback to "inferno" if available
    if "fire" in COLORMAPS:
        return COLORMAPS["fire"]
    elif "inferno" in COLORMAPS:
        return COLORMAPS["inferno"]
    else:
        # fallback: simple red-yellow-white
        return [(r, min(255, r*2), 0) for r in range(128)] + [(255, 255, min(255, (i-128)*4)) for i in range(128,256)]

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.last_time = time.time()
        self.t = 0.0
        self.heat = [0] * (self.width * self.height)

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        self.t += dt

        cooling = self.params["COOLING"]
        sparking = self.params["SPARKING"]
        speed = self.params["SPEED"]
        color_cycle = self.params["COLOR_CYCLE"]
        colormap = self.params.get("COLORMAP", "fire")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "COOLING": cooling = int(mod)
                elif key == "SPARKING": sparking = int(mod)
                elif key == "SPEED": speed = mod
                elif key == "COLOR_CYCLE": color_cycle = mod

        w, h = self.width, self.height
        palette = COLORMAPS.get(colormap) if colormap in COLORMAPS else get_fire_palette()
        palette_len = len(palette)

        # Step 1. Cool down every cell a little
        for x in range(w):
            for y in range(h):
                idx = y * w + x
                cooldown = random.randint(0, ((cooling * 10) // h) + 2)
                self.heat[idx] = max(0, self.heat[idx] - cooldown)

        # Step 2. Heat from each cell drifts up and diffuses a little
        for x in range(w):
            for y in range(h-1, 1, -1):
                idx = y * w + x
                below = (y-1) * w + x
                below2 = (y-2) * w + x
                self.heat[idx] = (self.heat[below] + self.heat[below2] + self.heat[idx]) // 3

        # Step 3. Randomly ignite new sparks at the bottom
        for x in range(w):
            if random.randint(0, 255) < sparking:
                idx = x
                self.heat[idx] = min(255, self.heat[idx] + random.randint(160, 255))

        # Step 4. Map heat to color
        frame = []
        for y in range(h):
            for x in range(w):
                idx = y * w + x
                coloridx = int((self.heat[idx] / 255.0) * (palette_len - 1))
                r, g, b = palette[coloridx]
                # Optionally cycle color
                if color_cycle > 0.0:
                    hue_shift = (self.t * color_cycle) % 1.0
                    # Simple HSV shift
                    import colorsys
                    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
                    h = (h + hue_shift) % 1.0
                    r, g, b = colorsys.hsv_to_rgb(h, s, v)
                    r = int(r * 255)
                    g = int(g * 255)
                    b = int(b * 255)
                frame.append((int(r), int(g), int(b), 0))
        return frame