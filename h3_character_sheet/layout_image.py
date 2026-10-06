"""Render the Designer's existing mannequin atlas using the shared geometry."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ATLAS_PATH = Path(__file__).resolve().parents[1] / "web/assets/mannequin-atlas.png"
ATLAS_CROPS = {
    "face_front": (0, 75, 470, 560),
    "face_left": (1010, 35, 140, 205),
    "body_front": (495, 20, 350, 625),
    "body_left": (904, 20, 350, 625),
    "body_back": (55, 625, 350, 625),
    "hands": (415, 755, 445, 400),
    "feet": (860, 820, 380, 340),
}


def render_layout_image(layout: dict) -> Image.Image:
    width, height = layout["canvas"]
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    frame_width = max(1, (min(width, height) + 128) // 256)
    with Image.open(ATLAS_PATH) as source:
        atlas = source.convert("RGBA")
    for panel in layout["panels"]:
        x, y, w, h = panel["rect"]
        left, top = round(x * width), round(y * height)
        right, bottom = round((x + w) * width), round((y + h) * height)
        crop_x, crop_y, crop_w, crop_h = ATLAS_CROPS[panel["id"]]
        artwork = atlas.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
        artwork = ImageOps.contain(artwork, (max(1, right - left), max(1, bottom - top)), Image.Resampling.LANCZOS)
        position = (left + (right - left - artwork.width) // 2, top + (bottom - top - artwork.height) // 2)
        canvas.paste(artwork, position, artwork)
        draw.rectangle((left, top, right - 1, bottom - 1), outline="black", width=frame_width)
    return canvas
