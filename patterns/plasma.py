import math
import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

PARAMS = {
    "NUM_GENERATORS": {
        "default": 3, "min": 1, "max": 8, "step": 1,
        "modulatable": True,
        "mod_mode": "add"
    },
    "MOVE_SPEED": {
        "default": 0.01, "min": -0.6, "max": 0.6, "step": 0.01,
        "modulatable": True,
        "mod_mode": "add"
    },
    "COLOR_CYCLE_SPEED": {
        "default": 0.0, "min": -0.1, "max": 0.1, "step": 0.001,
        "modulatable": True,
        "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "warm_rainbow",
        "options": list(COLORMAPS.keys())
    },
    "SPRITE": {
        "default": "none",
        "options": []
    }
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.frame_count = 0

        # Pre-randomize generator parameters
        self.generators = []
        for _ in range(PARAMS["NUM_GENERATORS"]["default"]):
            angle = random.uniform(0, 2 * math.pi)
            freq = random.uniform(0.05, 0.2)
            phase = random.uniform(0, 2 * math.pi)
            self.generators.append((angle, freq, phase))

    def render(self, lfo_signals=None):
        self.frame_count += 1

        # Parameters
        num_gen = self.params["NUM_GENERATORS"]
        move_speed = self.params["MOVE_SPEED"]
        cycle_speed = self.params["COLOR_CYCLE_SPEED"]

        # Apply modulation
        for key in ("NUM_GENERATORS", "MOVE_SPEED", "COLOR_CYCLE_SPEED"):
            meta = self.param_meta.get(key, {})
            if meta.get("modulatable") and meta.get("mod_active"):
                # 1) Identify which LFO/ENV source to use
                src = meta.get("mod_source")
                # 2) Grab that one numeric value (default 0.0)
                amt = (lfo_signals or {}).get(src, 0.0)
                # 3) Compute the new, scaled parameter
                mod_val = apply_modulation(self.params[key], meta, amt)

                # 4) Assign back
                if key == "NUM_GENERATORS":
                    num_gen     = max(1, int(round(mod_val)))
                elif key == "MOVE_SPEED":
                    move_speed  = mod_val
                elif key == "COLOR_CYCLE_SPEED":
                    cycle_speed = mod_val

        cmap = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["jet"])
        cmap_len = len(cmap)

        t = self.frame_count * move_speed
        hue_shift = self.frame_count * cycle_speed

        # Ensure enough generators
        while len(self.generators) < num_gen:
            angle = random.uniform(0, 2 * math.pi)
            freq = random.uniform(0.05, 0.2)
            phase = random.uniform(0, 2 * math.pi)
            self.generators.append((angle, freq, phase))

        frame = []
        for y in range(self.height):
            for x in range(self.width):
                value = 0.0
                for i in range(num_gen):
                    angle, freq, phase = self.generators[i]
                    dx = x - self.width / 2
                    dy = y - self.height / 2
                    dist = dx * math.cos(angle) + dy * math.sin(angle)
                    value += math.sin(freq * dist + phase + t)
                normalized = 0.5 + 0.5 * (value / num_gen)
                index = int((normalized + hue_shift) * (cmap_len - 1)) % cmap_len
                r, g, b = cmap[index]
                frame.append((r, g, b, 0))

        return frame
