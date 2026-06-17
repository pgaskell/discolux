"""
wall.py – Send LED frame data to a WLED controller over the network.

Supported protocols
───────────────────
  HTTP JSON   – WLED /json/state with row-segments (original, slowest)
  WARLS       – UDP :21324  per-pixel index+RGB (4 B/pixel)
  DRGB        – UDP :21324  flat RGB stream     (3 B/pixel)
  DRGBW       – UDP :21324  flat RGBW stream    (4 B/pixel)
  DNRGB       – UDP :21324  flat RGB with start-index, multi-packet safe
  E1.31       – UDP :5568   sACN / E1.31  (170 px / universe)
  Art-Net     – UDP :6454   Art-Net DMX   (170 px / universe)

All settings are read from ``config.py``.
"""

import json as _json
import socket
import struct
import threading
from urllib.request import Request, urlopen
from urllib.error import URLError

from config import (
    MATRIX_WIDTH, MATRIX_HEIGHT,
    WLED_HOST, WLED_TIMEOUT,
    LED_PROTOCOL,
)

# ── Protocol constants ──────────────────────────────────────────────────────
WLED_UDP_PORT = 21324
E131_PORT = 5568
ARTNET_PORT = 6454

# Max RGB pixels per sACN / Art-Net universe (512 channels / 3)
PIXELS_PER_UNIVERSE = 170

# WLED realtime UDP protocol bytes
_PROTO_WARLS = 1
_PROTO_DRGB = 2
_PROTO_DRGBW = 3
_PROTO_DNRGB = 4

# Valid protocol names exposed for the UI
PROTOCOL_CHOICES = [
    "DRGB",
    "DRGBW",
    "DNRGB",
    "WARLS",
    "E1.31",
    "Art-Net",
    "HTTP JSON",
]


class Wall:
    """Abstraction for pushing frames to a WLED controller."""

    def __init__(self, width: int = MATRIX_WIDTH, height: int = MATRIX_HEIGHT,
                 protocol: str = LED_PROTOCOL, host: str = WLED_HOST):
        self.width = width
        self.height = height
        self.num_pixels = width * height
        self.host = host
        self._protocol = protocol.upper().replace(" ", "")

        # Reusable UDP socket – set non-blocking so sendto() never stalls the
        # render loop when a device is temporarily unreachable / ARP-pending.
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)

        # HTTP endpoint (only for HTTP JSON mode)
        self._url = f"http://{self.host}/json/state" if self.host else None

        # E1.31 sequence counter (wraps 1-255)
        self._e131_seq = 0

        # Art-Net sequence counter (wraps 0-255)
        self._artnet_seq = 0

        # Initialise WLED (async – must not block render loop)
        self._init_wled_async()

    # ── public API ──────────────────────────────────────────────────────

    @property
    def protocol(self) -> str:
        return self._protocol

    @protocol.setter
    def protocol(self, value: str):
        """Change protocol at runtime (called from UI)."""
        new = value.upper().replace(" ", "")
        if new == self._protocol:
            return  # no-op: avoid unnecessary _init_wled HTTP call
        self._protocol = new
        self._init_wled_async()

    def show(self, frame: list[tuple]) -> None:
        """Send *frame* (flat list of (R,G,B[,W]) tuples, length W×H).

        Patterns generate frames in **row-major** order (row 0 left-to-right,
        then row 1, …).  The physical LED wiring is **column-major** (column 0
        top-to-bottom, then column 1, …).  We remap here so every protocol
        handler receives pixels in the order the strip expects.

        The HTTP JSON path does its own segment logic, so it receives the
        original row-major frame untouched.
        """
        if not self.host:
            return

        proto = self._protocol

        # HTTP JSON uses its own segment-based addressing — no remap needed
        if proto in ("HTTPJSON", "HTTP"):
            self._send_http_json(frame)
            return


        # Remap based on mode
        rm = getattr(self, 'remap_mode', 'COLUMN_MAJOR')
        if rm == 'PANEL_SERPENTINE':
            remapped = self._row_to_panel_serpentine(frame)
        elif rm == 'THREE_PANEL_COL_MAJOR':
            remapped = self._row_to_three_panel_col_major(frame)
        elif rm == 'COLUMN_SERPENTINE':
            remapped = self._row_to_col_serpentine(frame)
        else:
            remapped = self._row_to_col_major(frame)

        if proto == "DRGB":
            self._send_drgb(remapped)
        elif proto == "DRGBW":
            self._send_drgbw(remapped)
        elif proto == "DNRGB":
            self._send_dnrgb(remapped)
        elif proto == "WARLS":
            self._send_warls(remapped)
        elif proto == "E1.31":
            self._send_e131(remapped)
        elif proto in ("ARTNET", "ART-NET"):
            self._send_artnet(remapped)
        else:
            # Fallback to DRGB
            self._send_drgb(remapped)
    def set_remap_mode(self, mode: str):
        """Set remapping mode: 'COLUMN_MAJOR', 'PANEL_SERPENTINE', or 'THREE_PANEL_COL_MAJOR'"""
        self.remap_mode = mode.upper()

    def _row_to_three_panel_col_major(self, frame: list[tuple]) -> list[tuple]:
        """
        Remap for 3 independent column-serpentine panels side by side.

        Input:  row-major 48×32 frame (width=48, height=32)
        Output: three 16×32 sections concatenated, each remapped to
                column-serpentine order starting at the bottom-left:
                  • Even columns (0, 2, …): bottom → top  (row H-1 … row 0)
                  • Odd  columns (1, 3, …): top → bottom  (row 0 … row H-1)

        This matches Govee LED Wall wiring:
          • 3 data channels, one per 16×32 curtain
          • Strip enters at the bottom-left of each curtain and snakes up/down
            each column
        """
        w, h = self.width, self.height
        num_panels = 3
        panel_w = w // num_panels   # 16
        out = []
        for p in range(num_panels):
            x0 = p * panel_w
            for col in range(panel_w):
                # Physical column is h+2 (34) LEDs: dead at each end.
                # Serpentine: even cols bottom→top, odd cols top→bottom.
                out.append((0, 0, 0))  # dead pixel at physical start
                rows = range(h - 1, -1, -1) if col % 2 == 0 else range(h)
                for row in rows:
                    src = row * w + x0 + col
                    out.append(frame[src] if src < len(frame) else (0, 0, 0))
                out.append((0, 0, 0))  # dead pixel at physical end
        return out

    def _row_to_panel_serpentine(self, frame: list[tuple]) -> list[tuple]:
        """
        Remap for chained panels, each panel is row-major, each row within a
        panel is serpentine (reversed every other row), panels chained
        left-to-right.  num_panels is derived from the width so the strip
        does not need to be exactly 5 panels wide.
        """
        w, h = self.width, self.height
        # Derive num_panels: try common divisors in preference order
        for np in (5, 4, 3, 2, 1):
            if w % np == 0:
                num_panels = np
                break
        panel_w = w // num_panels
        panel_h = h
        # Pre-fill with black so any unaddressed pixel is safe
        out = [(0, 0, 0)] * (w * h)
        for p in range(num_panels):
            for y in range(panel_h):
                serp = (y % 2 == 1)
                for x in range(panel_w):
                    src_x = p * panel_w + (panel_w - 1 - x if serp else x)
                    src_y = y
                    src_idx = src_y * w + src_x
                    dst_idx = p * panel_w * panel_h + y * panel_w + x
                    if dst_idx < len(out):
                        out[dst_idx] = frame[src_idx] if src_idx < len(frame) else (0, 0, 0)
        return out

    def clear(self) -> None:
        """Send an all-black frame."""
        if not self.host:
            return
        black = [(0, 0, 0)] * self.num_pixels
        self.show(black)

    def set_dimensions(self, width: int, height: int) -> None:
        """Reconfigure for a new matrix size."""
        self.width = width
        self.height = height
        self.num_pixels = width * height
        self._init_wled_async()

    # ────────────────────────────────────────────────────────────────────
    #  Pixel reordering: row-major → column-major
    # ────────────────────────────────────────────────────────────────────
    def _row_to_col_major(self, frame: list[tuple]) -> list[tuple]:
        """Transpose a row-major frame to column-major order.

        Input order  (row-major):    row0_col0, row0_col1, …, row1_col0, …
        Output order (column-major): col0_row0, col0_row1, …, col1_row0, …

        This matches the physical wiring where the LED strip runs down
        each column before moving to the next column.
        """
        w, h = self.width, self.height
        out = [(0, 0, 0)] * (w * h)
        for row in range(h):
            for col in range(w):
                src = row * w + col       # row-major index
                dst = col * h + row       # column-major index
                out[dst] = frame[src] if src < len(frame) else (0, 0, 0)
        return out

    def _row_to_col_serpentine(self, frame: list[tuple]) -> list[tuple]:
        """Transpose row-major to column-major with serpentine (boustrophedon)
        column direction.

        Even columns (0, 2, …): top → bottom  (row 0 first)
        Odd  columns (1, 3, …): bottom → top  (row H-1 first)

        Use this when the LED strip zigzags between columns rather than
        resetting to the same end for every column.
        """
        w, h = self.width, self.height
        out = []
        for col in range(w):
            rows = range(h) if col % 2 == 0 else range(h - 1, -1, -1)
            for row in rows:
                src = row * w + col
                out.append(frame[src] if src < len(frame) else (0, 0, 0))
        return out

    # ────────────────────────────────────────────────────────────────────
    #  WARLS  –  protocol byte 1
    #  Packet: [1, timeout, index_hi, index_lo, R, G, B, …]
    #  5 bytes per pixel; chunked to stay under MTU
    # ────────────────────────────────────────────────────────────────────
    def _send_warls(self, frame: list[tuple]) -> None:
        timeout = 2  # seconds before WLED returns to normal mode
        max_px_per_pkt = 280  # (1400 - 2 header) / 5
        for chunk_start in range(0, len(frame), max_px_per_pkt):
            chunk = frame[chunk_start:chunk_start + max_px_per_pkt]
            buf = bytearray([_PROTO_WARLS, timeout])
            for i, px in enumerate(chunk):
                idx = chunk_start + i
                buf.append(idx >> 8)       # index high byte
                buf.append(idx & 0xFF)     # index low byte
                buf.append(px[0] & 0xFF)
                buf.append(px[1] & 0xFF)
                buf.append(px[2] & 0xFF)
            self._udp_send(buf, WLED_UDP_PORT)

    # ────────────────────────────────────────────────────────────────────
    #  DRGB  –  protocol byte 2
    #  Packet: [2, timeout, R, G, B, R, G, B, …]
    # ────────────────────────────────────────────────────────────────────
    def _send_drgb(self, frame: list[tuple]) -> None:
        timeout = 2
        buf = bytearray([_PROTO_DRGB, timeout])
        for px in frame:
            buf.append(px[0] & 0xFF)
            buf.append(px[1] & 0xFF)
            buf.append(px[2] & 0xFF)
        self._udp_send(buf, WLED_UDP_PORT)

    # ────────────────────────────────────────────────────────────────────
    #  DRGBW  –  protocol byte 3
    #  Packet: [3, timeout, R, G, B, W, R, G, B, W, …]
    # ────────────────────────────────────────────────────────────────────
    def _send_drgbw(self, frame: list[tuple]) -> None:
        timeout = 2
        buf = bytearray([_PROTO_DRGBW, timeout])
        for px in frame:
            buf.append(px[0] & 0xFF)
            buf.append(px[1] & 0xFF)
            buf.append(px[2] & 0xFF)
            w = px[3] if len(px) > 3 else 0
            buf.append(w & 0xFF)
        self._udp_send(buf, WLED_UDP_PORT)

    # ────────────────────────────────────────────────────────────────────
    #  DNRGB  –  protocol byte 4
    #  Packet: [4, timeout, startIdx_hi, startIdx_lo, R, G, B, …]
    #  Supports multi-packet for >490 pixels
    # ────────────────────────────────────────────────────────────────────
    def _send_dnrgb(self, frame: list[tuple]) -> None:
        timeout = 2
        max_px_per_pkt = 128
        total_px = len(frame)
        chunk_start = 0
        while chunk_start < total_px:
            chunk_end = min(chunk_start + max_px_per_pkt, total_px)
            chunk = frame[chunk_start:chunk_end]
            buf = bytearray([
                _PROTO_DNRGB,
                timeout,
                (chunk_start >> 8) & 0xFF,
                chunk_start & 0xFF,
            ])
            for px in chunk:
                buf.append(px[0] & 0xFF)
                buf.append(px[1] & 0xFF)
                buf.append(px[2] & 0xFF)
            self._udp_send(buf, WLED_UDP_PORT)
            chunk_start += len(chunk)

    # ────────────────────────────────────────────────────────────────────
    #  E1.31 (sACN)  –  UDP port 5568
    #  170 RGB pixels per universe, multi-universe
    # ────────────────────────────────────────────────────────────────────
    def _send_e131(self, frame: list[tuple]) -> None:
        # Always send RGB (3 channels/pixel); W channel is dropped.
        # DiscoLux frames are always 4-tuples with W=0, so we must not use
        # len(frame[0]) to decide — that would always pick RGBW and cause
        # WLED (in RGB mode) to misinterpret every W=0 byte as a colour channel.
        flat = []
        for px in frame:
            flat.extend([px[0] & 0xFF, px[1] & 0xFF, px[2] & 0xFF])

        # IMPORTANT: advance by 510 bytes (170 pixels × 3) per universe — the
        # true DMX universe capacity for RGB.  Using 512 causes a 512 mod 3 = 2
        # byte drift per universe, which shifts R/G/B channels and produces the
        # wrong colour on every subsequent universe.
        CHANNELS_PER_UNIVERSE = 510  # 170 pixels × 3 channels
        total_channels = len(flat)
        universe = 1
        offset = 0
        while offset < total_channels:
            chunk = flat[offset:offset + CHANNELS_PER_UNIVERSE]
            if not chunk:
                break

            self._e131_seq = (self._e131_seq % 255) + 1
            pkt = self._build_e131_packet(universe, chunk, self._e131_seq)
            self._udp_send(pkt, E131_PORT)

            universe += 1
            offset += CHANNELS_PER_UNIVERSE

    def _build_e131_packet(self, universe: int, channel_data: list[int],
                           sequence: int) -> bytes:
        """Build a minimal E1.31 (sACN) data packet."""
        n_channels = len(channel_data)
        # Lengths for the nested layers
        dmp_len = n_channels + 11        # DMP layer
        frame_len = dmp_len + 77         # Framing layer (fixed fields)
        root_len = frame_len + 22        # Root layer

        pkt = bytearray()

        # ── Root Layer ──────────────────────────────────────────────────
        # Preamble size (16-bit BE)
        pkt.extend(struct.pack("!H", 0x0010))
        # Post-amble size
        pkt.extend(struct.pack("!H", 0x0000))
        # ACN Packet Identifier (12 bytes)
        pkt.extend(b"ASC-E1.17\x00\x00\x00")
        # Flags + Length (high 4 bits = 0x7)
        pkt.extend(struct.pack("!H", 0x7000 | (root_len & 0x0FFF)))
        # Vector – VECTOR_ROOT_E131_DATA = 0x00000004
        pkt.extend(struct.pack("!I", 0x00000004))
        # CID – 16 bytes (arbitrary unique sender id)
        pkt.extend(b"DiscoLux0000\x00\x00\x00\x00")

        # ── Framing Layer ───────────────────────────────────────────────
        # Flags + Length
        pkt.extend(struct.pack("!H", 0x7000 | (frame_len & 0x0FFF)))
        # Vector – VECTOR_E131_DATA_PACKET = 0x00000002
        pkt.extend(struct.pack("!I", 0x00000002))
        # Source Name – 64 bytes, null-padded
        src_name = b"DiscoLux"
        pkt.extend(src_name + b"\x00" * (64 - len(src_name)))
        # Priority (uint8)
        pkt.append(100)
        # Synchronization Address (uint16)
        pkt.extend(struct.pack("!H", 0))
        # Sequence Number (uint8)
        pkt.append(sequence & 0xFF)
        # Options Flags (uint8)
        pkt.append(0)
        # Universe (uint16)
        pkt.extend(struct.pack("!H", universe))

        # ── DMP Layer ───────────────────────────────────────────────────
        # Flags + Length
        pkt.extend(struct.pack("!H", 0x7000 | (dmp_len & 0x0FFF)))
        # Vector – VECTOR_DMP_SET_PROPERTY = 0x02
        pkt.append(0x02)
        # Address Type & Data Type – 0xA1
        pkt.append(0xA1)
        # First Property Address (uint16)
        pkt.extend(struct.pack("!H", 0))
        # Address Increment (uint16)
        pkt.extend(struct.pack("!H", 1))
        # Property Value Count (uint16) – includes DMX start code
        pkt.extend(struct.pack("!H", n_channels + 1))
        # DMX start code
        pkt.append(0x00)
        # Channel data
        pkt.extend(channel_data)

        return bytes(pkt)

    # ────────────────────────────────────────────────────────────────────
    #  Art-Net  –  UDP port 6454
    #  170 RGB pixels per universe, multi-universe
    # ────────────────────────────────────────────────────────────────────
    def _send_artnet(self, frame: list[tuple]) -> None:
        flat = []
        for px in frame:
            flat.extend([px[0] & 0xFF, px[1] & 0xFF, px[2] & 0xFF])

        total_channels = len(flat)
        universe = 0
        offset = 0
        while offset < total_channels:
            chunk = flat[offset:offset + 512]
            channels_in_pkt = len(chunk)
            if channels_in_pkt == 0:
                break
            # Art-Net requires even-length data
            if channels_in_pkt % 2:
                chunk.append(0)
                channels_in_pkt += 1

            pkt = self._build_artnet_packet(universe, chunk, self._artnet_seq)
            self._udp_send(pkt, ARTNET_PORT)

            self._artnet_seq = (self._artnet_seq + 1) & 0xFF
            universe += 1
            offset += 512

    def _build_artnet_packet(self, universe: int, channel_data: list[int],
                             sequence: int) -> bytes:
        """Build an Art-Net ArtDmx packet (OpCode 0x5000)."""
        n_channels = len(channel_data)
        pkt = bytearray()

        # Art-Net header: "Art-Net\0"
        pkt.extend(b"Art-Net\x00")
        # OpCode – ArtDmx 0x5000 (little-endian)
        pkt.extend(struct.pack("<H", 0x5000))
        # Protocol version (14) – big-endian
        pkt.extend(struct.pack("!H", 14))
        # Sequence
        pkt.append(sequence & 0xFF)
        # Physical port
        pkt.append(0)
        # Universe (little-endian 16-bit: Sub-Uni | Net)
        pkt.extend(struct.pack("<H", universe & 0x7FFF))
        # Length (big-endian 16-bit)
        pkt.extend(struct.pack("!H", n_channels))
        # DMX data
        pkt.extend(channel_data)

        return bytes(pkt)

    # ────────────────────────────────────────────────────────────────────
    #  HTTP JSON  –  WLED /json/state  (original row-segment approach)
    # ────────────────────────────────────────────────────────────────────
    def _send_http_json(self, frame: list[tuple]) -> None:
        if self._url is None:
            return
        # Skip if a previous HTTP request is still in flight so we never
        # queue up blocking calls and stall the render loop.
        if getattr(self, '_http_in_flight', False):
            return

        w, h = self.width, self.height
        segs = []
        for row in range(h):
            start = row * w
            row_pixels = frame[start:start + w]
            if not row_pixels:
                segs.append({"id": row, "col": [[0, 0, 0]]})
                continue

            n = len(row_pixels)
            r = sum(p[0] for p in row_pixels) // n
            g = sum(p[1] for p in row_pixels) // n
            b = sum(p[2] for p in row_pixels) // n
            segs.append({"id": row, "col": [[r, g, b]]})

        payload = {"seg": segs}
        self._http_in_flight = True
        def _send():
            try:
                self._post_json(payload)
            finally:
                self._http_in_flight = False
        threading.Thread(target=_send, daemon=True).start()

    # ── helpers ─────────────────────────────────────────────────────────

    def _udp_send(self, data: bytes | bytearray, port: int) -> None:
        """Fire-and-forget UDP send to the WLED host."""
        try:
            self._sock.sendto(data, (self.host, port))
        except OSError:
            pass  # network hiccup – drop silently

    def _post_json(self, data: dict) -> None:
        """Send a JSON POST to the WLED ``/json/state`` endpoint."""
        payload = _json.dumps(data, separators=(",", ":")).encode()
        req = Request(self._url, data=payload,
                      headers={"Content-Type": "application/json"})
        try:
            urlopen(req, timeout=WLED_TIMEOUT)
        except (URLError, OSError):
            pass

    def _init_wled_async(self) -> None:
        """Kick off _init_wled in a daemon thread so it never blocks the caller."""
        threading.Thread(target=self._init_wled, daemon=True).start()

    def _init_wled(self) -> None:
        """Initialise the WLED controller.

        For HTTP JSON mode this creates row-segments.
        For UDP realtime modes we just send a quick "turn on" via HTTP
        (best-effort) and rely on realtime packets taking over.
        """
        if not self.host:
            return

        proto = self._protocol

        if proto in ("HTTPJSON", "HTTP"):
            # Create one segment per matrix row
            segs = []
            for row in range(self.height):
                segs.append({
                    "id": row,
                    "start": row * self.width,
                    "stop": (row + 1) * self.width,
                    "col": [[0, 0, 0]],
                    "fx": 0,
                    "frz": False,
                })
            payload = {"on": True, "bri": 255, "seg": segs}
        else:
            # For UDP modes just turn on and set full brightness
            payload = {"on": True, "bri": 255}

        try:
            self._url = f"http://{self.host}/json/state"
            self._post_json(payload)
            print(f"[wall] WLED initialised – protocol={proto} "
                  f"pixels={self.num_pixels} host={self.host}")
        except Exception as e:
            print(f"[wall] Warning: could not initialise WLED: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# MultiWall – send frames to multiple WLED controllers
# ═══════════════════════════════════════════════════════════════════════════

MULTI_MODE_CHOICES = ["single", "mirror", "extend"]
EXTEND_DIR_CHOICES = ["right", "left", "below", "above"]  # kept for compat


class MultiWall:
    """Manages one or more WLED controllers in single, mirror, or extend mode.

    single  – only the first active device receives frames.
    mirror  – identical frame sent to all active devices.
    extend  – each active device renders its own (x, y) sub-region of the
              canvas.  Canvas = bounding box of all active device origins+sizes.
    """

    def __init__(self, devices: list, mode: str = "single",
                 extend_direction: str = "right"):
        self._device_info: list[dict] = []
        for d in devices:
            w = Wall(
                width=d.get("width", MATRIX_WIDTH),
                height=d.get("height", MATRIX_HEIGHT),
                protocol=d.get("protocol", LED_PROTOCOL),
                host=d.get("host", WLED_HOST),
            )
            w.set_remap_mode(d.get("wiring_mode", "COLUMN_MAJOR"))
            self._device_info.append({
                "wall":   w,
                "x":      int(d.get("x", 0)),
                "y":      int(d.get("y", 0)),
                "active": bool(d.get("active", True)),
            })
        self._mode = mode.lower()
        self._update_canvas_size()

    # ── helpers ──────────────────────────────────────────────────────────

    def _active_devices(self) -> list:
        return [d for d in self._device_info if d["active"]]

    def _update_canvas_size(self) -> None:
        active = self._active_devices()
        if not active:
            d0 = self._device_info[0] if self._device_info else None
            self._width  = d0["wall"].width  if d0 else 24
            self._height = d0["wall"].height if d0 else 24
            return
        if self._mode == "extend":
            self._width  = max(d["x"] + d["wall"].width  for d in active)
            self._height = max(d["y"] + d["wall"].height for d in active)
        else:
            d0 = active[0]
            self._width  = d0["wall"].width
            self._height = d0["wall"].height

    # ── canvas dimensions ─────────────────────────────────────────────────

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def num_pixels(self) -> int:
        return self._width * self._height

    @property
    def host(self) -> str:
        return self._device_info[0]["wall"].host if self._device_info else ""

    # ── protocol / remap pass-throughs ────────────────────────────────────

    @property
    def protocol(self) -> str:
        return self._device_info[0]["wall"].protocol if self._device_info else ""

    @protocol.setter
    def protocol(self, value: str) -> None:
        for d in self._device_info:
            d["wall"].protocol = value

    def set_remap_mode(self, mode: str, device_idx: int = 0) -> None:
        if 0 <= device_idx < len(self._device_info):
            self._device_info[device_idx]["wall"].set_remap_mode(mode)

    # ── runtime config ────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        self._mode = mode.lower()
        self._update_canvas_size()

    def set_extend_direction(self, direction: str) -> None:
        pass  # no-op – direction is now encoded per-device via x/y origin

    def update_device(self, idx: int, host: str = None, width: int = None,
                      height: int = None, protocol: str = None,
                      wiring_mode: str = None, x: int = None,
                      y: int = None, active: bool = None) -> None:
        """Update a device's settings at runtime; appends if idx is new."""
        if idx >= len(self._device_info):
            if host:
                nw = Wall(
                    width=width or MATRIX_WIDTH,
                    height=height or MATRIX_HEIGHT,
                    protocol=protocol or LED_PROTOCOL,
                    host=host,
                )
                if wiring_mode:
                    nw.set_remap_mode(wiring_mode)
                self._device_info.append({
                    "wall": nw, "x": x or 0, "y": y or 0, "active": True,
                })
        else:
            d = self._device_info[idx]
            w = d["wall"]
            if host is not None and host != w.host:
                w.host = host
                w._url = f"http://{host}/json/state"
            new_w = width  if width  is not None else w.width
            new_h = height if height is not None else w.height
            if new_w != w.width or new_h != w.height:
                w.set_dimensions(new_w, new_h)
            if protocol    is not None: w.protocol = protocol
            if wiring_mode is not None: w.set_remap_mode(wiring_mode)
            if x      is not None: d["x"]      = x
            if y      is not None: d["y"]      = y
            if active is not None: d["active"] = active
        self._update_canvas_size()

    # ── frame output ──────────────────────────────────────────────────────

    def show(self, frame: list) -> None:
        active = self._active_devices()
        if not active:
            return
        if self._mode == "mirror":
            for d in active:
                d["wall"].show(frame)
        elif self._mode == "extend":
            self._show_extend(frame, active)
        else:
            active[0]["wall"].show(frame)

    def _show_extend(self, frame: list, active_devices: list) -> None:
        BLACK = (0, 0, 0, 0)
        tw = self._width
        for d in active_devices:
            w = d["wall"]
            ox, oy = d["x"], d["y"]
            dw, dh = w.width, w.height
            dev_frame = []
            for row in range(dh):
                for col in range(dw):
                    src = (oy + row) * tw + (ox + col)
                    dev_frame.append(frame[src] if 0 <= src < len(frame) else BLACK)
            w.show(dev_frame)

    def clear(self) -> None:
        for d in self._device_info:
            d["wall"].clear()

