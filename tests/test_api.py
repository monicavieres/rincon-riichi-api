"""Tests for hand generation and the API."""

from rincon_riichi_api.generate import generate_wait_hand, generate_winning_waits
from rincon_riichi_api.hand import can_win, get_waits


def test_generate_ryanmen():
    result = generate_wait_hand("ryanmen")
    hand = result["tiles"]
    assert len(hand) == 13
    assert sorted(result["waits"]) == sorted(get_waits(hand))
    assert result["wait_type"] == "Ryanmen"


def test_generate_all_wait_types():
    types = ["ryanmen", "kanchan", "penchan", "tanki", "shanpon", "nobetan",
             "sanmenchan", "sanmentan", "entotsu", "ryantan", "kantan",
             "aryanmen", "pentan"]
    for t in types:
        result = generate_wait_hand(t)
        hand = result["tiles"]
        assert len(hand) == 13, f"{t} hand length wrong"
        # solver agrees the real waits match the reported waits
        assert sorted(get_waits(hand)) == sorted(result["waits"]), f"{t} waits mismatch"


def test_generate_winning_waits_count():
    hands = generate_winning_waits(3)
    assert len(hands) == 3


def test_api_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["version"]


def test_api_validate(client):
    hand = ["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "1z", "1z", "1z", "5z", "5z"]
    resp = client.post("/hand/validate", json={"tiles": hand})
    assert resp.status_code == 200
    assert resp.json()["is_winning"] is True


def test_api_validate_invalid(client):
    resp = client.post("/hand/validate", json={"tiles": ["xx"]})
    assert resp.status_code == 422


def test_api_generate(client):
    resp = client.get("/hand/generate?wait_type=ryanmen")
    assert resp.status_code == 200
    body = resp.json()
    assert body["wait_type"] == "Ryanmen"
    assert len(body["tiles"]) == 13


def test_api_score(client):
    resp = client.post("/score", json={"han": 3, "fu": 30, "dealer": False, "win": "Ron"})
    assert resp.status_code == 200
    assert resp.json()["payments"] == "3900"


def test_api_score_table(client):
    resp = client.get("/score/table")
    assert resp.status_code == 200
    assert len(resp.json()["rows"]) > 0


def test_api_table_deal(client):
    resp = client.get("/table/deal")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["players"]) == 4
    for p in body["players"]:
        assert len(p["hand"]) == 13


def test_api_yaku_list(client):
    resp = client.get("/yaku")
    assert resp.status_code == 200
    assert len(resp.json()["yaku"]) > 20
