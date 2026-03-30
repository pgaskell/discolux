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

        # Reusable UDP socket (non-blocking sends)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # HTTP endpoint (only for HTTP JSON mode)
        self._url = f"http://{self.host}/json/state" if self.host else None

        # E1.31 sequence counter (wraps 1-255)
        self._e131_seq = 0

        # Art-Net sequence counter (wraps 0-255)
        self._artnet_seq = 0

        # Initialise WLED
        self._init_wled()

    # ── public API ──────────────────────────────────────────────────────

    @property
    def protocol(self) -> str:
        return self._protocol

    @protocol.setter
    def protocol(self, value: str):
        """Change protocol at runtime (called from UI)."""
        self._protocol = value.upper().replace(" ", "")
        self._init_wled()

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
        if hasattr(self, 'remap_mode') and self.remap_mode == 'PANEL_SERPENTINE':
            remapped = self._row_to_panel_serpentine(frame)
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
        """Set remapping mode: 'COLUMN_MAJOR' (default) or 'PANEL_SERPENTINE'"""
        self.remap_mode = mode.upper()

    def _row_to_panel_serpentine(self, frame: list[tuple]) -> list[tuple]:
        """
        Remap for 5 chained panels, each panel is row-major, each row within a panel is serpentine (reversed every other row), panels chained left-to-right.
        Assumes width and height are divisible by 5.
        """
        w, h = self.width, self.height
        num_panels = 5
        panel_w = w // num_panels
        panel_h = h
        out = [None] * (w * h)
        for p in range(num_panels):
            for y in range(panel_h):
                serp = (y % 2 == 1)
                for x in range(panel_w):
                    src_x = p * panel_w + (panel_w - 1 - x if serp else x)
                    src_y = y
                    src_idx = src_y * w + src_x
                    dst_idx = p * panel_w * panel_h + y * panel_w + x
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
        self._init_wled()

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
        out = [None] * (w * h)
        for row in range(h):
            for col in range(w):
                src = row * w + col       # row-major index
                dst = col * h + row       # column-major index
                out[dst] = frame[src] if src < len(frame) else (0, 0, 0)
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
        # Determine if frame is RGB or RGBW
        if frame and len(frame[0]) == 4:
            channels_per_pixel = 4
        else:
            channels_per_pixel = 3
        flat = []
        for px in frame:
            flat.extend([px[0] & 0xFF, px[1] & 0xFF, px[2] & 0xFF])
            if channels_per_pixel == 4:
                flat.append(px[3] & 0xFF)

        total_channels = len(flat)
        universe = 1
        offset = 0
        while offset < total_channels:
            chunk = flat[offset:offset + 512]
            channels_in_pkt = len(chunk)
            if channels_in_pkt == 0:
                break

            self._e131_seq = (self._e131_seq % 255) + 1
            pkt = self._build_e131_packet(universe, chunk, self._e131_seq)
            self._udp_send(pkt, E131_PORT)

            universe += 1
            offset += 512

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

        self._post_json({"seg": segs})

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
