# music-disc-maker

Build scripted Minecraft Bedrock custom music disc add-ons without globally replacing vanilla sound effects.

## Single-disc mode

```bash
music-disc-maker song.mp3 --id whiplash --title "Whiplash!"
```

The CLI also works as a module:

```bash
python -m music_disc_maker song.mp3 --id whiplash --title "Whiplash!"
```

## Config mode

`music_disc_maker.toml`:

```toml
pack_id = "custom_discs"
pack_title = "Custom Music Discs"
namespace = "custom"
output_root = "dist"
dummy_sound_event = "pre_ram.screamer"
server_module_version = "2.8.0-beta"
item_format_version = "1.21.70"
sound_definitions_format_version = "1.20.20"
min_engine_version = [1, 21, 70]
default_comparator_signal = 13
comparator_signal_min = 1
comparator_signal_max = 13
pack_icon_size = 256

[[discs]]
input = "audio/whiplash.mp3"
id = "whiplash"
title = "Whiplash!"
comparator_signal = 13

[[discs]]
input = "audio/doom_banjo.mp3"
id = "doom_banjo"
title = "Doom Banjo"
sound_id = "record.doom_banjo"
comparator_signal = 11
```

Run it:

```bash
music-disc-maker --config music_disc_maker.toml
```

If `--config` is omitted, the tool checks the current directory for common config names such as `music_disc_maker.toml`, `music-disc-maker.toml`, `.music-disc-maker.toml`, JSON equivalents, `discs.json`, and `[tool.music-disc-maker]` / `[tool.music_disc_maker]` in `pyproject.toml`.

CLI arguments override config-file values where applicable. Config-file paths are resolved relative to the config file, not wherever your shell happens to be yelling from.


## Generate a config from audio files

Scan the current directory and create `music_disc_maker.toml`:

```bash
music-disc-maker-config
```

The config generator uses `ffprobe` metadata when available. The generated disc `id` comes from the normalized song title, while the display `title` becomes `Artist - Title` when artist metadata is present. If metadata is missing, filenames like `01 - DJ Stomp - Whiplash! (Official Audio).mp3` are parsed as a fallback, because manually typing that crap is how souls leave bodies.

The metadata scan shows a `tqdm` progress bar by default. Disable it with `--no-progress` when piping logs or being aggressively boring.

Useful options:

```bash
music-disc-maker-config --recursive --overwrite --pack-title "DJ Stomp Discs" --namespace dj
```

Preview without writing:

```bash
music-disc-maker-config --stdout
```

If your files use `Title - Artist.ext` instead of `Artist - Title.ext`:

```bash
music-disc-maker-config --filename-order title-artist --overwrite
```

For a big messy library, use MusicBrainz Picard or beets to fix the tags first, then regenerate the TOML. This tool reads metadata; it does not rewrite your files.

## Testing

```bash
python -m pytest
```

## License

MIT License. See the [LICENSE](LICENSE) file for details.
