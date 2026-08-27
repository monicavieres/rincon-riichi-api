"""FastAPI application exposing the Rincón Riichi hand engine and simulation."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from . import __version__
from .generate import (
    generate_full_hand,
    generate_wait_hand,
    generate_winning_waits,
    random_discard_pool,
)
from .hand import can_win, get_waits, is_tenpai, wait_info
from .models import GenerateHandRequest, GenerateHandResponse, HandRequest, ScoreRequest
from .scoring import score as score_hand
from .scoring import value_table
from .table import deal_table, status
from .tiles import sort_tiles
from .yaku import detect_yaku, yaku_reference

app = FastAPI(
    title="Rincón Riichi API",
    description="Riichi Mahjong hand engine and table simulation for Rincón Riichi.",
    version=__version__,
)


@app.get("/")
def root() -> dict:
    return {
        "name": "Rincón Riichi API",
        "version": __version__,
        "docs": "/docs",
        "endpoints": [
            "/hand/validate",
            "/hand/waits",
            "/hand/generate",
            "/hand/batch",
            "/hand/win",
            "/score",
            "/score/table",
            "/yaku",
            "/yaku/detect",
            "/table/deal",
            "/table/discards",
        ],
    }


# ---- Hand engine -----------------------------------------------------------
@app.post("/hand/validate", response_model=dict)
def validate_hand(req: HandRequest) -> dict:
    """Validate a 14-tile hand and report win/tenpai status."""
    tiles = req.tiles
    return {
        "tiles": sort_tiles(tiles),
        "is_winning": can_win(tiles),
        "is_tenpai": is_tenpai(tiles),
        "waits": get_waits(tiles),
    }


@app.post("/hand/waits")
def hand_waits(req: HandRequest) -> dict:
    """Compute the exact winning tiles (waits) and wait type of a hand."""
    info = wait_info(req.tiles)
    return info


@app.post("/hand/generate", response_model=GenerateHandResponse)
def hand_generate(req: GenerateHandRequest) -> GenerateHandResponse:
    """Generate a verified tenpai hand of a requested wait type."""
    try:
        result = generate_wait_hand(req.wait_type, suit=req.suit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GenerateHandResponse(**result)


@app.get("/hand/generate")
def hand_generate_get(wait_type: str, suit: str | None = None) -> dict:
    """GET variant of hand generation (easier to call from a browser)."""
    try:
        return generate_wait_hand(wait_type, suit=suit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/hand/win")
def hand_win(count: int = 1) -> dict:
    """Generate a random winning (agari) hand."""
    return generate_full_hand()


@app.get("/hand/batch")
def hand_batch(count: int = 5) -> dict:
    """Generate a batch of random wait-type hands."""
    return {"hands": generate_winning_waits(count)}


@app.get("/hand/pool")
def hand_pool(size: int = 14) -> dict:
    """Return a random tile pool (e.g. wall face / discards)."""
    return {"tiles": random_discard_pool(size)}


# ---- Scoring ---------------------------------------------------------------
@app.post("/score")
def score(req: ScoreRequest) -> dict:
    """Compute the score payment for a han/fu/dealer/win/honba combination."""
    return score_hand(req.han, req.fu, dealer=req.dealer, win=req.win, honba=req.honba)


@app.get("/score/table")
def score_table() -> dict:
    """Return the standard non-dealer Ron payment table."""
    return {"rows": value_table()}


# ---- Yaku ------------------------------------------------------------------
@app.get("/yaku")
def yaku_list() -> dict:
    return {"yaku": yaku_reference()}


@app.post("/yaku/detect")
def yaku_detect(req: HandRequest) -> dict:
    return {"tiles": req.tiles, "yaku": detect_yaku(req.tiles)}


# ---- Table simulation ------------------------------------------------------
@app.get("/table/deal")
def table_deal(with_honors: bool = True, start_wind: str = "East") -> dict:
    table = deal_table(with_honors=with_honors, start_wind=start_wind)
    return status(table)


@app.get("/table/discards")
def table_discards(with_honors: bool = True, turns: int = 6) -> dict:
    table = deal_table(with_honors=with_honors)
    from .table import simulate_discards

    result = simulate_discards(table, turns=turns)
    result["table"] = status(table)
    return result
