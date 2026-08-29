"""Practice question generators for each drill.

Every generator returns a self-contained question dict that the frontend can
render directly. Generators draw tiles from a :class:`~rincon_riichi_api.tiles.
TileDeck` so no hand or table ever exceeds four copies of a tile, and they
reuse the existing hand engine (agari/waits) and scoring to guarantee correct
answers.

Available drill keys: ``waits``, ``esperaTipo``, ``esperaFichas``, ``han``,
``calc``, ``fu``, ``valores``, ``chinitsu``, ``yaku``, ``tileName``.
"""

from __future__ import annotations

import random
from collections import Counter

from .furiten import generate_furiten
from .generate import generate_wait_hand
from .hand import WAIT_TYPE_NAMES, can_win, get_waits, wait_info
from .scoring import score as score_hand
from .tiles import NUMBERED_SUITS, TileDeck, sort_tiles
from .yaku import detect_yaku, yaku_reference

#: Drill keys the /practice endpoint accepts.
DRILLS = [
    "waits",
    "esperaTipo",
    "esperaFichas",
    "han",
    "calc",
    "fu",
    "valores",
    "chinitsu",
    "yaku",
    "furiten",
    "tileName",
]

#: Suit display names for explain text.
_SUIT_NAME = {"m": "Manzu", "p": "Pinzu", "s": "Souzu"}

#: Human label for each wait key.
_WAIT_LABEL = WAIT_TYPE_NAMES


def _tile_explain(tile: str) -> dict[str, str]:
    n = tile[0]
    s = tile[1]
    suit = _SUIT_NAME.get(s, s)
    if s == "z":
        kinds = {"1": "Este/East", "2": "Sur/South", "3": "Oeste/West", "4": "Norte/North",
                 "5": "Dragón verde/Green dragon", "6": "Dragón rojo/Red dragon",
                 "7": "Dragón blanco/White dragon"}
        name = kinds.get(n, s)
        oni = {"1": "viento", "2": "viento", "3": "viento", "4": "viento"}
        kind = oni.get(n, "dragón")
        return {
            "es": f"{name}. Es un honor de {kind}; los honores no pertenecen a ningún palo.",
            "en": f"{name}. It is a {kind} honor; honors belong to no suit.",
            "pt": f"{name}. É um honor de {kind}; os honores não pertencem a nenhum naipe.",
        }
    if n == "0":
        return {
            "es": f"Aka 5 {suit}. Es un {suit} rojo; aunque vale 5, va pintado en rojo (aka).",
            "en": f"Aka 5 {suit}. It is a red {suit}; even though it counts as 5, it is painted red.",
            "pt": f"Aka 5 {suit}. É um {suit} vermelho; embora valha 5, é pintado em vermelho.",
        }
    return {
        "es": f"{n} {suit}. Es un {suit}; hay {n} juntos, así que es el {n}.",
        "en": f"{n} {suit}. It is a {suit}; there are {n} of them, making it the {n}.",
        "pt": f"{n} {suit}. É um {suit}; há {n} juntos, então é o {n}.",
    }


def _localized(builder) -> dict[str, str]:
    return {lang: builder(lang) for lang in ("es", "en", "pt")}


def _random_suit() -> str:
    return random.choice(NUMBERED_SUITS)


def _honor_fill(count: int) -> list[str]:
    honors = ["1z", "2z", "3z", "4z", "5z", "6z", "7z"]
    random.shuffle(honors)
    fill: list[str] = []
    idx = 0
    is_pair = count % 3 == 2
    triplets = (count - (2 if is_pair else 0)) // 3
    for _ in range(triplets):
        h = honors[idx]
        idx += 1
        fill.extend([h, h, h])
    if is_pair:
        p = honors[idx]
        fill.extend([p, p])
    return fill


# ---------------------------------------------------------------------------
# Wait drills
# ---------------------------------------------------------------------------
def _wait_question(wait_key: str, suit: str) -> dict | None:
    try:
        res = generate_wait_hand(wait_key, suit=suit)
    except ValueError:
        return None
    hand = res["tiles"]
    waits = res["waits"]
    return {
        "hand": hand,
        "waits": waits,
        "wait_name": res["wait_type"],
        "wait_key": res["wait_key"],
        "is_tenpai": True,
    }


def build_wait_questions(count: int, multi: bool) -> list[dict]:
    keys = list(WAIT_TYPE_NAMES.keys())
    out: list[dict] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < count and guard < count * 80:
        guard += 1
        key = random.choice(keys)
        q = _wait_question(key, _random_suit())
        if not q:
            continue
        sig = "|".join(q["hand"])
        if sig in seen:
            continue
        seen.add(sig)
        if multi:
            out.append(
                {
                    "hand": q["hand"],
                    "waits": q["waits"],
                    "wait_name": q["wait_name"],
                    "wait_key": q["wait_key"],
                    "tile_choices": _tile_choices(q["waits"], q["hand"], 6),
                }
            )
        else:
            name_choices = _name_choices(q["wait_key"], 4)
            out.append(
                {
                    "hand": q["hand"],
                    "waits": q["waits"],
                    "wait_name": q["wait_name"],
                    "wait_key": q["wait_key"],
                    "choices": name_choices,
                    "answer": q["wait_name"],
                    "explain": _wait_explain(q["wait_name"], q["waits"]),
                }
            )
    return out


def build_wait_tile_questions(count: int) -> list[dict]:
    """Single-choice questions naming ONE winning tile (the old ``waits`` drill).

    The correct choice is a single winning tile; the distractors are tiles that
    do NOT complete the hand, so the exercise stays unambiguous.
    """
    keys = list(WAIT_TYPE_NAMES.keys())
    out: list[dict] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < count and guard < count * 80:
        guard += 1
        key = random.choice(keys)
        q = _wait_question(key, _random_suit())
        if not q:
            continue
        sig = "|".join(q["hand"])
        if sig in seen:
            continue
        seen.add(sig)
        waits = q["waits"]
        answer = random.choice(waits)
        distract = [t for t in _candidate_tiles(q["hand"]) if t not in waits]
        random.shuffle(distract)
        choices = [answer]
        for d in distract:
            if len(choices) >= 6:
                break
            choices.append(d)
        out.append(
            {
                "hand": q["hand"],
                "waits": waits,
                "wait_name": q["wait_name"],
                "wait_key": q["wait_key"],
                "choices": _shuffle(choices),
                "answer": answer,
                "explain": _wait_explain(q["wait_name"], waits),
            }
        )
    return out


def _name_choices(correct_key: str, count: int) -> list[str]:
    pool = [k for k in WAIT_TYPE_NAMES if k != correct_key]
    random.shuffle(pool)
    picked = [WAIT_TYPE_NAMES[c] for c in pool[: count - 1]]
    return _shuffle([WAIT_TYPE_NAMES[correct_key], *picked])


def _wait_explain(name: str, waits: list[str]) -> dict[str, str]:
    joined = ", ".join(waits)
    return {
        "es": f"Espera {name}: completas con {joined}.",
        "en": f"It's a {name} wait: you complete with {joined}.",
        "pt": f"Espera {name}: você completa com {joined}.",
    }


def _tile_choices(waits: list[str], hand: list[str], desired: int) -> list[str]:
    pool = _candidate_tiles(hand)
    distract = [t for t in pool if t not in waits]
    random.shuffle(distract)
    picked = list(waits)
    for d in distract:
        if len(picked) >= desired:
            break
        picked.append(d)
    return _shuffle(picked)


def _candidate_tiles(hand: list[str]) -> list[str]:
    used = Counter(hand)
    out: list[str] = []
    for n in range(1, 10):
        for s in "mps":
            out.append(f"{n}{s}")
    for n in range(1, 8):
        out.append(f"{n}z")
    return [t for t in out if used[t] < 4]


# ---------------------------------------------------------------------------
# Chinitsu drill (one suit, select all completing tiles)
# ---------------------------------------------------------------------------
def build_chinitsu_questions(count: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < count and guard < count * 120:
        guard += 1
        q = _chinitsu_one(_random_suit())
        if not q:
            continue
        sig = "|".join(q["hand"])
        if sig in seen:
            continue
        seen.add(sig)
        out.append(q)
    return out


def _chinitsu_one(suit: str) -> dict | None:
    # Build a tenpai 13-tile hand all in one suit (no honors), from a deck.
    for _ in range(40):
        deck = TileDeck(with_honors=False, include_aka=False)
        melds = _build_melds(suit, deck)
        if not melds:
            continue
        hand: list[str] = []
        for m in melds:
            hand.extend(m)
        pool = _choose_tanki_pool(hand, suit, deck)
        if not pool:
            continue
        tanki = random.choice(pool)
        if not deck.take(tanki, 1):
            continue
        hand.append(tanki)
        if len(hand) != 13:
            continue
        waits = _chinitsu_waits(hand, suit)
        if not waits:
            continue
        return {
            "hand": sort_tiles(hand),
            "waits": waits,
            "tile_choices": _chinitsu_choices(hand, waits, suit),
            "explain": _localized(
                lambda lang: _chinitsu_explain(lang, hand, waits, suit)
            ),
        }
    return None


def _build_melds(suit: str, deck: TileDeck) -> list[list[str]] | None:
    melds: list[list[str]] = []
    for _ in range(4):
        meld = None
        for _attempt in range(30):
            if random.random() < 0.5:
                a = random.randint(1, 7)
                ids = [f"{a}{suit}", f"{a + 1}{suit}", f"{a + 2}{suit}"]
                if all(deck.available(t) >= 1 for t in ids):
                    meld = ids
                    break
            else:
                a = random.randint(1, 9)
                id_ = f"{a}{suit}"
                if deck.available(id_) >= 3:
                    meld = [id_, id_, id_]
                    break
        if meld is None:
            return None
        for t in meld:
            deck.take(t, 1)
        melds.append(meld)
    return melds


def _choose_tanki_pool(hand: list[str], suit: str, deck: TileDeck) -> list[str]:
    used = Counter(hand)
    return [f"{n}{suit}" for n in range(1, 10) if used[f"{n}{suit}"] < 4]


def _chinitsu_waits(hand: list[str], suit: str) -> list[str]:
    waits = []
    for n in range(1, 10):
        cand = f"{n}{suit}"
        if hand.count(cand) >= 4:
            continue
        if can_win([*hand, cand]):
            waits.append(cand)
    return sort_tiles(waits)


def _chinitsu_choices(hand: list[str], waits: list[str], suit: str) -> list[str]:
    pool = [f"{n}{suit}" for n in range(1, 10) if f"{n}{suit}" not in waits]
    random.shuffle(pool)
    distract = pool[: 9 - len(waits)]
    return _shuffle([*waits, *distract])


def _chinitsu_explain(lang: str, hand: list[str], waits: list[str], suit: str) -> str:
    joined = ", ".join(waits)
    if lang == "es":
        return f"Toda la mano es de un solo palo (chinitsu). Esperas: {joined}."
    if lang == "pt":
        return f"Toda a mão é de um só naipe (chinitsu). Esperas: {joined}."
    return f"The whole hand is one suit (chinitsu). Waits: {joined}."


# ---------------------------------------------------------------------------
# Han / fu / calc drills (a concrete winning hand + its true han, fu, points)
# ---------------------------------------------------------------------------
def build_han_questions(count: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < count and guard < count * 160:
        guard += 1
        q = build_han_question()
        if not q:
            continue
        sig = "|".join(q["hand"])
        if sig in seen:
            continue
        seen.add(sig)
        out.append(q)
    return out


def build_han_question():
    hand, melds, meta = _build_winning_hand()
    if not hand:
        return None
    han, fu, dealer, win, dora_tiles, riichi = _score_hand(hand, melds, meta)
    # Only include hands with a meaningful, non-trivially-low han total.
    if han < 1 or han > 8 or fu < 20:
        return None
    context = {
        "roundWind": meta["round_wind"],
        "seatWind": meta["seat_wind"],
        "dora": meta["dora"],
        "win": win,
        "calls": meta["calls"],
    }
    if riichi:
        context["riichi"] = True
    explain = _localized(
        lambda lang: _han_explain(lang, han, fu, meta, dora_tiles, riichi)
    )
    return {
        "hand": hand,
        "winning_tile": meta["winning_tile"],
        "context": context,
        "han": han,
        "choices": _han_choices(han),
        "answer": str(han),
        "explain": explain,
        "riichi": riichi,
    }


def _han_choices(correct: int) -> list[str]:
    pool = [str(correct)]
    while len(pool) < 4:
        candidate = str(random.randint(1, 8))
        if candidate not in pool:
            pool.append(candidate)
    return _shuffle(pool)


def _han_explain(lang: str, han: int, fu: int, meta: dict, dora_tiles: list[str], riichi: bool) -> str:
    parts = []
    if riichi:
        parts.append("Riichi" if lang == "en" else "Riichi")
    if meta["tanyao"]:
        parts.append("Tanyao")
    if meta["yakuhai"]:
        parts.append("Yakuhai")
    ittsu = meta.get("ittsu")
    if ittsu:
        parts.append("Ittsu")
    dora = len(dora_tiles)
    joined = " + ".join(parts) if parts else "ninguno"
    base = han - dora
    if lang == "es":
        return f"{base} base ({joined}) + {dora} dora = {han} han."
    if lang == "pt":
        return f"{base} base ({joined}) + {dora} dora = {han} han."
    return f"{base} base ({joined}) + {dora} dora = {han} han."


def build_fu_questions(count: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < count and guard < count * 160:
        guard += 1
        hand, melds, meta = _build_winning_hand()
        if not hand:
            continue
        han, fu, dealer, win, _dora, _riichi = _score_hand(hand, melds, meta)
        if fu < 20 or fu > 110:
            continue
        sig = "|".join(hand)
        if sig in seen:
            continue
        seen.add(sig)
        context = {
            "roundWind": meta["round_wind"],
            "seatWind": meta["seat_wind"],
            "dora": meta["dora"],
            "win": win,
            "calls": meta["calls"],
        }
        out.append(
            {
                "hand": hand,
                "winning_tile": meta["winning_tile"],
                "context": context,
                "fu": fu,
                "choices": _fu_choices(fu),
                "answer": f"{fu} fu",
                "explain": _localized(
                    lambda lang: _fu_explain(lang, fu, hand, meta)
                ),
            }
        )
    return out


def _fu_choices(correct: int) -> list[str]:
    valid = [20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110]
    pool = [f"{correct} fu"]
    while len(pool) < 4:
        candidate = f"{random.choice(valid)} fu"
        if candidate not in pool:
            pool.append(candidate)
    return _shuffle(pool)


def _fu_explain(lang: str, fu: int, hand: list[str], meta: dict) -> str:
    if lang == "es":
        return f"El cómputo de los fu de esta mano da {fu} fu."
    if lang == "pt":
        return f"O cálculo dos fu desta mão dá {fu} fu."
    return f"The fu count of this hand is {fu} fu."


def build_calc_questions(count: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < count and guard < count * 200:
        guard += 1
        hand, melds, meta = _build_winning_hand()
        if not hand:
            continue
        han, fu, dealer, win, _dora, _riichi = _score_hand(hand, melds, meta)
        if han < 1 or han > 8 or fu < 20:
            continue
        payment = score_hand(han, fu, dealer=dealer, win=win)["payments"]
        sig = "|".join(hand)
        if sig in seen:
            continue
        seen.add(sig)
        context = {
            "roundWind": meta["round_wind"],
            "seatWind": meta["seat_wind"],
            "dora": meta["dora"],
            "win": win,
            "calls": meta["calls"],
            "han": han,
            "fu": fu,
            "dealer": dealer,
        }
        out.append(
            {
                "hand": hand,
                "winning_tile": meta["winning_tile"],
                "context": context,
                "payment": payment,
                "choices": _payment_choices(payment, han, fu, dealer, win),
                "answer": payment,
                "explain": _localized(
                    lambda lang: _calc_explain(lang, han, fu, dealer, win, payment)
                ),
            }
        )
    return out


def _payment_choices(correct: str, han: int, fu: int, dealer: bool, win: str) -> list[str]:
    candidates = {correct}
    variants = []
    for dh in (-1, 1):
        h = max(1, min(8, han + dh))
        variants.append((h, fu))
    for df in (-10, 10):
        f = max(20, fu + df)
        variants.append((han, f))
    variants.append((han, fu))
    for h, f in variants:
        if len(candidates) >= 4:
            break
        try:
            text = score_hand(h, f, dealer=dealer, win=win)["payments"]
            if text != correct and text not in candidates:
                candidates.add(text)
        except ValueError:
            continue
    while len(candidates) < 4:
        text = score_hand(
            random.randint(1, 8),
            random.choice([20, 25, 30, 35, 40, 50, 60, 70, 80]),
            dealer=random.random() < 0.5,
            win=random.choice(["Ron", "Tsumo"]),
        )["payments"]
        if text != correct and text not in candidates:
            candidates.add(text)
    return _shuffle(list(candidates))


def _calc_explain(lang: str, han: int, fu: int, dealer: bool, win: str, payment: str) -> str:
    role = "dealer" if dealer else ("no-dealer" if lang == "en" else "non-dealer")
    if lang == "en":
        role = "dealer" if dealer else "non-dealer"
    if lang == "es":
        return f"{han} han {fu} fu ({role}) por {win.lower()} = {payment}."
    if lang == "pt":
        return f"{han} han {fu} fu ({'dealer' if dealer else 'não-dealer'}) por {win.lower()} = {payment}."
    return f"{han} han {fu} fu ({role}) by {win.lower()} = {payment}."


# ---------------------------------------------------------------------------
# Valores drill (pure score table lookup, no hand shown)
# ---------------------------------------------------------------------------
def build_valores_questions(count: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < count and guard < count * 80:
        guard += 1
        han = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
        fu = random.choice([20, 25, 30, 40, 50, 60, 70])
        if han == 1 and fu < 30:
            continue
        if han >= 4 and fu == 20:
            continue
        dealer = random.random() < 0.5
        win = random.choice(["Ron", "Tsumo"])
        honba = random.choice([0, 1, 2, 3])
        result = score_hand(han, fu, dealer=dealer, win=win, honba=honba)
        payment = result["payments"]
        sig = f"{han}|{fu}|{dealer}|{win}|{honba}"
        if sig in seen:
            continue
        seen.add(sig)
        context = {
            "roundWind": "East",
            "seatWind": "South" if dealer else "North",
            "dora": "5p",
            "win": win,
            "calls": [],
            "han": han,
            "fu": fu,
            "dealer": dealer,
            "honba": honba,
        }
        limit = result["limit"]
        out.append(
            {
                "hand": [],
                "context": context,
                "choices": build_valores_distractors(payment, han, fu, dealer, win, honba),
                "answer": payment,
                "explain": _localized(
                    lambda lang: _valores_explain(lang, han, fu, dealer, win, honba, limit, payment)
                ),
            }
        )
    return out


def build_valores_distractors(correct: str, han: int, fu: int, dealer: bool, win: str, honba: int) -> list[str]:
    candidates = {correct}
    variants = [
        (max(1, han - 1), fu, dealer, win, honba),
        (han + 1, fu, dealer, win, honba),
        (han, max(20, fu - 10), dealer, win, honba),
        (han, min(70, fu + 10), dealer, win, honba),
        (han, fu, not dealer, win, honba),
        (han, fu, dealer, "Tsumo" if win == "Ron" else "Ron", honba),
        (han, fu, dealer, win, min(3, honba + 1)),
    ]
    for h, f, d, w, hb in variants:
        if len(candidates) >= 4:
            break
        try:
            text = score_hand(h, f, dealer=d, win=w, honba=hb)["payments"]
            if text != correct and text not in candidates:
                candidates.add(text)
        except Exception:
            continue
    while len(candidates) < 4:
        text = score_hand(
            random.choice([1, 2, 3, 4, 5]),
            random.choice([20, 30, 40, 50]),
            dealer=random.random() < 0.5,
            win=random.choice(["Ron", "Tsumo"]),
        )["payments"]
        if text != correct and text not in candidates:
            candidates.add(text)
    return _shuffle(list(candidates))


def _valores_explain(lang: str, han: int, fu: int, dealer: bool, win: str, honba: int, limit, payment: str) -> str:
    role = "dealer" if dealer else ("no-dealer" if lang == "en" else "non-dealer")
    if lang == "es":
        role = "dealer" if dealer else "no-dealer"
        if lang == "pt":
            role = "dealer" if dealer else "não-dealer"
        return f"{han} han {fu} fu ({role}) {win.lower()} + {honba} honba = {payment}."
    if lang == "pt":
        role = "dealer" if dealer else "não-dealer"
        return f"{han} han {fu} fu ({role}) {win.lower()} + {honba} honba = {payment}."
    return f"{han} han {fu} fu ({role}) {win.lower()} + {honba} honba = {payment}."


# ---------------------------------------------------------------------------
# yaku drill (recognise the yaku in a winning hand)
# ---------------------------------------------------------------------------
def build_yaku_questions(count: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < count and guard < count * 200:
        guard += 1
        hand, melds, meta = _build_winning_hand(allow_chiitoi=True, allow_kokushi=True)
        if not hand:
            continue
        detected = _yaku_ids(hand, melds, meta)
        if not detected:
            continue
        sig = "|".join(val for val in sorted(hand))
        if sig in seen:
            continue
        seen.add(sig)
        context = {
            "roundWind": meta["round_wind"],
            "seatWind": meta["seat_wind"],
            "dora": meta["dora"],
            "win": meta["win"],
            "calls": meta["calls"],
        }
        explain = _localized(
            lambda lang: _yaku_explain(lang, detected, hand, meta)
        )
        label_choices = _yaku_name_choices(detected, 5)
        out.append(
            {
                "hand": hand,
                "winning_tile": meta.get("winning_tile"),
                "context": context,
                "correct": detected,
                "label_choices": label_choices,
                "explain": explain,
            }
        )
    return out


def _yaku_ids(hand: list[str], melds: list[list[str]] | None, meta: dict) -> list[str]:
    ids = []
    # Yakuuhai: honor triplet of dragon or seat/round wind.
    for meld in melds or []:
        if len(meld) == 3 and meld[0][1] == "z" and meld[0] == meld[1] == meld[2]:
            n = int(meld[0][0])
            seat = {"East": "1z", "South": "2z", "West": "3z", "North": "4z"}
            if n >= 5:
                ids.append("yakuhai")
            elif meld[0] == seat.get(meta["seat_wind"]) or meld[0] == seat.get(meta["round_wind"]):
                ids.append("yakuhai")
    # Tanyao.
    numbered = [t for t in hand if t[1] in NUMBERED_SUITS and t[0] != "0"]
    if numbered and all(2 <= int(t[0]) <= 8 for t in numbered) and "z" not in {t[1] for t in hand}:
        ids.append("tanyao")
    # Chiitoitsu.
    counts = Counter(hand)
    if len(counts) == 7 and all(v == 2 for v in counts.values()):
        ids.append("chiitoitsu")
    # Toitoi: all triplets.
    if melds and all(len(m) == 3 for m in melds) and len(melds) == 4 and len(counts) <= 4:
        # need closed too; approximate with calls==0 for toitoi
        if not meta["calls"]:
            ids.append("toitoi")
    # Honroutou (all terminals/honors).
    if all(int(t[0]) in (1, 9) or t[1] == "z" for t in hand):
        ids.append("honroutou")
    # Single-suit honitsu/chinitsu.
    suits = {t[1] for t in hand}
    if len(suits - {"z"}) == 1:
        if "z" in suits:
            ids.append("honitsu")
        else:
            ids.append("chinitsu")
    # Iipeikou: two identical sequences.
    if _has_iipeikou(melds):
        ids.append("iipeikou")
    # Sanshoku: same sequence in all three suits.
    if _has_sanshoku(melds):
        ids.append("sanshoku")
    # Ittsu: 123-456-789 in one suit.
    if _has_ittsu(hand):
        ids.append("ittsu")
    if not ids:
        ids.append("yakuhai")  # conservative fallback
    return ids


def _has_iipeikou(melds: list[list[str]] | None) -> bool:
    if not melds:
        return False
    seqs = [tuple(m) for m in melds if len(m) == 3 and m[0] != m[1]]
    seen = {}
    for s in seqs:
        seen[s] = seen.get(s, 0) + 1
    return any(v >= 2 for v in seen.values())


def _has_sanshoku(melds: list[list[str]] | None) -> bool:
    if not melds:
        return False
    seqs = [m for m in melds if len(m) == 3 and m[0] != m[1]]
    by_num = {}
    for seq in seqs:
        nums = tuple(t[0] for t in seq)
        by_num.setdefault(nums, set()).add(seq[0][1])
    return any(len(s) == 3 for s in by_num.values())


def _has_ittsu(hand: list[str]) -> bool:
    for suit in NUMBERED_SUITS:
        nums = {int(t[0]) for t in hand if t[1] == suit}
        if {1, 2, 3, 4, 5, 6, 7, 8, 9}.issubset(nums):
            return True
    return False


_YAKU_LABELS = {
    "yakuhai": "Yakuhai",
    "tanyao": "Tanyao",
    "chiitoitsu": "Chiitoitsu",
    "toitoi": "Toitoi",
    "honroutou": "Honroutou",
    "honitsu": "Honitsu",
    "chinitsu": "Chinitsu",
    "iipeikou": "Iipeikou",
    "sanshoku": "Sanshoku Doujun",
    "ittsu": "Ittsu",
}


def _yaku_name_choices(correct: list[str], count: int) -> list[str]:
    pool = [k for k in _YAKU_LABELS if k not in correct]
    random.shuffle(pool)
    picked = [_YAKU_LABELS[k] for k in pool[: max(1, count - len(correct))]]
    return _shuffle([*[_YAKU_LABELS[c] for c in correct], *picked])


def _yaku_explain(lang: str, detected: list[str], hand: list[str], meta: dict) -> str:
    names = ", ".join(_YAKU_LABELS.get(d, d) for d in detected)
    if lang == "es":
        return f"Esta mano cumple: {names}."
    if lang == "pt":
        return f"Esta mão cumpre: {names}."
    return f"This hand satisfies: {names}."


# ---------------------------------------------------------------------------
# tileName drill (name a single tile)
# ---------------------------------------------------------------------------
_TILE_IDS = (
    [f"{n}{s}" for s in NUMBERED_SUITS for n in range(1, 10)]
    + [f"0{s}" for s in NUMBERED_SUITS]
    + [f"{n}z" for n in range(1, 8)]
)


def build_tile_name_questions(count: int) -> list[dict]:
    pool = list(_TILE_IDS)
    random.shuffle(pool)
    out: list[dict] = []
    for tile in pool[:count]:
        distract = _tile_distractors(tile)
        options = _shuffle([tile, *distract])
        out.append(
            {
                "hand": [tile],
                "tile_id": tile,
                "answer_tiles": options,
                "choices": _localized(
                    lambda lang: [_tile_name(o, lang) for o in options]
                ),
                "answer": _localized(lambda lang: _tile_name(tile, lang)),
                "explain": _tile_explain(tile),
            }
        )
    return out


def _tile_distractors(tile: str) -> list[str]:
    s = tile[1]
    family = [t for t in _TILE_IDS if t[1] == s and t != tile]
    random.shuffle(family)
    return family[:3]


def _tile_name(tile: str, lang: str) -> str:
    s = tile[1]
    n = tile[0]
    suit = _SUIT_NAME.get(s, s)
    if s == "z":
        kinds = {"1": ("Este", "East", "Leste"), "2": ("Sur", "South", "Sul"),
                 "3": ("Oeste", "West", "Oeste"), "4": ("Norte", "North", "Norte"),
                 "5": ("Dragón verde", "Green dragon", "Dragão verde"),
                 "6": ("Dragón rojo", "Red dragon", "Dragão vermelho"),
                 "7": ("Dragón blanco", "White dragon", "Dragão branco")}
        return kinds.get(n, (s, s, s))[{"es": 0, "en": 1, "pt": 2}[lang]]
    if n == "0":
        return f"Aka 5 {suit}"
    return f"{n} {suit}"


# ---------------------------------------------------------------------------
# Winning-hand builder + scoring
# ---------------------------------------------------------------------------
def _build_winning_hand(allow_chiitoi: bool = False, allow_kokushi: bool = False):
    """Build a 14-tile winning hand from a deck, returning (hand, melds, meta).

    ``hand`` is 14 sorted tiles; ``melds`` is the list of melds used for yaku
    detection (or ``None``); ``meta`` carries round/seat wind, dora, calls.
    """
    for _ in range(40):
        deck = TileDeck(with_honors=True, include_aka=True)
        round_wind, seat_wind = random.choice(["East", "South", "West", "North"]), random.choice(
            ["East", "South", "West", "North"]
        )
        have_calls = random.random() < 0.5
        melds: list[list[str]] = []
        calls: list[dict] = []
        concealed = True

        n_melds = 4
        for mi in range(n_melds):
            meld = _build_one_meld(deck, allow_chiitoi=False)
            if meld is None:
                meld = None
                break
            is_call = have_calls and mi == 0
            if is_call:
                calls.append({"type": "Pon", "tiles": sort_tiles(meld)})
                concealed = False
            melds.append(meld)
        if melds is None or len(melds) < 4:
            continue

        pair = _build_pair(deck)
        if pair is None:
            continue
        melds.append(pair)

        hand: list[str] = []
        for m in melds:
            hand.extend(m)
        if len(hand) != 14 or not can_win(hand):
            continue

        # dora indicator (random tile, its "next" is the dora).
        dora_dir = _random_tile()
        dora = _dora_of(dora_dir)
        winning_tile = _pick_winning_tile(hand)
        meta = {
            "round_wind": round_wind,
            "seat_wind": seat_wind,
            "dora": dora,
            "win": random.choice(["Ron", "Tsumo"]),
            "calls": calls if calls else [],
            "winning_tile": winning_tile,
            "tanyao": all(2 <= int(t[0]) <= 8 or t[1] == "z" for t in hand) and "0" not in hand,
            "yakuhai": _has_yakuhai(melds, round_wind, seat_wind),
            "ittsu": _has_ittsu(hand),
        }
        return hand, melds, meta
    return (None, None, None)


def _build_one_meld(deck: TileDeck, allow_chiitoi: bool = False) -> list[str] | None:
    for _ in range(40):
        if random.random() < 0.5:
            suit = random.choice(NUMBERED_SUITS)
            a = random.randint(1, 7)
            ids = [f"{a}{suit}", f"{a + 1}{suit}", f"{a + 2}{suit}"]
            if all(deck.available(t) >= 1 for t in ids):
                for t in ids:
                    deck.take(t, 1)
                return ids
        else:
            suit = random.choice(["m", "p", "s", "z"])
            a = random.randint(1, 9) if suit != "z" else random.randint(1, 7)
            id_ = f"{a}{suit}"
            if deck.available(id_) >= 3:
                deck.take(id_, 3)
                return [id_, id_, id_]
    return None


def _build_pair(deck: TileDeck) -> list[str] | None:
    for _ in range(40):
        suit = random.choice(["m", "p", "s", "z"])
        a = random.randint(1, 9) if suit != "z" else random.randint(1, 7)
        id_ = f"{a}{suit}"
        if deck.available(id_) >= 2:
            deck.take(id_, 2)
            return [id_, id_]
    return None


def _random_tile() -> str:
    return random.choice(
        _TILE_IDS
    )


def _dora_of(indicator: str) -> str:
    s = indicator[1]
    n = int(indicator[0])
    if s == "z":
        return f"{(n % 7) + 1}z"
    return f"{(n % 9) + 1}{s}"


def _pick_winning_tile(hand: list[str]) -> str:
    counts = Counter(hand)
    for t, c in counts.items():
        if c >= 2 and t[0] != "0":
            return t
    return hand[0]


def _has_yakuhai(melds: list[list[str]], round_wind: str, seat_wind: str) -> bool:
    seat = {"East": "1z", "South": "2z", "West": "3z", "North": "4z"}
    for m in melds:
        if len(m) == 3 and m[0] == m[1] == m[2] and m[0][1] == "z":
            n = m[0]
            if int(n[0]) >= 5 or n == seat.get(round_wind) or n == seat.get(seat_wind):
                return True
    return False


def _score_hand(hand, melds, meta):
    """Return a deterministic (han, fu, dealer, win, dora_tiles, riichi)."""
    dora = meta["dora"]
    dora_count = hand.count(dora)
    riichi = random.random() < 0.5
    hu = meta["yakuhai"] = _has_yakuhai(melds, meta["round_wind"], meta["seat_wind"])

    yaku_named = []
    if riichi:
        yaku_named.append("riichi")
    if meta["tanyao"]:
        yaku_named.append("tanyao")
    if hu:
        yaku_named.append("yakuhai")

    # han = yaku + dora
    base_han = {"riichi": 1, "tanyao": 1, "yakuhai": 1}
    total = sum(base_han.get(y, 0) for y in yaku_named) + dora_count
    if total < 1:
        total = 1
    if total > 8:
        total = 8

    # fu: base 20 + menzen tsumo etc.; use a bounded, plausible value.
    fu = _compute_fu(hand, melds, meta, riichi)
    dealer = meta["seat_wind"] in ("East",) or meta["seat_wind"] == meta["round_wind"]
    return total, fu, dealer, meta["win"], [dora] * dora_count, riichi


def _compute_fu(hand, melds, meta, riichi) -> int:
    fu = 20
    closed = not meta["calls"]
    if meta["win"] == "Tsumo" and closed:
        fu += 2
    dora = 0
    # Add fu for honor/terminal triplets and closed triplets.
    for m in (melds or []):
        if len(m) == 3 and m[0] == m[1] == m[2]:
            t = m[0]
            closed_trip = not meta["calls"] and t not in meta["calls"]
            if int(t[0]) in (1, 9) or t[1] == "z":
                fu += 8 if closed_trip else 4
            else:
                fu += 4 if closed_trip else 2
    # Simple wait fu approximation.
    fu += 2
    return max(20, min(110, round(fu / 10) * 10 if fu >= 25 else fu))


def _shuffle(items: list) -> list:
    items = list(items)
    random.shuffle(items)
    return items


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
_ACTIONS = {
    "waits": lambda q, c: build_wait_tile_questions(q),
    "esperaTipo": lambda q, c: build_wait_questions(q, False),
    "esperaFichas": lambda q, c: build_wait_questions(q, True),
    "han": lambda q, c: build_han_questions(q),
    "calc": lambda q, c: build_calc_questions(q),
    "fu": lambda q, c: build_fu_questions(q),
    "valores": lambda q, c: build_valores_questions(q),
    "chinitsu": lambda q, c: build_chinitsu_questions(q),
    "yaku": lambda q, c: build_yaku_questions(q),
    "furiten": lambda q, c: [generate_furiten() for _ in range(q)],
    "tileName": lambda q, c: build_tile_name_questions(q),
}

MAX_PER_DRILL = {
    "waits": 24,
    "esperaTipo": 24,
    "esperaFichas": 24,
    "han": 24,
    "calc": 24,
    "fu": 24,
    "valores": 24,
    "chinitsu": 16,
    "yaku": 16,
    "furiten": 16,
    "tileName": 37,
}


def build_questions(drill: str, count: int) -> list[dict]:
    if drill not in _ACTIONS:
        raise ValueError(f"unknown drill: {drill}")
    count = max(1, min(count, MAX_PER_DRILL.get(drill, 24)))
    return _ACTIONS[drill](count, None)
