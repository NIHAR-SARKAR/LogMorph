"""Generate placeholder Tauri icon files using only the Python standard library.

Run from the repo root:
    cd tauri && python generate-icons.py
"""
import struct
import zlib
import os


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    chunk = chunk_type + data
    crc = zlib.crc32(chunk) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)


def make_png(width: int, height: int, rgba: tuple) -> bytes:
    """Create a minimal valid PNG for a solid-color square."""
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = png_chunk(b"IHDR", ihdr_data)

    # IDAT: raw image data with filter byte 0 per scanline
    raw = b""
    row = bytes(rgba) * width
    for _ in range(height):
        raw += b"\x00" + row
    compressed = zlib.compress(raw)
    idat = png_chunk(b"IDAT", compressed)

    # IEND
    iend = png_chunk(b"IEND", b"")

    return signature + ihdr + idat + iend


def make_ico(pngs: dict) -> bytes:
    """Create a minimal ICO file from PNG-encoded images of various sizes.

    pngs: dict mapping size -> png bytes
    """
    num_images = len(pngs)
    icon_dir = struct.pack("<HHH", 0, 1, num_images)

    entries = b""
    image_data = b""
    offset = 6 + 16 * num_images

    for size in sorted(pngs.keys()):
        png = pngs[size]
        # Width/Height stored as 8-bit when <= 255; for 256 we store 0
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), offset)
        image_data += png
        offset += len(png)

    return icon_dir + entries + image_data


def make_icns(pngs: dict) -> bytes:
    """Create a minimal ICNS file from PNG-encoded images.

    Uses standard macOS icon type codes for square sizes.
    """
    type_codes = {
        16: b"icp4",
        32: b"icp5",
        64: b"icp6",
        128: b"ic07",
        256: b"ic08",
        512: b"ic09",
    }

    image_data = b""
    for size in sorted(pngs.keys()):
        t = type_codes.get(size, b"ic07")
        png = pngs[size]
        image_data += t + struct.pack(">I", 8 + len(png)) + png

    file_length = 4 + 4 + len(image_data)
    return b"icns" + struct.pack(">I", file_length) + image_data


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(base_dir, "icons")
    os.makedirs(icons_dir, exist_ok=True)

    # Brand-ish blue color (#3b82f6)
    color = (59, 130, 246, 255)

    sizes = [16, 32, 64, 128, 256, 512]
    pngs = {size: make_png(size, size, color) for size in sizes}

    # Write individual PNGs
    with open(os.path.join(icons_dir, "32x32.png"), "wb") as f:
        f.write(pngs[32])
    with open(os.path.join(icons_dir, "128x128.png"), "wb") as f:
        f.write(pngs[128])
    with open(os.path.join(icons_dir, "128x128@2x.png"), "wb") as f:
        f.write(pngs[256])

    # ICO with common Windows sizes
    ico_data = make_ico({16: pngs[16], 32: pngs[32], 48: pngs[64], 256: pngs[256]})
    with open(os.path.join(icons_dir, "icon.ico"), "wb") as f:
        f.write(ico_data)

    # ICNS with common macOS sizes
    icns_data = make_icns({16: pngs[16], 32: pngs[32], 128: pngs[128], 256: pngs[256], 512: pngs[512]})
    with open(os.path.join(icons_dir, "icon.icns"), "wb") as f:
        f.write(icns_data)

    print(f"Placeholder icons generated in {icons_dir}")


if __name__ == "__main__":
    main()
