from __future__ import annotations

from pathlib import Path
from typing import Any

from music_disc_maker.io_utils import generate_uuid, write_json


def build_manifest(
    name: str,
    description: str,
    module_type: str,
    pack_uuid: str,
    min_engine_version: list[int],
    dependency_uuid: str | None = None,
    script_module: bool = False,
    server_module_version: str | None = None,
) -> dict[str, Any]:
    """Build a Minecraft pack manifest object."""
    modules: list[dict[str, Any]] = [
        {
            "type": module_type,
            "uuid": generate_uuid(),
            "version": [1, 0, 0],
        }
    ]

    if script_module:
        modules.append({
            "type": "script",
            "language": "javascript",
            "uuid": generate_uuid(),
            "entry": "scripts/main.js",
            "version": [1, 0, 0],
        })

    manifest: dict[str, Any] = {
        "format_version": 2,
        "header": {
            "name": name,
            "description": description,
            "uuid": pack_uuid,
            "version": [1, 0, 0],
            "min_engine_version": min_engine_version,
        },
        "modules": modules,
    }

    dependencies: list[dict[str, Any]] = []

    if script_module and server_module_version:
        dependencies.append({
            "module_name": "@minecraft/server",
            "version": server_module_version,
        })

    if dependency_uuid:
        dependencies.append({
            "uuid": dependency_uuid,
            "version": [1, 0, 0],
        })

    if dependencies:
        manifest["dependencies"] = dependencies

    return manifest


def write_manifest(
    path: Path,
    name: str,
    description: str,
    module_type: str,
    pack_uuid: str,
    min_engine_version: list[int],
    dependency_uuid: str | None = None,
    script_module: bool = False,
    server_module_version: str | None = None,
) -> None:
    """Write a Minecraft pack manifest."""
    write_json(
        path / "manifest.json",
        build_manifest(
            name=name,
            description=description,
            module_type=module_type,
            pack_uuid=pack_uuid,
            min_engine_version=min_engine_version,
            dependency_uuid=dependency_uuid,
            script_module=script_module,
            server_module_version=server_module_version,
        ),
    )
