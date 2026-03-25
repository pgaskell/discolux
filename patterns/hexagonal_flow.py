import time, math
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS
import colorsys

PARAMS = {
    "HEX_SIZE": {
        "default": 3.0, "min": 1.0, "max": 8.0, "step": 0.1,
        "modulatable": True
    },
    "WAVE_SPEED": {
        "default": 0.25, "min": 0.01, "max": 2.0, "step": 0.01,
        "modulatable": True
    },
    "COLOR_CYCLE": {
        "default": 0.18, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "DIRECTION": {
        "default": 0.0, "min": 0.0, "max": 6.283, "step": 0.01,  # 0..2pi
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
        hex_size = self.params["HEX_SIZE"]
        wave_speed = self.params["WAVE_SPEED"]
        color_cycle = self.params["COLOR_CYCLE"]
        direction = self.params["DIRECTION"]
        colormap = self.params.get("COLORMAP", "none")

        # Modulation
        for key in PARAMS:
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                mod = apply_modulation(self.params[key], meta, amt)
                if key == "HEX_SIZE": hex_size = mod
                elif key == "WAVE_SPEED": wave_speed = mod
                elif key == "COLOR_CYCLE": color_cycle = mod
                elif key == "DIRECTION": direction = mod

        w, h = self.width, self.height
        lut = COLORMAPS.get(colormap) if colormap != "none" else None

        # Hex grid math
        dx = hex_size * 3/2
        dy = hex_size * math.sqrt(3)

        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0  # Center of the wall

        frame = []
        for y in range(h):
            for x in range(w):
                # Center coordinates
                fx = x - cx
                fy = y - cy

                # Convert centered pixel to hex grid coordinates (axial)
                q = (fx * 2/3) / hex_size
                r = (-fx / 3 + math.sqrt(3)/3 * fy) / hex_size

                # Find center of this hex
                hex_q = round(q)
                hex_r = round(r)
                center_x = hex_size * 3/2 * hex_q
                center_y = hex_size * math.sqrt(3) * (hex_r + hex_q/2)

                # Distance from center of hex (for soft edge)
                dist = math.hypot(fx - center_x, fy - center_y)

                # Wave phase for this hex
                wave_phase = (hex_q * math.cos(direction) + hex_r * math.sin(direction))
                v = math.sin(self.t * wave_speed + wave_phase) * 0.5 + 0.5
                v *= max(0.0, 1.0 - dist / (hex_size * 0.9))  # Soft edge

                hue = ((hex_q + hex_r) * 0.08 + self.t * color_cycle) % 1.0

                if lut:
                    lut_idx = int(hue * (len(lut) - 1))
                    r_c, g_c, b_c = lut[lut_idx]
                    r_c = int(r_c * v)
                    g_c = int(g_c * v)
                    b_c = int(b_c * v)
                else:
                    r_c, g_c, b_c = colorsys.hsv_to_rgb(hue, 1.0, v)
                    r_c = int(r_c * 255)
                    g_c = int(g_c * 255)
                    b_c = int(b_c * 255)
                frame.append((r_c, g_c, b_c, 0))
        return frame