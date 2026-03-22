from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON_PATH = ROOT / "ibkr-shell.ico"


def _pixel_rgba(x: int, y: int) -> tuple[int, int, int, int]:
    red, green, blue = 23, 162, 184
    if 2 <= x <= 13 and 2 <= y <= 13:
        red, green, blue = 18, 52, 86
    if x in {4, 8, 12} and 4 <= y <= 11:
        red, green, blue = 255, 255, 255
    if y in {11, 12} and 4 <= x <= 12:
        red, green, blue = 255, 255, 255
    return red, green, blue, 255


def _png_bytes(width: int = 16, height: int = 16) -> bytes:
    pixels = bytearray()
    for y in range(height):
        pixels.append(0)
        for x in range(width):
            pixels.extend(_pixel_rgba(x, y))
    compressed = zlib.compress(bytes(pixels))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    return png


def write_icon(path: Path = ICON_PATH) -> Path:
    png = _png_bytes()
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 16, 16, 0, 0, 1, 32, len(png), 22)
    path.write_bytes(header + entry + png)
    return path


def main() -> int:
    path = write_icon()
    print(f"Generated Windows icon: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
