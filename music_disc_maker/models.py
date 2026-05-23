from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from music_disc_maker.defaults import (
    COMPARATOR_SIGNAL_MAX,
    COMPARATOR_SIGNAL_MIN,
    DEFAULT_SERVER_MODULE_VERSION,
    ITEM_FORMAT_VERSION,
    MIN_ENGINE_VERSION,
    PACK_ICON_SIZE,
    SOUND_DEFINITIONS_FORMAT_VERSION,
)


@dataclass(frozen=True)
class DiscInput:
    """Input data for one generated custom disc."""

    input_file: Path
    disc_id: str
    title: str
    sound_id: str
    dummy_sound_event: str
    comparator_signal: int


@dataclass(frozen=True)
class BuiltDisc:
    """Generated metadata for one finished custom disc."""

    item_id: str
    disc_id: str
    title: str
    sound_id: str
    dummy_sound_event: str
    comparator_signal: int
    duration_seconds: float
    duration_ticks: int


@dataclass(frozen=True)
class BuildConfig:
    """Top-level pack generation settings."""

    pack_id: str
    pack_title: str
    namespace: str
    discs: list[DiscInput]
    output_root: Path
    server_module_version: str = DEFAULT_SERVER_MODULE_VERSION
    item_format_version: str = ITEM_FORMAT_VERSION
    sound_definitions_format_version: str = SOUND_DEFINITIONS_FORMAT_VERSION
    min_engine_version: list[int] = field(default_factory=lambda: MIN_ENGINE_VERSION.copy())
    comparator_signal_min: int = COMPARATOR_SIGNAL_MIN
    comparator_signal_max: int = COMPARATOR_SIGNAL_MAX
    pack_icon_size: int = PACK_ICON_SIZE


@dataclass(frozen=True)
class PackPaths:
    """Filesystem paths used by the generated add-on."""

    pack_dir: Path
    rp_path: Path
    bp_path: Path
