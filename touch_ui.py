#!/usr/bin/python3
"""
touch_ui.py – Pygame-based touch UI for DiscoLux (800 × 480 layout).

Four bottom-tabs:
  EDIT   – pattern / LUT / sprite dropdowns, 4 param sliders + mod
           checkboxes, LFO and envelope panels on the right.
  VIEW   – full-screen simulator preview of the current frame.
  PATCH  – 8×8 patch grid, bank navigation, live thumbnail, BPM tap,
           save / delete buttons.
  CONFIG – random-cycle settings, auto-BPM sync toggle, brightness.

Frame output is delegated to a ``Wall`` instance passed from the main
entry point (``discolux.py``).
"""

import pygame
import random
import time
import importlib
import os
import json
import colorsys
from os.path import isfile
from PIL import Image

from config import MATRIX_WIDTH, MATRIX_HEIGHT, FRAME_RATE, save_yaml
from lfo import evaluate_lfos, LFO_CONFIG
from audio_env import evaluate_env, ENV_CONFIG, get_input_level
from wall import PROTOCOL_CHOICES

# ─── Wall dimensions ───────────────────────────────────────────────────────
WALL_W = MATRIX_WIDTH
WALL_H = MATRIX_HEIGHT

# ─── Screen layout ─────────────────────────────────────────────────────────
SCREEN_W = 800
SCREEN_H = 480
TAB_H = 50                       # height of the tab bar at the bottom
CONTENT_H = SCREEN_H - TAB_H    # 430 px for content
TAB_NAMES = ["EDIT", "VIEW", "PATCH", "CONFIG"]
NUM_TABS = len(TAB_NAMES)
TAB_W = SCREEN_W // NUM_TABS

# ─── Colours ───────────────────────────────────────────────────────────────
BG_COLOR = (30, 30, 30)
TAB_BG = (50, 50, 50)
TAB_ACTIVE = (80, 80, 180)
SLIDER_COLOR = (100, 200, 255)
FONT_SIZE = 16
SLIDER_WIDTH = 28
SLIDER_MARGIN = 10

# ─── Patch grid ────────────────────────────────────────────────────────────
current_bank = 0
random_mode = "Global"
PATCH_ROWS, PATCH_COLS = 8, 8
TOTAL_SLOTS = PATCH_ROWS * PATCH_COLS
MAX_BANKS = 8
SLOT_SIZE = 48
SLOT_SP = 3

instant_update = True

CONFIG_FILE = "discolux_settings.yaml"


def _gather_settings(cycle_beats, auto_bpm,
                     bright_slider, width_dd, height_dd, mic_sensitivity,
                     protocol_dd, _cfg):
    """Collect all CONFIG-tab values into a dict for saving."""
    return {
        "matrix_width": int(width_dd.selected),
        "matrix_height": int(height_dd.selected),
        "wled_host": _cfg.WLED_HOST,
        "wled_timeout": _cfg.WLED_TIMEOUT,
        "led_protocol": protocol_dd.selected,
        "frame_rate": _cfg.FRAME_RATE,
        "cycle_beats": cycle_beats,
        "auto_bpm": auto_bpm,
        "brightness": round(bright_slider.value, 2),
        "mic_sensitivity": round(mic_sensitivity, 2),
    }


def _load_settings() -> dict:
    """Load CONFIG-tab settings from YAML, or return defaults."""
    from config import _cfg as loaded
    return dict(loaded)


# ═══════════════════════════════════════════════════════════════════════════
# Pattern / sprite / patch helpers  (unchanged logic, kept compact)
# ═══════════════════════════════════════════════════════════════════════════

def load_patterns():
    patterns = {}
    for fname in os.listdir("patterns"):
        if fname.endswith(".py") and not fname.startswith("_"):
            modname = fname[:-3]
            try:
                mod = importlib.import_module(f"patterns.{modname}")
                if hasattr(mod, "Pattern") and hasattr(mod, "PARAMS"):
                    patterns[modname] = mod
            except Exception as e:
                print(f"Error loading pattern {modname}: {e}")
    return patterns


def load_sprites(folder="sprites"):
    sprites, names = {}, []
    for fname in sorted(os.listdir(folder)):
        low = fname.lower()
        if not (low.endswith(".png") or low.endswith(".gif")):
            continue
        name = os.path.splitext(fname)[0]
        path = os.path.join(folder, fname)
        if low.endswith(".png"):
            sprites[name] = [pygame.image.load(path).convert_alpha()]
        else:
            gif = Image.open(path)
            frames = []
            try:
                while True:
                    f = gif.convert("RGBA")
                    frames.append(
                        pygame.image.fromstring(f.tobytes(), f.size, "RGBA").convert_alpha()
                    )
                    gif.seek(gif.tell() + 1)
            except EOFError:
                pass
            sprites[name] = frames
        names.append(name)
    return sprites, ["none"] + names


# ─── Patch persistence ─────────────────────────────────────────────────────

def patch_filename(bank, slot):
    return f"patches/bank_{bank}_{slot:02d}.json"

# ── In-RAM patch cache (loaded once at startup) ────────────────────────────
_patch_cache: dict = {}      # (bank, slot) → patch dict
_thumb_cache: dict = {}      # (bank, slot) → pygame Surface


def _load_all_patches_into_cache():
    """Scan all banks/slots and cache every patch JSON in RAM."""
    for bk in range(MAX_BANKS):
        for sl in range(TOTAL_SLOTS):
            fn = patch_filename(bk, sl)
            if os.path.isfile(fn):
                try:
                    with open(fn) as f:
                        _patch_cache[(bk, sl)] = json.load(f)
                except Exception as e:
                    print(f"[cache] Failed to load {fn}: {e}")


def _generate_all_thumbnails(patterns, sprites):
    """Pre-render thumbnails for every cached patch so grid display is instant."""
    for (bk, sl), p in _patch_cache.items():
        if (bk, sl) in _thumb_cache:
            continue
        try:
            mod = patterns[p["pattern"]]
            tmp = mod.Pattern(WALL_W, WALL_H, params=p["params"])
            fr = tmp.render(lfo_signals={})
            _thumb_cache[(bk, sl)] = _make_thumb(
                tmp, fr, sprites, p["params"], (SLOT_SIZE, SLOT_SIZE))
        except Exception as e:
            print(f"[cache] Thumbnail failed for bank_{bk}_{sl:02d}: {e}")


def save_patch(bank, index, pattern_name, params, param_meta, lfo_config, env_config):
    patch = {
        "pattern": pattern_name,
        "params": params,
        "modulation": _extract_mod(param_meta),
        "lfo_config": lfo_config,
        "env_config": env_config,
    }
    with open(patch_filename(bank, index), "w") as f:
        json.dump(patch, f, indent=2)
    _patch_cache[(bank, index)] = patch
    _thumb_cache.pop((bank, index), None)  # thumbnail will be regenerated


def load_patch(bank, index):
    """Return patch dict from RAM cache (falls back to disk on miss)."""
    key = (bank, index)
    if key in _patch_cache:
        return _patch_cache[key]
    fn = patch_filename(bank, index)
    if not os.path.isfile(fn):
        return None
    with open(fn) as f:
        data = json.load(f)
    _patch_cache[key] = data
    return data


def delete_patch(bank, index):
    fn = patch_filename(bank, index)
    if os.path.isfile(fn):
        os.remove(fn)
    _patch_cache.pop((bank, index), None)
    _thumb_cache.pop((bank, index), None)


def _extract_mod(param_meta):
    cfg = {}
    for name, meta in param_meta.items():
        if isinstance(meta, dict) and meta.get("modulatable"):
            cfg[name] = {
                "mod_active": bool(meta.get("mod_source")),
                "mod_source": meta.get("mod_source"),
                "mod_mode": meta.get("mod_mode", "add"),
            }
    return cfg


def reload_patch_grid(patterns, sprites, icons, slots):
    """Refresh the 64-slot grid from the RAM cache — no file I/O."""
    for i in range(TOTAL_SLOTS):
        key = (current_bank, i)
        p = _patch_cache.get(key)
        if p is not None:
            slots[i] = True
            # Use cached thumbnail if available
            if key in _thumb_cache:
                icons[i] = _thumb_cache[key]
            else:
                mod = patterns[p["pattern"]]
                tmp = mod.Pattern(WALL_W, WALL_H, params=p["params"])
                fr = tmp.render(lfo_signals={})
                thumb = _make_thumb(tmp, fr, sprites, p["params"],
                                    (SLOT_SIZE, SLOT_SIZE))
                _thumb_cache[key] = thumb
                icons[i] = thumb
        else:
            slots[i] = None
            icons[i] = None


def restore_patch(bank, index, pattern_names, patterns, lfo_panels, env_panels,
                  pat_dd, cmap_dd, sprite_dd, create_sliders_fn):
    patch = load_patch(bank, index)
    new_idx = pattern_names.index(patch["pattern"])
    module = patterns[pattern_names[new_idx]]
    pspecs = module.PARAMS
    params = patch["params"].copy()
    pat = module.Pattern(WALL_W, WALL_H, params=params)
    sliders, dds, cbs = create_sliders_fn(pspecs, params)
    for nm, m in patch["modulation"].items():
        meta = pspecs.get(nm)
        if not meta:
            continue
        meta["mod_active"] = m["mod_active"]
        meta["mod_source"] = m["mod_source"]
        meta["mod_mode"] = m["mod_mode"]
        for cb in cbs:
            if cb.param_name == nm:
                cb.active = (cb.source_id == m["mod_source"])
    import lfo
    lfo.LFO_CONFIG.update(patch["lfo_config"])
    for ln, panel in zip(("lfo1", "lfo2"), lfo_panels):
        c = lfo.LFO_CONFIG[ln]
        panel.config.update(c)
        panel.waveform_dropdown.selected = c["waveform"]
        panel.depth_slider.value = c["depth"]
        panel.offset_slider.value = c.get("offset", 0.0)
        panel.config["offset"] = c.get("offset", 0.0)
        panel.sync_mode = c["sync_mode"]
        if c["sync_mode"] == "free":
            panel.mhz_dropdown.selected = str(int(c["hz"] * 1000))
        else:
            panel.beat_dropdown.selected = panel._bl(c["period_beats"])
    import audio_env
    audio_env.ENV_CONFIG.update(patch["env_config"])
    for en, panel in zip(("envl", "envh"), env_panels):
        c = audio_env.ENV_CONFIG[en]
        panel.th_slider.value = c["threshold_db"]
        panel.gn_slider.value = c["gain_db"]
        panel.atk_dd.selected = panel.attack_map[c["attack"]]
        panel.rel_dd.selected = panel.release_map[c["release"]]
        panel.mode_dd.selected = c["mode"]
        panel.config.update(c)
    pat_dd.selected = patch["pattern"]
    if "COLORMAP" in params:
        cmap_dd.selected = params["COLORMAP"]
    if "SPRITE" in params:
        sprite_dd.selected = params["SPRITE"]
    pat.update_params(params)
    return new_idx, pat, sliders, dds, cbs


# ─── Drawing helpers ───────────────────────────────────────────────────────

def _make_thumb(pattern, frame, sprites, params, size):
    base = pygame.Surface((pattern.width, pattern.height), pygame.SRCALPHA)
    draw_simulator(base, frame, pattern.width, pattern.height,
                   pygame.Rect(0, 0, pattern.width, pattern.height))
    sname = params.get("SPRITE", "none")
    if sname in sprites and sprites[sname]:
        ss = sprites[sname][0]
        sw, sh = ss.get_size()
        base.blit(ss, ((pattern.width - sw) // 2, (pattern.height - sh) // 2))
    return pygame.transform.smoothscale(base, size)


def draw_simulator(screen, frame, gw, gh, rect, mode="fill"):
    if len(frame) < gw * gh:
        return  # frame/dimension mismatch – skip this render
    ps = min(rect.width // gw, rect.height // gh)
    if ps < 1:
        return
    dw, dh = ps * gw, ps * gh
    ox = rect.x + (rect.width - dw) // 2
    oy = rect.y + (rect.height - dh) // 2

    if mode == "point":
        # Black background, small circles at cell centres
        pygame.draw.rect(screen, (0, 0, 0),
                         pygame.Rect(ox, oy, dw, dh))
        radius = max(1, ps * 3 // 16)
        half = ps // 2
        for y in range(gh):
            for x in range(gw):
                r, g, b, *_ = frame[y * gw + x]
                cx = ox + x * ps + half
                cy = oy + y * ps + half
                pygame.draw.circle(screen, (r, g, b), (cx, cy), radius)
    elif mode == "grid":
        # Filled cells with 1 px black border
        for y in range(gh):
            for x in range(gw):
                r, g, b, *_ = frame[y * gw + x]
                cell = pygame.Rect(ox + x * ps, oy + y * ps, ps, ps)
                pygame.draw.rect(screen, (r, g, b), cell)
                pygame.draw.rect(screen, (0, 0, 0), cell, 1)
    else:
        # "fill" – original solid cells, no border
        for y in range(gh):
            for x in range(gw):
                r, g, b, *_ = frame[y * gw + x]
                pygame.draw.rect(screen, (r, g, b),
                                 pygame.Rect(ox + x * ps, oy + y * ps, ps, ps))


def draw_mod_indicator(screen, font, signals, key, color, rect):
    """Compact bipolar bar inside *rect*."""
    pygame.draw.rect(screen, (50, 50, 50), rect)
    cx = rect.x + rect.width // 2
    pygame.draw.line(screen, (200, 200, 200), (cx, rect.y), (cx, rect.y + rect.height))
    val = max(-1.0, min(1.0, signals.get(key, 0.0)))
    length = int(val * (rect.width // 2))
    if length >= 0:
        bar = pygame.Rect(cx, rect.y, length, rect.height)
    else:
        bar = pygame.Rect(cx + length, rect.y, -length, rect.height)
    pygame.draw.rect(screen, color, bar)


# ═══════════════════════════════════════════════════════════════════════════
# UI Widgets  (unchanged logic, position parameters supplied at creation)
# ═══════════════════════════════════════════════════════════════════════════

class Slider:
    def __init__(self, name, default, mn, mx, step, x, y, height, valid_values=None):
        self.name, self.value = name, default
        self.min, self.max, self.step = mn, mx, step
        self.valid_values = valid_values
        self.rect = pygame.Rect(x, y, SLIDER_WIDTH, height)
        self.active = False

    def draw(self, screen, font):
        pygame.draw.rect(screen, (80, 80, 80), self.rect)
        ratio = (self.value - self.min) / max(self.max - self.min, 1e-9)
        hy = self.rect.y + self.rect.height * (1.0 - ratio)
        pygame.draw.rect(screen, SLIDER_COLOR, (self.rect.x, hy - 4, SLIDER_WIDTH, 8))
        for i, ch in enumerate(self.name[:8]):
            screen.blit(font.render(ch, True, (255, 255, 255)),
                        (self.rect.x + SLIDER_WIDTH + 3, self.rect.y + i * (FONT_SIZE - 2)))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.active = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.active = False
        elif event.type == pygame.MOUSEMOTION and self.active:
            ratio = max(0.0, min(1.0, (event.pos[1] - self.rect.y) / self.rect.height))
            raw = self.max - ratio * (self.max - self.min)
            if self.valid_values:
                self.value = min(self.valid_values, key=lambda v: abs(v - raw))
            else:
                self.value = min(max(round(raw / self.step) * self.step, self.min), self.max)


class HSlider:
    """Compact horizontal slider."""
    H = 18

    def __init__(self, name, default, mn, mx, step, x, y, w):
        self.name, self.value = name, default
        self.min, self.max, self.step = mn, mx, step
        self.rect = pygame.Rect(x, y, w, self.H)
        self.active = False

    def draw(self, screen, font):
        pygame.draw.rect(screen, (80, 80, 80), self.rect)
        ratio = (self.value - self.min) / max(self.max - self.min, 1e-9)
        hx = self.rect.x + int(ratio * self.rect.width)
        pygame.draw.rect(screen, SLIDER_COLOR, (hx - 4, self.rect.y, 8, self.H))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.active = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.active = False
        elif event.type == pygame.MOUSEMOTION and self.active:
            ratio = max(0.0, min(1.0, (event.pos[0] - self.rect.x) / self.rect.width))
            raw = self.min + ratio * (self.max - self.min)
            self.value = min(max(round(raw / self.step) * self.step, self.min), self.max)


class ModCheckbox:
    SZ = 18

    def __init__(self, param_name, source_id, x, y, color):
        self.param_name, self.source_id = param_name, source_id
        self.rect = pygame.Rect(x, y, self.SZ, self.SZ)
        self.color, self.active = color, False

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, 0 if self.active else 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.active = not self.active
            return True
        return False


class Dropdown:
    def __init__(self, name, options, default, x, y,
                 width=120, show_label=True, label_map=None,
                 dropup=False, max_visible=8):
        self.name = name
        self.options = options
        self.selected = default
        self.x, self.y = x, y
        self.width = width
        self.show_label = show_label
        self.label_map = label_map or {}
        self.dropup = dropup
        self.rect = pygame.Rect(x, y, width, 24)
        self.entry_h = 24
        self.open = False
        self.max_visible = max_visible
        self.start_index = 0
        ar_off = self.entry_h
        self.arrow_up_rect = pygame.Rect(
            x, y - ar_off if dropup else y + ar_off * (max_visible + 1),
            width, ar_off)
        self.arrow_down_rect = pygame.Rect(
            x, y - ar_off * (max_visible + 2) if dropup else y + ar_off * (max_visible + 2),
            width, ar_off)

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return False
        if self.rect.collidepoint(event.pos):
            self.open = not self.open
            return True
        if not self.open:
            return False
        if event.button in (4, 5):
            if event.button == 4:
                self.start_index = max(0, self.start_index - 1)
            else:
                self.start_index = min(max(0, len(self.options) - self.max_visible),
                                       self.start_index + 1)
            return True
        if self.arrow_up_rect.collidepoint(event.pos):
            self.start_index = max(0, self.start_index - 1)
            return True
        if self.arrow_down_rect.collidepoint(event.pos):
            if self.start_index + self.max_visible < len(self.options):
                self.start_index += 1
            return True
        for idx in range(self.start_index,
                         min(len(self.options), self.start_index + self.max_visible)):
            i = idx - self.start_index
            off = -self.entry_h * (i + 1) if self.dropup else self.entry_h * (i + 1)
            er = pygame.Rect(self.x, self.y + off, self.width, self.entry_h)
            if er.collidepoint(event.pos):
                self.selected = self.options[idx]
                self.open = False
                return True
        self.open = False
        return True

    def draw(self, screen, font):
        pygame.draw.rect(screen, (100, 100, 100), self.rect)
        txt = str(self.label_map.get(self.selected, self.selected))
        if len(txt) > 16:
            txt = txt[:13] + "..."
        screen.blit(font.render(txt, True, (255, 255, 255)), (self.x + 4, self.y + 3))
        if self.show_label:
            lbl = self.name.split("_")[-1] + ":"
            s = font.render(lbl, True, (160, 160, 160))
            screen.blit(s, (self.x - s.get_width() - 4, self.y + 3))
        if not self.open:
            return
        start, end = self.start_index, min(len(self.options), self.start_index + self.max_visible)
        for idx in range(start, end):
            i = idx - start
            off = -self.entry_h * (i + 1) if self.dropup else self.entry_h * (i + 1)
            or_ = pygame.Rect(self.x, self.y + off, self.width, self.entry_h)
            pygame.draw.rect(screen, (70, 70, 70), or_)
            lbl = str(self.label_map.get(self.options[idx], self.options[idx]))
            if len(lbl) > 16:
                lbl = lbl[:13] + "..."
            screen.blit(font.render(lbl, True, (255, 255, 255)), (self.x + 4, or_.y + 3))
        # arrows
        for ar, enabled in ((self.arrow_up_rect, self.start_index > 0),
                            (self.arrow_down_rect, self.start_index + self.max_visible < len(self.options))):
            screen.fill((120, 120, 120), ar)
        up_t = font.render("↑", True, (200, 200, 200) if self.start_index > 0 else (80, 80, 80))
        dn_t = font.render("↓", True, (200, 200, 200)
                           if self.start_index + self.max_visible < len(self.options) else (80, 80, 80))
        screen.blit(up_t, (self.arrow_up_rect.centerx - up_t.get_width() // 2,
                           self.arrow_up_rect.centery - up_t.get_height() // 2))
        screen.blit(dn_t, (self.arrow_down_rect.centerx - dn_t.get_width() // 2,
                           self.arrow_down_rect.centery - dn_t.get_height() // 2))


# ─── Compact LFO panel (fits ~280 × 80) ───────────────────────────────────

class LFOPanel:
    def __init__(self, name, x, y, config):
        self.name, self.x, self.y, self.config = name, x, y, config
        wl = {"sine": "sin", "square": "sqr", "triangle": "tri", "saw": "saw"}
        self.waveform_dropdown = Dropdown(name + "_w", ["sine", "square", "triangle", "saw"],
                                          config["waveform"], x, y, width=70,
                                          show_label=False, label_map=wl)
        self.depth_slider = HSlider(name + "_d", config["depth"], 0, 1, 0.01,
                                    x + 75, y + 2, 50)
        self.offset_slider = HSlider(name + "_o", config.get("offset", 0), -1, 1, 0.01,
                                     x + 130, y + 2, 50)
        self.sync_rect = pygame.Rect(x, y + 28, 70, 24)
        self.mhz_dropdown = Dropdown(name + "_mhz", ["50", "100", "200", "500", "1000"],
                                     str(int(config["hz"] * 1000)), x + 75, y + 28,
                                     width=70, show_label=False)
        self.beat_dropdown = Dropdown(name + "_bt", ["1/4", "1/2", "1", "2", "4"],
                                     self._bl(config["period_beats"]), x + 75, y + 28,
                                     width=70, show_label=False)

    def _bl(self, v):
        return {0.25: "1/4", 0.5: "1/2", 1.0: "1", 2.0: "2", 4.0: "4"}.get(v, "1")

    def _bv(self, l):
        return {"1/4": 0.25, "1/2": 0.5, "1": 1.0, "2": 2.0, "4": 4.0}.get(l, 1.0)

    def handle_event(self, ev):
        self.waveform_dropdown.handle_event(ev)
        self.depth_slider.handle_event(ev)
        self.offset_slider.handle_event(ev)
        if ev.type == pygame.MOUSEBUTTONDOWN and self.sync_rect.collidepoint(ev.pos):
            self.config["sync_mode"] = "quantized" if self.config["sync_mode"] == "free" else "free"
        (self.mhz_dropdown if self.config["sync_mode"] == "free" else self.beat_dropdown).handle_event(ev)
        self.config["waveform"] = self.waveform_dropdown.selected
        self.config["depth"] = self.depth_slider.value
        self.config["offset"] = self.offset_slider.value
        if self.config["sync_mode"] == "free":
            self.config["hz"] = int(self.mhz_dropdown.selected) / 1000.0
        else:
            self.config["period_beats"] = self._bv(self.beat_dropdown.selected)

    def draw(self, screen, font):
        pygame.draw.rect(screen, (40, 40, 40),
                         pygame.Rect(self.x - 4, self.y - 16, 195, 72), border_radius=3)
        screen.blit(font.render(self.name.upper(), True, (255, 255, 255)), (self.x, self.y - 15))
        self.depth_slider.draw(screen, font)
        self.offset_slider.draw(screen, font)
        pygame.draw.rect(screen, (90, 90, 90), self.sync_rect)
        lbl = "mHz" if self.config["sync_mode"] == "free" else "Q"
        screen.blit(font.render(lbl, True, (255, 255, 255)), (self.sync_rect.x + 6, self.sync_rect.y + 3))
        self.waveform_dropdown.draw(screen, font)
        rate_dd = self.mhz_dropdown if self.config["sync_mode"] == "free" else self.beat_dropdown
        rate_dd.draw(screen, font)

    def draw_open_dropdowns(self, screen, font):
        """Draw any open dropdown lists (call after all panels are drawn)."""
        for dd in (self.waveform_dropdown, self.mhz_dropdown, self.beat_dropdown):
            if dd.open:
                dd.draw(screen, font)


# ─── Compact Envelope panel (fits ~280 × 80) ──────────────────────────────

class EnvPanel:
    def __init__(self, name, x, y, config):
        self.name, self.x, self.y, self.config = name, x, y, config
        self.attack_map = {0.001: "1ms", 0.005: "5ms", 0.010: "10ms", 0.020: "20ms"}
        self.release_map = {0.025: "25ms", 0.050: "50ms", 0.100: "100ms", 0.150: "150ms"}
        self._am = {"1ms": 0.001, "5ms": 0.005, "10ms": 0.010, "20ms": 0.020}
        self._rm = {"25ms": 0.025, "50ms": 0.050, "100ms": 0.100, "150ms": 0.150}
        self.gn_slider = HSlider(f"{name}_g", config.get("gain_db", 0), -40, 10, 1, x, y, 80)
        self.th_slider = HSlider(f"{name}_t", config.get("threshold_db", 0), -40, 20, 1, x, y + 24, 80)
        ad = next((l for l, v in self._am.items() if abs(v - config["attack"]) < 1e-6), "10ms")
        self.atk_dd = Dropdown(f"{name}_a", list(self._am.keys()), ad, x + 85, y, width=60, show_label=False)
        rd = next((l, ) for l, v in self._rm.items() if abs(v - config["release"]) < 1e-6)
        rd = next((l for l, v in self._rm.items() if abs(v - config["release"]) < 1e-6), "100ms")
        self.rel_dd = Dropdown(f"{name}_r", list(self._rm.keys()), rd, x + 150, y, width=60, show_label=False)
        self.mode_dd = Dropdown(f"{name}_m", ["up", "down", "updown"], config["mode"], x + 85, y + 24, width=70, show_label=False)

    def handle_event(self, ev):
        for w in (self.th_slider, self.gn_slider, self.atk_dd, self.rel_dd, self.mode_dd):
            w.handle_event(ev)
        self.config["threshold_db"] = self.th_slider.value
        self.config["gain_db"] = self.gn_slider.value
        self.config["attack"] = self._am[self.atk_dd.selected]
        self.config["release"] = self._rm[self.rel_dd.selected]
        self.config["mode"] = self.mode_dd.selected

    def draw(self, screen, font):
        pygame.draw.rect(screen, (40, 40, 40),
                         pygame.Rect(self.x - 4, self.y - 16, 220, 64), border_radius=3)
        screen.blit(font.render(self.name.upper(), True, (255, 255, 255)), (self.x, self.y - 15))
        self.gn_slider.draw(screen, font)
        self.th_slider.draw(screen, font)
        self.atk_dd.draw(screen, font)
        self.rel_dd.draw(screen, font)
        self.mode_dd.draw(screen, font)

    def draw_open_dropdowns(self, screen, font):
        """Draw any open dropdown lists (call after all panels are drawn)."""
        for dd in (self.atk_dd, self.rel_dd, self.mode_dd):
            if dd.open:
                dd.draw(screen, font)


# ═══════════════════════════════════════════════════════════════════════════
# Slider factory  (positions adapted for the EDIT tab)
# ═══════════════════════════════════════════════════════════════════════════

def create_sliders(param_specs, current_values):
    sliders, dropdowns, cbs = [], [], []
    sc = 0
    dd_x, dd_y = 10, 30
    sl_x, sl_y = 10, 58
    sl_h = CONTENT_H - 150  # leave room for mod checkboxes below

    for k, spec in param_specs.items():
        if k in ("COLORMAP", "SPRITE"):
            continue
        if isinstance(spec, dict) and "options" in spec:
            dropdowns.append(Dropdown(k, spec["options"], current_values[k], dd_x, dd_y))
            dd_x += 140
        elif isinstance(spec, dict):
            if sc >= 4:
                continue
            sc += 1
            d = spec["default"]
            if "valid" in spec:
                vv = spec["valid"]
                sliders.append(Slider(k, current_values[k], min(vv), max(vv), 1,
                                      sl_x, sl_y, sl_h, valid_values=vv))
            else:
                mn = spec.get("min", d / 2)
                mx = spec.get("max", d * 2)
                st = spec.get("step", 0.1)
                sliders.append(Slider(k, current_values[k], mn, mx, st, sl_x, sl_y, sl_h))
            if spec.get("modulatable"):
                cx = sl_x + SLIDER_WIDTH // 2 - 9
                ys = sl_y + sl_h + 6
                sp = 20
                cbs.extend([
                    ModCheckbox(k, "lfo1", cx, ys + 0 * sp, (100, 255, 255)),
                    ModCheckbox(k, "lfo2", cx, ys + 1 * sp, (255, 100, 255)),
                    ModCheckbox(k, "envl", cx, ys + 2 * sp, (255, 255, 100)),
                    ModCheckbox(k, "envh", cx, ys + 3 * sp, (255, 150, 50)),
                ])
            sl_x += SLIDER_WIDTH + SLIDER_MARGIN + 12
    return sliders, dropdowns, cbs


# ═══════════════════════════════════════════════════════════════════════════
# Randomize LFO / ENV / modulation assignments
# ═══════════════════════════════════════════════════════════════════════════

_LFO_WAVEFORMS = ["sine", "square", "triangle", "saw"]
_LFO_BEAT_OPTIONS = ["1/4", "1/2", "1", "2", "4"]
_LFO_BEAT_VALUES = {"1/4": 0.25, "1/2": 0.5, "1": 1.0, "2": 2.0, "4": 4.0}
_ENV_ATK_OPTIONS = ["1ms", "5ms", "10ms", "20ms"]
_ENV_ATK_VALUES = {"1ms": 0.001, "5ms": 0.005, "10ms": 0.010, "20ms": 0.020}
_ENV_REL_OPTIONS = ["25ms", "50ms", "100ms", "150ms"]
_ENV_REL_VALUES = {"25ms": 0.025, "50ms": 0.050, "100ms": 0.100, "150ms": 0.150}
_ENV_MODES = ["up", "down", "updown"]
_MOD_SOURCES = ["lfo1", "lfo2", "envl", "envh"]


def _randomize_lfo(panel):
    """Randomize an LFO panel — always quantized mode."""
    wf = random.choice(_LFO_WAVEFORMS)
    panel.config["waveform"] = wf
    panel.waveform_dropdown.selected = wf

    depth = round(random.uniform(0.0, 1.0), 2)
    panel.config["depth"] = depth
    panel.depth_slider.value = depth

    offset = round(random.uniform(-1.0, 1.0), 2)
    panel.config["offset"] = offset
    panel.offset_slider.value = offset

    # Always quantized
    panel.config["sync_mode"] = "quantized"
    beat_label = random.choice(_LFO_BEAT_OPTIONS)
    panel.config["period_beats"] = _LFO_BEAT_VALUES[beat_label]
    panel.beat_dropdown.selected = beat_label


def _randomize_env(panel):
    """Randomize an envelope panel."""
    th = random.randint(-40, 20)
    panel.config["threshold_db"] = th
    panel.th_slider.value = th

    gn = random.randint(-40, 10)
    panel.config["gain_db"] = gn
    panel.gn_slider.value = gn

    atk = random.choice(_ENV_ATK_OPTIONS)
    panel.config["attack"] = _ENV_ATK_VALUES[atk]
    panel.atk_dd.selected = atk

    rel = random.choice(_ENV_REL_OPTIONS)
    panel.config["release"] = _ENV_REL_VALUES[rel]
    panel.rel_dd.selected = rel

    mode = random.choice(_ENV_MODES)
    panel.config["mode"] = mode
    panel.mode_dd.selected = mode


def _randomize_mod(lfo1_p, lfo2_p, envl_p, envh_p, mod_cbs, pspecs):
    """Randomize LFOs, ENVs, and modulation routing for all modulatable params."""
    _randomize_lfo(lfo1_p)
    _randomize_lfo(lfo2_p)
    _randomize_env(envl_p)
    _randomize_env(envh_p)

    # Update the global configs so evaluate_lfos / evaluate_env pick them up
    from lfo import LFO_CONFIG
    from audio_env import ENV_CONFIG
    LFO_CONFIG["lfo1"].update(lfo1_p.config)
    LFO_CONFIG["lfo2"].update(lfo2_p.config)
    ENV_CONFIG["envl"].update(envl_p.config)
    ENV_CONFIG["envh"].update(envh_p.config)

    # Gather modulatable param names
    mod_params = [k for k, spec in pspecs.items()
                  if isinstance(spec, dict) and spec.get("modulatable")]

    # For each modulatable param, randomly decide: no mod, or one source
    for pname in mod_params:
        meta = pspecs.get(pname)
        if not meta:
            continue
        if random.random() < 0.4:
            # No modulation (40% chance)
            meta["mod_active"] = False
            meta["mod_source"] = None
            for cb in mod_cbs:
                if cb.param_name == pname:
                    cb.active = False
        else:
            # Pick a random source
            src = random.choice(_MOD_SOURCES)
            meta["mod_active"] = True
            meta["mod_source"] = src
            for cb in mod_cbs:
                if cb.param_name == pname:
                    cb.active = (cb.source_id == src)


# ═══════════════════════════════════════════════════════════════════════════
# Main UI loop
# ═══════════════════════════════════════════════════════════════════════════

def launch_ui(wall=None):
    global current_bank, random_mode, WALL_W, WALL_H

    pygame.init()
    import lfo as _lfo
    import audio_env as _aenv

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
    pygame.display.set_caption("DiscoLux")
    font = pygame.font.SysFont("monospace", FONT_SIZE)
    bold_font = pygame.font.SysFont("monospace", FONT_SIZE, bold=True)
    sm_font = pygame.font.SysFont("monospace", FONT_SIZE - 2)

    active_tab = 1  # 0=EDIT 1=VIEW 2=PATCH 3=CONFIG

    # ── Tab bar rects ───────────────────────────────────────────────────
    tab_rects = [pygame.Rect(i * TAB_W, CONTENT_H, TAB_W, TAB_H) for i in range(NUM_TABS)]

    # ── Patterns, sprites, colormaps ────────────────────────────────────
    patterns = load_patterns()
    pattern_names = sorted(patterns.keys())
    current_index = 0
    sprites, sprite_names = load_sprites("sprites")
    from colormaps import COLORMAPS
    cmap_names = list(COLORMAPS.keys())

    # initial pattern
    module = patterns[pattern_names[current_index]]
    pspecs = module.PARAMS
    params = {k: v["default"] for k, v in pspecs.items()}
    if "SPRITE" in pspecs:
        pspecs["SPRITE"]["options"] = sprite_names
    pattern = module.Pattern(WALL_W, WALL_H, params=params)
    sliders, dropdowns, mod_cbs = create_sliders(pspecs, params)

    # ── EDIT-tab dropdowns (top row) ────────────────────────────────────
    pat_dd = Dropdown("Pattern", pattern_names, pattern_names[0],
                      10, 4, width=180, show_label=False, max_visible=15)
    cmap_dd = Dropdown("COLORMAP", cmap_names,
                       params.get("COLORMAP", cmap_names[0]),
                       200, 4, width=168, show_label=False, max_visible=15)
    sprite_dd = Dropdown("SPRITE", sprite_names,
                         params.get("SPRITE", "none"),
                         378, 4, width=168, show_label=False, max_visible=15)

    # ── EDIT-tab mod panels (right column, stacked) ─────────────────────
    RX = SCREEN_W - 205  # right column x
    lfo1_p = LFOPanel("lfo1", RX, 40, LFO_CONFIG["lfo1"])
    lfo2_p = LFOPanel("lfo2", RX, 130, LFO_CONFIG["lfo2"])
    envl_p = EnvPanel("envl", RX, 220, ENV_CONFIG["envl"])
    envh_p = EnvPanel("envh", RX, 310, ENV_CONFIG["envh"])
    mod_panels = [lfo1_p, lfo2_p, envl_p, envh_p]

    # ── EDIT-tab randomize buttons (centred above tab bar) ──────────────
    _edit_btn_w = 140
    _edit_btn_h = 32
    _edit_btn_gap = 10
    _edit_btn_total = 2 * _edit_btn_w + _edit_btn_gap
    _edit_mid_x = 220 + (RX - 10 - 220) // 2   # centre of simulator area
    _edit_btn_y = CONTENT_H - _edit_btn_h - 6
    rnd_settings_btn = pygame.Rect(_edit_mid_x - _edit_btn_total // 2,
                                   _edit_btn_y, _edit_btn_w, _edit_btn_h)
    rnd_pattern_btn = pygame.Rect(_edit_mid_x - _edit_btn_total // 2 + _edit_btn_w + _edit_btn_gap,
                                  _edit_btn_y, _edit_btn_w, _edit_btn_h)

    # ── PATCH-tab state ─────────────────────────────────────────────────
    patches_arr = [None] * TOTAL_SLOTS
    patch_icons = [None] * TOTAL_SLOTS
    save_mode = False
    clear_mode = False

    # Thumbnail preview on the left
    thumb_rect = pygame.Rect(10, 10, 180, 180)

    # Patch grid centered
    GRID_TOTAL_W = PATCH_COLS * (SLOT_SIZE + SLOT_SP) - SLOT_SP
    GRID_TOTAL_H = PATCH_ROWS * (SLOT_SIZE + SLOT_SP) - SLOT_SP
    GRID_X = (SCREEN_W - GRID_TOTAL_W) // 2
    GRID_Y = (CONTENT_H - GRID_TOTAL_H) // 2
    patch_rects = []
    for row in range(PATCH_ROWS):
        for col in range(PATCH_COLS):
            px = GRID_X + col * (SLOT_SIZE + SLOT_SP)
            py = GRID_Y + row * (SLOT_SIZE + SLOT_SP)
            patch_rects.append(pygame.Rect(px, py, SLOT_SIZE, SLOT_SIZE))

    # Buttons on the right – vertically centered in content area
    BTN_X = GRID_X + GRID_TOTAL_W + 15
    BTN_W = SCREEN_W - BTN_X - 10
    # Total height of right-side controls block:
    #   save(36) + 4 + del(36) + 4 + tap(50) + 6 + rnd row(32) + 6
    #   + bank row(32) + 6 + beat row1(28) + 3 + beat row2(28)
    _rblock_h = 36 + 4 + 36 + 4 + 50 + 6 + 32 + 6 + 32 + 6 + 28 + 3 + 28
    _ry0 = max(6, (CONTENT_H - _rblock_h) // 2)

    save_btn = pygame.Rect(BTN_X, _ry0, BTN_W, 36)
    del_btn = pygame.Rect(BTN_X, _ry0 + 40, BTN_W, 36)
    tap_btn = pygame.Rect(BTN_X, _ry0 + 80, BTN_W, 50)
    tap_times = []

    # RND + Global/Bank buttons
    rnd_btn = pygame.Rect(BTN_X, _ry0 + 136, BTN_W // 2 - 3, 32)
    rnd_mode_btn = pygame.Rect(BTN_X + BTN_W // 2 + 3, _ry0 + 136, BTN_W // 2 - 3, 32)

    # bank nav
    bank_left_rect = pygame.Rect(BTN_X, _ry0 + 174, 35, 32)
    bank_right_rect = pygame.Rect(BTN_X + BTN_W - 35, _ry0 + 174, 35, 32)
    bank_label_rect = pygame.Rect(BTN_X + 37, _ry0 + 174, BTN_W - 74, 32)

    # Beat-count buttons (2 rows of 3, below bank nav on PATCH tab)
    BEAT_OPTIONS = [1, 2, 4, 8, 16, 32]
    _beat_row_y = _ry0 + 212
    _beat_bw = (BTN_W - 6) // 3   # 3 buttons per row with 3px gaps
    _beat_bh = 28
    beat_btns = []
    for idx, val in enumerate(BEAT_OPTIONS):
        row, col = divmod(idx, 3)
        bx = BTN_X + col * (_beat_bw + 3)
        by = _beat_row_y + row * (_beat_bh + 3)
        beat_btns.append((val, pygame.Rect(bx, by, _beat_bw, _beat_bh)))

    # ── Solid colour buttons (3×3 grid, below preview on PATCH tab) ────
    SOLID_COLORS = [
        ("R", (255, 0, 0)),     ("G", (0, 255, 0)),     ("B", (0, 0, 255)),
        ("C", (0, 255, 255)),   ("M", (255, 0, 255)),   ("Y", (255, 255, 0)),
        ("O", (255, 140, 0)),   ("W", (255, 255, 255)), ("K", (0, 0, 0)),
    ]
    _sc_gap = 3
    _sc_size = (thumb_rect.width - 2 * _sc_gap) // 3   # fill preview width
    _sc_total_w = 3 * _sc_size + 2 * _sc_gap
    _sc_x0 = thumb_rect.x + (thumb_rect.width - _sc_total_w) // 2
    _sc_y0 = thumb_rect.bottom + 8
    solid_btns = []
    for idx, (lbl, col) in enumerate(SOLID_COLORS):
        row, col_i = divmod(idx, 3)
        sr = pygame.Rect(_sc_x0 + col_i * (_sc_size + _sc_gap),
                         _sc_y0 + row * (_sc_size + _sc_gap),
                         _sc_size, _sc_size)
        solid_btns.append((lbl, SOLID_COLORS[idx][1], sr))
    solid_override = None  # when set, overrides frame output with solid colour

    # ── CONFIG-tab state ────────────────────────────────────────────────
    import config as _cfg
    saved_cfg = _load_settings()

    random_cycle = True
    random_mode = "Global"
    cycle_beats = saved_cfg.get("cycle_beats", 32)
    auto_bpm = saved_cfg.get("auto_bpm", False)
    brightness = saved_cfg.get("brightness", 1.0)
    mic_sensitivity = saved_cfg.get("mic_sensitivity", 1.0)

    # Apply saved matrix dimensions
    _cfg.MATRIX_WIDTH = saved_cfg.get("matrix_width", 24)
    _cfg.MATRIX_HEIGHT = saved_cfg.get("matrix_height", 24)
    WALL_W = _cfg.MATRIX_WIDTH
    WALL_H = _cfg.MATRIX_HEIGHT

    last_cycle_time = time.time()

    # SYNC button + large BPM readout to its right
    sync_btn = pygame.Rect(30, 20, 120, 40)
    bpm_display_rect = pygame.Rect(160, 20, 130, 40)

    bright_slider = HSlider("brightness", brightness, 0.0, 1.0, 0.01, 30, 90, 200)

    # Mic sensitivity slider + level meter
    mic_slider = HSlider("mic_sens", mic_sensitivity, 0.1, 3.0, 0.01, 30, 180, 200)
    mic_level_rect = pygame.Rect(30, 210, 200, 12)

    # Matrix dimension controls
    dim_options = [str(i) for i in range(4, 65)]
    width_dd = Dropdown("Width", dim_options, str(_cfg.MATRIX_WIDTH),
                        430, 20, width=80, show_label=True, max_visible=12)
    height_dd = Dropdown("Height", dim_options, str(_cfg.MATRIX_HEIGHT),
                         430, 55, width=80, show_label=True, max_visible=12)

    # Protocol selector
    protocol_dd = Dropdown("Protocol", PROTOCOL_CHOICES,
                           saved_cfg.get("led_protocol", "DRGB"),
                           430, 100, width=120, show_label=True, max_visible=7)

    # Display mode selector (simulator rendering style)
    SIM_MODES = ["Fill", "Grid", "Point"]
    sim_mode = "Fill"
    sim_mode_dd = Dropdown("Display", SIM_MODES, sim_mode,
                           430, 145, width=120, show_label=True, max_visible=3)

    # Quit button (bottom-right of CONFIG tab content area)
    quit_btn = pygame.Rect(SCREEN_W - 140, CONTENT_H - 50, 120, 40)

    # Save config button
    save_cfg_btn = pygame.Rect(SCREEN_W - 140, CONTENT_H - 100, 120, 40)

    # Load ALL patches into RAM cache (eliminates file I/O during runtime)
    _load_all_patches_into_cache()
    print(f"[cache] {len(_patch_cache)} patches loaded into RAM")

    # Pre-render ALL thumbnails so bank switching is instant
    _generate_all_thumbnails(patterns, sprites)
    print(f"[cache] {len(_thumb_cache)} thumbnails generated")

    # Build initial patch grid from cache
    reload_patch_grid(patterns, sprites, patch_icons, patches_arr)

    clock = pygame.time.Clock()
    running = True
    frame = None

    # ════════════════════════════════════════════════════════════════════
    while running:
        screen.fill(BG_COLOR)

        # ── random cycle (always active regardless of tab) ──────────────
        if random_cycle:
            now = time.time()
            beats_elapsed = (now - last_cycle_time) * (_lfo.BPM / 60.0)

            if beats_elapsed >= cycle_beats:
                last_cycle_time = now
                # Build list of available patches (from RAM cache)
                if random_mode == "Global":
                    saved = list(_patch_cache.keys())
                else:
                    saved = [(current_bank, sl)
                             for sl in range(TOTAL_SLOTS)
                             if (current_bank, sl) in _patch_cache]
                if saved:
                    bk, sl = random.choice(saved)
                    try:
                        old_bank = current_bank
                        current_bank = bk
                        (current_index, pattern, sliders,
                         dropdowns, mod_cbs) = restore_patch(
                            bk, sl, pattern_names, patterns,
                            [lfo1_p, lfo2_p], [envl_p, envh_p],
                            pat_dd, cmap_dd, sprite_dd, create_sliders)
                        params = pattern.params.copy()
                        # Only rebuild grid if we switched banks
                        if bk != old_bank:
                            reload_patch_grid(patterns, sprites,
                                              patch_icons, patches_arr)
                    except Exception as e:
                        print(f"[ui] Random switch failed: {e}")

        # ── auto-BPM ────────────────────────────────────────────────────
        if auto_bpm:
            detected = _aenv.detect_bpm()
            if detected is not None:
                _lfo.BPM = detected

        # ── events ──────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Tab switching
            if event.type == pygame.MOUSEBUTTONDOWN:
                for ti, tr in enumerate(tab_rects):
                    if tr.collidepoint(event.pos):
                        # auto-save config when leaving CONFIG tab
                        if active_tab == 3 and ti != 3:
                            save_yaml(_gather_settings(
                                cycle_beats, auto_bpm,
                                bright_slider, width_dd, height_dd, mic_sensitivity,
                                protocol_dd, _cfg))
                        active_tab = ti
                        # reset save/clear modes when leaving PATCH
                        if ti != 2:
                            save_mode = clear_mode = False
                        break

            # ── EDIT tab events ─────────────────────────────────────────
            if active_tab == 0:
                for d in dropdowns:
                    d.handle_event(event)
                for s in sliders:
                    s.handle_event(event)
                for c in mod_cbs:
                    if c.handle_event(event):
                        meta = pattern.param_meta.get(c.param_name)
                        if not meta or not meta.get("modulatable"):
                            continue
                        meta["mod_active"] = c.active
                        if c.active:
                            meta["mod_source"] = c.source_id
                            for o in mod_cbs:
                                if o is not c and o.param_name == c.param_name:
                                    o.active = False
                        else:
                            meta["mod_source"] = None
                for p in mod_panels:
                    p.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pat_dd.handle_event(event)
                    cmap_dd.handle_event(event)
                    sprite_dd.handle_event(event)

                    # ── Randomize buttons ───────────────────────────────
                    if rnd_settings_btn.collidepoint(event.pos):
                        # Randomize current pattern's slider params + LUT
                        for s in sliders:
                            s.value = round(random.uniform(s.min, s.max) / s.step) * s.step
                            if s.valid_values:
                                s.value = random.choice(s.valid_values)
                            params[s.name] = s.value
                        # Randomize LUT (but not sprite)
                        new_cmap = random.choice(cmap_names)
                        cmap_dd.selected = new_cmap
                        params["COLORMAP"] = new_cmap
                        pattern.update_params(params)
                        # Randomize LFOs (Q mode only), ENVs, and modulation
                        _randomize_mod(lfo1_p, lfo2_p, envl_p, envh_p,
                                       mod_cbs, pspecs)

                    elif rnd_pattern_btn.collidepoint(event.pos):
                        # Pick a random pattern, randomize its params + LUT
                        new_pat_name = random.choice(pattern_names)
                        current_index = pattern_names.index(new_pat_name)
                        module = patterns[new_pat_name]
                        pspecs = module.PARAMS
                        params = {k: v["default"] for k, v in pspecs.items()}
                        # Randomize slider params
                        for k, spec in pspecs.items():
                            if k in ("COLORMAP", "SPRITE"):
                                continue
                            if isinstance(spec, dict) and "options" in spec:
                                continue
                            if isinstance(spec, dict):
                                if "valid" in spec:
                                    params[k] = random.choice(spec["valid"])
                                else:
                                    mn = spec.get("min", spec["default"] / 2)
                                    mx = spec.get("max", spec["default"] * 2)
                                    st = spec.get("step", 0.1)
                                    params[k] = round(random.uniform(mn, mx) / st) * st
                        # Randomize LUT, keep current sprite
                        new_cmap = random.choice(cmap_names)
                        params["COLORMAP"] = new_cmap
                        params["SPRITE"] = sprite_dd.selected
                        cmap_dd.selected = new_cmap
                        pat_dd.selected = new_pat_name
                        for meta in pspecs.values():
                            if isinstance(meta, dict) and meta.get("modulatable"):
                                meta["mod_active"] = False
                                meta["mod_source"] = None
                        sliders, dropdowns, mod_cbs = create_sliders(pspecs, params)
                        pattern = module.Pattern(WALL_W, WALL_H, params=params)
                        # Randomize LFOs (Q mode only), ENVs, and modulation
                        _randomize_mod(lfo1_p, lfo2_p, envl_p, envh_p,
                                       mod_cbs, pspecs)

            # ── PATCH tab events ────────────────────────────────────────
            elif active_tab == 2 and event.type == pygame.MOUSEBUTTONDOWN:
                # Solid colour buttons
                _solid_hit = False
                for _slbl, _scol, _srect in solid_btns:
                    if _srect.collidepoint(event.pos):
                        solid_override = _scol
                        _solid_hit = True
                        break
                if _solid_hit:
                    pass
                elif save_btn.collidepoint(event.pos):
                    save_mode = not save_mode
                    clear_mode = False
                elif del_btn.collidepoint(event.pos):
                    clear_mode = not clear_mode
                    save_mode = False
                elif tap_btn.collidepoint(event.pos):
                    now = time.time()
                    tap_times.append(now)
                    tap_times = [t for t in tap_times if now - t < 3.0]
                    # Always reset the cycle counter (downbeat)
                    last_cycle_time = now
                    # Only update BPM when there are 2+ taps
                    if len(tap_times) >= 2:
                        ivs = [b - a for a, b in zip(tap_times, tap_times[1:])]
                        avg = sum(ivs) / len(ivs)
                        if avg > 0:
                            _lfo.BPM = 60.0 / avg
                elif rnd_btn.collidepoint(event.pos):
                    random_cycle = not random_cycle
                    last_cycle_time = time.time()
                elif rnd_mode_btn.collidepoint(event.pos):
                    random_mode = "Global" if random_mode == "Bank" else "Bank"
                elif bank_left_rect.collidepoint(event.pos) and current_bank > 0:
                    current_bank -= 1
                    reload_patch_grid(patterns, sprites, patch_icons, patches_arr)
                elif bank_right_rect.collidepoint(event.pos) and current_bank < MAX_BANKS - 1:
                    current_bank += 1
                    reload_patch_grid(patterns, sprites, patch_icons, patches_arr)
                else:
                    # Beat-count buttons
                    _beat_hit = False
                    for bval, brect in beat_btns:
                        if brect.collidepoint(event.pos):
                            cycle_beats = bval
                            _beat_hit = True
                            break
                    if _beat_hit:
                        pass
                    else:
                        for i, sr in enumerate(patch_rects):
                            if sr.collidepoint(event.pos):
                                if save_mode:
                                    lc = {"lfo1": lfo1_p.config.copy(), "lfo2": lfo2_p.config.copy()}
                                    ec = {"envl": envl_p.config.copy(), "envh": envh_p.config.copy()}
                                    save_patch(current_bank, i, pattern_names[current_index],
                                               params, pattern.param_meta, lc, ec)
                                    if frame:
                                        th = pygame.Surface((pattern.width, pattern.height))
                                        draw_simulator(th, frame, pattern.width, pattern.height,
                                                       pygame.Rect(0, 0, pattern.width, pattern.height))
                                        patch_icons[i] = pygame.transform.smoothscale(
                                            th, (SLOT_SIZE, SLOT_SIZE))
                                    patches_arr[i] = True
                                    save_mode = False
                                elif clear_mode:
                                    delete_patch(current_bank, i)
                                    patches_arr[i] = None
                                    patch_icons[i] = None
                                    clear_mode = False
                                else:
                                    if patches_arr[i]:
                                        (current_index, pattern, sliders,
                                         dropdowns, mod_cbs) = restore_patch(
                                            current_bank, i, pattern_names, patterns,
                                            [lfo1_p, lfo2_p], [envl_p, envh_p],
                                            pat_dd, cmap_dd, sprite_dd, create_sliders)
                                        params = pattern.params.copy()
                                        solid_override = None
                                break

            # ── CONFIG tab events ───────────────────────────────────────
            elif active_tab == 3:
                bright_slider.handle_event(event)
                mic_slider.handle_event(event)
                # Track sensitivity from slider
                mic_sensitivity = mic_slider.value
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if sync_btn.collidepoint(event.pos):
                        auto_bpm = not auto_bpm
                    elif save_cfg_btn.collidepoint(event.pos):
                        save_yaml(_gather_settings(
                            cycle_beats, auto_bpm,
                            bright_slider, width_dd, height_dd, mic_sensitivity,
                            protocol_dd, _cfg))
                    elif quit_btn.collidepoint(event.pos):
                        # Save settings before quitting
                        save_yaml(_gather_settings(
                            cycle_beats, auto_bpm,
                            bright_slider, width_dd, height_dd, mic_sensitivity,
                            protocol_dd, _cfg))
                        running = False
                    width_dd.handle_event(event)
                    height_dd.handle_event(event)
                    protocol_dd.handle_event(event)
                    sim_mode_dd.handle_event(event)
                    # apply display mode change
                    sim_mode = sim_mode_dd.selected
                    # apply protocol change to wall
                    if wall is not None and wall.protocol != protocol_dd.selected.upper().replace(" ", ""):
                        wall.protocol = protocol_dd.selected
                    # apply dimension changes
                    new_w = int(width_dd.selected)
                    new_h = int(height_dd.selected)
                    if new_w != _cfg.MATRIX_WIDTH or new_h != _cfg.MATRIX_HEIGHT:
                        _cfg.MATRIX_WIDTH = new_w
                        _cfg.MATRIX_HEIGHT = new_h
                        WALL_W = new_w
                        WALL_H = new_h
                        try:
                            pattern = module.Pattern(WALL_W, WALL_H, params=params)
                        except Exception as e:
                            print(f"[ui] Pattern resize failed: {e}")

        # ── instant slider updates ──────────────────────────────────────
        if instant_update and active_tab == 0:
            for s in sliders:
                params[s.name] = s.value
            pattern.update_params(params)

        # ── pattern dropdown change ─────────────────────────────────────
        new_pat = pat_dd.selected
        if new_pat != pattern_names[current_index]:
            current_index = pattern_names.index(new_pat)
            module = patterns[new_pat]
            pspecs = module.PARAMS
            params = {k: v["default"] for k, v in pspecs.items()}
            params["COLORMAP"] = cmap_dd.selected
            params["SPRITE"] = sprite_dd.selected
            for meta in pspecs.values():
                if isinstance(meta, dict) and meta.get("modulatable"):
                    meta["mod_active"] = False
                    meta["mod_source"] = None
            sliders, dropdowns, mod_cbs = create_sliders(pspecs, params)
            pattern = module.Pattern(WALL_W, WALL_H, params=params)

        params["COLORMAP"] = cmap_dd.selected
        params["SPRITE"] = sprite_dd.selected
        pattern.update_params(params)

        # ── evaluate mod sources & render ───────────────────────────────
        mod_signals = evaluate_lfos()
        mod_signals.update(evaluate_env())
        try:
            frame = pattern.render(lfo_signals=mod_signals)
        except Exception as e:
            # If render fails (e.g. after a resize), create a blank frame
            print(f"[ui] Render failed: {e}")
            frame = [(0, 0, 0, 0)] * (WALL_W * WALL_H)

        # ── sprite overlay ──────────────────────────────────────────────
        sn = params.get("SPRITE", "none")
        if sn in sprites and sprites[sn]:
            sframes = sprites[sn]
            beat = (pygame.time.get_ticks() / 1000.0) * (_lfo.BPM / 60.0)
            sf = sframes[int(beat) % len(sframes)]
            sw, sh = sf.get_size()
            if sw <= pattern.width and sh <= pattern.height:
                ox = (pattern.width - sw) // 2
                oy = (pattern.height - sh) // 2
                for yy in range(sh):
                    for xx in range(sw):
                        rgba = sf.get_at((xx, yy))
                        if rgba[3] > 0:
                            idx = (oy + yy) * pattern.width + (ox + xx)
                            if 0 <= idx < len(frame):
                                frame[idx] = (rgba.r, rgba.g, rgba.b, 0)

        # ── solid colour override (replaces frame so preview also shows it)
        if solid_override is not None:
            frame = [solid_override + (0,)] * (WALL_W * WALL_H)

        # ── send to wall ────────────────────────────────────────────────
        if wall is not None:
            brightness = bright_slider.value
            if brightness < 1.0:
                out = []
                for px in frame:
                    r, g, b = px[0], px[1], px[2]
                    w = px[3] if len(px) > 3 else 0
                    out.append((int(r * brightness), int(g * brightness),
                                int(b * brightness), int(w * brightness)))
                wall.show(out)
            else:
                wall.show(frame)

        # ══════════════════════════════════════════════════════════════════
        # Drawing – content area (above tab bar)
        # ══════════════════════════════════════════════════════════════════

        if active_tab == 0:
            # ── EDIT ────────────────────────────────────────────────────
            # Layer 1: sliders, checkboxes, simulator
            for s in sliders:
                s.draw(screen, font)
            for c in mod_cbs:
                c.draw(screen)

            # Simulator preview between sliders and LFO/ENV panels
            sim_left = 220
            sim_right = RX - 10
            sim_w = sim_right - sim_left
            sim_h = CONTENT_H - 40
            if frame and sim_w > 20 and sim_h > 20:
                draw_simulator(screen, frame, pattern.width, pattern.height,
                               pygame.Rect(sim_left, 30, sim_w, sim_h),
                               sim_mode.lower())

            # Layer 2: mod panels (closed dropdowns only)
            for p in mod_panels:
                p.draw(screen, font)

            # mod-signal indicators (wider, moved up)
            ind_y = 385
            ind_w, ind_h = 150, 8
            for j, (key, col) in enumerate([
                ("lfo1", (100, 200, 255)), ("lfo2", (255, 100, 200)),
                ("envl", (255, 255, 100)), ("envh", (255, 150, 50))]):
                draw_mod_indicator(screen, font, mod_signals, key, col,
                                   pygame.Rect(RX, ind_y + j * (ind_h + 3), ind_w, ind_h))

            # Randomize buttons (centred above tab bar)
            pygame.draw.rect(screen, (90, 140, 90), rnd_settings_btn, border_radius=4)
            _rs_lbl = sm_font.render("RND Settings", True, (255, 255, 255))
            screen.blit(_rs_lbl, (rnd_settings_btn.x + (rnd_settings_btn.width - _rs_lbl.get_width()) // 2,
                                  rnd_settings_btn.y + (rnd_settings_btn.height - _rs_lbl.get_height()) // 2))
            pygame.draw.rect(screen, (140, 90, 140), rnd_pattern_btn, border_radius=4)
            _rp_lbl = sm_font.render("RND Pattern", True, (255, 255, 255))
            screen.blit(_rp_lbl, (rnd_pattern_btn.x + (rnd_pattern_btn.width - _rp_lbl.get_width()) // 2,
                                  rnd_pattern_btn.y + (rnd_pattern_btn.height - _rp_lbl.get_height()) // 2))

            # Layer 3: param dropdowns (closed first)
            for d in dropdowns:
                if not d.open:
                    d.draw(screen, font)
            pat_dd.draw(screen, font)
            cmap_dd.draw(screen, font)
            sprite_dd.draw(screen, font)

            # Layer 4 (topmost): any open dropdowns drawn last
            for p in mod_panels:
                p.draw_open_dropdowns(screen, font)
            for d in dropdowns:
                if d.open:
                    d.draw(screen, font)
            if pat_dd.open:
                pat_dd.draw(screen, font)
            if cmap_dd.open:
                cmap_dd.draw(screen, font)
            if sprite_dd.open:
                sprite_dd.draw(screen, font)

        elif active_tab == 1:
            # ── VIEW ────────────────────────────────────────────────────
            if frame:
                draw_simulator(screen, frame, pattern.width, pattern.height,
                               pygame.Rect(0, 0, SCREEN_W, CONTENT_H),
                               sim_mode.lower())

        elif active_tab == 2:
            # ── PATCH ───────────────────────────────────────────────────
            for i, sr in enumerate(patch_rects):
                pygame.draw.rect(screen, (50, 50, 50), sr)
                ic = patch_icons[i]
                if ic:
                    screen.blit(ic, ic.get_rect(center=sr.center))
                bc = (200, 80, 80) if (save_mode or clear_mode) else (100, 100, 100)
                pygame.draw.rect(screen, bc, sr, 2)

            # save / delete buttons
            pygame.draw.rect(screen, (200, 80, 80) if save_mode else (80, 180, 80), save_btn)
            stxt = "SAVE" if not save_mode else "TAP SLOT"
            sl = font.render(stxt, True, (255, 255, 255))
            screen.blit(sl, (save_btn.x + (save_btn.width - sl.get_width()) // 2,
                             save_btn.y + (save_btn.height - sl.get_height()) // 2))
            pygame.draw.rect(screen, (200, 80, 80) if clear_mode else (80, 80, 180), del_btn)
            dtxt = "DELETE" if not clear_mode else "TAP SLOT"
            dl = font.render(dtxt, True, (255, 255, 255))
            screen.blit(dl, (del_btn.x + (del_btn.width - dl.get_width()) // 2,
                             del_btn.y + (del_btn.height - dl.get_height()) // 2))

            # tap tempo
            pygame.draw.rect(screen, (90, 90, 90), tap_btn)
            tl = bold_font.render("TAP", True, (255, 255, 255))
            screen.blit(tl, (tap_btn.x + (tap_btn.width - tl.get_width()) // 2,
                             tap_btn.y + 8))
            bpm_txt = f"{int(_lfo.BPM)} BPM"
            bl = bold_font.render(bpm_txt, True, (127, 255, 0))
            screen.blit(bl, (tap_btn.x + (tap_btn.width - bl.get_width()) // 2,
                             tap_btn.y + 32))

            # thumbnail
            screen.blit(sm_font.render("Preview", True, (160, 160, 160)),
                        (thumb_rect.x, thumb_rect.y - 14))
            pygame.draw.rect(screen, (50, 50, 50), thumb_rect)
            if frame:
                draw_simulator(screen, frame, pattern.width, pattern.height,
                               thumb_rect, sim_mode.lower())

            # bank nav
            pygame.draw.rect(screen, (80, 80, 80), bank_left_rect)
            lt = font.render("<", True, (255, 255, 255))
            screen.blit(lt, (bank_left_rect.x + (bank_left_rect.width - lt.get_width()) // 2,
                             bank_left_rect.y + (bank_left_rect.height - lt.get_height()) // 2))
            pygame.draw.rect(screen, (80, 80, 80), bank_right_rect)
            rt = font.render(">", True, (255, 255, 255))
            screen.blit(rt, (bank_right_rect.x + (bank_right_rect.width - rt.get_width()) // 2,
                             bank_right_rect.y + (bank_right_rect.height - rt.get_height()) // 2))
            pygame.draw.rect(screen, (120, 120, 120), bank_label_rect)
            bt = font.render(f"Bank {current_bank}", True, (0, 0, 0))
            screen.blit(bt, (bank_label_rect.x + (bank_label_rect.width - bt.get_width()) // 2,
                             bank_label_rect.y + (bank_label_rect.height - bt.get_height()) // 2))

            # RND toggle + mode buttons (above bank nav)
            rnd_col = (200, 80, 80) if random_cycle else (80, 80, 80)
            pygame.draw.rect(screen, rnd_col, rnd_btn)
            rnd_lbl = sm_font.render("RND " + ("ON" if random_cycle else "OFF"), True, (255, 255, 255))
            screen.blit(rnd_lbl, (rnd_btn.x + (rnd_btn.width - rnd_lbl.get_width()) // 2,
                                  rnd_btn.y + (rnd_btn.height - rnd_lbl.get_height()) // 2))
            mode_col = (90, 90, 160) if random_mode == "Global" else (90, 130, 90)
            pygame.draw.rect(screen, mode_col, rnd_mode_btn)
            mode_lbl = sm_font.render(random_mode, True, (255, 255, 255))
            screen.blit(mode_lbl, (rnd_mode_btn.x + (rnd_mode_btn.width - mode_lbl.get_width()) // 2,
                                   rnd_mode_btn.y + (rnd_mode_btn.height - mode_lbl.get_height()) // 2))

            # Beat-count buttons (2 rows of 3, below bank nav)
            for bval, brect in beat_btns:
                sel = (bval == cycle_beats)
                bc = (80, 80, 180) if sel else (70, 70, 70)
                pygame.draw.rect(screen, bc, brect, border_radius=3)
                if sel:
                    pygame.draw.rect(screen, (120, 120, 220), brect, 2, border_radius=3)
                bl = sm_font.render(str(bval), True, (255, 255, 255))
                screen.blit(bl, (brect.x + (brect.width - bl.get_width()) // 2,
                                 brect.y + (brect.height - bl.get_height()) // 2))

            # Solid colour buttons (3×3 grid below preview)
            for _slbl, _scol, _srect in solid_btns:
                pygame.draw.rect(screen, _scol, _srect)
                pygame.draw.rect(screen, (180, 180, 180) if solid_override == _scol else (80, 80, 80), _srect, 2)
                if _scol == (0, 0, 0):  # label "K" on black so it's visible
                    kl = sm_font.render(_slbl, True, (160, 160, 160))
                    screen.blit(kl, (_srect.x + (_srect.width - kl.get_width()) // 2,
                                     _srect.y + (_srect.height - kl.get_height()) // 2))

        elif active_tab == 3:
            # ── CONFIG ──────────────────────────────────────────────────

            # auto-BPM sync button
            sc = (100, 255, 100) if auto_bpm else (90, 90, 90)
            pygame.draw.rect(screen, sc, sync_btn)
            screen.blit(font.render("SYNC " + ("ON" if auto_bpm else "OFF"),
                                    True, (255, 255, 255)),
                        (sync_btn.x + 8, sync_btn.y + 10))

            # BPM readout (large, to the right of SYNC, same height)
            pygame.draw.rect(screen, (40, 40, 40), bpm_display_rect, border_radius=4)
            bpm_font = pygame.font.SysFont("monospace", 28, bold=True)
            bpm_surf = bpm_font.render(f"{int(_lfo.BPM)}", True, (127, 255, 0))
            screen.blit(bpm_surf, (bpm_display_rect.x + (bpm_display_rect.width - bpm_surf.get_width()) // 2,
                                   bpm_display_rect.y + (bpm_display_rect.height - bpm_surf.get_height()) // 2))
            bpm_lbl = sm_font.render("BPM", True, (160, 160, 160))
            screen.blit(bpm_lbl, (bpm_display_rect.right - bpm_lbl.get_width() - 4,
                                  bpm_display_rect.y + 2))

            # brightness
            screen.blit(font.render(f"Brightness: {bright_slider.value:.0%}",
                                    True, (200, 200, 200)), (30, 102))
            bright_slider.draw(screen, font)

            # Mic sensitivity slider
            screen.blit(font.render(f"Mic Sensitivity: {mic_slider.value:.2f}",
                                    True, (200, 200, 200)), (30, 195))
            mic_slider.draw(screen, font)

            # Mic level meter (post-sensitivity)
            level = get_input_level(mic_sensitivity)
            pygame.draw.rect(screen, (50, 50, 50), mic_level_rect)
            bar_w = int(level * mic_level_rect.width)
            if bar_w > 0:
                col = (0, 200, 0) if level < 0.7 else (255, 200, 0) if level < 0.9 else (255, 50, 50)
                pygame.draw.rect(screen, col,
                                 pygame.Rect(mic_level_rect.x, mic_level_rect.y, bar_w, mic_level_rect.height))

            # matrix dimensions
            width_dd.draw(screen, font)
            height_dd.draw(screen, font)

            # protocol selector
            protocol_dd.draw(screen, font)

            # display mode selector
            sim_mode_dd.draw(screen, font)

            # quit button
            pygame.draw.rect(screen, (180, 50, 50), quit_btn)
            ql = bold_font.render("QUIT", True, (255, 255, 255))
            screen.blit(ql, (quit_btn.x + (quit_btn.width - ql.get_width()) // 2,
                             quit_btn.y + (quit_btn.height - ql.get_height()) // 2))

            # save config button
            pygame.draw.rect(screen, (80, 160, 80), save_cfg_btn)
            sl = bold_font.render("SAVE", True, (255, 255, 255))
            screen.blit(sl, (save_cfg_btn.x + (save_cfg_btn.width - sl.get_width()) // 2,
                             save_cfg_btn.y + (save_cfg_btn.height - sl.get_height()) // 2))

            # config-tab: open dropdowns on top
            if width_dd.open:
                width_dd.draw(screen, font)
            if height_dd.open:
                height_dd.draw(screen, font)
            if protocol_dd.open:
                protocol_dd.draw(screen, font)
            if sim_mode_dd.open:
                sim_mode_dd.draw(screen, font)

        # ── Tab bar ─────────────────────────────────────────────────────
        for i, tr in enumerate(tab_rects):
            col = TAB_ACTIVE if i == active_tab else TAB_BG
            pygame.draw.rect(screen, col, tr)
            pygame.draw.rect(screen, (80, 80, 80), tr, 1)
            lbl = font.render(TAB_NAMES[i], True, (255, 255, 255))
            screen.blit(lbl, (tr.x + (TAB_W - lbl.get_width()) // 2,
                              tr.y + (TAB_H - lbl.get_height()) // 2))

        pygame.display.flip()
        clock.tick(FRAME_RATE)

    if wall is not None:
        wall.clear()
    pygame.quit()
