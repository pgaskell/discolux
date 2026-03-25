import math
import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

PARAMS = {
    "NUM_WAVES": {
        "default": 5, "min": 1, "max": 20, "step": 1,
        "modulatable": True,
        "mod_mode": "add"
    },
    "WAVE_SPEED": {
        "default": 0.1, "min": 0.01, "max": 0.2, "step": 0.01,
        "modulatable": True
    },
    "SPATIAL_FREQ": {
        "default": 0.15, "min": 0.01, "max": 0.4, "step": 0.01,
        "modulatable": True,
        "mod_mode": "add"
    },
    "COLOR_CYCLE_SPEED": {
        "default": 0.01, "min": 0.0, "max": 0.5, "step": 0.001,
        "modulatable": True,
        "mod_mode": "add"
    },
    "COLORMAP": {
        "default": "lava_art",
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
        self.waves = []

        # Prepopulate waves
        for _ in range(PARAMS["NUM_WAVES"]["default"]):
            self._spawn_wave()

    def _spawn_wave(self):
        x = random.uniform(0, self.width)
        y = random.uniform(0, self.height)
        self.waves.append((x, y, 0))  # (x, y, age)

    def render(self, lfo_signals=None):
        self.frame_count += 1

        # Params
        num_waves = self.params["NUM_WAVES"]
        wave_speed = self.params["WAVE_SPEED"]
        spatial_freq = self.params["SPATIAL_FREQ"]
        color_shift = self.params["COLOR_CYCLE_SPEED"]

        # Apply modulation
        for key in ("NUM_WAVES", "WAVE_SPEED", "SPATIAL_FREQ", "COLOR_CYCLE_SPEED"):
            meta = self.param_meta.get(key, {})
            if meta.get("modulatable") and meta.get("mod_active"):
                # 1) which signal to use?
                src = meta.get("mod_source")
                # 2) pull out that one float (default 0.0)
                amt = (lfo_signals or {}).get(src, 0.0)
                # 3) scale it to [min…max] according to your mod_mode
                mod_val = apply_modulation(self.params[key], meta, amt)

                # 4) store back into your local variables
                if key == "NUM_WAVES":
                    num_waves      = max(1, int(round(mod_val)))
                elif key == "WAVE_SPEED":
                    wave_speed     = mod_val
                elif key == "SPATIAL_FREQ":
                    spatial_freq   = mod_val
                elif key == "COLOR_CYCLE_SPEED":
                    color_shift    = mod_val

        cmap = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["jet"])
        cmap_len = len(cmap)
        hue_offset = self.frame_count * color_shift

        # Age and spawn waves
        self.waves = [(x, y, age + 1) for x, y, age in self.waves if age < 1000]
        while len(self.waves) < num_waves:
            self._spawn_wave()

        frame = []
        for y in range(self.height):
            for x in range(self.width):
                total = 0.0
                for wx, wy, age in self.waves:
                    dx = x - wx
                    dy = y - wy
                    r = math.hypot(dx, dy)
                    phase = r * spatial_freq - age * wave_speed
                    total += math.sin(phase)
                norm = 0.5 + 0.5 * (total / num_waves)
                hue = (norm + hue_offset) % 1.0
                index = int(hue * (cmap_len - 1))
                r, g, b = cmap[index]
                frame.append((r, g, b, 0))

        return frame
