from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from music_disc_maker.loader import find_config_file, load_build_config, load_config_file


def make_args(**overrides):
    values = {
        "input": None,
        "id": None,
        "title": None,
        "config": None,
        "no_config": True,
        "pack_id": None,
        "pack_title": None,
        "namespace": None,
        "sound_id": None,
        "dummy_sound_event": None,
        "comparator_signal": None,
        "default_comparator_signal": None,
        "comparator_signal_min": None,
        "comparator_signal_max": None,
        "server_module_version": None,
        "item_format_version": None,
        "sound_definitions_format_version": None,
        "min_engine_version": None,
        "pack_icon_size": None,
        "output_root": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_load_toml_config_resolves_paths_relative_to_config(tmp_path: Path) -> None:
    audio_dir = tmp_path / "assets"
    audio_dir.mkdir()
    audio_file = audio_dir / "song.mp3"
    audio_file.write_bytes(b"fake")
    config_file = tmp_path / "music_disc_maker.toml"
    config_file.write_text(
        """
pack_id = "My Discs"
pack_title = "My Discs"
namespace = "dj"
output_root = "build"
server_module_version = "2.8.0-beta"
item_format_version = "1.21.70"
sound_definitions_format_version = "1.20.20"
min_engine_version = "1.21.70"
default_comparator_signal = 9
pack_icon_size = 128

[[discs]]
input = "assets/song.mp3"
id = "Whiplash"
title = "Whiplash!"
""".strip(),
        encoding="utf-8",
    )

    config = load_build_config(make_args(config=config_file, no_config=False))

    assert config.pack_id == "my_discs"
    assert config.pack_title == "My Discs"
    assert config.namespace == "dj"
    assert config.output_root == tmp_path / "build"
    assert config.pack_icon_size == 128
    assert config.min_engine_version == [1, 21, 70]
    assert len(config.discs) == 1
    assert config.discs[0].input_file == audio_file
    assert config.discs[0].disc_id == "whiplash"
    assert config.discs[0].sound_id == "record.whiplash"
    assert config.discs[0].comparator_signal == 9


def test_cli_values_override_config_values(tmp_path: Path) -> None:
    audio_file = tmp_path / "song.mp3"
    audio_file.write_bytes(b"fake")
    config_file = tmp_path / "music_disc_maker.toml"
    config_file.write_text(
        """
pack_id = "from_config"
namespace = "ignored"
pack_icon_size = 64
""".strip(),
        encoding="utf-8",
    )

    config = load_build_config(make_args(
        input=audio_file,
        id="Main Song",
        title="Main Song",
        config=config_file,
        no_config=False,
        pack_id="from_cli",
        namespace="dj",
        pack_icon_size=512,
    ))

    assert config.pack_id == "from_cli"
    assert config.namespace == "dj"
    assert config.pack_icon_size == 512
    assert config.discs[0].disc_id == "main_song"


def test_json_config_is_still_supported(tmp_path: Path) -> None:
    audio_file = tmp_path / "song.mp3"
    audio_file.write_bytes(b"fake")
    config_file = tmp_path / "discs.json"
    config_file.write_text(
        '{"pack_id":"json_pack","discs":[{"input":"song.mp3","id":"json_disc","title":"JSON Disc"}]}',
        encoding="utf-8",
    )

    config = load_build_config(make_args(config=config_file, no_config=False))

    assert config.pack_id == "json_pack"
    assert config.discs[0].input_file == audio_file


def test_pyproject_tool_table_is_supported(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.music-disc-maker]
pack_id = "pyproject_discs"
""".strip(),
        encoding="utf-8",
    )

    assert load_config_file(pyproject) == {"pack_id": "pyproject_discs"}
    assert find_config_file(tmp_path) == pyproject


def test_missing_disc_configuration_fails_cleanly() -> None:
    with pytest.raises(ValueError, match="No discs configured"):
        load_build_config(make_args())
