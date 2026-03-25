# patterns/game_of_life.py
import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# ─── Adjustable Parameters ────────────────────────────────────────────────
PARAMS = {
    "UPDATE_RATE": {
        "default": 1.0,  "min": 0.1,  "max": 10.0,  "step": 0.1,
        "modulatable": True
    },
    "DENSITY": {
        "default": 0.2,  "min": 0.0,  "max": 1.0,   "step": 0.01,
        "modulatable": True
    },
    "BIRTH_RATE": {
        "default": 0.0,  "min": 0.0,  "max": 0.2,   "step": 0.01,
        "modulatable": True
    },
    "DEATH_RATE": {
        "default": 0.0,  "min": 0.0,  "max": 0.2,   "step": 0.01,
        "modulatable": True
    },
    "COLORMAP": {
        "default": "jet",
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
        # hook up our PARAMS for modulation
        self.param_meta = PARAMS

        # simulation state
        self.cells = [[False]*width for _ in range(height)]
        self.next_cells = [[False]*width for _ in range(height)]
        self.time_accum = 0.0

        # seed initial grid
        density = self.params["DENSITY"]
        for y in range(self.height):
            for x in range(self.width):
                self.cells[y][x] = (random.random() < density)

        self.frame_count = 0

    def step(self, birth, death):
        # one Game-of-Life generation step, with random birth/death
        H, W = self.height, self.width
        for y in range(H):
            for x in range(W):
                # count live neighbors (with wrap-around)
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx==0 and dy==0: continue
                        if self.cells[(y+dy)%H][(x+dx)%W]:
                            cnt += 1

                alive = self.cells[y][x]
                if alive:
                    # standard survival
                    new_state = (cnt == 2 or cnt == 3)
                    # random death
                    if death > 0 and random.random() < death:
                        new_state = False
                else:
                    # standard birth
                    new_state = (cnt == 3)
                    # random birth
                    if birth > 0 and random.random() < birth:
                        new_state = True

                self.next_cells[y][x] = new_state

        # swap buffers
        self.cells, self.next_cells = self.next_cells, self.cells

    def render(self, lfo_signals=None):
        self.frame_count += 1

        # ── 1) read & apply modulation ──────────────────────────────
        rate  = self.params["UPDATE_RATE"]
        birth = self.params["BIRTH_RATE"]
        death = self.params["DEATH_RATE"]
        # apply any active LFO/ENV mods
        for key in ("UPDATE_RATE", "DENSITY", "BIRTH_RATE", "DEATH_RATE"):
            meta = self.param_meta.get(key, {})
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                v = apply_modulation(self.params[key], meta, amt)
                if key == "UPDATE_RATE":
                    rate = v
                elif key == "DENSITY":
                    # (not re-seeding after init, but could be used for dynamic effects)
                    pass
                elif key == "BIRTH_RATE":
                    birth = v
                elif key == "DEATH_RATE":
                    death = v

        # ── 2) advance simulation at the desired rate ────────────────
        # assume UI is ~30 fps
        dt = 1.0 / 30.0
        self.time_accum += rate * dt
        while self.time_accum >= 1.0:
            self.time_accum -= 1.0
            self.step(birth, death)

        # ── 3) build output frame ────────────────────────────────────
        cmap     = COLORMAPS.get(self.params["COLORMAP"], COLORMAPS["jet"])
        cmap_len = len(cmap)
        frame = []

        H, W = self.height, self.width
        for y in range(H):
            for x in range(W):
                if self.cells[y][x]:
                    # recolor according to neighbor-count
                    cnt = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx==0 and dy==0: continue
                            if self.cells[(y+dy)%H][(x+dx)%W]:
                                cnt += 1
                    frac = cnt / 8.0
                    idx  = int(frac * (cmap_len - 1))
                    r, g, b = cmap[idx]
                    frame.append((r, g, b, 0))
                else:
                    frame.append((0, 0, 0, 0))

        return frame
