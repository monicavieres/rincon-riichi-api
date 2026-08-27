"""Furiten drill generation: a full four-player table snapshot.

The subject (one seat) has a tenpai concealed hand. Each of the four players
has a discard pond (in real play shape). The drill asks: *is the subject in
furiten?* — i.e. does any tile needed to win already sit in the subject's *own*
discards?

Calls (pon / kan / chi) are modelled as exposed melds that a player made on a
tile discarded by another player; the generator records the caller, the source
player, the tiles involved, and whether a kan is closed. Tiles are always drawn
from a :class:`~rincon_riichi_api.tiles.TileDeck`, so no tile ever exceeds four
copies on the table.
"""

from __future__ import annotations

import random

from .hand import get_waits
from .tiles import NUMBERED_SUITS, TileDeck, sort_tiles

#: The four seats, in play order (relative to the round wind label E).
_SEATS = ["East", "South", "West", "North"]


def generate_furiten(
    wait_type: str | None = None,
    subject_seat: str | None = None,
    furiten: bool | None = None,
    with_calls: bool = True,
    max_attempts: int = 40,
) -> dict:
    """Generate a four-player furiten drill.

    The scenario is produced by simulating a slice of real play. The subject
    holds a verified tenpai concealed hand; a live wall is dealt and turns are
    walked (draw → discard) in seat order. When a player makes an open call
    (pon/chi/kan) the called tile leaves the discarder's pond and the turn moves
    past the caller, so pond sizes differ naturally. Tiles are always drawn from
    a :class:`~rincon_riichi_api.tiles.TileDeck`, so no tile exceeds four copies.

    Returns a dict:
      ``hand``        subject's 13-tile tenpai concealed hand (sorted)
      ``waits``       the exact winning tiles for the subject hand
      ``discards``    ``{wind: [tile,...]}`` per player, consistent with the
                      simulated turn order (subject's own pond is adjusted so it
                      contains (or omits) every wait tile as requested)
      ``calls``       list of exposed melds with caller / source / tiles /
                      ``closed`` flag (empty when no calls)
      ``main_seat``   the subject wind
      ``furiten``     bool: whether the subject is in furiten this turn
      ``round_wind``  round wind label
      ``wait_type``   human label for the wait shape (best-effort)
    """
    if subject_seat is None:
        subject_seat = random.choice(_SEATS)

    _VALID_KEYS = [
        "ryanmen", "kanchan", "penchan", "tanki", "shanpon",
        "nobetan", "sanmenchan", "sanmentan", "entotsu",
    ]
    if wait_type is None or wait_type not in _VALID_KEYS:
        wait_type = random.choice(_VALID_KEYS)

    for _ in range(max_attempts):
        deck = TileDeck(with_honors=True, include_aka=True)
        # 1. Build a verified tenpai concealed hand and take its tiles.
        build = build_wait_hand(waits_for=wait_type, deck=deck)
        if build is None:
            wait_type = random.choice(_VALID_KEYS)
            continue
        hand, waits, label = build
        waits = [w for w in waits if w in _canonical(deck, hand, waits)]
        if not waits:
            continue

        # 2. Simulate a slice of play: draws + discards in seat order, with
        #    open calls that skip turns (all tiles drawn from the same deck).
        discards, calls = _simulate_turns(deck, subject_seat, waits, with_calls)

        # 3. Enforce the requested furiten state on the subject's own pond while
        #    keeping the pond counts plausible.
        discards = _enforce_furiten(deck, discards, subject_seat, waits, furiten)

        # 4. Safety guard for the physical 4-copies limit.
        if _over_four(hand, waits, discards, calls):
            continue

        return _assemble(
            subject_seat, hand, waits, label, discards, calls,
            round_wind="East",
        )
    raise ValueError("could not generate a furiten scenario")


def _canonical(deck: TileDeck, hand: list[str], waits: list[str]) -> list[str]:
    """Filter waits to tiles still physically consistent on the table."""
    # A wait tile may be drawn again only if fewer than 4 copies exist in play
    # (hand + waits considered). Keep it simple: no wait is drawn, so any wait
    # whose count in the hand is <4 is valid.
    from collections import Counter

    c = Counter(hand)
    return [w for w in waits if c[w] < 4]


#: Turn order (the round wind East is the dealer / first player).
_SEAT_ORDER = ["East", "South", "West", "North"]


def _simulate_turns(
    deck: TileDeck,
    subject_seat: str,
    waits: list[str],
    with_calls: bool,
) -> tuple[dict[str, list[str]], list[dict]]:
    """Walk a slice of turns, drawing+discarding and applying open calls.

    A full round deals one draw+discard to each seat in order. When a discard is
    claimed by an open call (pon/chi/kan) the tile leaves the discarder's pond,
    the caller melds it and then discards (so the caller gains an extra turn),
    and the turn moves past the caller. This makes pond sizes differ naturally
    without ever exceeding four copies of any tile.

    Returns ``(discards, calls)``.
    """
    discards: dict[str, list[str]] = {seat: [] for seat in _SEAT_ORDER}
    calls: list[dict] = []

    total_target = random.randint(10, 18)
    max_calls = random.choice([1, 1, 2])
    made = 0
    guard = 0
    while made < total_target and guard < 600:
        guard += 1
        seat = _SEAT_ORDER[guard % len(_SEAT_ORDER)]
        tile = deck.pop_tile()
        if tile is None:
            break

        claimed = (
            with_calls
            and len(calls) < max_calls
            and random.random() < 0.55
        )
        if claimed:
            call = _make_call(deck, seat, tile, subject_seat)
            if call:
                calls.append(call)
                # The caller discards a tile of their own afterward.
                extra = deck.pop_tile()
                if extra is not None:
                    discards[call["by"]].append(extra)
                    made += 1
                made += 1
                continue

        discards[seat].append(tile)
        made += 1

    return discards, calls


def _make_call(
    deck: TileDeck, discarder: str, tile: str, subject_seat: str
) -> dict | None:
    """Build a feasible open call on ``tile`` by a non-subject opponent.

    Returns the call dict, or ``None`` when no opponent can legally form it.
    ``by`` is the caller; ``from`` is the player who discarded the tile.
    """
    candidates = [s for s in _SEAT_ORDER if s != discarder and s != subject_seat]
    if not candidates:
        return None
    random.shuffle(candidates)
    caller = candidates[0]
    options = ["Pon", "Kan"]
    if not _is_honor(tile):
        options.append("Chi")
    random.shuffle(options)

    # Try each option until one is buildable.
    for kind in options:
        if kind == "Pon":
            if deck.available(tile) < 2:
                continue
            deck.take(tile, 2)
            return _call("Pon", caller, discarder, [tile, tile, tile], False)
        if kind == "Chi":
            tiles = _build_chi(deck, tile)
            if tiles is None:
                continue
            return _call("Chi", caller, discarder, tiles, False)
        if kind == "Kan":
            if deck.available(tile) < 3:
                continue
            closed = random.random() < 0.5
            if closed:
                deck.take(tile, 3)
                return _call("Kan", caller, discarder, [tile, tile, tile, tile], True)
            deck.take(tile, 2)
            return _call("Kan", caller, discarder, [tile, tile, tile], False)
    return None


def _call(typ: str, by: str, from_: str, tiles: list[str], closed: bool) -> dict:
    return {
        "type": typ,
        "by": by,
        "from": from_,
        "tiles": sort_tiles(tiles),
        "closed": bool(closed),
    }


def _build_chi(deck: TileDeck, tile: str) -> list[str] | None:
    if _is_honor(tile):
        return None
    n = int(tile[0])
    s = tile[1]
    for start in range(max(1, n - 2), min(7, n) + 1):
        seq = [f"{start}{s}", f"{start + 1}{s}", f"{start + 2}{s}"]
        if tile not in seq:
            continue
        need = [t for t in seq if t != tile]
        if all(deck.available(t) >= 1 for t in need) and all(deck.take(t, 1) for t in need):
            return seq
    return None


def _is_honor(tile: str) -> bool:
    return tile[1] == "z"


def _enforce_furiten(
    deck: TileDeck,
    discards: dict[str, list[str]],
    subject_seat: str,
    waits: list[str],
    furiten: bool | None,
) -> dict[str, list[str]]:
    """Adjust the subject's pond so it contains (or omits) every wait tile.

    When ``furiten`` is True the subject has previously discarded every wait
    tile; when False none of them are present. Missing tiles are taken from the
    deck, so the 4-copies limit is never exceeded.
    """
    pond = discards[subject_seat]
    wanted = furiten if furiten is not None else random.random() < 0.5

    if wanted:
        # Remove any wait tiles, then re-add them once from the deck.
        pond[:] = [t for t in pond if t not in waits]
        for w in waits:
            if deck.available(w) >= 1:
                deck.take(w, 1)
                pond.append(w)
    else:
        pond[:] = [t for t in pond if t not in waits]
        # Top up so the pond isn't empty.
        pond.extend(deck.take_random(max(0, random.randint(1, 2) - len(pond))))
    return discards


def _assemble(
    subject_seat: str,
    hand: list[str],
    waits: list[str],
    label: str,
    discards: dict[str, list[str]],
    calls: list[dict],
    round_wind: str,
) -> dict:
    return {
        "hand": sort_tiles(hand),
        "waits": sort_tiles(waits),
        "wait_type": label,
        "wait_key": label.lower(),
        "main_seat": subject_seat,
        "round_wind": round_wind,
        "furiten": _is_furiten(hand, waits, discards.get(subject_seat, [])),
        "discards": {w: sort_tiles(d) for w, d in discards.items()},
        "calls": calls,
    }


def _is_furiten(hand: list[str], waits: list[str], own_discards: list[str]) -> bool:
    return any(w in own_discards for w in waits)


def _over_four(
    hand: list[str], waits: list[str], discards: dict[str, list[str]], calls: list[dict]
) -> bool:
    """Return True if any tile exceeds 4 copies across the whole table."""
    from collections import Counter
    from .tiles import max_copies

    all_tiles = list(hand)
    for tiles in discards.values():
        all_tiles.extend(tiles)
    for call in calls:
        all_tiles.extend(call["tiles"])
    return max_copies(all_tiles) > 4


# ---------------------------------------------------------------------------
# Small tenpai-hand builder (kept here to avoid a circular import with generate)
# ---------------------------------------------------------------------------
def build_wait_hand(waits_for: str, deck: TileDeck) -> tuple[list[str], list[str], str] | None:
    """Return (hand, waits, label) for a verified tenpai shape, drawing tiles
    from ``deck`` so the hand itself never exceeds four copies."""
    suit = random.choice(NUMBERED_SUITS)
    for _ in range(30):
        shape, expected, label = _shape_spec(waits_for, suit)
        if shape is None:
            return None
        # Check the shape tiles are available (no more than 4 copies already).
        if any(deck.available(t) < 1 for t in shape):
            continue
        # Honour tiles as isolated filler (never sequences).
        filler = _fill_honor(13 - len(shape), deck)
        if filler is None:
            continue
        for t in shape:
            deck.take(t, 1)
        hand = shape + filler
        waits = get_waits(hand)
        if waits and (waits_for in ("entotsu",) or sorted(waits) == sorted(expected)):
            return sort_tiles(hand), waits, label
        # Restore the shape tiles consumed for this failed attempt.
        for t in shape:
            deck.put(t, 1)
        for t in filler:
            deck.put(t, 1)
    return None


def _shape_spec(key: str, suit: str) -> tuple[list[str], list[str], str] | None:
    def t(n: int) -> str:
        return f"{n}{suit}"

    r = random.randint
    if key == "ryanmen":
        n = r(2, 7)
        return ([t(n), t(n + 1)], [t(n - 1), t(n + 2)], "Ryanmen")
    if key == "kanchan":
        n = r(1, 7)
        return ([t(n), t(n + 2)], [t(n + 1)], "Kanchan")
    if key == "penchan":
        if random.random() < 0.5:
            return ([t(1), t(2)], [t(3)], "Penchan")
        return ([t(8), t(9)], [t(7)], "Penchan")
    if key == "tanki":
        n = r(1, 9)
        return ([t(n)], [t(n)], "Tanki")
    if key == "shanpon":
        p = r(1, 9)
        q = r(1, 9)
        while q == p:
            q = r(1, 9)
        return ([t(p), t(p), t(q), t(q)], [t(p), t(q)], "Shanpon")
    if key == "nobetan":
        n = r(1, 6)
        return ([t(n), t(n + 1), t(n + 2), t(n + 3)], [t(n), t(n + 3)], "Nobetan")
    if key == "sanmenchan":
        n = r(2, 4)
        return (
            [t(n), t(n + 1), t(n + 2), t(n + 3), t(n + 4)],
            [t(n - 1), t(n + 2), t(n + 5)],
            "Sanmenchan",
        )
    if key == "sanmentan":
        n = r(1, 3)
        return (
            [t(n), t(n + 1), t(n + 2), t(n + 3), t(n + 4), t(n + 5), t(n + 6)],
            [t(n), t(n + 3), t(n + 6)],
            "Sanmentan",
        )
    if key == "entotsu":
        n = r(2, 7)
        return ([t(n), t(n + 1), t(n + 2), t(n + 2), t(n + 2)], [], "Entotsu")
    if key == "ryantan":
        return ([t(4), t(5), t(5), t(5)], [t(3), t(4), t(6)], "Ryantan")
    if key == "kantan":
        return ([t(3), t(5), t(5), t(5)], [t(3), t(4)], "Kantan")
    if key == "aryanmen":
        return ([t(4), t(5), t(6), t(6)], [t(3), t(6)], "Aryanmen")
    if key == "pentan":
        return ([t(1), t(2), t(2), t(2)], [t(1), t(3)], "Pentan")
    return None


def _fill_honor(count: int, deck: TileDeck) -> list[str] | None:
    """Fill ``count`` tiles with isolated honor triplets + optional pair."""
    honors = ["1z", "2z", "3z", "4z", "5z", "6z", "7z"]
    random.shuffle(honors)
    fill: list[str] = []
    idx = 0
    is_pair = count % 3 == 2
    triplets = (count - (2 if is_pair else 0)) // 3
    for _ in range(triplets):
        h = honors[idx]
        idx += 1
        if not deck.take(h, 3):
            return None
        fill.extend([h, h, h])
    if is_pair:
        p = honors[idx]
        if not deck.take(p, 2):
            return None
        fill.extend([p, p])
    return fill
