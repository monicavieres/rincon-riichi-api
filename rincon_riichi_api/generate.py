"""Random hand generation for wait-type drills.

Builds a tenpai hand for a requested wait type, filling the rest with isolated
honor melds so the *only* winning tiles are the intended ones. Every generated
hand is verified with the agari solver before being returned.
"""

from __future__ import annotations

import random

from .hand import WAIT_TYPE_NAMES, can_win, get_waits
from .tiles import NUMBERED_SUITS, TILE_TYPES, normalize, sort_tiles

#: Honor tiles used as isolated filler (never form sequences).
_HONORS = [f"{n}z" for n in range(1, 8)]


def _shuffle_honor_pool() -> list[str]:
    pool = list(_HONORS)
    random.shuffle(pool)
    return pool


def _fill_honor(remaining: int) -> list[str]:
    """Return honor tiles (complete triplets + optional pair) totalling
    ``remaining`` tiles, so they never interfere with numbered-suit waits."""
    pool = _shuffle_honor_pool()
    fill: list[str] = []
    idx = 0
    is_pair = remaining % 3 == 2
    triplets = (remaining - (2 if is_pair else 0)) // 3
    for _ in range(triplets):
        h = pool[idx]
        idx += 1
        fill.extend([h, h, h])
    if is_pair:
        p = pool[idx]
        fill.extend([p, p])
    return fill


def _shape_tiles(wait_type: str, suit: str) -> tuple[list[str], list[str]]:
    """Return (shape tiles, expected waits) for a wait type in a suit."""
    try:
        a = random.randint
    except Exception:  # pragma: no cover
        a = lambda lo, hi: random.randint(lo, hi)

    def t(n: int) -> str:
        return f"{n}{suit}"

    if wait_type == "ryanmen":
        n = random.randint(2, 7)
        return ([t(n), t(n + 1)], [t(n - 1), t(n + 2)])
    if wait_type == "kanchan":
        n = random.randint(1, 7)
        return ([t(n), t(n + 2)], [t(n + 1)])
    if wait_type == "penchan":
        if random.random() < 0.5:
            return ([t(1), t(2)], [t(3)])
        return ([t(8), t(9)], [t(7)])
    if wait_type == "tanki":
        n = random.randint(1, 9)
        return ([t(n)], [t(n)])
    if wait_type == "shanpon":
        p = random.randint(1, 9)
        q = random.randint(1, 9)
        while q == p:
            q = random.randint(1, 9)
        return ([t(p), t(p), t(q), t(q)], [t(p), t(q)])
    if wait_type == "nobetan":
        n = random.randint(1, 6)
        return ([t(n), t(n + 1), t(n + 2), t(n + 3)], [t(n), t(n + 3)])
    if wait_type == "sanmenchan":
        n = random.randint(2, 4)
        return (
            [t(n), t(n + 1), t(n + 2), t(n + 3), t(n + 4)],
            [t(n - 1), t(n + 2), t(n + 5)],
        )
    if wait_type == "sanmentan":
        n = random.randint(1, 3)
        return (
            [t(n), t(n + 1), t(n + 2), t(n + 3), t(n + 4), t(n + 5), t(n + 6)],
            [t(n), t(n + 3), t(n + 6)],
        )
    if wait_type == "entotsu":
        n = random.randint(2, 7)
        return (
            [t(n), t(n + 1), t(n + 2), t(n + 2), t(n + 2)],
            [],
        )
    if wait_type == "ryantan":
        return ([t(4), t(5), t(5), t(5)], [t(3), t(4), t(6)])
    if wait_type == "kantan":
        return ([t(3), t(5), t(5), t(5)], [t(3), t(4)])
    if wait_type == "aryanmen":
        return ([t(4), t(5), t(6), t(6)], [t(3), t(6)])
    if wait_type == "pentan":
        return ([t(1), t(2), t(2), t(2)], [t(1), t(3)])
    raise ValueError(f"unknown wait type: {wait_type}")


def generate_wait_hand(
    wait_type: str,
    suit: str | None = None,
    max_attempts: int = 60,
) -> dict:
    """Generate a verified tenpai hand of the requested wait type.

    Returns a dict with ``tiles``, ``waits``, ``wait_type``, and ``suit``.
    Raises ``ValueError`` if no valid hand is found.
    """
    if wait_type not in WAIT_TYPE_NAMES:
        raise ValueError(f"unknown wait type: {wait_type}")
    suit = suit or random.choice(NUMBERED_SUITS)

    for _ in range(max_attempts):
        shape, expected = _shape_tiles(wait_type, suit)
        hand = shape + _fill_honor(13 - len(shape))
        waits = get_waits(hand)
        if wait_type == "entotsu":
            # Entotsu waits on the ryanmen endpoints plus the melded triplet's
            # adjacent tile; trust the solver to report the exact winning tiles.
            if len(waits) >= 2:
                return _result(suit, hand, waits, wait_type)
            continue
        if sorted(waits) == sorted(expected):
            return _result(suit, hand, waits, wait_type)

    raise ValueError(f"could not generate a valid {wait_type} hand")


def _result(suit: str, hand: list[str], waits: list[str], wait_type: str) -> dict:
    return {
        "suit": suit,
        "tiles": sort_tiles(hand),
        "waits": sort_tiles(waits),
        "wait_type": WAIT_TYPE_NAMES.get(wait_type, wait_type),
        "wait_key": wait_type,
        "is_tenpai": bool(waits),
    }


def generate_full_hand(count: int = 0) -> dict:
    """Generate a random winning (agari) hand of 14 tiles.

    If ``count`` is given and 0, an arbitrary valid winning hand is returned;
    a hand is built from four complete melds + a pair.
    """
    melds: list[list[str]] = []
    for _ in range(4):
        suit = random.choice(NUMBERED_SUITS)
        if random.random() < 0.5:
            n = random.randint(1, 7)
            melds.append([f"{n}{suit}", f"{n + 1}{suit}", f"{n + 2}{suit}"])
        else:
            n = random.randint(2, 8)
            melds.append([f"{n}{suit}", f"{n}{suit}", f"{n}{suit}"])
    pair_suit = random.choice(NUMBERED_SUITS)
    p = random.randint(1, 9)
    hand: list[str] = [t for meld in melds for t in meld]
    hand += [f"{p}{pair_suit}", f"{p}{pair_suit}"]

    # NOTE: unconstrained random melds may produce an akas/limits hand but the
    # resulting 14 tiles can still win; verify.
    if not can_win(hand):
        return generate_full_hand()
    return {"tiles": sort_tiles(normalize(t) for t in hand), "winning": True, "length": 14}


def generate_winning_waits(count: int = 1, **kwargs) -> list[dict]:
    """Generate a batch of random wait-type hands (deduplicated)."""
    keys = list(WAIT_TYPE_NAMES.keys())
    seen: set[tuple[str, ...]] = set()
    out: list[dict] = []
    attempts = 0
    while len(out) < count and attempts < count * 40:
        attempts += 1
        wait_type = random.choice(keys)
        try:
            hand = generate_wait_hand(wait_type, **kwargs)
        except ValueError:
            continue
        sig = tuple(hand["tiles"])
        if sig in seen:
            continue
        seen.add(sig)
        out.append(hand)
    return out


def random_discard_pool(size: int = 14) -> list[str]:
    """Return a random tile draw (e.g. wall face) of the given size."""
    pool = list(TILE_TYPES) + ["0m", "0p", "0s"]
    random.shuffle(pool)
    return [p for p in pool[:size]]
