import pytest

from calculations.rolling_stats import (
    TeamMatchResult as R,
    compute_rolling_average,
    compute_weighted_form_score,
)

# mais recente primeiro: V V E D D
RESULTS = [R(2, 0), R(1, 0), R(1, 1), R(0, 2), R(0, 1)]


def test_points_and_letters():
    assert [r.points for r in RESULTS] == [3, 3, 1, 0, 0]
    assert [r.outcome_letter for r in RESULTS] == ["W", "W", "D", "L", "L"]


def test_rolling_window_3():
    r = compute_rolling_average(RESULTS, 3)
    assert r["matches_considered"] == 3
    assert r["goals_for_avg"] == pytest.approx(1.33)
    assert r["goals_against_avg"] == pytest.approx(0.33)
    assert r["points_avg"] == pytest.approx(2.33)


def test_rolling_window_5():
    r = compute_rolling_average(RESULTS, 5)
    assert (r["goals_for_avg"], r["goals_against_avg"], r["points_avg"]) == (0.8, 0.8, 1.4)


def test_window_larger_than_history_uses_only_what_exists():
    r = compute_rolling_average(RESULTS, 10)
    assert r["matches_considered"] == 5
    assert r["points_avg"] == pytest.approx(1.4)


def test_empty_history_returns_none_not_zero():
    r = compute_rolling_average([], 5)
    assert r["matches_considered"] == 0
    assert r["goals_for_avg"] is None and r["points_avg"] is None


def test_weighted_form_favors_recent_games():
    f = compute_weighted_form_score(RESULTS)
    assert f["weighted_form_score"] == pytest.approx(2.0)
    assert f["recent_form"] == ["W", "W", "D", "L", "L"]
    assert compute_weighted_form_score(list(reversed(RESULTS)))["weighted_form_score"] < 2.0


def test_weighted_form_is_capped_at_10_games():
    f = compute_weighted_form_score([R(1, 0)] * 12)
    assert f["matches_considered"] == 10
    assert f["weighted_form_score"] == pytest.approx(3.0)
    assert f["recent_form"] == ["W"] * 10


def test_weighted_form_empty():
    f = compute_weighted_form_score([])
    assert f["weighted_form_score"] is None and f["recent_form"] == []
