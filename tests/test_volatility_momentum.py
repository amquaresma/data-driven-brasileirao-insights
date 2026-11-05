import pytest

from calculations.momentum import compute_momentum
from calculations.rolling_stats import TeamMatchResult as R
from calculations.volatility import compute_volatility


def test_volatility_needs_two_matches():
    v = compute_volatility([R(1, 0)])
    assert v["matches_considered"] == 1 and v["volatility_index"] is None


def test_volatility_is_zero_for_identical_results():
    v = compute_volatility([R(1, 1)] * 6)
    assert v["points_stddev"] == 0 and v["goal_difference_stddev"] == 0 and v["volatility_index"] == 0


def test_volatility_known_values():
    v = compute_volatility([R(1, 0), R(0, 1)])  # pontos 3 e 0, saldo +1 e -1
    assert v["points_stddev"] == pytest.approx(1.5)
    assert v["goal_difference_stddev"] == pytest.approx(1.0)
    assert v["volatility_index"] == pytest.approx(1.25)


def test_momentum_of_an_improving_team():
    recent = [R(3, 0), R(2, 0), R(2, 1), R(1, 1), R(2, 0)]
    older = [R(0, 2), R(1, 2), R(0, 1), R(1, 1), R(0, 3)]
    m = compute_momentum(recent + older)
    assert m["attacking_trend"] == pytest.approx(0.8)
    assert m["defensive_trend"] == pytest.approx(0.7)
    assert m["points_trend"] == pytest.approx(1.2)
    assert m["momentum_score"] == pytest.approx(3.9)


def test_momentum_of_a_declining_team_is_negative():
    recent = [R(0, 2), R(1, 2), R(0, 1), R(1, 1), R(0, 3)]
    older = [R(3, 0), R(2, 0), R(2, 1), R(1, 1), R(2, 0)]
    assert compute_momentum(recent + older)["momentum_score"] < 0


def test_momentum_without_history():
    assert compute_momentum([])["momentum_score"] is None
