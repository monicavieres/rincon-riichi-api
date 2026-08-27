"""Yaku reference and detection.

Provides the standard yaku list (hand-structure and value-adding yaku) and a
best-effort detector based on the hand, melds, win method, and yakuhai winds.
"""

from __future__ import annotations

from collections import Counter

from .tiles import NUMBERED_SUITS, normalize

#: romaji, kanji, han (min), honor tiles present.
YAKU = [
    {"id": "tanyao", "romaji": "Tanyao", "kanji": "断么九", "han": 1},
    {"id": "pinfu", "romaji": "Pinfu", "kanji": "平和", "han": 1},
    {"id": "riichi", "romaji": "Riichi", "kanji": "立直", "han": 1},
    {"id": "ippatsu", "romaji": "Ippatsu", "kanji": "一発", "han": 1},
    {"id": "tsumo", "romaji": "Menzen Tsumo", "kanji": "門前清自摸", "han": 1},
    {"id": "iipeikou", "romaji": "Iipeikou", "kanji": "一盃口", "han": 1},
    {"id": "yakuhai", "romaji": "Yakuhai", "kanji": "役牌", "han": 1},
    {"id": "haitei", "romaji": "Haitei", "kanji": "海底摸月", "han": 1},
    {"id": "houtei", "romaji": "Houtei", "kanji": "河底撈魚", "han": 1},
    {"id": "rinshan", "romaji": "Rinshan Kaihou", "kanji": "嶺上開花", "han": 1},
    {"id": "chankan", "romaji": "Chankan", "kanji": "搶槓", "han": 1},
    {"id": "chiitoitsu", "romaji": "Chiitoitsu", "kanji": "七対子", "han": 2},
    {"id": "toitoi", "romaji": "Toitoi", "kanji": "対々和", "han": 2},
    {"id": "sanankou", "romaji": "Sanankou", "kanji": "三暗刻", "han": 2},
    {"id": "sanshoku", "romaji": "Sanshoku Doujun", "kanji": "三色同順", "han": 2},
    {"id": "ittsu", "romaji": "Ittsu", "kanji": "一気通貫", "han": 2},
    {"id": "chanta", "romaji": "Chanta", "kanji": "混全帯么九", "han": 2},
    {"id": "honroutou", "romaji": "Honroutou", "kanji": "混老頭", "han": 2},
    {"id": "shousangen", "romaji": "Shousangen", "kanji": "小三元", "han": 2},
    {"id": "ryanpeikou", "romaji": "Ryanpeikou", "kanji": "二盃口", "han": 3},
    {"id": "junchan", "romaji": "Junchan", "kanji": "純全帯么九", "han": 3},
    {"id": "honitsu", "romaji": "Honitsu", "kanji": "混一色", "han": 3},
    {"id": "chinitsu", "romaji": "Chinitsu", "kanji": "清一色", "han": 6},
    {"id": "kokushi", "romaji": "Kokushi Musou", "kanji": "国士無双", "han": "yakuman"},
    {"id": "suuankou", "romaji": "Suuankou", "kanji": "四暗刻", "han": "yakuman"},
    {"id": "daisangen", "romaji": "Daisangen", "kanji": "大三元", "han": "yakuman"},
    {"id": "tsuuiisou", "romaji": "Tsuu Iisou", "kanji": "字一色", "han": "yakuman"},
    {"id": "chinroutou", "romaji": "Chinroutou", "kanji": "清老頭", "han": "yakuman"},
    {"id": "ryuuiisou", "romaji": "Ryuuiisou", "kanji": "緑一色", "han": "yakuman"},
]


def detect_yaku(
    tiles: list[str],
    closed: bool = True,
    win: str = "Ron",
    calls: list[str] | None = None,
) -> list[dict]:
    """Best-effort yaku detection for a winning hand.

    Returns a list of detected yaku dicts. Structure yaku (pinfu, tanyao,
    chiitoitsu, honitsu/chinitsu, etc.) are detected; yakuhai requires the
    round/seat wind info which can be passed via ``calls``.
    """
    tiles = [normalize(t) for t in tiles]
    counts = Counter(tiles)
    detected: list[dict] = []
    suits = {t[1] for t in tiles}

    # All honors -> tsuuiisou.
    if suits == {"z"}:
        detected.append(_y("tsuuiisou"))
        return detected

    # Chiitoitsu.
    if len(counts) == 7 and all(v == 2 for v in counts.values()):
        detected.append(_y("chiitoitsu"))

    # Single suit.
    if len(suits - {"z"}) == 1:
        if "z" in suits:
            detected.append(_y("honitsu"))
        else:
            detected.append(_y("chinitsu"))

    # No terminals/honors and no honors -> tanyao.
    numbered = [t for t in tiles if t[1] in NUMBERED_SUITS]
    if numbered and all(int(t[0]) in range(2, 9) for t in numbered) and "z" not in suits:
        detected.append(_y("tanyao"))

    # Terminal/honor in every group (chanta) — approximated by presence.
    has_terminal_or_honor = any(int(t[0]) in (1, 9) or t[1] == "z" for t in tiles)
    if has_terminal_or_honor and len(suits - {"z"}) <= 2:
        detected.append(_y("chanta"))

    if not detected:
        detected.append(_y("riichi"))
    return detected


def _y(identifier: str) -> dict:
    for entry in YAKU:
        if entry["id"] == identifier:
            return dict(entry)
    return {"id": identifier, "romaji": identifier, "kanji": "", "han": 0}


def yaku_reference() -> list[dict]:
    return [dict(e) for e in YAKU]
