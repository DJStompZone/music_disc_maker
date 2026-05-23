from __future__ import annotations

import pytest

from music_disc_maker.validation import clamp_comparator_signal, normalize_local_id, parse_min_engine_version, validate_sound_id


def test_normalize_local_id() -> None:
    assert normalize_local_id("Whip Lash", "id") == "whip_lash"


def test_normalize_local_id_rejects_bad_characters() -> None:
    with pytest.raises(ValueError):
        normalize_local_id("oh/no", "id")


def test_validate_sound_id_allows_namespaced_and_dotted_ids() -> None:
    assert validate_sound_id("custom:record.whiplash") == "custom:record.whiplash"


def test_clamp_comparator_signal() -> None:
    assert clamp_comparator_signal(-10) == 1
    assert clamp_comparator_signal(8) == 8
    assert clamp_comparator_signal(99) == 13


def test_parse_min_engine_version() -> None:
    assert parse_min_engine_version("1.21.70") == [1, 21, 70]
