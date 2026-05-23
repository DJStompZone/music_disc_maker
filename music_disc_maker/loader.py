from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any

from music_disc_maker.defaults import (
    COMPARATOR_SIGNAL_MAX,
    COMPARATOR_SIGNAL_MIN,
    CONFIG_FILE_NAMES,
    DEFAULT_COMPARATOR_SIGNAL,
    DEFAULT_DUMMY_RECORD_EVENT,
    DEFAULT_NAMESPACE,
    DEFAULT_PACK_ID,
    DEFAULT_PACK_TITLE,
    DEFAULT_SERVER_MODULE_VERSION,
    ITEM_FORMAT_VERSION,
    MIN_ENGINE_VERSION,
    PACK_ICON_SIZE,
    SOUND_DEFINITIONS_FORMAT_VERSION,
)
from music_disc_maker.models import BuildConfig, DiscInput
from music_disc_maker.validation import (
    clamp_comparator_signal,
    coerce_min_engine_version,
    make_default_sound_id,
    normalize_local_id,
    normalize_namespace,
    validate_sound_id,
)

CONFIG_TABLE_NAMES = ("music-disc-maker", "music_disc_maker")


def find_config_file(start: Path | None = None) -> Path | None:
    """Return the first supported config file found in the provided directory."""
    search_root = start or Path.cwd()

    for name in CONFIG_FILE_NAMES:
        candidate = search_root / name

        if candidate.is_file():
            return candidate

    pyproject = search_root / "pyproject.toml"

    if pyproject.is_file() and load_config_file(pyproject):
        return pyproject

    return None


def load_config_file(path: Path) -> dict[str, Any]:
    """Load a TOML, JSON, or pyproject-backed configuration file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    elif path.suffix.lower() == ".toml":
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Unsupported config file type: {path.suffix}")

    if path.name == "pyproject.toml":
        tool = data.get("tool", {})

        for table_name in CONFIG_TABLE_NAMES:
            table = tool.get(table_name)

            if isinstance(table, dict):
                return table

        return {}

    return data


def load_build_config(args: argparse.Namespace) -> BuildConfig:
    """Load build configuration from defaults, config files, and CLI overrides."""
    config_path = resolve_config_path(args)
    raw_config = load_config_file(config_path) if config_path else {}
    config_base = config_path.parent if config_path else Path.cwd()
    single_disc_mode = has_single_disc_args(args)

    if single_disc_mode:
        discs = [load_single_disc(args, raw_config, config_base)]
    else:
        discs = load_config_discs(raw_config, args, config_base)

    if not discs:
        raise ValueError("No discs configured. Provide input/--id/--title or add [[discs]] entries to a config file.")

    comparator_min = int(resolve_value(args, raw_config, "comparator_signal_min", COMPARATOR_SIGNAL_MIN))
    comparator_max = int(resolve_value(args, raw_config, "comparator_signal_max", COMPARATOR_SIGNAL_MAX))

    return BuildConfig(
        pack_id=normalize_local_id(str(resolve_value(args, raw_config, "pack_id", DEFAULT_PACK_ID)), "pack_id"),
        pack_title=str(resolve_value(args, raw_config, "pack_title", DEFAULT_PACK_TITLE)),
        namespace=normalize_namespace(str(resolve_value(args, raw_config, "namespace", DEFAULT_NAMESPACE))),
        discs=discs,
        output_root=resolve_output_root(args, raw_config, config_base),
        server_module_version=str(resolve_value(args, raw_config, "server_module_version", DEFAULT_SERVER_MODULE_VERSION)),
        item_format_version=str(resolve_value(args, raw_config, "item_format_version", ITEM_FORMAT_VERSION)),
        sound_definitions_format_version=str(resolve_value(args, raw_config, "sound_definitions_format_version", SOUND_DEFINITIONS_FORMAT_VERSION)),
        min_engine_version=coerce_min_engine_version(resolve_value(args, raw_config, "min_engine_version", MIN_ENGINE_VERSION.copy())),
        comparator_signal_min=comparator_min,
        comparator_signal_max=comparator_max,
        pack_icon_size=int(resolve_value(args, raw_config, "pack_icon_size", PACK_ICON_SIZE)),
    )


def resolve_config_path(args: argparse.Namespace) -> Path | None:
    """Resolve the explicit or discovered config path."""
    if getattr(args, "no_config", False):
        return None

    explicit = getattr(args, "config", None)

    if explicit:
        return explicit

    return find_config_file(Path.cwd())


def resolve_output_root(args: argparse.Namespace, raw_config: dict[str, Any], config_base: Path) -> Path:
    """Resolve output_root, making config-file paths relative to the config file."""
    if getattr(args, "output_root", None) is not None:
        return args.output_root

    value = raw_config.get("output_root")

    if value is None:
        return Path(".")

    return resolve_path(Path(str(value)), config_base)


def has_single_disc_args(args: argparse.Namespace) -> bool:
    """Return whether the CLI is being used in single-disc mode."""
    return any(getattr(args, name, None) is not None for name in ("input", "id", "title", "sound_id"))


def load_single_disc(args: argparse.Namespace, raw_config: dict[str, Any], config_base: Path) -> DiscInput:
    """Load a single disc from CLI arguments with config-backed defaults."""
    if not args.input or not args.id or not args.title:
        raise ValueError("single-disc mode requires input, --id, and --title")

    disc_id = normalize_local_id(args.id, "--id")
    comparator_min = int(resolve_value(args, raw_config, "comparator_signal_min", COMPARATOR_SIGNAL_MIN))
    comparator_max = int(resolve_value(args, raw_config, "comparator_signal_max", COMPARATOR_SIGNAL_MAX))
    comparator_default = int(resolve_value(args, raw_config, "default_comparator_signal", DEFAULT_COMPARATOR_SIGNAL))
    comparator_value = args.comparator_signal if args.comparator_signal is not None else comparator_default
    sound_id = validate_sound_id(args.sound_id or make_default_sound_id(disc_id))

    return DiscInput(
        input_file=args.input,
        disc_id=disc_id,
        title=args.title,
        sound_id=sound_id,
        dummy_sound_event=str(resolve_value(args, raw_config, "dummy_sound_event", DEFAULT_DUMMY_RECORD_EVENT)),
        comparator_signal=clamp_comparator_signal(int(comparator_value), comparator_min, comparator_max),
    )


def load_config_discs(raw_config: dict[str, Any], args: argparse.Namespace, config_base: Path) -> list[DiscInput]:
    """Load disc entries from a config file."""
    comparator_min = int(resolve_value(args, raw_config, "comparator_signal_min", COMPARATOR_SIGNAL_MIN))
    comparator_max = int(resolve_value(args, raw_config, "comparator_signal_max", COMPARATOR_SIGNAL_MAX))
    comparator_default = int(resolve_value(args, raw_config, "default_comparator_signal", DEFAULT_COMPARATOR_SIGNAL))
    dummy_sound_event = str(resolve_value(args, raw_config, "dummy_sound_event", DEFAULT_DUMMY_RECORD_EVENT))
    discs = []

    for entry in raw_config.get("discs", []):
        if not isinstance(entry, dict):
            raise ValueError("Each disc config entry must be a table/object")

        disc_id = normalize_local_id(str(entry["id"]), "disc id")
        sound_id = validate_sound_id(str(entry.get("sound_id") or make_default_sound_id(disc_id)))
        comparator_value = int(entry.get("comparator_signal", comparator_default))

        discs.append(DiscInput(
            input_file=resolve_path(Path(str(entry["input"])), config_base),
            disc_id=disc_id,
            title=str(entry["title"]),
            sound_id=sound_id,
            dummy_sound_event=str(entry.get("dummy_sound_event", dummy_sound_event)),
            comparator_signal=clamp_comparator_signal(comparator_value, comparator_min, comparator_max),
        ))

    return discs


def resolve_value(args: argparse.Namespace, raw_config: dict[str, Any], name: str, default: Any) -> Any:
    """Resolve a value by CLI, then config file, then hardcoded default."""
    cli_value = getattr(args, name, None)

    if cli_value is not None:
        return cli_value

    return raw_config.get(name, default)


def resolve_path(path: Path, base: Path) -> Path:
    """Resolve a possibly relative config path against a base directory."""
    if path.is_absolute():
        return path

    return base / path
