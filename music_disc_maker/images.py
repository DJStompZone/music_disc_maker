from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def get_nearest_resample() -> Any:
    """Return Pillow's nearest-neighbor resample constant across supported versions."""
    resampling_cls = getattr(Image, "Resampling", None)

    if resampling_cls is not None:
        return getattr(resampling_cls, "NEAREST")

    return getattr(Image, "NEAREST")


def process_icon(template_path: Path, output_path: Path) -> Image.Image:
    """Create a hue-shifted disc icon from a template, or create a simple fallback icon."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if template_path.exists():
        img = Image.open(template_path).convert("RGBA")
    else:
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255), 255)
        draw.ellipse([2, 2, 14, 14], fill=color)

    hsv_img = img.convert("HSV")
    h, s, v = hsv_img.split()
    hue_offset = random.randint(0, 255)
    table = [(i + hue_offset) % 256 for i in range(256)]
    shifted_h = h.point(table)
    final_img = Image.merge("HSV", (shifted_h, s, v)).convert("RGBA")

    if template_path.exists():
        final_img.putalpha(img.getchannel("A"))

    final_img.save(output_path)
    return final_img


def write_pack_icon(icon: Image.Image, pack_path: Path, size: int) -> None:
    """Write a root pack_icon.png using a generated disc icon."""
    pack_path.mkdir(parents=True, exist_ok=True)
    pack_icon = icon.resize((size, size), get_nearest_resample())
    pack_icon.save(pack_path / "pack_icon.png")
