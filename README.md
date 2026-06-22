# DiscoLux

**Real-time LED wall controller with a touch-friendly UI, built for Raspberry Pi.**

DiscoLux drives addressable LED matrices (WS2812 / WS2814 / SK6812) via
[WLED](https://kno.wled.ge/) controllers over Ethernet or Wi-Fi.  It features
a pattern engine with modulation, a patch recall system, audio reactivity, and
an 800 × 480 touchscreen interface designed for live performance.

> **Authors:** P. Gaskell & AI assistants

---

This software was written specifically for a custom LED matrix display and a modified Govee LightWall.

The complete parts needed to build a modified LightWall are available on Amazon.

| Item | Supplier | QTY | Price | Total | Link |
|------|----------|-----|-------|-------|------|
| Govee Lightwall | Amazon | 1 | 449.99 | 449.99 | [Link](https://www.amazon.com/Govee-Lightwall-Portable-Dimmable-Waterproof/dp/B0GKPS7D76) |
| GLEDOPTO Elite 4 Channel ESP32 WLED LED Strip Light Controller | Amazon | 1 | 30.59 | 30.59 | [Link](https://www.amazon.com/GLEDOPTO-Controller-Ethernet-Pluggable-Addressable/dp/B0FZ7WCYCK) |
| USB 2.0 Mini Microphone | Amazon | 1 | 9.59 | 9.59 | [Link](https://www.amazon.com/Microphone-Raspberry-Desktop-Recording-YouTube/dp/B0CYM618H7) |
| 7 Inch Touchscreen IPS DSI Display | Amazon | 1 | 38.99 | 38.99 | [Link](https://www.amazon.com/Hosyond-Touchscreen-Compatible-Capacitive-Driver-Free/dp/B0D3QB7X4Z) |
| CanaKit Raspberry Pi 4 4GB Basic Kit | Amazon | 1 | 124.99 | 124.99 | [Link](https://www.amazon.com/CanaKit-Raspberry-4GB-Basic-Kit/dp/B07TXKY4Z9) |
| Ethernet Cord, Black | Amazon | 1 | 15.99 | 15.99 | [Link](https://www.amazon.com/Cable-Matters-Snagless-Ethernet-Internet/dp/B0CP9XQWQ6) |
| Sandisk Ultra microSD 64 GB | Amazon | 1 | 23.91 | 23.91 | [Link](https://www.amazon.com/SanDisk-Ultra%C2%AE-microSDHC-120MB-Class/dp/B0BDRVFDKP) |
| | | | | **Total (1 wall):** | **694.05** |

| Item | Supplier | QTY | Price | Total | Link |
|------|----------|-----|-------|-------|------|
| Govee Lightwall | Amazon | 2 | 449.99 | 899.98 | [Link](https://www.amazon.com/Govee-Lightwall-Portable-Dimmable-Waterproof/dp/B0GKPS7D76) |
| GLEDOPTO Elite 4 Channel ESP32 WLED LED Strip Light Controller | Amazon | 2 | 30.59 | 61.18 | [Link](https://www.amazon.com/GLEDOPTO-Controller-Ethernet-Pluggable-Addressable/dp/B0FZ7WCYCK) |
| USB 2.0 Mini Microphone | Amazon | 1 | 9.59 | 9.59 | [Link](https://www.amazon.com/Microphone-Raspberry-Desktop-Recording-YouTube/dp/B0CYM618H7) |
| 7 Inch Touchscreen IPS DSI Display | Amazon | 1 | 38.99 | 38.99 | [Link](https://www.amazon.com/Hosyond-Touchscreen-Compatible-Capacitive-Driver-Free/dp/B0D3QB7X4Z) |
| CanaKit Raspberry Pi 4 4GB Basic Kit | Amazon | 1 | 124.99 | 124.99 | [Link](https://www.amazon.com/CanaKit-Raspberry-4GB-Basic-Kit/dp/B07TXKY4Z9) |
| 5 Port Gigabit Unmanaged Ethernet Switch | Amazon | 1 | 12.11 | 12.11 | [Link](https://www.amazon.com/Ethernet-Splitter-Optimization-Unmanaged-TL-SG105/dp/B00A128S24) |
| Ethernet Cord, Black | Amazon | 1 | 15.99 | 15.99 | [Link](https://www.amazon.com/Cable-Matters-Snagless-Ethernet-Internet/dp/B0CP9XQWQ6) |
| Sandisk Ultra microSD 64 GB | Amazon | 1 | 23.91 | 23.91 | [Link](https://www.amazon.com/SanDisk-Ultra%C2%AE-microSDHC-120MB-Class/dp/B0BDRVFDKP) |
| | | | | **Total (2 walls):** | **1186.74** |

| Item | Supplier | QTY | Price | Total | Link |
|------|----------|-----|-------|-------|------|
| Govee Lightwall | Amazon | 3 | 449.99 | 1349.97 | [Link](https://www.amazon.com/Govee-Lightwall-Portable-Dimmable-Waterproof/dp/B0GKPS7D76) |
| GLEDOPTO Elite 4 Channel ESP32 WLED LED Strip Light Controller | Amazon | 3 | 30.59 | 91.77 | [Link](https://www.amazon.com/GLEDOPTO-Controller-Ethernet-Pluggable-Addressable/dp/B0FZ7WCYCK) |
| USB 2.0 Mini Microphone | Amazon | 1 | 9.59 | 9.59 | [Link](https://www.amazon.com/Microphone-Raspberry-Desktop-Recording-YouTube/dp/B0CYM618H7) |
| 7 Inch Touchscreen IPS DSI Display | Amazon | 1 | 38.99 | 38.99 | [Link](https://www.amazon.com/Hosyond-Touchscreen-Compatible-Capacitive-Driver-Free/dp/B0D3QB7X4Z) |
| CanaKit Raspberry Pi 4 4GB Basic Kit | Amazon | 1 | 124.99 | 124.99 | [Link](https://www.amazon.com/CanaKit-Raspberry-4GB-Basic-Kit/dp/B07TXKY4Z9) |
| 5 Port Gigabit Unmanaged Ethernet Switch | Amazon | 1 | 12.11 | 12.11 | [Link](https://www.amazon.com/Ethernet-Splitter-Optimization-Unmanaged-TL-SG105/dp/B00A128S24) |
| Ethernet Cord, Black | Amazon | 1 | 15.99 | 15.99 | [Link](https://www.amazon.com/Cable-Matters-Snagless-Ethernet-Internet/dp/B0CP9XQWQ6) |
| Sandisk Ultra microSD 64 GB | Amazon | 1 | 23.91 | 23.91 | [Link](https://www.amazon.com/SanDisk-Ultra%C2%AE-microSDHC-120MB-Class/dp/B0BDRVFDKP) |
| | | | | **Total (3 walls):** | **1667.32** |

## Features

- **43 built-in patterns** — plasma, fire, kaleidoscope, VU meter, starfield,
  spirals, particle systems, cellular automata, and more
- **Real-time simulator** — three display modes (Fill, Grid, Point) preview
  the matrix on-screen
- **7 output protocols** — DRGB, DRGBW, DNRGB, WARLS, E1.31 (sACN),
  Art-Net, and HTTP JSON
- **LFO modulation** — two independent LFOs (sine / triangle / saw / square /
  random) with free-running or beat-synced rates
- **Audio-envelope modulation** — low-band and high-band RMS envelopes from a
  USB microphone, with configurable threshold, gain, attack, and release
- **Patch system** — 8 banks × 64 slots; each patch stores the pattern,
  parameters, modulation routing, LFO config, and envelope config
- **Random cycling** — automatically step through saved patches every N beats
  (1 – 32), scoped to the current bank or all banks
- **Sprite overlays** — static PNGs or animated GIFs composited on top of
  patterns (64 included)
- **Gamma & white-balance calibration** for RGBW LED strips
- **Auto-BPM detection** from the microphone input
- **Tap-tempo** with immediate downbeat reset
- **Kiosk boot** — custom Plymouth splash screen, silent boot, auto-login,
  and fullscreen launch with no desktop visible
- **All patches cached in RAM** — instant switching with zero disk I/O at
  runtime

---

## Hardware

| Component | Tested with |
|-----------|-------------|
| Single-board computer | Raspberry Pi 5 (8 GB) — also works on Pi 4 |
| Display | 800 × 480 DSI touchscreen (e.g. official Pi 7″) |
| LED controller | Gledopto Elite 4D-EXMU running WLED |
| LED matrix | 40 × 12 WS2814 RGBW (480 pixels, column-major wiring) |
| Audio input | USB microphone or sound card |
| Network | Ethernet or Wi-Fi to the WLED controller |

---

## Project Structure

```
discolux_ctrl/
├── discolux.py          # Main entry point
├── touch_ui.py          # 800×480 Pygame touch UI (EDIT / VIEW / PATCH / CONFIG tabs)
├── wall.py              # LED output — 7 protocols, column-major remap
├── config.py            # YAML-backed configuration
├── lfo.py               # Dual LFO engine (beat-sync + free-run)
├── audio_env.py         # Audio envelope follower + BPM detector
├── gamma.py             # Per-channel gamma / white-balance correction
├── colormaps.py         # Colour look-up tables for patterns
├── start_discolux.sh    # Boot launcher (called by labwc autostart)
├── launch_remote.py     # Launch/kill from a remote SSH session
├── install.sh           # Full deployment script for a fresh Pi
├── discolux_settings.yaml
├── requirements.txt
├── patterns/            # 43 pattern modules (drop in a .py to add more)
├── patches/             # Saved patch JSON files (8 banks × 64 slots)
└── sprites/             # PNG / GIF sprite overlays
```

---

## Installation

### Prerequisites

- Raspberry Pi OS **Bookworm** or **Trixie** (64-bit)
- labwc Wayland compositor + LightDM (default on current Pi OS Desktop)
- Python 3.11+

### Automated install

Clone or copy the project to `/home/rpi/discolux_ctrl`, then:

```bash
cd /home/rpi/discolux_ctrl
sudo ./install.sh
```

The install script:

1. Installs system packages (SDL2, PortAudio, Plymouth, LightDM, PipeWire,
   fonts)
2. Installs Python packages (`pygame`, `numpy`, `sounddevice`, `Pillow`,
   `PyYAML`, `scipy`)
3. Configures LightDM autologin with labwc
4. Sets up labwc kiosk mode (no desktop, no taskbar — just DiscoLux)
5. Installs the custom Plymouth boot splash theme
6. Configures silent boot (no Pi logo, no kernel messages, no cursor)
7. Sets file permissions
8. Rebuilds initramfs to include the splash theme

After install, **reboot** and DiscoLux will launch automatically.

### Manual launch (from SSH)

```bash
cd /home/rpi/discolux_ctrl
python3 launch_remote.py          # start on the Pi's display
python3 launch_remote.py --kill   # stop
```

---

## Configuration

Edit `discolux_settings.yaml` (or use the CONFIG tab in the UI):

```yaml
matrix_width: 40          # LED columns
matrix_height: 12         # LED rows
wled_host: 10.0.0.2       # WLED controller IP (blank = simulator only)
wled_timeout: 0.5         # HTTP timeout (only for HTTP JSON protocol)
led_protocol: DRGB        # DRGB / DRGBW / DNRGB / WARLS / E1.31 / Art-Net / HTTP JSON
frame_rate: 30            # Target FPS
cycle_beats: 16           # Beats per random patch change
auto_bpm: true            # Auto-detect BPM from microphone
brightness: 1.0           # Master brightness (0.0 – 1.0)
mic_sensitivity: 1.55     # Microphone gain multiplier
```

### WLED setup

On your WLED controller:

1. Set **Segment 0** to cover all your pixels (e.g. 0 – 479 for 480 LEDs)
2. Ensure the segment is **not frozen**
3. Under **Sync Interfaces → Realtime**:
   - Enable **Receive UDP realtime**
   - Set **type** to match your chosen protocol (e.g. "WARLS/Hyperion/DRGB")
   - For E1.31 / Art-Net: configure the matching universe range

---

## User Interface

The UI has four tabs along the bottom of the 800 × 480 touchscreen:

### EDIT tab

- **Pattern dropdown** — select from 43 patterns
- **Colormap dropdown** — choose a colour look-up table
- **Sprite dropdown** — overlay a PNG or animated GIF sprite
- **4 parameter sliders** — each pattern exposes up to 4 adjustable parameters
- **Modulation checkboxes** — route LFO1, LFO2, ENV_L, or ENV_H to any
  modulatable parameter
- **LFO panels** — waveform, depth, offset, beat-sync or free-run rate
- **Envelope panels** — threshold, gain, attack, release, mode
- **Live simulator preview** in the centre

### VIEW tab

- Full-screen simulator preview of the current pattern
- Rendering style controlled by the Display mode selector on the CONFIG tab
  (Fill / Grid / Point)

### PATCH tab

- **8 × 8 patch grid** with live thumbnails
- **Save / Delete** buttons for the selected slot
- **Tap-tempo** button with BPM display
- **RND** toggle for random patch cycling + **Global / Bank** scope selector
- **Bank navigation** (◀ Bank N ▶) across 8 banks
- Live preview thumbnail

### CONFIG tab

- **Beat count** buttons (1 / 2 / 4 / 8 / 16 / 32) — beats per random cycle
- **BPM Sync** toggle with live BPM readout
- **Brightness** slider (0 – 100%)
- **Mic Sensitivity** slider with live level meter
- **Matrix Width / Height** dropdowns (4 – 64)
- **Protocol** selector (DRGB, DRGBW, DNRGB, WARLS, E1.31, Art-Net, HTTP JSON)
- **Display** mode selector (Fill, Grid, Point)
- **Save** and **Quit** buttons

---

## Writing a Pattern

Drop a `.py` file into `patterns/` and it appears in the UI automatically.
Each pattern module must define:

```python
PARAMS = {
    "speed": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1,
        "modulatable": True,
    },
    "scale": {
        "default": 1.0, "min": 0.5, "max": 4.0, "step": 0.1,
    },
    # Up to 4 parameters
}

class Pattern:
    def __init__(self, width, height, params=None):
        self.width = width
        self.height = height
        self.params = params or {k: v["default"] for k, v in PARAMS.items()}
        self.param_meta = PARAMS

    def update_params(self, params):
        self.params = params

    def render(self, lfo_signals=None):
        """Return a list of (R, G, B, W) tuples, length = width * height."""
        frame = []
        # ... your rendering logic ...
        return frame
```

The `lfo_signals` dict contains `"lfo1"`, `"lfo2"`, `"envl"`, `"envh"` as
floats in the range [−1, 1].  Modulatable parameters are automatically
blended with these signals when routed via the modulation checkboxes on the
EDIT tab.

---

## Pixel Mapping

The LED matrix uses **column-major** wiring: the data line runs down column 0,
then column 1, etc.  `wall.py` automatically remaps the row-major frame buffer
to column-major order before transmission — no configuration needed.

---

## Protocols

| Protocol   | Port  | Notes |
|------------|-------|-------|
| DRGB       | 21324 | 3 bytes/pixel, single packet, max 489 pixels |
| DRGBW      | 21324 | 4 bytes/pixel for RGBW strips |
| DNRGB      | 21324 | Chunked with pixel offset, unlimited size |
| WARLS      | 21324 | Per-pixel index addressing |
| E1.31 sACN | 5568  | Multi-universe, 170 pixels/universe |
| Art-Net    | 6454  | Multi-universe, 170 pixels/universe |
| HTTP JSON  | 80    | WLED `/json/state` API (higher latency) |

---

## Boot Sequence

When deployed with `install.sh`, the boot sequence is:

1. **Plymouth splash** — dark screen with rainbow "DiscoLux" title, subtitle,
   and animated progress bar
2. **LightDM autologin** — logs in as the target user with labwc
3. **labwc autostart** — launches `start_discolux.sh` (waits for audio server,
   then runs `discolux.py`)
4. **DiscoLux fullscreen** — the app takes over the display, no desktop or
   taskbar visible

No Pi logo, no kernel text, no cursor — just splash → app.

---

## License

MIT
