# gamma.py
"""
Gamma‐ and white‐balance calibration for your LED wall.

Define per‐channel gamma exponents and scale factors once at startup
by calling init_gamma(), then use apply_gamma() just before sending
to the LEDs (or in your sprite‐editor) to correct your raw RGBW values.
"""

__all__ = ["init_gamma", "apply_gamma", "make_gamma_lut"]

# Internal storage for gammas, scales, and lookup tables
_gamma = {"r": 1.0, "g": 1.0, "b": 1.0, "w": 1.0}
_scale = {"r": 1.0, "g": 1.0, "b": 1.0, "w": 1.0}
_luts = {"r": list(range(256)),
         "g": list(range(256)),
         "b": list(range(256)),
         "w": list(range(256))}


def make_gamma_lut(gamma: float) -> list[int]:
    """
    Build a 256‐entry inverse‐gamma lookup table.
    lut[i] = round(255 * (i/255)^(1/gamma))
    """
    return [int(255 * ((i / 255) ** (1.0 / gamma))) for i in range(256)]


def init_gamma(
    gammas: dict[str, float],
    scales: dict[str, float] | None = None
) -> None:
    """
    Initialize your per‐channel gamma exponents and (optional) scale factors.

    gammas: {"r":γ_r, "g":γ_g, "b":γ_b, "w":γ_w}
    scales: {"r":s_r,    "g":s_g,    "b":s_b,    "w":s_w}   (defaults to 1.0)

    Must be called once at startup (before any apply_gamma calls).
    """
    global _gamma, _scale, _luts
    # update gamma exponents
    for ch in ("r", "g", "b", "w"):
        if ch in gammas:
            _gamma[ch] = gammas[ch]
    # update optional scales
    if scales:
        for ch in ("r", "g", "b", "w"):
            if ch in scales:
                _scale[ch] = scales[ch]
    # rebuild all four lookup tables
    for ch in ("r", "g", "b", "w"):
        _luts[ch] = make_gamma_lut(_gamma[ch])


def apply_gamma(r: int, g: int, b: int, w: int) -> tuple[int, int, int, int]:
    """
    Take raw 0–255 (r,g,b,w) values, gamma‐correct & scale them,
    then return four corrected 0–255 ints for driving the LEDs.
    """
    # clamp inputs
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    w = max(0, min(255, w))

    # lookup + scale
    r2 = min(255, int(_luts["r"][r] * _scale["r"]))
    g2 = min(255, int(_luts["g"][g] * _scale["g"]))
    b2 = min(255, int(_luts["b"][b] * _scale["b"]))
    w2 = min(255, int(_luts["w"][w] * _scale["w"]))

    return r2, g2, b2, w2
