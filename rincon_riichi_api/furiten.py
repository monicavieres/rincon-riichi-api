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

    Returns a dict:
      ``hand``        subject's 13-tile tenpai concealed hand (sorted)
      ``waits``       the exact winning tiles for the subject hand
      ``discards``    ``{wind: [tile,...]}`` per player (subject's own pond
                      deliberately contains (or omits) every wait tile)
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

    deck = TileDeck(with_honors=True, include_aka=True)

    for _ in range(max_attempts):
        # 1. Build a verified tenpai concealed hand and take its tiles.
        build = build_wait_hand(waits_for=wait_type, deck=deck)
        if build is None:
            deck = TileDeck(with_honors=True, include_aka=True)
            wait_type = random.choice(_VALID_KEYS)
            continue
        hand, waits, label = build
        waits = [w for w in waits if w in _canonical(deck, hand, waits)]
        if not waits:
            continue

        # 2. Deal the other three players' concealed hands from the deck.
        others = [w for w in _SEATS if w != subject_seat]
        hands: dict[str, list[str]] = {subject_seat: hand}
        ok = True
        for seat in others:
            tiles = deck.take_random(13)
            if len(tiles) != 13:
                ok = False
                break
            hands[seat] = tiles
        if not ok:
            continue

        # 3. Build discard ponds. The wall face after dealing is ``deck``.
        discards = _simulate_discards(
            deck, hands, subject_seat, waits, furiten=furiten
        )

        # 4. Exposed melds (calls) drawn from the remaining wall face.
        calls: list[dict] = []
        if with_calls:
            calls = _build_calls(deck, hands, subject_seat, others, waits)
            # A call can double-count tiles in a way that looks like >4 copies
            # on the table; drop the calls if that happens so the scenario stays
            # physically possible.
            if _over_four(hand, waits, discards, calls):
                calls = []

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


def _simulate_discards(
    deck: TileDeck,
    hands: dict[str, list[str]],
    subject_seat: str,
    waits: list[str],
    furiten: bool | None,
) -> dict[str, list[str]]:
    """Produce a globally-consistent pond per player, honouring the furiten flag.

    Every pond tile is drawn (and removed) from ``deck``, so no tile exceeds
    four copies across the whole table. The subject's own pond is built first so
    the waits can be reserved before the other seats draw.
    """
    ponds: dict[str, list[str]] = {}
    subject_target = _valid_subject_target(deck, subject_seat, waits, furiten)
    for seat in _SEATS:
        if seat == subject_seat:
            ponds[seat] = _build_subject_pond(deck, waits, subject_target)
        else:
            n = random.randint(1, 2)
            ponds[seat] = deck.take_random(n)
    return ponds


def _valid_subject_target(
    deck: TileDeck,
    subject_seat: str,
    waits: list[str],
    furiten: bool | None,
) -> bool:
    """Decide whether the subject pond should contain every wait tile.

    Returns True when that is physically possible (enough copies remain).
    """
    wanted = furiten
    if wanted is None:
        wanted = random.random() < 0.5
    if wanted and all(deck.available(w) >= 1 for w in waits):
        return True
    if wanted:
        # Not enough copies remain to place every wait; force non-furiten.
        return False
    return False


def _build_subject_pond(deck: TileDeck, waits: list[str], contain_waits: bool) -> list[str]:
    pond: list[str] = []
    if contain_waits:
        for w in waits:
            if deck.take(w, 1):
                pond.append(w)
        # Top up with a couple of random tiles so the pond doesn't look empty.
        extra = deck.take_random(random.randint(0, 2))
        pond.extend(extra)
    else:
        # Draw random tiles but never the waits.
        n = random.randint(1, 2)
        for _ in range(n):
            t = _pop_non_wait(deck, waits)
            if t is None:
                break
            pond.append(t)
    return pond


def _pop_non_wait(deck: TileDeck, excluded: list[str]) -> str | None:
    for _ in range(20):
        t = deck.pop_tile()
        if t is None:
            return None
        if t not in excluded:
            return t
        deck.put(t, 1)  # put back and try another
    return None


def _build_calls(
    deck: TileDeck,
    hands: dict[str, list[str]],
    subject_seat: str,
    others: list[str],
    waits: list[str],
) -> list[dict]:
    """Create 0-2 exposed melds with caller / source / closed-kan info."""
    calls: list[dict] = []
    prefer = random.choice([True, False])
    call_tile = None
    if prefer:
        # Use a wait tile someone else discarded toward the subject.
        for w in waits:
            if deck.available(w) > 0 and hands.get(subject_seat, []).count(w) >= 2:
                call_tile = w
                break
    if call_tile is None:
        # Fall back to any tile present in a non-subject hand or deck.
        candidates = [t for t, c in deck._counter.items() if c > 0]
        if candidates:
            call_tile = random.choice(candidates)

    if call_tile is None:
        return calls

    maker = random.choice(others)
    caller = subject_seat
    kind = random.choice(["Pon", "Chi", "Kan"])
    if kind == "Chi":
        # A chi is a sequence; we can't always build one from a single tile.
        tiles = _build_chi(deck, call_tile)
        if tiles is None:
            kind = "Pon"
    if kind == "Pon":
        tiles = [call_tile, call_tile, call_tile]
        if not deck.take(call_tile, 2):
            return calls  # unable to supply the pair
    if kind == "Kan":
        closed = random.random() < 0.5
        if closed:
            if not deck.take(call_tile, 3):
                return calls
            tiles = [call_tile, call_tile, call_tile, call_tile]
        else:
            if not deck.take(call_tile, 2):
                return calls
            tiles = [call_tile, call_tile, call_tile]
    else:
        closed = False

    calls.append(
        {
            "type": kind,
            "by": caller,
            "from": maker,
            "tiles": sort_tiles(tiles),
            "closed": bool(closed),
        }
    )
    return calls


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
