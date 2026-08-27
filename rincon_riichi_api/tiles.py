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


def max_copies(tiles: list[str]) -> int:
    """Return the number of copies of the most frequent tile in ``tiles``."""
    counts = count_tiles(tiles)
    return max(counts.values(), default=0)


def assert_at_most_four(tiles: list[str]) -> list[str]:
    """Raise if any tile appears more than 4 times (physically impossible).

    Returns the input list unchanged so it can be used as an inline guard.
    """
    for tile, count in count_tiles(tiles).items():
        if count > 4:
            raise ValueError(f"more than 4 copies of {tile!r} ({count})")
    return tiles


class TileDeck:
    """A drawable multiset of tiles that never exceeds 4 copies of one tile.

    Backed by a ``Counter`` so generators can draw realistic hands without
    ever violating the physical 4-per-tile limit.
    """

    def __init__(self, with_honors: bool = True, include_aka: bool = True) -> None:
        from .table import SIMPLE_WALL, FULL_WALL  # local: avoid circular import

        base = FULL_WALL if with_honors else SIMPLE_WALL
        self._counter = count_tiles(base)
        if not include_aka:
            # aka (0x) counts as an extra 5x; kept only when include_aka.
            for t in ("0m", "0p", "0s"):
                self._counter.pop(t, None)
        self._total = sum(self._counter.values())

    @property
    def remaining(self) -> int:
        return self._total

    def copy(self) -> "TileDeck":
        new = TileDeck.__new__(TileDeck)
        new._counter = dict(self._counter)
        new._total = self._total
        return new

    def available(self, tile: str) -> int:
        return self._counter.get(tile, 0)

    def take(self, tile: str, count: int = 1) -> bool:
        """Remove ``count`` copies of ``tile``; return False if unavailable."""
        have = self._counter.get(tile, 0)
        if have < count:
            return False
        self._counter[tile] = have - count
        self._total -= count
        return True

    def put(self, tile: str, count: int = 1) -> None:
        self._counter[tile] = self._counter.get(tile, 0) + count
        self._total += count

    def draw(self, tile: str) -> str | None:
        return tile if self.take(tile, 1) else None

    def pop_tile(self) -> str | None:
        """Pop one tile at random (returns None when empty)."""
        import random

        candidates = [t for t, c in self._counter.items() if c > 0]
        if not candidates:
            return None
        tile = random.choice(candidates)
        self.take(tile, 1)
        return tile

    def take_random(self, count: int) -> list[str]:
        """Pop ``count`` random tiles (as many as available)."""
        out: list[str] = []
        for _ in range(count):
            t = self.pop_tile()
            if t is None:
                break
            out.append(t)
        return out

    def remaining_tiles(self) -> list[str]:
        out: list[str] = []
        for tile, c in self._counter.items():
            out.extend([tile] * c)
        return out
