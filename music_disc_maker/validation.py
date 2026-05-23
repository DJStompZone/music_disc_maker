from __future__ import annotations

import argparse
import re
from typing import Any

from music_disc_maker.defaults import COMPARATOR_SIGNAL_MAX, COMPARATOR_SIGNAL_MIN


def normalize_local_id(value: str, field_name: str) -> str:
    """Normalize and validate a Minecraft-friendly local identifier."""
    normalized = value.strip().lower().replace(" ", "_")

    if not re.fullmatch(r"[a-z0-9_-]+", normalized):
        raise ValueError(f"{field_name} must contain only lowercase letters, numbers, underscores, and hyphens.")

    return normalized


def normalize_namespace(value: str) -> str:
    """Normalize and validate a Minecraft namespace."""
    normalized = value.strip().lower()

    if not re.fullmatch(r"[a-z0-9_.-]+", normalized):
        raise ValueError("namespace must contain only lowercase letters, numbers, underscores, dots, and hyphens.")

    return normalized


def validate_sound_id(value: str) -> str:
    """Validate a sound definition key for sound_definitions.json."""
    normalized = value.strip().lower()

    if not re.fullmatch(r"[a-z0-9_.:-]+", normalized):
        raise ValueError("sound_id must contain only lowercase letters, numbers, underscores, dots, colons, and hyphens.")

    return normalized


def make_default_sound_id(disc_id: str) -> str:
    """Return the custom sound definition key for a generated disc."""
    return f"record.{disc_id}"


def clamp_comparator_signal(
    value: int,
    minimum: int = COMPARATOR_SIGNAL_MIN,
    maximum: int = COMPARATOR_SIGNAL_MAX,
) -> int:
    """Clamp a music disc comparator signal to the configured range."""
    return min(max(value, minimum), maximum)


def parse_min_engine_version(value: str) -> list[int]:
    """Parse a Minecraft min_engine_version string like 1.21.70."""
    parts = value.split(".")

    if len(parts) != 3:
        raise argparse.ArgumentTypeError("min engine version must look like 1.21.70")

    try:
        return [int(part) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("min engine version must contain only numbers") from exc


def coerce_min_engine_version(value: Any) -> list[int]:
    """Coerce a config-file min_engine_version value to a three-integer list."""
    if isinstance(value, str):
        return parse_min_engine_version(value)

    if isinstance(value, list | tuple) and len(value) == 3:
        try:
            return [int(part) for part in value]
        except (TypeError, ValueError) as exc:
            raise ValueError("min_engine_version must contain only integers") from exc

    raise ValueError("min_engine_version must be a string like 1.21.70 or a three-item integer list")
