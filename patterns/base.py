class Pattern:
    def __init__(self, width, height, params=None):
        self.width = width
        self.height = height
        self.params = {k: v["default"] if isinstance(v, dict) else v for k, v in (params or {}).items()}

    def update_params(self, params):
        self.params.update(params)

    def render(self, lfo_signals=None):
        return [(0, 0, 0, 0)] * (self.width * self.height)

def apply_modulation(base, meta, amount):
    """
    base   :: the un-modulated parameter value
    meta   :: the PARAMS metadata dict for this parameter
    amount :: a single float from your LFO or envelope in [-1..1] or [0..1]
    returns :: a new, clamped parameter value
    """
    mode     = meta.get("mod_mode", "add")
    minv     = meta.get("min", 0.0)
    maxv     = meta.get("max", 1.0)
    span     = maxv - minv

    if mode == "add":
        val = base + amount * span
    elif mode == "scale":
        val = base * (1 + amount)
    elif mode == "replace":
        val = minv + amount * span
    else:
        val = base

    # clamp to [minv, maxv]
    return max(minv, min(val, maxv))