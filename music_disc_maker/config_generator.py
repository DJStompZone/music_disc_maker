from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from music_disc_maker.defaults import (
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
from music_disc_maker.validation import normalize_local_id, normalize_namespace

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

DEFAULT_CONFIG_OUTPUT = "music_disc_maker.toml"
DEFAULT_AUDIO_EXTENSIONS = (
    ".aac",
    ".aiff",
    ".alac",
    ".flac",
    ".m4a",
    ".mp3",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
)
FILENAME_ORDER_ARTIST_TITLE = "artist-title"
FILENAME_ORDER_TITLE_ARTIST = "title-artist"
FILENAME_ORDER_AUTO = "auto"
FILENAME_ORDER_CHOICES = (
    FILENAME_ORDER_ARTIST_TITLE,
    FILENAME_ORDER_TITLE_ARTIST,
    FILENAME_ORDER_AUTO,
)
NOISE_BRACKET_TEXT = (
    "official audio",
    "official video",
    "official lyric video",
    "lyric video",
    "lyrics",
    "visualizer",
    "music video",
    "hd",
    "hq",
    "4k",
    "320kbps",
    "320 kbps",
    "128kbps",
    "128 kbps",
    "explicit",
)
TRACK_PREFIX_PATTERN = re.compile(
    r"^\s*(?:(?:\(?\[?(?:disc|disk|cd)\s*\d+\]?\)?\s*[-_. ]+\s*)?\(?\[?(?:track\s*)?\d{1,3}\]?\)?(?:\s*[-_.]\s*|\s+))+",
    re.IGNORECASE,
)
SEPARATOR_PATTERN = re.compile(r"\s+(?:-|–|—|‒|―)\s+")


@dataclass(frozen=True)
class AudioMetadata:
    """Best-effort metadata extracted from an audio file."""

    title: str | None = None
    artist: str | None = None


@dataclass(frozen=True)
class GeneratedDiscEntry:
    """One generated [[discs]] TOML entry."""

    input_path: str
    disc_id: str
    title: str
    comparator_signal: int = DEFAULT_COMPARATOR_SIGNAL


@dataclass(frozen=True)
class FilenameParseResult:
    """Best-effort artist/title data parsed from a filename stem."""

    artist: str | None
    title: str


def find_audio_files(
    directory: Path,
    recursive: bool = False,
    extensions: Sequence[str] = DEFAULT_AUDIO_EXTENSIONS,
) -> list[Path]:
    """Return sorted audio files from a directory."""
    normalized_extensions = {extension.lower() if extension.startswith(".") else f".{extension.lower()}" for extension in extensions}
    globber = directory.rglob if recursive else directory.glob

    return sorted(
        path for path in globber("*")
        if path.is_file() and path.suffix.lower() in normalized_extensions
    )


def probe_audio_metadata(path: Path) -> AudioMetadata:
    """Read title and artist metadata with ffprobe when available."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return AudioMetadata()

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return AudioMetadata()

    tags = data.get("format", {}).get("tags", {})

    if not isinstance(tags, dict):
        return AudioMetadata()

    normalized_tags = {str(key).lower(): str(value).strip() for key, value in tags.items() if str(value).strip()}

    return AudioMetadata(
        title=first_tag_value(normalized_tags, ("title", "tracktitle", "track_title", "name")),
        artist=first_tag_value(normalized_tags, ("artist", "album_artist", "albumartist", "performer", "composer")),
    )


def first_tag_value(tags: dict[str, str], names: Iterable[str]) -> str | None:
    """Return the first non-empty metadata tag value from a list of candidate names."""
    for name in names:
        value = tags.get(name)

        if value:
            return value

    return None


def build_disc_entries(
    audio_files: Sequence[Path],
    base_dir: Path,
    comparator_signal: int = DEFAULT_COMPARATOR_SIGNAL,
    filename_order: str = FILENAME_ORDER_ARTIST_TITLE,
    progress: bool = False,
) -> list[GeneratedDiscEntry]:
    """Build TOML disc entries from audio files and best-effort metadata."""
    seen_ids: dict[str, int] = {}
    entries = []

    for audio_file in progress_iter(audio_files, enabled=progress, desc="Reading metadata"):
        metadata = probe_audio_metadata(audio_file)
        title, artist = resolve_title_and_artist(audio_file, metadata, filename_order=filename_order)
        base_id = normalize_title_to_id(title)
        disc_id = make_unique_id(base_id, seen_ids)
        display_title = f"{artist} - {title}" if artist else title

        entries.append(GeneratedDiscEntry(
            input_path=relative_config_path(audio_file, base_dir),
            disc_id=disc_id,
            title=display_title,
            comparator_signal=comparator_signal,
        ))

    return entries


def progress_iter(items: Sequence[Path], enabled: bool, desc: str) -> Iterator[Path]:
    """Yield items with an optional tqdm progress bar."""
    if not enabled or tqdm is None:
        yield from items
        return

    yield from tqdm(items, desc=desc, unit="file", dynamic_ncols=True, file=sys.stderr)


def resolve_title_and_artist(
    path: Path,
    metadata: AudioMetadata,
    filename_order: str = FILENAME_ORDER_ARTIST_TITLE,
) -> tuple[str, str | None]:
    """Resolve a disc title and artist from metadata, falling back to filename parsing."""
    title = clean_text(metadata.title)
    artist = clean_text(metadata.artist)

    if title:
        return clean_display_title(title), clean_display_artist(artist)

    parsed = parse_artist_title_from_stem(path.stem, filename_order=filename_order)

    return parsed.title, artist or parsed.artist


def parse_artist_title_from_stem(stem: str, filename_order: str = FILENAME_ORDER_ARTIST_TITLE) -> FilenameParseResult:
    """Infer artist and title from common music filename patterns."""
    if filename_order not in FILENAME_ORDER_CHOICES:
        raise ValueError(f"filename_order must be one of: {', '.join(FILENAME_ORDER_CHOICES)}")

    cleaned = clean_filename_text(stem)
    parts = [part.strip() for part in SEPARATOR_PATTERN.split(cleaned) if part.strip()]
    parts = [strip_track_number_prefix(part) for part in parts]
    parts = [part for part in parts if part]

    if len(parts) >= 2:
        if filename_order == FILENAME_ORDER_TITLE_ARTIST:
            title = parts[0]
            artist = parts[-1]
        else:
            artist = parts[0]
            title = parts[-1]

        return FilenameParseResult(artist=clean_display_artist(artist), title=clean_display_title(title) or "Untitled")

    title = clean_display_title(cleaned) or "Untitled"
    return FilenameParseResult(artist=None, title=title)


def split_artist_title_from_stem(stem: str) -> tuple[str | None, str]:
    """Infer artist and title from common 'Artist - Title' file stems."""
    parsed = parse_artist_title_from_stem(stem)
    return parsed.artist, parsed.title


def clean_text(value: str | None) -> str | None:
    """Normalize whitespace in a text value and return None for empty input."""
    if value is None:
        return None

    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def clean_filename_text(value: str) -> str:
    """Convert common filename separators and junk markers into readable title text."""
    cleaned = unicodedata.normalize("NFKC", value)
    cleaned = cleaned.replace("_", " ")
    cleaned = cleaned.replace("／", "-")
    cleaned = cleaned.replace("∕", "-")
    cleaned = cleaned.replace("⧸", "-")
    cleaned = cleaned.replace("⧹", "-")
    cleaned = re.sub(r"\s*[|]+\s*", " - ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = strip_track_number_prefix(cleaned)
    cleaned = strip_noise_brackets(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -._")
    return cleaned


def strip_track_number_prefix(value: str) -> str:
    """Remove common leading track/disc number prefixes from a filename segment."""
    cleaned = value.strip()
    previous = None

    while previous != cleaned:
        previous = cleaned
        cleaned = TRACK_PREFIX_PATTERN.sub("", cleaned).strip()

    return cleaned


def strip_noise_brackets(value: str) -> str:
    """Remove low-value bracketed filename tags like '(Official Audio)' and '[HD]'."""
    def replace_match(match: re.Match[str]) -> str:
        inner = re.sub(r"\s+", " ", match.group(1)).strip().lower()
        normalized = re.sub(r"[^a-z0-9 ]+", "", inner)

        if normalized in NOISE_BRACKET_TEXT:
            return " "

        return match.group(0)

    without_noise = re.sub(r"[\[(]([^\])]+)[\])]", replace_match, value)
    return re.sub(r"\s+", " ", without_noise).strip()


def clean_display_title(value: str | None) -> str | None:
    """Clean title text while preserving meaningful punctuation."""
    cleaned = clean_text(value)

    if cleaned is None:
        return None

    cleaned = strip_noise_brackets(cleaned)
    cleaned = strip_track_number_prefix(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -._")
    return cleaned or None


def clean_display_artist(value: str | None) -> str | None:
    """Clean artist text while preserving meaningful punctuation."""
    cleaned = clean_text(value)

    if cleaned is None:
        return None

    cleaned = strip_track_number_prefix(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -._")
    return cleaned or None


def normalize_title_to_id(value: str) -> str:
    """Convert a display title into a stable Minecraft local item ID."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    normalized = re.sub(r"_+", "_", normalized)

    if not normalized:
        normalized = "disc"

    return normalize_local_id(normalized, "generated disc id")


def make_unique_id(base_id: str, seen_ids: dict[str, int]) -> str:
    """Return a stable unique ID, suffixing duplicates with _2, _3, etc."""
    count = seen_ids.get(base_id, 0) + 1
    seen_ids[base_id] = count

    if count == 1:
        return base_id

    return f"{base_id}_{count}"


def relative_config_path(path: Path, base_dir: Path) -> str:
    """Return a portable path string relative to the generated config file."""
    try:
        relative = path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        relative = path

    return relative.as_posix()


def render_config_toml(
    entries: Sequence[GeneratedDiscEntry],
    pack_id: str = DEFAULT_PACK_ID,
    pack_title: str = DEFAULT_PACK_TITLE,
    namespace: str = DEFAULT_NAMESPACE,
    output_root: str | None = None,
    dummy_sound_event: str = DEFAULT_DUMMY_RECORD_EVENT,
    server_module_version: str = DEFAULT_SERVER_MODULE_VERSION,
    item_format_version: str = ITEM_FORMAT_VERSION,
    sound_definitions_format_version: str = SOUND_DEFINITIONS_FORMAT_VERSION,
    min_engine_version: Sequence[int] = MIN_ENGINE_VERSION,
    default_comparator_signal: int = DEFAULT_COMPARATOR_SIGNAL,
    pack_icon_size: int = PACK_ICON_SIZE,
) -> str:
    """Render a complete music_disc_maker.toml file."""
    lines = [
        f"pack_id = {toml_string(normalize_local_id(pack_id, 'pack_id'))}",
        f"pack_title = {toml_string(pack_title)}",
        f"namespace = {toml_string(normalize_namespace(namespace))}",
    ]

    if output_root is not None:
        lines.append(f"output_root = {toml_string(output_root)}")

    lines.extend([
        f"dummy_sound_event = {toml_string(dummy_sound_event)}",
        f"server_module_version = {toml_string(server_module_version)}",
        f"item_format_version = {toml_string(item_format_version)}",
        f"sound_definitions_format_version = {toml_string(sound_definitions_format_version)}",
        f"min_engine_version = {toml_int_array(min_engine_version)}",
        f"default_comparator_signal = {int(default_comparator_signal)}",
        f"pack_icon_size = {int(pack_icon_size)}",
        "",
    ])

    for entry in entries:
        lines.extend([
            "[[discs]]",
            f"input = {toml_string(entry.input_path)}",
            f"id = {toml_string(entry.disc_id)}",
            f"title = {toml_string(entry.title)}",
            f"comparator_signal = {int(entry.comparator_signal)}",
            "",
        ])

    return "\n".join(lines).rstrip() + "\n"


def toml_string(value: str) -> str:
    """Return a safely escaped TOML basic string."""
    return json.dumps(value, ensure_ascii=False)


def toml_int_array(values: Sequence[int]) -> str:
    """Return a TOML integer array."""
    return "[" + ", ".join(str(int(value)) for value in values) + "]"


def generate_config_file(
    directory: Path,
    output_file: Path,
    recursive: bool = False,
    overwrite: bool = False,
    extensions: Sequence[str] = DEFAULT_AUDIO_EXTENSIONS,
    pack_id: str = DEFAULT_PACK_ID,
    pack_title: str = DEFAULT_PACK_TITLE,
    namespace: str = DEFAULT_NAMESPACE,
    output_root: str | None = None,
    comparator_signal: int = DEFAULT_COMPARATOR_SIGNAL,
    filename_order: str = FILENAME_ORDER_ARTIST_TITLE,
    progress: bool = False,
) -> str:
    """Generate a TOML config for audio files in a directory and write it to disk."""
    if output_file.exists() and not overwrite:
        raise FileExistsError(f"Config file already exists: {output_file}. Use --overwrite to replace it.")

    audio_files = find_audio_files(directory=directory, recursive=recursive, extensions=extensions)
    entries = build_disc_entries(
        audio_files=audio_files,
        base_dir=directory,
        comparator_signal=comparator_signal,
        filename_order=filename_order,
        progress=progress,
    )
    toml_text = render_config_toml(
        entries=entries,
        pack_id=pack_id,
        pack_title=pack_title,
        namespace=namespace,
        output_root=output_root,
        default_comparator_signal=comparator_signal,
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(toml_text, encoding="utf-8")
    return toml_text


def parse_extension_list(value: str) -> tuple[str, ...]:
    """Parse a comma-separated extension list."""
    extensions = tuple(part.strip() for part in value.split(",") if part.strip())

    if not extensions:
        raise argparse.ArgumentTypeError("extension list cannot be empty")

    return extensions


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse config generator arguments."""
    parser = argparse.ArgumentParser(description="Generate a music_disc_maker.toml from audio files in a directory.")
    parser.add_argument("--directory", type=Path, default=None, help="Directory to scan. Default: current directory.")
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_CONFIG_OUTPUT), help=f"Output TOML path. Default: {DEFAULT_CONFIG_OUTPUT}")
    parser.add_argument("--recursive", action="store_true", help="Scan subdirectories recursively.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output file.")
    parser.add_argument("--stdout", action="store_true", help="Print the generated TOML instead of writing it.")
    parser.add_argument("--no-progress", action="store_true", help="Disable the metadata progress bar.")
    parser.add_argument("--filename-order", choices=FILENAME_ORDER_CHOICES, default=FILENAME_ORDER_ARTIST_TITLE, help="How to interpret filenames when metadata is missing. Default: artist-title.")
    parser.add_argument("--extensions", type=parse_extension_list, default=DEFAULT_AUDIO_EXTENSIONS, help="Comma-separated audio extensions to include.")
    parser.add_argument("--pack-id", default=DEFAULT_PACK_ID, help=f"Generated pack ID. Default: {DEFAULT_PACK_ID}")
    parser.add_argument("--pack-title", default=DEFAULT_PACK_TITLE, help=f"Generated pack title. Default: {DEFAULT_PACK_TITLE}")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE, help=f"Custom item namespace. Default: {DEFAULT_NAMESPACE}")
    parser.add_argument("--output-root", default=None, help="Optional output_root value to write into the config.")
    parser.add_argument("--comparator-signal", type=int, default=DEFAULT_COMPARATOR_SIGNAL, help=f"Comparator signal for generated discs. Default: {DEFAULT_COMPARATOR_SIGNAL}")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the config generator CLI."""
    args = parse_args(argv)
    directory = args.directory or Path.cwd()
    audio_files = find_audio_files(directory=directory, recursive=args.recursive, extensions=args.extensions)
    progress = not args.no_progress
    entries = build_disc_entries(
        audio_files=audio_files,
        base_dir=directory,
        comparator_signal=args.comparator_signal,
        filename_order=args.filename_order,
        progress=progress,
    )
    toml_text = render_config_toml(
        entries=entries,
        pack_id=args.pack_id,
        pack_title=args.pack_title,
        namespace=args.namespace,
        output_root=args.output_root,
        default_comparator_signal=args.comparator_signal,
    )

    if args.stdout:
        print(toml_text, end="")
        return 0

    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"Config file already exists: {args.output}. Use --overwrite to replace it.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(toml_text, encoding="utf-8")
    print(f"Created: {args.output}")
    print(f"Discs found: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
