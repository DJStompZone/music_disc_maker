from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from music_disc_maker.models import BuiltDisc

CUSTOM_DISC_LOOT_TABLE = "loot_tables/custom_discs/random_disc.json"
DEFAULT_DISC_POOL_EMPTY_WEIGHT = 19
DEFAULT_DISC_POOL_TABLE_WEIGHT = 1
DEFAULT_LOOT_TARGETS = (
    "simple_dungeon",
    "abandoned_mineshaft",
    "stronghold_corridor",
    "ancient_city",
)

VANILLA_LOOT_TABLES: dict[str, dict[str, Any]] = {
    "simple_dungeon": {
        "pools": [
            {
                "rolls": {"min": 1, "max": 3},
                "entries": [
                    {"type": "item", "name": "minecraft:saddle", "weight": 20},
                    {"type": "item", "name": "minecraft:golden_apple", "weight": 15},
                    {"type": "item", "name": "minecraft:appleEnchanted", "weight": 2},
                    {"type": "item", "name": "minecraft:record_13", "weight": 15},
                    {"type": "item", "name": "minecraft:record_cat", "weight": 15},
                    {"type": "item", "name": "minecraft:record_otherside", "weight": 2},
                    {"type": "item", "name": "minecraft:name_tag", "weight": 20},
                    {"type": "item", "name": "minecraft:horsearmorgold", "weight": 10},
                    {"type": "item", "name": "minecraft:horsearmoriron", "weight": 15},
                    {"type": "item", "name": "minecraft:horsearmordiamond", "weight": 5},
                    {"type": "item", "name": "minecraft:book", "weight": 10, "functions": [{"function": "enchant_randomly"}]},
                ],
            },
            {
                "rolls": {"min": 1, "max": 4},
                "entries": [
                    {"type": "item", "name": "minecraft:iron_ingot", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4}}]},
                    {"type": "item", "name": "minecraft:gold_ingot", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4}}]},
                    {"type": "item", "name": "minecraft:bread", "weight": 20},
                    {"type": "item", "name": "minecraft:wheat", "weight": 20, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4}}]},
                    {"type": "item", "name": "minecraft:bucket", "weight": 10},
                    {"type": "item", "name": "minecraft:redstone", "weight": 15, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4}}]},
                    {"type": "item", "name": "minecraft:coal", "weight": 15, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4}}]},
                    {"type": "item", "name": "minecraft:melon_seeds", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 2, "max": 4}}]},
                    {"type": "item", "name": "minecraft:pumpkin_seeds", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 2, "max": 4}}]},
                    {"type": "item", "name": "minecraft:beetroot_seeds", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 2, "max": 4}}]},
                ],
            },
            {
                "rolls": 3,
                "entries": [
                    {"type": "item", "name": "minecraft:bone", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 1, "max": 8}}]},
                    {"type": "item", "name": "minecraft:gunpowder", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 1, "max": 8}}]},
                    {"type": "item", "name": "minecraft:rotten_flesh", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 1, "max": 8}}]},
                    {"type": "item", "name": "minecraft:string", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 1, "max": 8}}]},
                ],
            },
        ]
    },
    "abandoned_mineshaft": {
        "pools": [
            {
                "rolls": 1,
                "entries": [
                    {"type": "item", "name": "minecraft:golden_apple", "weight": 20},
                    {"type": "item", "name": "minecraft:appleEnchanted", "weight": 1},
                    {"type": "item", "name": "minecraft:name_tag", "weight": 30},
                    {"type": "item", "name": "minecraft:book", "weight": 10, "functions": [{"function": "enchant_randomly"}]},
                    {"type": "item", "name": "minecraft:iron_pickaxe", "weight": 5},
                    {"type": "empty", "weight": 5},
                ],
            },
            {
                "rolls": {"min": 2, "max": 4},
                "entries": [
                    {"type": "item", "name": "minecraft:iron_ingot", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 1, "max": 5}}]},
                    {"type": "item", "name": "minecraft:gold_ingot", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3}}]},
                    {"type": "item", "name": "minecraft:redstone", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 4, "max": 9}}]},
                    {"type": "item", "name": "minecraft:dye", "weight": 5, "functions": [{"function": "set_data", "data": 4}, {"function": "set_count", "count": {"min": 4, "max": 9}}]},
                    {"type": "item", "name": "minecraft:diamond", "weight": 3, "functions": [{"function": "set_count", "count": {"min": 1, "max": 2}}]},
                    {"type": "item", "name": "minecraft:coal", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 3, "max": 8}}]},
                    {"type": "item", "name": "minecraft:bread", "weight": 15, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3}}]},
                    {"type": "item", "name": "minecraft:melon_seeds", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 2, "max": 4}}]},
                    {"type": "item", "name": "minecraft:pumpkin_seeds", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 2, "max": 4}}]},
                    {"type": "item", "name": "minecraft:beetroot_seeds", "weight": 10, "functions": [{"function": "set_count", "count": {"min": 2, "max": 4}}]},
                    {"type": "item", "name": "minecraft:glow_berries", "weight": 15, "functions": [{"function": "set_count", "count": {"min": 3, "max": 6}}]},
                ],
            },
            {
                "rolls": 3,
                "entries": [
                    {"type": "item", "name": "minecraft:rail", "weight": 20, "functions": [{"function": "set_count", "count": {"min": 4, "max": 8}}]},
                    {"type": "item", "name": "minecraft:golden_rail", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4}}]},
                    {"type": "item", "name": "minecraft:detector_rail", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4}}]},
                    {"type": "item", "name": "minecraft:activator_rail", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4}}]},
                    {"type": "item", "name": "minecraft:torch", "weight": 15, "functions": [{"function": "set_count", "count": {"min": 1, "max": 16}}]},
                ],
            },
        ]
    },
    "stronghold_corridor": {
        "pools": [
            {
                "rolls": {"min": 2, "max": 3},
                "entries": [
                    {"type": "item", "name": "minecraft:ender_pearl", "weight": 50},
                    {"type": "item", "name": "minecraft:emerald", "weight": 15, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3}}]},
                    {"type": "item", "name": "minecraft:diamond", "weight": 15, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3}}]},
                    {"type": "item", "name": "minecraft:iron_ingot", "weight": 50, "functions": [{"function": "set_count", "count": {"min": 1, "max": 5}}]},
                    {"type": "item", "name": "minecraft:gold_ingot", "weight": 25, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3}}]},
                    {"type": "item", "name": "minecraft:redstone", "weight": 25, "functions": [{"function": "set_count", "count": {"min": 4, "max": 9}}]},
                    {"type": "item", "name": "minecraft:bread", "weight": 75, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3}}]},
                    {"type": "item", "name": "minecraft:apple", "weight": 75, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3}}]},
                    {"type": "item", "name": "minecraft:iron_pickaxe", "weight": 25},
                    {"type": "item", "name": "minecraft:iron_sword", "weight": 25},
                    {"type": "item", "name": "minecraft:iron_chestplate", "weight": 25},
                    {"type": "item", "name": "minecraft:iron_helmet", "weight": 25},
                    {"type": "item", "name": "minecraft:iron_leggings", "weight": 25},
                    {"type": "item", "name": "minecraft:iron_boots", "weight": 25},
                    {"type": "item", "name": "minecraft:golden_apple", "weight": 5},
                    {"type": "item", "name": "minecraft:saddle", "weight": 5},
                    {"type": "item", "name": "minecraft:horsearmoriron", "weight": 5},
                    {"type": "item", "name": "minecraft:horsearmorgold", "weight": 5},
                    {"type": "item", "name": "minecraft:horsearmordiamond", "weight": 5},
                    {"type": "item", "name": "minecraft:record_otherside", "weight": 5},
                    {"type": "item", "name": "minecraft:book", "weight": 6, "functions": [{"function": "enchant_with_levels", "levels": 30, "treasure": True}]},
                ],
            }
        ]
    },
    "ancient_city": {
        "pools": [
            {
                "rolls": {"min": 5, "max": 10.0},
                "bonus_rolls": 0,
                "entries": [
                    {"type": "item", "name": "minecraft:enchanted_golden_apple", "weight": 1, "functions": [{"function": "set_count", "count": {"min": 1, "max": 2.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:music_disc_otherside", "weight": 1},
                    {"type": "item", "name": "minecraft:compass", "weight": 2, "functions": [{"function": "set_count", "count": 1, "add": False}]},
                    {"type": "item", "name": "minecraft:sculk_catalyst", "weight": 2, "functions": [{"function": "set_count", "count": {"min": 1, "max": 2.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:name_tag", "weight": 2},
                    {"type": "item", "name": "minecraft:diamond_hoe", "weight": 2, "functions": [{"function": "set_count", "count": 1, "add": False}, {"function": "set_damage", "damage": {"min": 0.8, "max": 1.0}, "add": False}, {"function": "enchant_with_levels", "levels": {"min": 30, "max": 50.0}, "treasure": True}]},
                    {"type": "item", "name": "minecraft:lead", "weight": 2, "functions": [{"function": "set_count", "count": 1, "add": False}]},
                    {"type": "item", "name": "minecraft:diamond_horse_armor", "weight": 2, "functions": [{"function": "set_count", "count": 1, "add": False}]},
                    {"type": "item", "name": "minecraft:saddle", "weight": 2, "functions": [{"function": "set_count", "count": 1, "add": False}]},
                    {"type": "item", "name": "minecraft:music_disc_13", "weight": 2},
                    {"type": "item", "name": "minecraft:music_disc_cat", "weight": 2},
                    {"type": "item", "name": "minecraft:diamond_leggings", "weight": 2, "functions": [{"function": "enchant_with_levels", "levels": {"min": 30, "max": 50.0}, "treasure": True}]},
                    {"type": "item", "name": "minecraft:book", "weight": 3, "functions": [{"function": "specific_enchants", "enchants": [{"id": "swift_sneak", "level": [1, 3]}]}]},
                    {"type": "item", "name": "minecraft:sculk", "weight": 3, "functions": [{"function": "set_count", "count": {"min": 4, "max": 10.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:sculk_sensor", "weight": 3, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:candle", "weight": 3, "functions": [{"function": "set_count", "count": {"min": 1, "max": 4.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:amethyst_shard", "weight": 3, "functions": [{"function": "set_count", "count": {"min": 1, "max": 15.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:experience_bottle", "weight": 3, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:glow_berries", "weight": 3, "functions": [{"function": "set_count", "count": {"min": 1, "max": 15.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:iron_leggings", "weight": 3, "functions": [{"function": "enchant_with_levels", "levels": {"min": 20, "max": 39.0}, "treasure": True}]},
                    {"type": "item", "name": "minecraft:echo_shard", "weight": 4, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:disc_fragment_5", "weight": 4, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:potion", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 1, "max": 3.0}, "add": False}, {"function": "set_data", "data": 30}]},
                    {"type": "item", "name": "minecraft:book", "weight": 5, "functions": [{"function": "enchant_randomly"}]},
                    {"type": "item", "name": "minecraft:book", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 3, "max": 10.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:bone", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 1, "max": 15.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:soul_torch", "weight": 5, "functions": [{"function": "set_count", "count": {"min": 1, "max": 15.0}, "add": False}]},
                    {"type": "item", "name": "minecraft:coal", "weight": 7, "functions": [{"function": "set_count", "count": {"min": 6, "max": 15.0}, "add": False}]},
                ],
            }
        ]
    },
}


@dataclass(frozen=True)
class LootTarget:
    """One vanilla chest loot table target to patch."""

    name: str
    path: str


def default_loot_targets() -> tuple[LootTarget, ...]:
    """Return the default vanilla chest loot targets."""
    return tuple(LootTarget(name=name, path=f"chests/{name}.json") for name in DEFAULT_LOOT_TARGETS)


def build_random_disc_loot_table(discs: list[BuiltDisc]) -> dict[str, Any]:
    """Build the shared loot table that chooses one generated custom disc."""
    return {
        "pools": [
            {
                "rolls": 1,
                "entries": [
                    {"type": "item", "name": disc.item_id, "weight": 1}
                    for disc in discs
                ],
            }
        ]
    }


def build_custom_disc_reference_pool() -> dict[str, Any]:
    """Build the low-probability pool appended to each vanilla target."""
    return {
        "rolls": 1,
        "entries": [
            {"type": "empty", "weight": DEFAULT_DISC_POOL_EMPTY_WEIGHT},
            {"type": "loot_table", "name": CUSTOM_DISC_LOOT_TABLE, "weight": DEFAULT_DISC_POOL_TABLE_WEIGHT},
        ],
    }


def build_patched_loot_table(target_name: str) -> dict[str, Any]:
    """Return a vanilla chest loot table with the custom disc pool appended."""
    if target_name not in VANILLA_LOOT_TABLES:
        raise ValueError(f"Unsupported loot target: {target_name}")

    table = copy.deepcopy(VANILLA_LOOT_TABLES[target_name])
    table.setdefault("pools", []).append(build_custom_disc_reference_pool())
    return table
