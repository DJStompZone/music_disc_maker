from __future__ import annotations

import argparse
from pathlib import Path

from music_disc_maker.defaults import (
    COMPARATOR_SIGNAL_MAX,
    COMPARATOR_SIGNAL_MIN,
    DEFAULT_COMPARATOR_SIGNAL,
    DEFAULT_DUMMY_RECORD_EVENT,
    DEFAULT_NAMESPACE,
    DEFAULT_PACK_ID,
    DEFAULT_PACK_TITLE,
    DEFAULT_SERVER_MODULE_VERSION,
    ITEM_FORMAT_VERSION,
    PACK_ICON_SIZE,
    SOUND_DEFINITIONS_FORMAT_VERSION,
)
from music_disc_maker.validation import parse_min_engine_version


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Build a scripted Minecraft Bedrock custom music disc add-on.")
    parser.add_argument("input", nargs="?", type=Path, help="Input audio file path for single-disc mode")
    parser.add_argument("--id", help="Disc ID for single-disc mode, for example: whiplash")
    parser.add_argument("--title", help="Disc display title for single-disc mode, for example: Whiplash!")
    parser.add_argument("--config", type=Path, help="TOML or JSON config file. If omitted, common config filenames are auto-discovered.")
    parser.add_argument("--no-config", action="store_true", help="Disable automatic config-file discovery.")
    parser.add_argument("--pack-id", default=None, help=f"Generated pack ID. Default: {DEFAULT_PACK_ID}")
    parser.add_argument("--pack-title", default=None, help=f"Generated pack title. Default: {DEFAULT_PACK_TITLE}")
    parser.add_argument("--namespace", default=None, help=f"Custom item namespace. Default: {DEFAULT_NAMESPACE}")
    parser.add_argument("--sound-id", default=None, help="Optional sound definition key for single-disc mode. Default: record.<disc_id>")
    parser.add_argument("--dummy-sound-event", default=None, help=f"Valid LevelSoundEvent used only to make minecraft:record parse. Default: {DEFAULT_DUMMY_RECORD_EVENT}")
    parser.add_argument("--comparator-signal", type=int, default=None, help=f"Comparator signal strength. Default: {DEFAULT_COMPARATOR_SIGNAL}")
    parser.add_argument("--default-comparator-signal", type=int, default=None, help=f"Default comparator signal for config-file discs. Default: {DEFAULT_COMPARATOR_SIGNAL}")
    parser.add_argument("--comparator-signal-min", type=int, default=None, help=f"Minimum allowed comparator signal. Default: {COMPARATOR_SIGNAL_MIN}")
    parser.add_argument("--comparator-signal-max", type=int, default=None, help=f"Maximum allowed comparator signal. Default: {COMPARATOR_SIGNAL_MAX}")
    parser.add_argument("--server-module-version", default=None, help=f"@minecraft/server module version. Default: {DEFAULT_SERVER_MODULE_VERSION}")
    parser.add_argument("--item-format-version", default=None, help=f"Item format version. Default: {ITEM_FORMAT_VERSION}")
    parser.add_argument("--sound-definitions-format-version", default=None, help=f"sound_definitions.json format version. Default: {SOUND_DEFINITIONS_FORMAT_VERSION}")
    parser.add_argument("--min-engine-version", type=parse_min_engine_version, default=None, help="Minimum engine version. Default: 1.21.70")
    parser.add_argument("--pack-icon-size", type=int, default=None, help=f"Generated pack_icon.png size. Default: {PACK_ICON_SIZE}")
    parser.add_argument("--output-root", type=Path, default=None, help="Directory where generated packs are written")
    return parser.parse_args()
