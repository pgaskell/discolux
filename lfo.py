import math
import time

# Global BPM (can be changed externally)
BPM = 120.0

# Time-tracking start (used for phase calc)
start_time = time.time()

# LFO config: two LFOs, identified as "lfo1" and "lfo2"
LFO_CONFIG = {
    "lfo1": {
        "waveform": "sine",
        "depth": 1.0,
        "offset": 0.0,
        "sync_mode": "quantized",  # "free" or "quantized"
        "hz": 0.5,
        "period_beats": 1.0,  # Only used if quantized
        "phase": 0.0
    },
    "lfo2": {
        "waveform": "triangle",
        "depth": 1.0,
        "offset": 0.0,
        "sync_mode": "free",
        "hz": 0.2,
        "period_beats": 2.0,
        "phase": 0.0
    }
}


def _get_time():
    return time.time() - start_time


def _waveform(phase, shape):
    """Given phase ∈ [0, 1), return waveform value ∈ [-1, 1]"""
    if shape == "sine":
        return math.sin(2 * math.pi * phase)
    elif shape == "square":
        return 1.0 if phase < 0.5 else -1.0
    elif shape == "triangle":
        return 4.0 * abs(phase - 0.5) - 1.0
    elif shape == "saw":
        return 2.0 * (phase - 0.5)
    else:
        return 0.0  # fallback


def evaluate_lfos():
    """Returns dict: {'lfo1':value,'lfo2':value} with value in [-1..1]."""
    now     = _get_time()
    signals = {}
    for name, cfg in LFO_CONFIG.items():
        depth     = cfg.get("depth", 1.0)
        offset    = cfg.get("offset", 0.0)
        shape     = cfg.get("waveform", "sine")
        phase_off = cfg.get("phase", 0.0)

        # 1) Figure out period (either quantized or free)
        if cfg.get("sync_mode") == "quantized":
            beats_per_sec = BPM / 60.0
            pb            = cfg.get("period_beats", 1.0) * 4.0
            period        = pb / beats_per_sec
        else:
            period = 1.0 / max(cfg.get("hz", 0.1), 1e-3)

        # 2) Compute phase ∈ [0,1)
        phase = ((now + phase_off) % period) / period

        # 3) Raw waveform ∈ [-1,1]
        raw = _waveform(phase, shape)

        # 4) Scale + offset
        val = raw * depth + offset

        # 5) (Optional) Clamp into [-1,1] rather than ±depth
        val = max(-1.0, min(1.0, val))

        signals[name] = val

    # debug print to verify live changes:
    #print("LFOs:", {k:round(v,3) for k,v in signals.items()})
    return signals
