from __future__ import annotations

from music_disc_maker.loader import load_build_config
from music_disc_maker.pack_builder import ScriptedDiscPackBuilder
from music_disc_maker.parser import parse_args


def main() -> int:
    """Run the pack generator."""
    args = parse_args()
    config = load_build_config(args)
    builder = ScriptedDiscPackBuilder(config)
    builder.build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
