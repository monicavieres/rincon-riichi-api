"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class HandRequest(BaseModel):
    tiles: list[str] = Field(..., description="Tile ids, e.g. ['1m','2m','3m',...]")

    @field_validator("tiles")
    @classmethod
    def _validate_tiles(cls, v: list[str]) -> list[str]:
        from .tiles import is_valid_tile

        for t in v:
            if not is_valid_tile(t):
                raise ValueError(f"invalid tile: {t}")
        return v


class GenerateHandRequest(BaseModel):
    wait_type: str = Field(..., description="Wait type key, e.g. 'ryanmen'")
    suit: str | None = Field(None, description="Suit: m, p, or s (random if absent)")

    @field_validator("suit")
    @classmethod
    def _validate_suit(cls, v: str | None) -> str | None:
        if v is not None and v not in ("m", "p", "s"):
            raise ValueError("suit must be m, p, or s")
        return v


class ValidateHandResponse(BaseModel):
    tiles: list[str]
    normalized: list[str]
    length: int
    is_winning: bool = False
    is_tenpai: bool = False
    waits: list[str] = []
    wait_type: str = "complex"


class GenerateHandResponse(BaseModel):
    tiles: list[str]
    waits: list[str]
    wait_type: str
    suit: str
    is_tenpai: bool


class ScoreRequest(BaseModel):
    han: int = Field(..., ge=1)
    fu: int = Field(..., ge=20)
    dealer: bool = False
    win: str = "Ron"
    honba: int = Field(0, ge=0)

    @field_validator("win")
    @classmethod
    def _validate_win(cls, v: str) -> str:
        if v not in ("Ron", "Tsumo"):
            raise ValueError("win must be 'Ron' or 'Tsumo'")
        return v
