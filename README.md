# Rincón Riichi API

A Python **FastAPI** service that generates and validates Riichi Mahjong hands and
simulates tables. It powers and extends the practice modules of
[Rincón Riichi](https://github.com/monicavieres/rincon-riichi).

## Features

- **Hand engine**
  - Agari validation (`can_win`) — 4 melds + pair, plus chiitoitsu / kokushi.
  - Tenpai detection and exact winning-tile (`waits`) computation via a solver.
  - Wait classification (ryanmen, kanchan, penchan, tanki, shanpon, nobetan,
    sanmenchan, sanmentan, entotsu, ryantan, kantan, aryanmen, pentan, ...).
  - Random hand generation isolated from interfering fill (honor-based).

- **Scoring**
  - Fu counting and base-point table (mangan / haneman / baiman / sanbaiman / yakuman).
  - Ron / Tsumo payments (dealer and non-dealer), honba and riichi deposits.

- **Yaku**
  - Full standard yaku reference (1–3 han, 6 han, yakuman) with detection.

- **Table simulation**
  - Deal hands, wall, dead wall, dora indicators, discards, honba, round/seat winds.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
uvicorn rincon_riichi_api.main:app --reload
```

Docs (auto-generated): http://127.0.0.1:8000/docs

## Example

```bash
# Validate a hand
curl -X POST http://127.0.0.1:8000/hand/validate \
  -H 'Content-Type: application/json' \
  -d '{"tiles":["1m","2m","3m","4p","5p","6p","7s","8s","9s","1z","1z","1z","5z","5z"]}'
```

## Tests

```bash
pytest -q
```
