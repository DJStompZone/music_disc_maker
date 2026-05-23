from __future__ import annotations

import json
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path
from typing import Any


def generate_uuid() -> str:
    """Return a new UUID string for Minecraft pack manifests."""
    return str(uuid.uuid4())


def clean_output_dir(path: Path) -> None:
    """Remove an existing generated pack directory before rebuilding it."""
    if path.exists():
        shutil.rmtree(path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write stable, readable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text, creating parent directories first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command and raise a useful error when it fails."""
    result = subprocess.run(args, check=False, capture_output=True, text=True)

    if result.returncode != 0:
        cmd = " ".join(args)
        raise RuntimeError(f"Command failed: {cmd}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")

    return result


def zip_directory(source_dir: Path, output_file: Path) -> None:
    """Create a zip-compatible Minecraft pack from a directory."""
    if output_file.exists():
        output_file.unlink()

    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir))


def create_mcaddon(pack_dir: Path, output_file: Path) -> None:
    """Create a single importable .mcaddon containing both generated packs."""
    if output_file.exists():
        output_file.unlink()

    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(pack_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(pack_dir))
