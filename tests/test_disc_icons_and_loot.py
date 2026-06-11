from __future__ import annotations

import json
import zipfile
from pathlib import Path

from PIL import Image

from music_disc_maker.disc_icons import render_disc_from_key
from music_disc_maker.loader import load_build_config
from music_disc_maker.loot import build_patched_loot_table, build_random_disc_loot_table
from music_disc_maker.models import BuiltDisc
from music_disc_maker.pack_builder import ScriptedDiscPackBuilder
from music_disc_maker.parser import parse_args


def test_bundled_disc_icon_is_transparent_and_deterministic() -> None:
    first = render_disc_from_key("custom:whiplash:Whiplash!")
    second = render_disc_from_key("custom:whiplash:Whiplash!")

    assert first.size == (16, 16)
    assert first.mode == "RGBA"
    assert first.tobytes() == second.tobytes()
    assert first.getpixel((15, 15))[3] == 0


def test_random_disc_loot_table_contains_custom_items() -> None:
    table = build_random_disc_loot_table([
        BuiltDisc(
            item_id="custom:whiplash",
            disc_id="whiplash",
            title="Whiplash!",
            sound_id="record.whiplash",
            dummy_sound_event="pre_ram.screamer",
            comparator_signal=13,
            duration_seconds=120.0,
            duration_ticks=2400,
        )
    ])

    assert table["pools"][0]["entries"][0]["name"] == "custom:whiplash"


def test_patched_vanilla_loot_table_keeps_vanilla_and_adds_custom_reference() -> None:
    table = build_patched_loot_table("simple_dungeon")
    names = [entry.get("name") for pool in table["pools"] for entry in pool["entries"]]

    assert "minecraft:saddle" in names
    assert "loot_tables/custom_discs/random_disc.json" in names


def test_builder_writes_procedural_icons_and_loot_tables(tmp_path: Path, monkeypatch) -> None:
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"not really audio")
    config_file = tmp_path / "music_disc_maker.toml"
    config_file.write_text(
        "\n".join([
            'pack_id = "test_discs"',
            'pack_title = "Test Discs"',
            'namespace = "custom"',
            'output_root = "dist"',
            'loot_enabled = true',
            "",
            "[[discs]]",
            'input = "song.mp3"',
            'id = "whiplash"',
            'title = "Whiplash!"',
        ]),
        encoding="utf-8",
    )

    def fake_convert_audio(input_file: Path, output_file: Path) -> float:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(b"ogg")
        return 30.0

    monkeypatch.setattr("music_disc_maker.pack_builder.convert_audio", fake_convert_audio)

    args = parse_args(["--config", str(config_file)])
    config = load_build_config(args)
    ScriptedDiscPackBuilder(config).build()

    pack_dir = tmp_path / "dist" / "test_discs_pack"
    icon = Image.open(pack_dir / "RP" / "textures" / "items" / "whiplash.png").convert("RGBA")
    random_disc = json.loads((pack_dir / "BP" / "loot_tables" / "custom_discs" / "random_disc.json").read_text(encoding="utf-8"))
    dungeon = json.loads((pack_dir / "BP" / "loot_tables" / "chests" / "simple_dungeon.json").read_text(encoding="utf-8"))

    assert icon.size == (16, 16)
    assert random_disc["pools"][0]["entries"][0]["name"] == "custom:whiplash"
    assert dungeon["pools"][-1]["entries"][-1]["name"] == "loot_tables/custom_discs/random_disc.json"
    assert (tmp_path / "dist" / "test_discs.mcaddon").exists()
