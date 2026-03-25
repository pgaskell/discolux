import colorsys

def make_colormap_from_anchors(anchors, resolution=256, easing="linear"):
    def is_hsv(color):
        return isinstance(color, tuple) and len(color) == 3 and max(color) <= 1.0

    def apply_easing(t, mode):
        if mode == "linear":
            return t
        elif mode == "ease_in":
            return t * t
        elif mode == "ease_out":
            return 1 - (1 - t) * (1 - t)
        elif mode == "ease_in_out":
            return t * t * (3 - 2 * t)
        else:
            return t

    anchors = sorted(anchors, key=lambda x: x[0])
    lut = []

    for i in range(resolution):
        x = i / (resolution - 1)

        for j in range(len(anchors) - 1):
            x0, c0 = anchors[j]
            x1, c1 = anchors[j + 1]
            if x0 <= x <= x1:
                t = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
                t = apply_easing(t, easing)

                if is_hsv(c0):
                    h = (1 - t) * c0[0] + t * c1[0]
                    s = (1 - t) * c0[1] + t * c1[1]
                    v = (1 - t) * c0[2] + t * c1[2]
                    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
                    lut.append((int(r * 255), int(g * 255), int(b * 255)))
                else:
                    r = int((1 - t) * c0[0] + t * c1[0])
                    g = int((1 - t) * c0[1] + t * c1[1])
                    b = int((1 - t) * c0[2] + t * c1[2])
                    lut.append((r, g, b))
                break
        else:
            # Clamp
            c = anchors[0][1] if x < anchors[0][0] else anchors[-1][1]
            if is_hsv(c):
                r, g, b = colorsys.hsv_to_rgb(c[0], c[1], c[2])
                lut.append((int(r * 255), int(g * 255), int(b * 255)))
            else:
                lut.append(c)

    return lut

def hsv_gradient(n=256, s=1.0, v=1.0):
    import colorsys
    return [
        tuple(int(c * 255) for c in colorsys.hsv_to_rgb(i / n, s, v))
        for i in range(n)
    ]

def _gen_vu_lut(n):
    """
    n-step LUT: 
      • 0 →  2/3 : green → yellow gradient  
      • 2/3 → 11/12 : solid yellow  
      • 11/12 → 1.0 : solid red  
    """
    lut = []
    for i in range(n):
        p = i / (n - 1)
        if p < 2/3:
            r = 127
            g = 255
            b = 0
        elif p < 11/12:
            r, g, b = 255, 255, 0
        else:
            r, g, b = 255, 0, 0
        lut.append((r, g, b))
    return lut

PASTEL_LUT = [
    (255, 179, 186),  # pastel pink
    (255, 223, 186),  # pastel peach
    (255, 255, 186),  # pastel yellow
    (186, 255, 201),  # pastel mint
    (186, 225, 255),  # pastel sky blue
    (219, 186, 255),  # pastel lavender
    (255, 186, 227),  # pastel rose
    (224, 224, 224),  # pastel gray
]


COLORMAPS = {
    "jet": make_colormap_from_anchors([
        (0.0, (0, 0, 143)),
        (0.125, (0, 0, 255)),
        (0.375, (0, 255, 255)),
        (0.625, (255, 255, 0)),
        (0.875, (255, 0, 0)),
        (1.0, (128, 0, 0)),
    ]),

    "hot": make_colormap_from_anchors([
        (0.0, (0, 0, 0)),
        (0.3, (255, 0, 0)),
        (0.6, (255, 255, 0)),
        (1.0, (255, 255, 255)),
    ]),

    "cool": make_colormap_from_anchors([
        (0.0, (0, 255, 255)),
        (1.0, (255, 0, 255)),
    ]),

    "warm_rainbow": make_colormap_from_anchors([
        (0.0, (0.0, 1.0, 1.0)),   # HSV red
        (0.25, (0.1, 1.0, 1.0)),  # HSV orange
        (0.5, (0.2, 1.0, 1.0)),   # HSV yellow-green
        (0.75, (0.33, 1.0, 1.0)), # HSV green
        (1.0, (0.5, 1.0, 1.0)),   # HSV cyan
    ], easing="ease_in_out"),

    "ocean": make_colormap_from_anchors([
        (0.0, (0, 0, 64)),
        (0.4, (0, 128, 255)),
        (1.0, (255, 255, 255)),
    ]),

    "viridis_approx": make_colormap_from_anchors([
        (0.0, (68, 1, 84)),
        (0.33, (59, 82, 139)),
        (0.66, (33, 145, 140)),
        (1.0, (253, 231, 37)),
    ]),

    "red_blue": make_colormap_from_anchors([
        (0.0, (127, 0, 0)),
        (0.33, (255, 0, 255)),
        (1.0, (0, 0, 127)),
    ]),

    "red_green": make_colormap_from_anchors([
        (0.0, (127, 0, 0)),
        (0.33, (255, 255, 0)),
        (1.0, (0, 255, 0)),
    ]),

    "green_blue": make_colormap_from_anchors([
        (0.0, (0, 127, 0)),
        (0.33, (0, 255, 255)),
        (1.0, (0, 0, 127)),
    ]),

    "red": make_colormap_from_anchors([
        (0.0, (32, 0, 0)),
        (1.0, (255, 0, 0)),
    ]),

    "green": make_colormap_from_anchors([
        (0.0, (0, 32, 0)),
        (1.0, (0, 255, 0)),
    ]),

    "blue": make_colormap_from_anchors([
        (0.0, (0, 0, 32)),
        (1.0, (0, 0, 255)),
    ]),

    "blue_white": make_colormap_from_anchors([
        (0.0, (0, 0, 32)),
        (1.0, (255, 255, 255)),
    ]),

    "magenta_white": make_colormap_from_anchors([
        (0.0, (64, 0, 64)),
        (1.0, (255, 255, 255)),
    ]),


    "lava_art": make_colormap_from_anchors([
        (0.0, (0.0, 0.0, 0.0)),    # Black
        (0.2, (0.05, 1.0, 0.1)),   # Greenish
        (0.4, (0.1, 1.0, 1.0)),    # Cyan
        (0.6, (0.2, 1.0, 1.0)),    # Yellowish
        (0.8, (0.02, 1.0, 1.0)),   # Fiery red
        (1.0, (0.0, 0.0, 1.0)),    # Blue flame
    ], easing="ease_out"),

    "hsv_full": hsv_gradient(),

    "pastels": PASTEL_LUT,

    "rainbow": hsv_gradient(),

    "vu_meter": _gen_vu_lut(256),
    
    "neon_spectrum": [
        (255, 0, 255), (0, 255, 255), (0, 255, 0), (255, 255, 0),
        (255, 128, 0), (255, 0, 0), (255, 0, 128), (128, 0, 255)
    ] * 32,

    "technicolor": [
        (0, 0, 0), (255, 0, 0), (255, 255, 0), (0, 255, 0),
        (0, 255, 255), (0, 0, 255), (255, 0, 255), (255, 255, 255)
    ] * 32,

    "ultra_rainbow": [
        (255, 0, 0), (255, 64, 0), (255, 128, 0), (255, 192, 0),
        (255, 255, 0), (192, 255, 0), (128, 255, 0), (0, 255, 0),
        (0, 255, 128), (0, 255, 255), (0, 128, 255), (0, 0, 255),
        (128, 0, 255), (255, 0, 255)
    ] * 18,

    "cyber_shift": [
        (0, 0, 0), (255, 64, 64), (64, 255, 64), (64, 64, 255),
        (255, 255, 64), (64, 255, 255), (255, 64, 255)
    ] * 36,
}
