"""Tests for the hand engine (agari, tenpai, waits)."""

import pytest

from rincon_riichi_api.hand import can_win, classify_wait, get_waits, is_tenpai, wait_info


WINNING_HAND = [
    "1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s",
    "1z", "1z", "1z", "5z", "5z",
]


def test_can_win_regular():
    assert can_win(WINNING_HAND)


def test_can_win_chiitoitsu():
    hand = ["1m", "1m", "2p", "2p", "3s", "3s", "4z", "4z", "5z", "5z", "6z", "6z", "7m", "7m"]
    assert can_win(hand)


def test_can_win_kokushi():
    hand = ["1m", "9m", "1p", "9p", "1s", "9s", "1z", "2z", "3z", "4z", "5z", "6z", "7z", "1m"]
    assert can_win(hand)


def test_can_win_false():
    assert not can_win(["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "1z", "1z", "1z", "5z", "6z"])


@pytest.mark.parametrize(
    "hand,expected",
    [
        (["2m", "3m", "1z", "1z", "1z", "2z", "2z", "2z", "3z", "3z", "3z", "4z", "4z"], ["1m", "4m"]),
        (["1m", "2m", "1z", "1z", "1z", "2z", "2z", "2z", "3z", "3z", "3z", "4z", "4z"], ["3m"]),
        (["2m", "3m", "4m", "5m", "1z", "1z", "1z", "2z", "2z", "2z", "3z", "3z", "3z"], ["2m", "5m"]),
    ],
)
def test_get_waits(hand, expected):
    assert sorted(get_waits(hand)) == sorted(expected)


def test_is_tenpai():
    assert is_tenpai(WINNING_HAND[:-1])


def test_classify_ryanmen():
    hand = ["2m", "3m", "1z", "1z", "1z", "2z", "2z", "2z", "3z", "3z", "3z", "4z", "4z"]
    assert wait_info(hand)["wait_type"] == "Ryanmen"


def test_classify_kanchan():
    hand = ["2m", "4m", "1z", "1z", "1z", "2z", "2z", "2z", "3z", "3z", "3z", "4z", "4z"]
    assert wait_info(hand)["wait_type"] == "Kanchan"


def test_classify_nobetan():
    hand = ["2m", "3m", "4m", "5m", "1z", "1z", "1z", "2z", "2z", "2z", "3z", "3z", "3z"]
    assert wait_info(hand)["wait_type"] == "Nobetan"


def test_classify_sanmenchan():
    hand = ["2m", "3m", "4m", "5m", "6m", "1z", "1z", "1z", "2z", "2z", "2z", "3z", "3z"]
    assert wait_info(hand)["wait_type"] == "Sanmenchan"
