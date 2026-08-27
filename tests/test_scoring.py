"""Tests for scoring."""

import pytest

from rincon_riichi_api.scoring import base_points, payments, score


@pytest.mark.parametrize(
    "han,fu,expected",
    [
        (1, 30, 1000),
        (2, 30, 2000),
        (3, 30, 3900),
        (3, 40, 5200),
        (4, 40, 8000),
    ],
)
def test_non_dealer_ron(han, fu, expected):
    assert payments(han, fu, dealer=False, win="Ron")["total"] == expected


def test_dealer_ron():
    assert payments(2, 30, dealer=True, win="Ron")["total"] == 2900


def test_tsumo_dealer():
    assert payments(4, 30, dealer=True, win="Tsumo")["text"] == "3900 all"


def test_tsumo_non_dealer():
    assert payments(3, 40, dealer=False, win="Tsumo")["text"] == "1300/2600"


def test_honba_adds():
    result = score(1, 30, dealer=False, win="Ron", honba=2)
    assert result["payments"] == "1600"


def test_limit_haneman():
    assert payments(6, 30, dealer=False, win="Ron")["total"] == 12000


def test_limit_baiman():
    assert payments(8, 30, dealer=False, win="Ron")["total"] == 16000
