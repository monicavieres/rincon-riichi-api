"""Scoring: han + fu -> base points, limits, and Ron/Tsumo payments.

Implements the standard Riichi score table (mangan / haneman / baiman /
sanbaiman / yakuman) plus honba and riichi deposits.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

#: Valid fu total values that appear in the score table.
VALID_FU = [20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110]

#: Limit hands by han cutoffs and their base-point multiplier.
LIMITS = [
    (13, "yakuman", 4.0),
    (11, "sanbaiman", 3.0),
    (8, "baiman", 2.0),
    (6, "haneman", 1.5),
]


def _ceiling(value: float) -> int:
    return int(math.ceil(value / 100) * 100)


def limit_for_han(han: int) -> dict | None:
    """Return the limit descriptor for a han count, or None if not a limit."""
    for cutoff, name, multiplier in LIMITS:
        if han >= cutoff:
            return {"name": name, "multiplier": multiplier}
    return None


def base_points(han: int, fu: int) -> int:
    """Compute base points for a han/fu combination (capped at mangan)."""
    limit = limit_for_han(han)
    if limit:
        return int(2000 * limit["multiplier"])
    fu_value = max(fu, 20)
    raw = fu_value * (2 ** (2 + han))
    return int(min(raw, 2000))


def payments(han: int, fu: int, dealer: bool, win: str = "Ron") -> dict:
    """Return payment details for a hand.

    ``win`` is ``"Ron"`` (single payer, total) or ``"Tsumo"`` (per-player).
    """
    base = base_points(han, fu)
    if win == "Tsumo":
        if dealer:
            each = _ceiling(base * 2)
            return {
                "win": "Tsumo",
                "dealer": True,
                "base": base,
                "text": f"{each} all",
                "per_player": each,
                "players": [each, each, each],
            }
        non_dealer = _ceiling(base * 1)
        dealer_pay = _ceiling(base * 2)
        text = (
            f"{non_dealer} all"
            if non_dealer == dealer_pay
            else f"{non_dealer}/{dealer_pay}"
        )
        return {
            "win": "Tsumo",
            "dealer": False,
            "base": base,
            "text": text,
            "non_dealer": non_dealer,
            "dealer_pay": dealer_pay,
            "players": [non_dealer, non_dealer, dealer_pay],
        }
    total = _ceiling(base * (6 if dealer else 4))
    return {
        "win": "Ron",
        "dealer": dealer,
        "base": base,
        "text": str(total),
        "total": total,
        "players": [total],
    }


def score(han: int, fu: int, dealer: bool, win: str = "Ron", honba: int = 0) -> dict:
    """Full score summary including honba and disabled riichi."""
    pay = payments(han, fu, dealer, win)
    honba_total = honba * 300
    limit = limit_for_han(han)

    if win == "Tsumo":
        per_person = honba * 100
        players = pay["players"]
        if len(set(players)) == 1:
            total = {
                "text": f"{players[0] + per_person} all",
                "per_player": players[0] + per_person,
                "players": [players[0] + per_person] * 3,
            }
        else:
            nd = players[0] + per_person
            dp = players[2] + per_person
            total = {"text": f"{nd}/{dp}", "per_player": nd, "players": [nd, nd, dp]}
    else:
        total = {
            "text": f"{pay['total'] + honba_total}",
            "total": pay["total"] + honba_total,
            "players": [pay["total"] + honba_total],
        }

    return {
        "han": han,
        "fu": fu,
        "dealer": dealer,
        "win": win,
        "honba": honba,
        "base_points": pay["base"],
        "limit": limit,
        "range": "limit" if limit else ("mangan" if base_points(han, fu) >= 2000 else "regular"),
        "payments": total["text"],
        "honba_extra": honba_total,
    }


def value_table() -> dict:
    """Return the standard non-dealer Ron payment table by han and fu."""
    rows = []
    for han in range(1, 6):
        for fu in VALID_FU:
            if han == 1 and fu < 30:
                continue
            if han >= 4 and fu == 20:
                continue
            rows.append(
                {
                    "han": han,
                    "fu": fu,
                    "dealer": False,
                    "win": "Ron",
                    "payments": score(han, fu, dealer=False, win="Ron")["payments"],
                }
            )
    return rows
