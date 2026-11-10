"""Generate the original BackupLens icon assets (PNG/ICO/ICNS) from icon.svg.

Run: python scripts/generate_icons.py
Requires Pillow (already a runtime dependency). The artwork is original: a rounded blue tile
with a white lens, not Apple or any competitor artwork.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packaging" / "icon"


def draw_icon(size: int) -> Image.Image:
    scale = size / 512
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (16 * scale, 16 * scale, 496 * scale, 496 * scale),
        radius=112 * scale,
        fill=(31, 115, 183, 255),
    )
    draw.rounded_rectangle(
        (108 * scale, 146 * scale, 404 * scale, 366 * scale),
        radius=44 * scale,
        outline=(255, 255, 255, 255),
        width=max(2, int(26 * scale)),
    )
    draw.ellipse(
        (186 * scale, 186 * scale, 326 * scale, 326 * scale),
        outline=(255, 255, 255, 255),
        width=max(2, int(26 * scale)),
    )
    draw.ellipse(
        (234 * scale, 234 * scale, 278 * scale, 278 * scale),
        fill=(255, 255, 255, 255),
    )
    draw.ellipse(
        (322 * scale, 176 * scale, 350 * scale, 204 * scale),
        fill=(159, 211, 255, 255),
    )
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    images = {size: draw_icon(size) for size in sizes}
    for size, image in images.items():
        image.save(OUT / f"icon-{size}.png", "PNG")
    images[256].save(OUT / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    try:
        images[512].save(OUT / "icon.icns", format="ICNS")
    except (OSError, ValueError):
        # macOS CI can create the ICNS with iconutil; the PNG set is enough for Linux.
        print("ICNS writer unavailable; macOS CI will use iconutil from icon-1024.png")
    print(f"Icon assets written to {OUT}")


if __name__ == "__main__":
    main()
