"""Hand engine: agari validation, tenpai, waits, and wait classification.

A hand is a list of tile ids (strings like ``"3m"``). A winning hand (agari)
is either four melds + one pair (regular), chiitoitsu (seven pairs), or
kokushi musou (thirteen orphans).
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from .tiles import (
    AKA_TILES,
    NUMBERED_SUITS,
    TILE_TYPES,
    is_valid_tile,
    normalize,
    sort_tiles,
)

#: Wait type display names (Spanish-friendly romaji), ordered for stable output.
WAIT_TYPE_NAMES = {
    "ryanmen": "Ryanmen",
    "kanchan": "Kanchan",
    "penchan": "Penchan",
    "tanki": "Tanki",
    "shanpon": "Shanpon",
    "nobetan": "Nobetan",
    "sanmenchan": "Sanmenchan",
    "sanmentan": "Sanmentan",
    "entotsu": "Entotsu",
    "ryantan": "Ryantan",
    "kantan": "Kantan",
    "aryanmen": "Aryanmen",
    "pentan": "Pentan",
}


# ----------------------------------------------------------------------------
# Agari validation
# ----------------------------------------------------------------------------
def _standard_win_counter(counts: Counter) -> bool:
    """Can the counter be decomposed into four melds + one pair (regular hand)?"""
    keys = list(counts.keys())

    def helper(counter: Counter) -> bool:
        if not counter:
            return True
        for tile in list(counter):
            if counter[tile] >= 3:
                counter[tile] -= 3
                if counter[tile] == 0:
                    del counter[tile]
                ok = helper(counter)
                counter[tile] = counter.get(tile, 0) + 3
                if ok:
                    return True
        for tile in list(counter):
            if tile in AKA_TILES:
                continue
            suit = tile[1]
            if suit == "z":
                continue
            number = int(tile[0])
            seq = (f"{number}{suit}", f"{number + 1}{suit}", f"{number + 2}{suit}")
            if all(counter[s] > 0 for s in seq):
                for s in seq:
                    counter[s] -= 1
                    if counter[s] == 0:
                        del counter[s]
                ok = helper(counter)
                for s in seq:
                    counter[s] = counter.get(s, 0) + 1
                if ok:
                    return True
        return False

    for pair_tile in keys:
        if counts[pair_tile] >= 2:
            counter = Counter(counts)
            counter[pair_tile] -= 2
            if counter[pair_tile] == 0:
                del counter[pair_tile]
            if helper(counter):
                return True
    return False


def _is_chiitoitsu(counts: Counter) -> bool:
    if sum(counts.values()) != 14:
        return False
    return len(counts) == 7 and all(v == 2 for v in counts.values())


def _orphan_ids() -> set[str]:
    return {f"{n}{s}" for s in NUMBERED_SUITS for n in (1, 9)} | {
        f"{n}z" for n in range(1, 8)
    }


def _is_kokushi(counts: Counter) -> bool:
    if sum(counts.values()) != 14:
        return False
    if set(counts.keys()) != _orphan_ids():
        return False
    return all(v in (1, 2) for v in counts.values())


def _win_counts(counts: Counter) -> bool:
    total = sum(counts.values())
    if total == 14 and _is_chiitoitsu(counts):
        return True
    if total == 14 and _is_kokushi(counts):
        return True
    if total % 3 != 2:
        return False
    return _standard_win_counter(counts)


def can_win(tiles: Iterable[str]) -> bool:
    """Return True if the tiles form a legal winning hand (14 tiles)."""
    normalized = [normalize(t) for t in tiles]
    _assert_valid(normalized)
    counts = Counter(normalized)
    return _win_counts(counts)


# ----------------------------------------------------------------------------
# Tenpai + waits
# ----------------------------------------------------------------------------
def is_tenpai(tiles: Iterable[str]) -> bool:
    """Return True if the hand (13 tiles) is one tile away from winning."""
    normalized = [normalize(t) for t in tiles]
    if len(normalized) != 13:
        return False
    return bool(get_waits(normalized))


def get_waits(tiles: Iterable[str]) -> list[str]:
    """Return the sorted winning tiles that complete a (tenpai) hand."""
    normalized = [normalize(t) for t in tiles]
    _assert_valid(normalized)
    counts = Counter(normalized)
    waits = []
    for tile in TILE_TYPES:
        if counts[tile] >= 4:
            continue
        candidate = counts.copy()
        candidate[tile] += 1
        if _win_counts(candidate):
            waits.append(tile)
    return sort_tiles(waits)


def _assert_valid(tiles: list[str]) -> None:
    if not all(is_valid_tile(t) for t in tiles):
        raise ValueError("hand contains an invalid tile")


# ----------------------------------------------------------------------------
# Wait classification
# ----------------------------------------------------------------------------
#: Simple numbered-suit shape -> wait-type templates. Each template maps a
#: sorted tuple of counts to the wait type it produces.
def classify_wait(hand: list[str]) -> str:
    """Name the wait of a 13-tile tenpai hand (best-effort).

    Falls back to ``"complex"`` for multi-shaped/unrecognised waits; the
    generator endpoint always names its own wait type directly.
    """
    normalized = [normalize(t) for t in hand]
    waits = get_waits(normalized)
    if not waits:
        return "complex"
    if len(waits) == 1:
        return _classify_single(waits, normalized)
    if len(waits) == 2:
        return _classify_two(waits, normalized)
    if len(waits) == 3:
        return _classify_three(waits, normalized)
    return "complex"


def _classify_single(waits: list[str], hand: list[str]) -> str:
    wait = normalize(waits[0])
    n = int(wait[0])
    suit = wait[1]
    counts = Counter(hand)

    # tanki: the waited tile is a lone pair candidate (a tile already in hand
    # that would become the pair). If the wait tile itself appears in the hand.
    hand_counts = Counter([normalize(t) for t in hand])
    if hand_counts[wait] >= 1:
        # could be tanki, but check an edge/hole shape first.
        pass

    if suit != "z":
        suit_nums = sorted({int(t[0]) for t in hand if t[1] == suit})
        # kanchan: hole a,a+2 -> wait a+1 (tiles on both sides of the wait)
        if (n - 1 in suit_nums and n + 1 in suit_nums):
            return "Kanchan"
        # penchan low: 12 -> wait 3 ; penchan high: 89 -> wait 7
        if n == 3 and {1, 2}.issubset(suit_nums):
            return "Penchan"
        if n == 7 and {8, 9}.issubset(suit_nums):
            return "Penchan"
        if (n - 1 in suit_nums and n - 2 in suit_nums):
            return "Penchan"
        if (n + 1 in suit_nums and n + 2 in suit_nums):
            return "Penchan"

    return "Tanki"


def _all_numbered(hand: list[str]) -> list[int]:
    return [int(t[0]) for t in hand if t[1] in NUMBERED_SUITS]


def _wait_numbers(tiles: list[str]) -> tuple[set[int], set[str]]:
    numbers = set()
    suits = set()
    for t in tiles:
        numbers.add(int(t[0]))
        suits.add(t[1])
    return numbers, suits


def _classify_two(waits: list[str], hand: list[str]) -> str:
    nums, suits = _wait_numbers(waits)
    if len(suits) > 1:
        return "complex"
    # shanpon: two waits that are the two pair-tiles.
    counts = Counter(hand)
    pair_tiles = {normalize(t) for t, c in counts.items() if c == 2}
    if pair_tiles == set(waits):
        return "Shanpon"
    ordered = sorted(nums)
    if len(ordered) != 2:
        return "complex"
    gap = ordered[1] - ordered[0]

    # Look at the actual shape of the suit that produces the wait.
    suit = next(iter(suits))
    suit_nums = sorted({int(t[0]) for t in hand if t[1] == suit})
    run_len = _longest_run(suit_nums)

    if gap == 1:
        return "Ryanmen"
    if gap == 2:
        return "Kanchan"
    if gap == 3:
        # ryanmen (2-tile shape 23 -> waits 1,4) vs nobetan (4-run 2345 -> waits 2,5)
        if run_len >= 4:
            return "Nobetan"
        return "Ryanmen"
    return "complex"


def _longest_run(nums: list[int]) -> int:
    best = 1
    cur = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            cur += 1
        else:
            best = max(best, cur)
            cur = 1
    return max(best, cur)


def _classify_three(waits: list[str], hand: list[str]) -> str:
    nums, suits = _wait_numbers(waits)
    if len(suits) > 1:
        return "complex"
    ordered = sorted(nums)
    # sanmenchan: 3 waits spaced by 3 (1-4-7, 2-5-8, 3-6-9)
    if len(ordered) == 3 and ordered[1] - ordered[0] == 3 and ordered[2] - ordered[1] == 3:
        # Could be sanmenchan OR sanmentan; check for a 7-run vs 5-run in the hand.
        suit_nums = sorted(set(_all_numbered(hand)))
        if _has_run(suit_nums, 7):
            return "Sanmentan"
        return "Sanmenchan"
    return "complex"


def _has_run(nums: list[int], length: int) -> bool:
    for i in range(len(nums) - length + 1):
        window = nums[i : i + length]
        if window == list(range(window[0], window[0] + length)):
            return True
    return False


# ----------------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------------
def wait_info(hand: list[str]) -> dict:
    """Return a structured description of the hand's wait."""
    normalized = [normalize(t) for t in hand]
    waits = get_waits(normalized)
    return {
        "tiles": sort_tiles(normalized),
        "waits": waits,
        "is_tenpai": bool(waits),
        "wait_type": classify_wait(normalized),
    }


# ----------------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------------
def wait_info(hand: list[str]) -> dict:
    """Return a structured description of the hand's wait."""
    normalized = [normalize(t) for t in hand]
    waits = get_waits(normalized)
    return {
        "tiles": sort_tiles(normalized),
        "waits": waits,
        "is_tenpai": bool(waits),
        "wait_type": classify_wait(normalized),
    }
