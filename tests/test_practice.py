"""Tests for the furiten simulator and practice drills."""

from collections import Counter

from rincon_riichi_api.furiten import generate_furiten
from rincon_riichi_api.hand import can_win, get_waits
from rincon_riichi_api.practice import DRILLS, build_questions
from rincon_riichi_api.scoring import score as score_hand
from rincon_riichi_api.tiles import TileDeck, max_copies


def _flatten(fur: dict) -> list[str]:
    tiles = list(fur["hand"])
    for pond in fur["discards"].values():
        tiles.extend(pond)
    for call in fur["calls"]:
        tiles.extend(call["tiles"])
    return tiles


def test_furiten_no_more_than_four_copies():
    for _ in range(40):
        fur = generate_furiten()
        assert max_copies(_flatten(fur)) <= 4


def test_furiten_flag_consistent():
    for _ in range(40):
        fur = generate_furiten()
        own = fur["discards"][fur["main_seat"]]
        assert fur["furiten"] == any(w in own for w in fur["waits"])


def test_furiten_hand_is_tenpai():
    for _ in range(40):
        fur = generate_furiten()
        assert len(fur["hand"]) == 13
        assert sorted(get_waits(fur["hand"])) == sorted(fur["waits"])


def test_furiten_calls_mark_caller_and_source():
    seen_calls = False
    for _ in range(60):
        fur = generate_furiten()
        for call in fur["calls"]:
            seen_calls = True
            assert call["type"] in ("Pon", "Chi", "Kan")
            assert call["by"] in ("East", "South", "West", "North")
            assert call["from"] in ("East", "South", "West", "North")
            assert call["by"] != call["from"]
            assert isinstance(call["closed"], bool)
    assert seen_calls


def test_furiten_waits_are_wins():
    for _ in range(30):
        fur = generate_furiten()
        for w in fur["waits"]:
            assert can_win([*fur["hand"], w])


def test_all_drills_generate():
    for drill in DRILLS:
        questions = build_questions(drill, 6)
        assert len(questions) == 6, drill
        for q in questions:
            hand = q.get("hand")
            if hand:
                assert max_copies(hand) <= 4, drill


def test_wait_drills_true_waits():
    for drill in ("waits", "esperaTipo", "esperaFichas"):
        for q in build_questions(drill, 20):
            assert sorted(get_waits(q["hand"])) == sorted(q["waits"]), drill


def test_waits_single_tile_answer_is_a_real_wait():
    for q in build_questions("waits", 30):
        assert len(q["hand"]) == 13
        # the correct answer must actually complete the hand
        assert q["answer"] in q["waits"]
        assert sorted(get_waits(q["hand"])) == sorted(q["waits"])
        # distractors must not also be winning tiles
        for choice in q["choices"]:
            if choice != q["answer"]:
                assert choice not in q["waits"]


def test_han_answer_matches_han():
    for q in build_questions("han", 20):
        assert q["answer"] == str(q["han"])
        assert int(q["answer"]) in range(1, 9)


def test_calc_payment_matches_score():
    for q in build_questions("calc", 20):
        c = q["context"]
        pay = score_hand(c["han"], c["fu"], dealer=c["dealer"], win=c["win"])[
            "payments"
        ]
        assert pay == q["payment"]
        assert q["payment"] in q["choices"]


def test_valores_payment_matches_score():
    for q in build_questions("valores", 20):
        c = q["context"]
        pay = score_hand(c["han"], c["fu"], dealer=c["dealer"], win=c["win"], honba=c["honba"])[
            "payments"
        ]
        assert pay == q["answer"]
        assert q["answer"] in q["choices"]


def test_tile_deck_never_exceeds_four():
    deck = TileDeck(with_honors=True, include_aka=True)
    hand = deck.take_random(60)
    assert max_copies(hand) <= 4
    assert len(hand) == 60


def test_api_practice(client):
    resp = client.get("/practice?drill=waits&count=6")
    assert resp.status_code == 200
    body = resp.json()
    assert body["drill"] == "waits"
    assert len(body["questions"]) == 6


def test_api_practice_unknown_drill(client):
    resp = client.get("/practice?drill=nope")
    assert resp.status_code == 400


def test_api_furiten(client):
    resp = client.get("/furiten/generate")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["hand"]) == 13
    assert len(body["discards"]) == 4
