from __future__ import annotations

import json
import zipfile
from pathlib import Path

from music_disc_maker.models import BuildConfig, DiscInput
from music_disc_maker.pack_builder import ScriptedDiscPackBuilder


def test_builder_writes_expected_pack_files(monkeypatch, tmp_path: Path) -> None:
    input_file = tmp_path / "song.mp3"
    input_file.write_bytes(b"fake")

    def fake_convert_audio(input_file: Path, output_file: Path) -> float:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(b"ogg")
        return 12.5

    monkeypatch.setattr("music_disc_maker.pack_builder.convert_audio", fake_convert_audio)

    config = BuildConfig(
        pack_id="test_discs",
        pack_title="Test Discs",
        namespace="dj",
        output_root=tmp_path,
        pack_icon_size=32,
        discs=[
            DiscInput(
                input_file=input_file,
                disc_id="whiplash",
                title="Whiplash!",
                sound_id="record.whiplash",
                dummy_sound_event="pre_ram.screamer",
                comparator_signal=13,
            )
        ],
    )

    ScriptedDiscPackBuilder(config).build()

    pack_dir = tmp_path / "test_discs_pack"
    item_path = pack_dir / "BP" / "items" / "whiplash.item.json"
    sound_defs_path = pack_dir / "RP" / "sounds" / "sound_definitions.json"
    registry_path = pack_dir / "BP" / "scripts" / "disc_registry.js"
    bp_manifest_path = pack_dir / "BP" / "manifest.json"

    assert item_path.is_file()
    assert sound_defs_path.is_file()
    assert registry_path.is_file()
    assert (pack_dir / "RP" / "pack_icon.png").is_file()
    assert (pack_dir / "BP" / "pack_icon.png").is_file()
    assert (tmp_path / "test_discs.mcaddon").is_file()

    item = json.loads(item_path.read_text(encoding="utf-8"))
    assert item["minecraft:item"]["description"]["identifier"] == "dj:whiplash"
    assert item["minecraft:item"]["components"]["minecraft:record"]["duration"] == 12.5
    assert item["minecraft:item"]["components"]["minecraft:record"]["sound_event"] == "pre_ram.screamer"

    sound_defs = json.loads(sound_defs_path.read_text(encoding="utf-8"))
    assert "record.whiplash" in sound_defs["sound_definitions"]

    registry = registry_path.read_text(encoding="utf-8")
    assert "dj:whiplash" in registry
    assert "durationTicks" in registry
    assert "250" in registry

    manifest = json.loads(bp_manifest_path.read_text(encoding="utf-8"))
    assert any(module.get("type") == "script" for module in manifest["modules"])
    assert any(dep.get("module_name") == "@minecraft/server" for dep in manifest["dependencies"])

    with zipfile.ZipFile(tmp_path / "test_discs.mcaddon") as archive:
        names = set(archive.namelist())

    assert "RP/sounds/sound_definitions.json" in names
    assert "BP/scripts/main.js" in names
