from __future__ import annotations

from pathlib import Path

from music_disc_maker.io_utils import run_command


def convert_audio(input_file: Path, output_file: Path) -> float:
    """Convert an input audio file to a mono streaming OGG and return duration in seconds."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    run_command([
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "44100",
        "-c:a",
        "libvorbis",
        "-q:a",
        "4",
        str(output_file),
    ])

    probe = run_command([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(output_file),
    ])

    try:
        return round(float(probe.stdout.strip()), 3)
    except ValueError as exc:
        raise RuntimeError(f"Unable to read duration from ffprobe output: {probe.stdout!r}") from exc
