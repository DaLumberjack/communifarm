"""Raster copy of the operator schematic.

Picture-elements loads the background with an image tag. An SVG from
``/local/`` is often served as text, and the card then shows a broken image
even when the file itself opens fine. The PNG is the same drawing.
"""

from __future__ import annotations

import struct
import zlib

from ..domain.climate import (
    KIND_GENERAL_ROOM,
    KIND_OUTDOOR,
    ROLE_AC,
    ROLE_CONDENSATE_PUMP,
    ROLE_FLOAT,
    ROLE_FRESH_AIR_INTAKE,
    ROLE_HEATER,
    ROLE_HUMIDITY,
    ROLE_PRESSURE,
    ROLE_TEMPERATURE,
)
from ..domain.climate_layout import (
    ROLE_LABEL,
    VIEW_H,
    VIEW_W,
    room_frames,
    sensor_xy,
)

SCALE = 10
WIDTH = int(VIEW_W * SCALE)
HEIGHT = int(VIEW_H * SCALE)

# 5x7 glyphs, top row first, bit 4 is the left pixel.
_FONT: dict[str, tuple[int, ...]] = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0b00100, 0b00100),
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
}

_PNG_CACHE: bytes | None = None


def render_operator_layout_png() -> bytes:
    """1200x780 PNG of the preset schematic. Cached; the drawing does not change."""
    global _PNG_CACHE
    if _PNG_CACHE is None:
        _PNG_CACHE = _encode(_paint())
    return _PNG_CACHE


def png_rgb(data: bytes, x: int, y: int) -> tuple[int, int, int]:
    """Read one pixel from a PNG this module wrote (filter None, RGB)."""
    if data[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError("pixel outside the image")
    payload = _idat(data)
    stride = width * 3 + 1
    row = payload[y * stride : (y + 1) * stride]
    start = 1 + x * 3
    return row[start], row[start + 1], row[start + 2]


def _paint() -> bytearray:
    buf = bytearray(WIDTH * HEIGHT * 3)
    _fill(buf, 0, 0, WIDTH, HEIGHT, (0x3A, 0x3F, 0x44))
    _line(buf, 8, 34, 116, 34, (0xE2, 0xC0, 0x44), 4)
    _line(buf, 8, 50, 16, 50, (0x4A, 0xA3, 0xD8), 5)
    for room in room_frames():
        if room.kind == KIND_OUTDOOR:
            continue
        _rect(buf, room.x, room.y, room.w, room.h, _hex(room.fill))
        _text(buf, room.x + 1.2, room.y + 3.2, room.title, 2.0, (0xF4, 0xF7, 0xF5), room.w - 2)
        if room.kind != KIND_GENERAL_ROOM and room.h >= 20:
            for slot in range(5):
                xy = sensor_xy(room.kind, slot)
                if xy is None:
                    continue
                _ring(buf, xy[0], xy[1], 0.7, (0xD7, 0xDD, 0xE2))
    outdoor = next(room for room in room_frames() if room.kind == KIND_OUTDOOR)
    _rect(buf, outdoor.x, outdoor.y, outdoor.w, outdoor.h, _hex(outdoor.fill))
    _text(buf, outdoor.x + 1.2, outdoor.y + 3.2, "Outdoors", 2.0, (0xF4, 0xF7, 0xF5), 16)
    _text(buf, 78, 5.6, "Communifarm CEA", 2.2, (0xE7, 0xF2, 0xF8), 38)
    for role, x in (
        (ROLE_TEMPERATURE, 18.0),
        (ROLE_HUMIDITY, 36.0),
        (ROLE_PRESSURE, 54.0),
    ):
        _text(buf, x, 6.2, ROLE_LABEL[role], 1.8, (0xE7, 0xF2, 0xF8), 8)
    for role, y in (
        (ROLE_AC, 18.0),
        (ROLE_HEATER, 26.0),
        (ROLE_FRESH_AIR_INTAKE, 34.0),
        (ROLE_FLOAT, 42.0),
        (ROLE_CONDENSATE_PUMP, 50.0),
    ):
        _rect(buf, 4.2, y - 1.6, 7.2, 3.2, (0x2C, 0x33, 0x38))
        _text(buf, 4.6, y + 0.7, ROLE_LABEL[role], 1.5, (0xF4, 0xE7, 0xB0), 6.4)
    _text(
        buf,
        4,
        76.5,
        "Preset schematic. Live sensors sit on the dots. Not a scale drawing.",
        1.6,
        (0xB7, 0xC0, 0xC6),
        112,
    )
    return buf


def _hex(value: str) -> tuple[int, int, int]:
    raw = value.removeprefix("#")
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def _px(units: float) -> int:
    return int(round(units * SCALE))


def _fill(
    buf: bytearray, x: int, y: int, w: int, h: int, color: tuple[int, int, int]
) -> None:
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(WIDTH, x + w)
    y1 = min(HEIGHT, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    pixel = bytes(color)
    span = pixel * (x1 - x0)
    for yy in range(y0, y1):
        start = (yy * WIDTH + x0) * 3
        buf[start : start + len(span)] = span


def _rect(
    buf: bytearray,
    x: float,
    y: float,
    w: float,
    h: float,
    color: tuple[int, int, int],
) -> None:
    _fill(buf, _px(x), _px(y), max(1, _px(w)), max(1, _px(h)), color)


def _line(
    buf: bytearray,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    ax, ay, bx, by = _px(x1), _px(y1), _px(x2), _px(y2)
    steps = max(abs(bx - ax), abs(by - ay), 1)
    half = max(0, thickness // 2)
    for step in range(steps + 1):
        x = ax + (bx - ax) * step // steps
        y = ay + (by - ay) * step // steps
        _fill(buf, x - half, y - half, thickness, thickness, color)


def _ring(buf: bytearray, cx: float, cy: float, radius: float, color: tuple[int, int, int]) -> None:
    center_x, center_y, rad = _px(cx), _px(cy), max(2, _px(radius))
    rad2 = rad * rad
    inner = (rad - 2) * (rad - 2)
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            dist = dx * dx + dy * dy
            if inner <= dist <= rad2:
                _fill(buf, center_x + dx, center_y + dy, 1, 1, color)


def _text(
    buf: bytearray,
    x: float,
    baseline: float,
    text: str,
    size: float,
    color: tuple[int, int, int],
    max_units: float,
) -> None:
    scale = max(1, round(size * SCALE / 7))
    rendered = text.upper()
    while scale > 1 and len(rendered) * 6 * scale > _px(max_units):
        scale -= 1
    cursor = _px(x)
    top = _px(baseline) - 7 * scale
    for char in rendered:
        glyph = _FONT.get(char)
        if glyph is None:
            cursor += 6 * scale
            continue
        for row, bits in enumerate(glyph):
            for col in range(5):
                if bits & (1 << (4 - col)):
                    _fill(
                        buf,
                        cursor + col * scale,
                        top + row * scale,
                        scale,
                        scale,
                        color,
                    )
        cursor += 6 * scale


def _encode(buf: bytearray) -> bytes:
    raw = bytearray()
    stride = WIDTH * 3
    for y in range(HEIGHT):
        raw.append(0)
        start = y * stride
        raw.extend(buf[start : start + stride])
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def _chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _idat(data: bytes) -> bytes:
    offset = 8
    parts: list[bytes] = []
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        tag = data[offset + 4 : offset + 8]
        chunk = data[offset + 8 : offset + 8 + length]
        if tag == b"IDAT":
            parts.append(chunk)
        if tag == b"IEND":
            break
        offset += 12 + length
    return zlib.decompress(b"".join(parts))
