from __future__ import annotations

from pathlib import Path

import pytest

from music_disc_maker import config_generator
from music_disc_maker.config_generator import (
    AudioMetadata,
    build_disc_entries,
    find_audio_files,
    generate_config_file,
    normalize_title_to_id,
    render_config_toml,
)


def test_find_audio_files_scans_current_directory_only_by_default(tmp_path: Path) -> None:
    (tmp_path / "a.mp3").write_bytes(b"fake")
    (tmp_path / "b.flac").write_bytes(b"fake")
    (tmp_path / "notes.txt").write_text("not audio", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "c.wav").write_bytes(b"fake")

    files = find_audio_files(tmp_path)

    assert [path.name for path in files] == ["a.mp3", "b.flac"]


def test_find_audio_files_can_scan_recursively(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "a.mp3").write_bytes(b"fake")
    (nested / "b.wav").write_bytes(b"fake")

    files = find_audio_files(tmp_path, recursive=True)

    assert [path.relative_to(tmp_path).as_posix() for path in files] == ["a.mp3", "nested/b.wav"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Song Title", "song_title"),
        ("Whiplash!", "whiplash"),
        ("Café del Mar", "cafe_del_mar"),
        ("!!!", "disc"),
    ],
)
def test_normalize_title_to_id(value: str, expected: str) -> None:
    assert normalize_title_to_id(value) == expected


def test_build_disc_entries_uses_metadata_for_id_and_display_title(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio_file = tmp_path / "whatever.mp3"
    audio_file.write_bytes(b"fake")

    monkeypatch.setattr(
        config_generator,
        "probe_audio_metadata",
        lambda path: AudioMetadata(title="Whiplash!", artist="DJ Stomp"),
    )

    entries = build_disc_entries([audio_file], tmp_path)

    assert entries[0].input_path == "whatever.mp3"
    assert entries[0].disc_id == "whiplash"
    assert entries[0].title == "DJ Stomp - Whiplash!"


def test_build_disc_entries_parses_artist_title_filename_when_metadata_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio_file = tmp_path / "DJ Stomp - Whiplash!.mp3"
    audio_file.write_bytes(b"fake")

    monkeypatch.setattr(config_generator, "probe_audio_metadata", lambda path: AudioMetadata())

    entries = build_disc_entries([audio_file], tmp_path)

    assert entries[0].disc_id == "whiplash"
    assert entries[0].title == "DJ Stomp - Whiplash!"


def test_build_disc_entries_deduplicates_ids(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    first = tmp_path / "one.mp3"
    second = tmp_path / "two.mp3"
    first.write_bytes(b"fake")
    second.write_bytes(b"fake")

    monkeypatch.setattr(config_generator, "probe_audio_metadata", lambda path: AudioMetadata(title="Same Song"))

    entries = build_disc_entries([first, second], tmp_path)

    assert [entry.disc_id for entry in entries] == ["same_song", "same_song_2"]


def test_render_config_toml_round_trip_with_loader(tmp_path: Path) -> None:
    audio_file = tmp_path / "whiplash.mp3"
    audio_file.write_bytes(b"fake")
    entries = [config_generator.GeneratedDiscEntry(input_path="whiplash.mp3", disc_id="whiplash", title="DJ Stomp - Whiplash!")]
    config_file = tmp_path / "music_disc_maker.toml"
    config_file.write_text(render_config_toml(entries, pack_title="DJ Discs", namespace="dj"), encoding="utf-8")

    from music_disc_maker.loader import load_build_config
    from tests.test_loader import make_args

    config = load_build_config(make_args(config=config_file, no_config=False))

    assert config.pack_title == "DJ Discs"
    assert config.namespace == "dj"
    assert config.discs[0].input_file == audio_file
    assert config.discs[0].disc_id == "whiplash"
    assert config.discs[0].title == "DJ Stomp - Whiplash!"


def test_generate_config_file_refuses_to_overwrite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "music_disc_maker.toml"
    output.write_text("existing", encoding="utf-8")

    monkeypatch.setattr(config_generator, "probe_audio_metadata", lambda path: AudioMetadata(title="Whiplash!"))

    with pytest.raises(FileExistsError):
        generate_config_file(tmp_path, output)


def test_parse_artist_title_strips_track_prefix_and_noise() -> None:
    parsed = config_generator.parse_artist_title_from_stem("01 - DJ Stomp - Whiplash! (Official Audio)")

    assert parsed.artist == "DJ Stomp"
    assert parsed.title == "Whiplash!"


def test_parse_artist_title_supports_title_artist_order() -> None:
    parsed = config_generator.parse_artist_title_from_stem("Whiplash! - DJ Stomp", filename_order="title-artist")

    assert parsed.artist == "DJ Stomp"
    assert parsed.title == "Whiplash!"


def test_build_disc_entries_uses_smarter_filename_parser_when_metadata_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio_file = tmp_path / "01 - DJ Stomp - Whiplash! [HD].mp3"
    audio_file.write_bytes(b"fake")

    monkeypatch.setattr(config_generator, "probe_audio_metadata", lambda path: AudioMetadata())

    entries = build_disc_entries([audio_file], tmp_path)

    assert entries[0].disc_id == "whiplash"
    assert entries[0].title == "DJ Stomp - Whiplash!"


def test_build_disc_entries_can_disable_progress(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio_file = tmp_path / "DJ Stomp - Whiplash!.mp3"
    audio_file.write_bytes(b"fake")

    monkeypatch.setattr(config_generator, "probe_audio_metadata", lambda path: AudioMetadata())

    entries = build_disc_entries([audio_file], tmp_path, progress=False)

    assert entries[0].disc_id == "whiplash"
