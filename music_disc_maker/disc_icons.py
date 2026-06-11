from __future__ import annotations

import colorsys
import hashlib
import random
import re
import zipfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable

from PIL import Image

DISC_SIZE = 16
LAYER_ORDER = (
    "layer1_outer",
    "layer2_surface",
    "layer3_accent",
    "layer4_edge",
    "layer5_inner_a",
    "layer6_inner_b",
    "layer7_center",
)
GROUPED_COLOR_LAYERS = frozenset({"layer2_surface", "layer3_accent", "layer4_edge"})
INDEPENDENT_COLOR_LAYERS = frozenset({"layer5_inner_a", "layer6_inner_b"})
INVARIANT_LAYERS = frozenset({"layer1_outer", "layer7_center"})
LAYER_FILE_PATTERN = re.compile(r"^(layer\d+_[a-z0-9_]+?)(?:_alt\d*|_alt)?\.png$", re.IGNORECASE)


@dataclass(frozen=True)
class ColorTransform:
    """Color transform applied to visible layer pixels."""

    hue_degrees: float = 0.0
    invert: bool = False
    brightness: float = 1.0


@dataclass(frozen=True)
class DiscPlan:
    """Deterministic render choices for one generated disc."""

    seed: int
    variants: dict[str, str]
    grouped_transform: ColorTransform
    independent_transforms: dict[str, ColorTransform]
    invariant_transforms: dict[str, ColorTransform]


class LayerSet:
    """Loaded 16x16 RGBA layer variants."""

    def __init__(self, variants: dict[str, list[tuple[str, Image.Image]]]) -> None:
        self.variants = variants
        self.validate()

    def validate(self) -> None:
        """Raise ValueError when required layers are missing or malformed."""
        missing = [layer for layer in LAYER_ORDER if layer not in self.variants]

        if missing:
            raise ValueError(f"Missing required disc icon layer(s): {', '.join(missing)}")

        for layer_name, variants in self.variants.items():
            if not variants:
                raise ValueError(f"Disc icon layer has no variants: {layer_name}")

            for filename, image in variants:
                if image.mode != "RGBA":
                    raise ValueError(f"{filename} is not RGBA after loading")
                if image.size != (DISC_SIZE, DISC_SIZE):
                    raise ValueError(f"{filename} must be {DISC_SIZE}x{DISC_SIZE}; got {image.size}")

    def choose_variant(self, layer_name: str, rng: random.Random) -> tuple[str, Image.Image]:
        """Choose a random variant for a layer."""
        return rng.choice(self.variants[layer_name])


def stable_seed(value: str) -> int:
    """Return a stable integer seed from arbitrary text."""
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def load_layers(source: Path | None = None) -> LayerSet:
    """Load layer PNGs from a custom source or bundled package assets."""
    if source is None:
        return load_default_layers()

    if source.is_dir():
        return load_layers_from_directory(source)

    if source.is_file() and source.suffix.lower() == ".zip":
        return load_layers_from_zip(source)

    raise ValueError(f"Disc icon layer source must be a directory or .zip file: {source}")


def load_default_layers() -> LayerSet:
    """Load the bundled procedural disc layer assets."""
    layer_root = resources.files("music_disc_maker").joinpath("assets", "disc_layers")
    variants: dict[str, list[tuple[str, Image.Image]]] = {}

    for resource in sorted(layer_root.iterdir(), key=lambda item: item.name):
        if not resource.name.endswith(".png"):
            continue

        layer_name = get_layer_name(resource.name)

        if not layer_name:
            continue

        with resources.as_file(resource) as path:
            image = Image.open(path).convert("RGBA")
            image.load()

        variants.setdefault(layer_name, []).append((resource.name, image))

    return LayerSet(variants)


def load_layers_from_directory(source: Path) -> LayerSet:
    """Load layer PNGs from a directory."""
    variants: dict[str, list[tuple[str, Image.Image]]] = {}

    for path in sorted(source.rglob("*.png")):
        if path.name == "composite.png":
            continue

        layer_name = get_layer_name(path.name)

        if not layer_name:
            continue

        image = Image.open(path).convert("RGBA")
        image.load()
        variants.setdefault(layer_name, []).append((path.name, image))

    return LayerSet(variants)


def load_layers_from_zip(source: Path) -> LayerSet:
    """Load layer PNGs from a zip archive."""
    variants: dict[str, list[tuple[str, Image.Image]]] = {}

    with zipfile.ZipFile(source) as archive:
        for member in sorted(archive.namelist()):
            filename = Path(member).name

            if not filename.endswith(".png") or filename == "composite.png":
                continue

            layer_name = get_layer_name(filename)

            if not layer_name:
                continue

            with archive.open(member) as handle:
                image = Image.open(handle).convert("RGBA")
                image.load()

            variants.setdefault(layer_name, []).append((filename, image))

    return LayerSet(variants)


def get_layer_name(filename: str) -> str | None:
    """Return the canonical layer name for a layer filename."""
    if filename in {f"{layer}.png" for layer in LAYER_ORDER}:
        return filename[:-4]

    match = LAYER_FILE_PATTERN.match(filename)

    if not match:
        return None

    candidate = match.group(1).lower()

    if candidate in LAYER_ORDER:
        return candidate

    return None


def make_disc_plan(layers: LayerSet, seed: int) -> DiscPlan:
    """Create a deterministic render plan for one disc."""
    rng = random.Random(seed)
    variants = {}

    for layer_name in LAYER_ORDER:
        filename, _ = layers.choose_variant(layer_name, rng)
        variants[layer_name] = filename

    grouped_transform = ColorTransform(
        hue_degrees=rng.uniform(0.0, 360.0),
        invert=rng.choice((False, True)),
        brightness=rng.uniform(0.96, 1.06),
    )
    independent_transforms = {
        layer_name: ColorTransform(
            hue_degrees=rng.uniform(0.0, 360.0),
            invert=rng.choice((False, True)),
            brightness=rng.uniform(0.94, 1.08),
        )
        for layer_name in sorted(INDEPENDENT_COLOR_LAYERS)
    }
    invariant_transforms = {
        layer_name: ColorTransform(brightness=rng.uniform(0.95, 1.05))
        for layer_name in sorted(INVARIANT_LAYERS)
    }

    return DiscPlan(
        seed=seed,
        variants=variants,
        grouped_transform=grouped_transform,
        independent_transforms=independent_transforms,
        invariant_transforms=invariant_transforms,
    )


def render_disc(layers: LayerSet, seed: int) -> Image.Image:
    """Render one procedural disc as a 16x16 RGBA image."""
    plan = make_disc_plan(layers, seed)
    selected_layers = {}

    for layer_name in LAYER_ORDER:
        image = get_variant_by_filename(layers, layer_name, plan.variants[layer_name])

        if layer_name in GROUPED_COLOR_LAYERS:
            transformed = transform_layer(image, plan.grouped_transform)
        elif layer_name in INDEPENDENT_COLOR_LAYERS:
            transformed = transform_layer(image, plan.independent_transforms[layer_name])
        elif layer_name in INVARIANT_LAYERS:
            transformed = transform_layer(image, plan.invariant_transforms[layer_name])
        else:
            transformed = image.copy()

        selected_layers[layer_name] = transformed

    output = Image.new("RGBA", (DISC_SIZE, DISC_SIZE), (0, 0, 0, 0))

    for layer_name in LAYER_ORDER:
        output.alpha_composite(selected_layers[layer_name])

    return output


def render_disc_from_key(key: str, layer_source: Path | None = None) -> Image.Image:
    """Render one deterministic procedural disc from a text key."""
    return render_disc(load_layers(layer_source), stable_seed(key))


def get_variant_by_filename(layers: LayerSet, layer_name: str, filename: str) -> Image.Image:
    """Return a copy of a named layer variant."""
    for candidate_name, image in layers.variants[layer_name]:
        if candidate_name == filename:
            return image.copy()

    raise KeyError(f"Layer variant not found: {layer_name}/{filename}")


def transform_layer(image: Image.Image, transform: ColorTransform) -> Image.Image:
    """Apply invert, hue rotation, and brightness while preserving transparency."""
    source = image.convert("RGBA")
    output = Image.new("RGBA", source.size, (0, 0, 0, 0))

    for y in range(source.height):
        for x in range(source.width):
            r, g, b, a = source.getpixel((x, y))

            if a == 0:
                continue

            if transform.invert:
                r, g, b = 255 - r, 255 - g, 255 - b

            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            h = (h + (transform.hue_degrees / 360.0)) % 1.0
            v = clamp01(v * transform.brightness)
            nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
            output.putpixel((x, y), (int(round(nr * 255)), int(round(ng * 255)), int(round(nb * 255)), a))

    return output


def clamp01(value: float) -> float:
    """Clamp a float to the inclusive range 0..1."""
    return max(0.0, min(1.0, value))
