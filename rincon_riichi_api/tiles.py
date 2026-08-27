"""Tile representation and validation for Riichi Mahjong.

Tiles are encoded as strings like ``"3m"``, ``"7p"``, ``"9s"``, ``"1z"``.
``0m`` / ``0p`` / ``0s`` represent the aka (red five) versions.
"""

from __future__ import annotations

import re

SUITS = ("m", "p", "s", "z")
NUMBERED_SUITS = ("m", "p", "s")
HONOR_SUITS = ("z",)

#: Standard numbered + honor tile types (34 unique tile kinds).
TILE_TYPES = tuple(f"{n}{s}" for s in NUMBERED_SUITS for n in range(1, 10)) + tuple(
    f"{n}z" for n in range(1, 8)
)

#: Aka (red five) tile ids.
AKA_TILES = {"0m", "0p", "0s"}

#: The four wind ranks (in order).
WINDS = ("East", "South", "West", "North")

_TILE_RE = re.compile(r"^[0-9][mpsz]$")


def is_valid_tile(tile: str) -> bool:
    """Return True if ``tile`` is a well-formed tile id."""
    if not isinstance(tile, str) or not _TILE_RE.match(tile):
        return False
    number = int(tile[0])
    suit = tile[1]
    if suit == "z":
        return 1 <= number <= 7
    return True


def is_aka(tile: str) -> bool:
    """Return True if ``tile`` is an aka (red five)."""
    return tile in AKA_TILES


def normalize(tile: str) -> str:
    """Return the canonical id for a tile, mapping aka zeros to their base five."""
    if tile in AKA_TILES:
        return f"5{tile[1]}"
    return tile


def sort_tiles(tiles: list[str]) -> list[str]:
    """Sort tiles by suit (m, p, s, z) then number."""
    order = {"m": 0, "p": 1, "s": 2, "z": 3}

    def key(tile: str):
        suit = tile[1]
        number = 5 if tile[0] == "0" else int(tile[0])
        return (order.get(suit, 4), number)

    return sorted(tiles, key=key)


def count_tiles(tiles: list[str]) -> dict[str, int]:
    """Return a dict mapping tile id -> copy count."""
    counts: dict[str, int] = {}
    for tile in tiles:
        counts[tile] = counts.get(tile, 0) + 1
    return counts
