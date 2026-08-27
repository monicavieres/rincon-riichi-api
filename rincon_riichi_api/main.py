"""FastAPI application exposing the Rincón Riichi hand engine and simulation."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .generate import (
    generate_full_hand,
    generate_wait_hand,
    generate_winning_waits,
    random_discard_pool,
)
from .hand import can_win, get_waits, is_tenpai, wait_info
from .models import GenerateHandRequest, GenerateHandResponse, HandRequest, ScoreRequest
from .practice import DRILLS, build_questions
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

# Allow the Rincón Riichi site (GitHub Pages + local dev) to call this API.
_origins = [
    "https://monicavieres.github.io",
    "https://monicavieres.github.io/rincon-riichi",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:5501",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://localhost:5501",
    "http://localhost:8900",
    "http://127.0.0.1:8900",
]
_extra = os.environ.get("ALLOWED_ORIGINS")
if _extra:
    _origins.extend(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            "/practice",
            "/furiten/generate",
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


# ---- Practice drills -------------------------------------------------------
@app.get("/practice")
def practice(drill: str, count: int = 10) -> dict:
    """Generate a batch of practice questions for a drill module.

    ``drill`` is one of the allowed module keys (see ``DRILLS``). Returned
    questions are self-contained and rendered directly by the site.
    """
    if drill not in DRILLS:
        raise HTTPException(status_code=400, detail=f"unknown drill: {drill}")
    try:
        questions = build_questions(drill, count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"drill": drill, "count": len(questions), "questions": questions}


@app.get("/furiten/generate")
def furiten_generate(
    wait_type: str | None = None,
    subject_seat: str | None = None,
    furiten: bool | None = None,
    with_calls: bool = True,
) -> dict:
    """Generate a four-player furiten drill snapshot."""
    from .furiten import generate_furiten

    try:
        return generate_furiten(
            wait_type=wait_type,
            subject_seat=subject_seat,
            furiten=furiten,
            with_calls=with_calls,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
