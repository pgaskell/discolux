"""
audio_env.py – Real-time audio envelope follower and FFT band analyser.

Provides two envelope outputs (``envl`` – low band, ``envh`` – high band)
and an N-band FFT analyser for VU-meter style visualisations.

The audio input stream is started automatically on import.
"""

import math
import numpy as np
import sounddevice as sd
from collections import deque

# ─── Audio parameters ──────────────────────────────────────────────────────
SAMPLERATE = 44100
BLOCKSIZE = 1024
FFT_SIZE = 2048

# Envelope frequency bands
LOW_BAND = (50, 150)
HIGH_BAND = (1000, 5000)
N_BANDS = 24

LOW_GAIN = 0.1
HIGH_GAIN = 1.0

# ─── Envelope configuration (saveable with patches) ───────────────────────
ENV_CONFIG = {
    "envl": {
        "threshold_db": -10,
        "gain_db": 0,
        "attack": 0.005,
        "release": 0.100,
        "mode": "up",
    },
    "envh": {
        "threshold_db": -10,
        "gain_db": 0,
        "attack": 0.005,
        "release": 0.100,
        "mode": "up",
    },
}

# ─── Precompute FFT bin masks ──────────────────────────────────────────────
_freqs = np.fft.rfftfreq(BLOCKSIZE, d=1.0 / SAMPLERATE)
_low_bins = np.where((_freqs >= LOW_BAND[0]) & (_freqs <= LOW_BAND[1]))[0]
_high_bins = np.where((_freqs >= HIGH_BAND[0]) & (_freqs <= HIGH_BAND[1]))[0]

# Log-spaced edges for the N-band analyser
_fmin, _fmax = 20.0, SAMPLERATE / 2
_edges = np.logspace(np.log10(_fmin), np.log10(_fmax), N_BANDS + 1)
_band_bins = [
    np.where((_freqs >= _edges[i]) & (_freqs < _edges[i + 1]))[0]
    for i in range(N_BANDS)
]

# ─── Internal state ───────────────────────────────────────────────────────
_raw_l = 0.0
_raw_h = 0.0
_sm_l = 0.0
_sm_h = 0.0
_prev_above_l = False
_prev_above_h = False
_state_l = True
_state_h = True
_raw_bands = [0.0] * N_BANDS
_peak_rms = 0.0  # broadband RMS for level meter (0.0 – 1.0 ish)

# Rolling FFT buffer (mono)
_fft_buffer: deque = deque(maxlen=FFT_SIZE)


# ─── Audio callback ───────────────────────────────────────────────────────

def _audio_cb(indata, frames, time_info, status):
    """Sounddevice callback – compute per-block RMS for low/high bands."""
    global _raw_l, _raw_h, _raw_bands, _peak_rms

    samples = indata[:, 0]  # mono
    _fft_buffer.extend(samples)

    # Broadband RMS for level meter
    rms = float(np.sqrt(np.mean(samples ** 2)))
    _peak_rms = max(rms, _peak_rms * 0.92)  # fast attack, slow decay

    mono = samples * np.hanning(frames)
    spec = np.fft.rfft(mono, n=FFT_SIZE)
    mag2 = np.abs(spec) ** 2

    _raw_l = LOW_GAIN * math.sqrt(np.mean(mag2[_low_bins])) if _low_bins.size else 0.0
    _raw_h = HIGH_GAIN * math.sqrt(np.mean(mag2[_high_bins])) if _high_bins.size else 0.0

    for idx, bins in enumerate(_band_bins):
        _raw_bands[idx] = math.sqrt(np.mean(mag2[bins])) if bins.size else 0.0

    _update_onset()


# Start the audio stream once on import
_stream = sd.InputStream(
    channels=1,
    samplerate=SAMPLERATE,
    blocksize=BLOCKSIZE,
    callback=_audio_cb,
)
_stream.start()


# ─── Public API ────────────────────────────────────────────────────────────

def get_input_level(sensitivity: float = 1.0) -> float:
    """Return current broadband input level (0.0 – ~1.0) for a level meter.

    *sensitivity* is a linear multiplier (default 1.0).  The CONFIG-tab
    slider feeds this value so the user can boost or cut the displayed
    level and, by extension, how strongly audio drives the envelopes.
    """
    return min(1.0, _peak_rms * 5.0 * max(sensitivity, 0.01))

def evaluate_env() -> dict[str, float]:
    """
    Return ``{'envl': float, 'envh': float}`` – current envelope outputs
    after threshold, gain, smoothing, and mode processing.
    """
    global _sm_l, _sm_h
    global _prev_above_l, _prev_above_h, _state_l, _state_h

    out = {}
    for name, raw in (("envl", _raw_l), ("envh", _raw_h)):
        cfg = ENV_CONFIG[name]
        thr_db = cfg["threshold_db"]
        gain_db = cfg["gain_db"]
        atk_tc = cfg["attack"]
        rel_tc = cfg["release"]
        mode = cfg["mode"]

        dt = BLOCKSIZE / SAMPLERATE
        alpha_a = math.exp(-dt / atk_tc)
        alpha_r = math.exp(-dt / rel_tc)

        thr_lin = 10 ** (thr_db / 20.0)
        gain_lin = 10 ** (gain_db / 20.0)

        # Select per-band state
        if name == "envl":
            sm, prev_above, state = _sm_l, _prev_above_l, _state_l
        else:
            sm, prev_above, state = _sm_h, _prev_above_h, _state_h

        val = max(0.0, raw - thr_lin)

        # Attack / release smoothing
        if val > sm:
            sm = (1 - alpha_a) * val + alpha_a * sm
        else:
            sm = (1 - alpha_r) * val + alpha_r * sm

        # Mode
        above = val > 0.0
        if mode == "up":
            sig = sm
        elif mode == "down":
            sig = -sm
        else:  # updown
            if above and not prev_above:
                state = not state
            sig = sm if state else -sm

        sig *= gain_lin

        # Store back
        if name == "envl":
            _sm_l, _prev_above_l, _state_l = sm, above, state
        else:
            _sm_h, _prev_above_h, _state_h = sm, above, state

        out[name] = sig

    return out


def evaluate_fft_bands(n_bands: int = N_BANDS) -> list[float]:
    """
    Return a list of *n_bands* values in ``[0.0 .. 1.0]`` representing
    the current FFT energy in log-spaced frequency bands.
    """
    data = np.array(_fft_buffer, dtype=float)
    if data.size < FFT_SIZE:
        data = np.pad(data, (FFT_SIZE - data.size, 0), "constant")

    window = np.hanning(FFT_SIZE)
    spec = np.abs(np.fft.rfft(data * window))
    spec /= spec.max() + 1e-12

    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLERATE)
    fmax = SAMPLERATE / 2.0
    fmin_nz = freqs[1] if freqs.size > 1 else 0.0
    log_edges = np.logspace(math.log10(fmin_nz), math.log10(fmax), n_bands - 1)
    edges = np.concatenate(([0.0], log_edges, [fmax]))

    out = []
    db_floor = -30.0

    for i in range(n_bands):
        low_e, high_e = edges[i], edges[i + 1]
        mask = (freqs >= low_e) & (freqs < high_e)

        if mask.any():
            m = float(spec[mask].mean())
        else:
            center_f = (low_e + high_e) / 2.0
            nearest = int(np.argmin(np.abs(freqs - center_f)))
            m = float(spec[nearest])

        m_db = max(db_floor, 10.0 * math.log10(m + 1e-12))
        m_norm = (m_db - db_floor) / (-db_floor)
        out.append(m_norm)

    return out


# ─── Auto-BPM detection via onset autocorrelation ─────────────────────────
# Enhanced with hysteresis, octave correction and median filtering for
# stable output on 4/4 dance music.

# Onset energy history – one value per audio callback (~23 ms per block)
_onset_history: deque = deque(maxlen=512)
_prev_energy: float = 0.0

# Hysteresis state
_bpm_estimates: deque = deque(maxlen=12)   # recent raw estimates
_stable_bpm: float | None = None           # current published BPM
_BPM_HYSTERESIS = 3.0                      # ignore changes smaller than this
_BPM_PREFER_LO = 110.0                     # preferred range for 4/4 dance
_BPM_PREFER_HI = 160.0


def _update_onset():
    """Called inside _audio_cb to keep onset history up-to-date."""
    global _prev_energy
    energy = _raw_l + _raw_h  # broadband energy proxy
    diff = max(0.0, energy - _prev_energy)
    _onset_history.append(diff)
    _prev_energy = energy


def _octave_correct(bpm: float) -> float:
    """Snap *bpm* into the preferred 4/4 dance range by halving/doubling."""
    for _ in range(4):
        if bpm < _BPM_PREFER_LO and bpm * 2 <= 200:
            bpm *= 2
        elif bpm > _BPM_PREFER_HI and bpm / 2 >= 60:
            bpm /= 2
        else:
            break
    return bpm


def detect_bpm(min_bpm: float = 60, max_bpm: float = 200) -> float | None:
    """
    Estimate BPM from recent onset-energy history using autocorrelation
    with octave correction and hysteresis.

    Returns a float BPM if a confident, stable estimate is found,
    otherwise ``None``.  Cheap enough to call once per frame.
    """
    global _stable_bpm

    buf = np.array(_onset_history, dtype=float)
    if buf.size < 200:
        return _stable_bpm  # not enough history yet

    # Normalise
    buf = buf - buf.mean()
    norm = np.dot(buf, buf)
    if norm < 1e-12:
        return _stable_bpm

    # Full autocorrelation via FFT
    n = 2 * buf.size
    fft = np.fft.rfft(buf, n=n)
    acf = np.fft.irfft(fft * np.conj(fft))[:buf.size]
    acf /= norm

    # Convert BPM range to lag range (in blocks)
    block_rate = SAMPLERATE / BLOCKSIZE  # blocks per second
    min_lag = max(1, int(block_rate * 60.0 / max_bpm))
    max_lag = min(buf.size - 1, int(block_rate * 60.0 / min_bpm))
    if min_lag >= max_lag:
        return _stable_bpm

    region = acf[min_lag:max_lag + 1]
    if region.max() < 0.18:
        return _stable_bpm  # weak periodicity – not confident

    # Find the top-3 peaks and prefer the one closest to dance range
    from scipy.signal import find_peaks as _fp
    try:
        peaks, props = _fp(region, height=0.15, distance=2)
    except Exception:
        peaks = np.array([int(np.argmax(region))])
        props = {"peak_heights": np.array([region.max()])}

    if peaks.size == 0:
        return _stable_bpm

    candidates = []
    heights = props.get("peak_heights", region[peaks])
    for pk, ht in zip(peaks, heights):
        lag = pk + min_lag
        raw = 60.0 * block_rate / lag
        corrected = _octave_correct(raw)
        # Score: autocorrelation height + bonus if in preferred range
        bonus = 0.05 if _BPM_PREFER_LO <= corrected <= _BPM_PREFER_HI else 0.0
        candidates.append((corrected, float(ht) + bonus))

    # Pick the highest-scoring candidate
    candidates.sort(key=lambda c: c[1], reverse=True)
    raw_bpm = round(candidates[0][0], 1)

    # Median filter: accumulate estimates, take median
    _bpm_estimates.append(raw_bpm)
    if len(_bpm_estimates) < 4:
        return _stable_bpm

    median_bpm = float(sorted(_bpm_estimates)[len(_bpm_estimates) // 2])

    # Hysteresis: only publish if change exceeds threshold
    if _stable_bpm is None or abs(median_bpm - _stable_bpm) > _BPM_HYSTERESIS:
        _stable_bpm = round(median_bpm, 1)

    return _stable_bpm
