from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from music_disc_maker.audio import convert_audio
from music_disc_maker.generate_js import generate_disc_registry_js, generate_main_js
from music_disc_maker.images import process_icon, write_pack_icon
from music_disc_maker.io_utils import clean_output_dir, create_mcaddon, generate_uuid, write_json, write_text, zip_directory
from music_disc_maker.manifests import write_manifest
from music_disc_maker.models import BuildConfig, BuiltDisc, DiscInput, PackPaths


class ScriptedDiscPackBuilder:
    """Build a Minecraft Bedrock scripted custom music disc add-on."""

    def __init__(self, config: BuildConfig) -> None:
        self.config = config
        self.paths = self.create_paths(config)

    @staticmethod
    def create_paths(config: BuildConfig) -> PackPaths:
        """Create the standard generated pack path layout."""
        pack_dir = config.output_root / f"{config.pack_id}_pack"
        return PackPaths(
            pack_dir=pack_dir,
            rp_path=pack_dir / "RP",
            bp_path=pack_dir / "BP",
        )

    def build(self) -> None:
        """Build the complete scripted music disc add-on."""
        self.validate_inputs()

        clean_output_dir(self.paths.pack_dir)
        self.paths.rp_path.mkdir(parents=True, exist_ok=True)
        self.paths.bp_path.mkdir(parents=True, exist_ok=True)

        rp_uuid = generate_uuid()
        bp_uuid = generate_uuid()
        texture_data: dict[str, dict[str, str]] = {}
        sound_definitions: dict[str, dict[str, Any]] = {}
        built_discs: list[BuiltDisc] = []
        first_icon: Image.Image | None = None

        for disc in self.config.discs:
            built_disc, icon, texture_entry, sound_definition = self.build_disc_assets(disc)
            built_discs.append(built_disc)
            texture_data[disc.disc_id] = texture_entry
            sound_definitions[disc.sound_id] = sound_definition

            if first_icon is None:
                first_icon = icon

        if first_icon is None:
            raise RuntimeError("No discs were generated.")

        write_pack_icon(first_icon, self.paths.rp_path, self.config.pack_icon_size)
        write_pack_icon(first_icon, self.paths.bp_path, self.config.pack_icon_size)

        self.write_resource_pack_files(texture_data, sound_definitions)
        self.write_behavior_pack_files(built_discs)
        self.write_manifests(rp_uuid=rp_uuid, bp_uuid=bp_uuid)

        rp_out = self.config.output_root / f"{self.config.pack_id}_RP.mcpack"
        bp_out = self.config.output_root / f"{self.config.pack_id}_BP.mcpack"
        addon_out = self.config.output_root / f"{self.config.pack_id}.mcaddon"

        zip_directory(self.paths.rp_path, rp_out)
        zip_directory(self.paths.bp_path, bp_out)
        create_mcaddon(self.paths.pack_dir, addon_out)
        self.print_summary(rp_out, bp_out, addon_out, built_discs)

    def validate_inputs(self) -> None:
        """Validate all configured disc inputs."""
        seen_ids: set[str] = set()
        seen_sounds: set[str] = set()

        for disc in self.config.discs:
            if not disc.input_file.exists():
                raise FileNotFoundError(f"Input audio file does not exist: {disc.input_file}")

            if disc.disc_id in seen_ids:
                raise ValueError(f"Duplicate disc id: {disc.disc_id}")

            if disc.sound_id in seen_sounds:
                raise ValueError(f"Duplicate sound id: {disc.sound_id}")

            seen_ids.add(disc.disc_id)
            seen_sounds.add(disc.sound_id)

    def build_disc_assets(self, disc: DiscInput) -> tuple[BuiltDisc, Image.Image, dict[str, str], dict[str, Any]]:
        """Build icon and audio assets for one disc."""
        item_id = f"{self.config.namespace}:{disc.disc_id}"
        sound_path_no_ext = f"sounds/music/game/records/{disc.disc_id}"

        icon = process_icon(
            template_path=Path("record_template.png"),
            output_path=self.paths.rp_path / "textures" / "items" / f"{disc.disc_id}.png",
        )

        duration_seconds = convert_audio(
            input_file=disc.input_file,
            output_file=self.paths.rp_path / f"{sound_path_no_ext}.ogg",
        )

        duration_ticks = max(1, round(duration_seconds * 20))

        built_disc = BuiltDisc(
            item_id=item_id,
            disc_id=disc.disc_id,
            title=disc.title,
            sound_id=disc.sound_id,
            dummy_sound_event=disc.dummy_sound_event,
            comparator_signal=disc.comparator_signal,
            duration_seconds=duration_seconds,
            duration_ticks=duration_ticks,
        )

        texture_entry = {
            "textures": f"textures/items/{disc.disc_id}",
        }

        sound_definition = {
            "category": "record",
            "sounds": [
                {
                    "name": sound_path_no_ext,
                    "stream": True,
                    "volume": 1.0,
                }
            ],
        }

        return built_disc, icon, texture_entry, sound_definition

    def write_resource_pack_files(
        self,
        texture_data: dict[str, dict[str, str]],
        sound_definitions: dict[str, dict[str, Any]],
    ) -> None:
        """Write all resource pack JSON and language files."""
        write_json(self.paths.rp_path / "textures" / "item_texture.json", {
            "resource_pack_name": self.config.pack_id,
            "texture_name": "atlas.items",
            "texture_data": texture_data,
        })

        write_json(self.paths.rp_path / "sounds" / "sound_definitions.json", {
            "format_version": self.config.sound_definitions_format_version,
            "sound_definitions": sound_definitions,
        })

        lang_lines = [
            f"pack.name={self.config.pack_title}",
            "pack.description=Custom scripted music discs",
        ]

        for disc in self.config.discs:
            lang_lines.append(f"item.{self.config.namespace}:{disc.disc_id}.name={disc.title}")

        write_text(self.paths.rp_path / "texts" / "en_US.lang", "\n".join(lang_lines) + "\n")

    def write_behavior_pack_files(self, built_discs: list[BuiltDisc]) -> None:
        """Write behavior pack item definitions and scripts."""
        for disc in built_discs:
            self.write_item_definition(disc)

        write_text(self.paths.bp_path / "scripts" / "disc_registry.js", generate_disc_registry_js(built_discs))
        write_text(self.paths.bp_path / "scripts" / "main.js", generate_main_js())

    def write_item_definition(self, disc: BuiltDisc) -> None:
        """Write one custom disc item definition."""
        write_json(self.paths.bp_path / "items" / f"{disc.disc_id}.item.json", {
            "format_version": self.config.item_format_version,
            "minecraft:item": {
                "description": {
                    "identifier": disc.item_id,
                    "menu_category": {
                        "group": "minecraft:itemGroup.name.record",
                        "category": "items",
                    },
                },
                "components": {
                    "minecraft:icon": disc.disc_id,
                    "minecraft:display_name": {
                        "value": disc.title,
                    },
                    "minecraft:max_stack_size": 1,
                    "minecraft:record": {
                        "sound_event": disc.dummy_sound_event,
                        "duration": disc.duration_seconds,
                        "comparator_signal": disc.comparator_signal,
                    },
                },
            },
        })

    def write_manifests(self, rp_uuid: str, bp_uuid: str) -> None:
        """Write resource and behavior pack manifests."""
        write_manifest(
            path=self.paths.rp_path,
            name=f"{self.config.pack_title} RP",
            description="Custom scripted music disc resources",
            module_type="resources",
            pack_uuid=rp_uuid,
            min_engine_version=self.config.min_engine_version,
        )

        write_manifest(
            path=self.paths.bp_path,
            name=f"{self.config.pack_title} BP",
            description="Custom scripted music disc behavior",
            module_type="data",
            pack_uuid=bp_uuid,
            min_engine_version=self.config.min_engine_version,
            dependency_uuid=rp_uuid,
            script_module=True,
            server_module_version=self.config.server_module_version,
        )

    def print_summary(self, rp_out: Path, bp_out: Path, addon_out: Path, built_discs: list[BuiltDisc]) -> None:
        """Print a compact build summary."""
        print(f"Created: {rp_out}")
        print(f"Created: {bp_out}")
        print(f"Created: {addon_out}")
        print(f"Script module: @minecraft/server {self.config.server_module_version}")
        print("Generated discs:")

        for disc in built_discs:
            print(f"  {disc.item_id} -> {disc.sound_id} ({disc.duration_seconds}s)")
            print(f"    Test sound: /playsound {disc.sound_id} @s")
            print(f"    Give item: /give @s {disc.item_id}")
