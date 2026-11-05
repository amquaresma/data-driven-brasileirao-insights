import pytest

from calculations.match_features import FeatureMatch as F
from calculations.match_features import build_match_features

TARGETS = {"home_goals", "away_goals", "total_goals", "result", "over_2_5"}


def three_matches(last_score=(0, 3)):
    return [
        F("m1", "c", "2026-01-01", None, "A", "B", 2, 0),
        F("m2", "c", "2026-01-08", None, "B", "A", 1, 1),
        F("m3", "c", "2026-01-15", None, "A", "B", *last_score),
    ]


def test_first_match_has_no_history():
    row = build_match_features(three_matches())[0]
    assert row["home_elo"] == pytest.approx(1500.0)
    assert row["home_form"] is None
    assert row["home_matches_played"] == 0
    assert row["home_rest_days"] is None
    assert row["min_history_ok"] is False


def test_features_use_only_previous_matches():
    row = build_match_features(three_matches())[2]
    assert row["home_elo"] == pytest.approx(1509.42)
    assert row["away_elo"] == pytest.approx(1490.58)
    assert row["home_matches_played"] == 2
    assert row["home_rest_days"] == 7


def test_changing_the_matchs_own_score_never_changes_its_features():
    base = build_match_features(three_matches((0, 3)))[2]
    other = build_match_features(three_matches((5, 5)))[2]
    assert {k: v for k, v in base.items() if k not in TARGETS} == {
        k: v for k, v in other.items() if k not in TARGETS
    }


def test_matches_on_the_same_date_share_the_same_prior_state():
    rows = build_match_features(
        [F("m1", "c", "2026-01-01", None, "A", "B", 2, 0), F("m2", "c", "2026-01-01", None, "A", "C", 3, 0)]
    )
    assert rows[1]["home_matches_played"] == 0
    assert rows[1]["home_elo"] == pytest.approx(1500.0)


def test_targets():
    rows = build_match_features(
        [
            F("a", "c", "2026-01-01", None, "A", "B", 2, 1),
            F("b", "c", "2026-01-02", None, "C", "D", 1, 1),
            F("c", "c", "2026-01-03", None, "E", "F", 0, 1),
        ]
    )
    assert [r["result"] for r in rows] == ["H", "D", "A"]
    assert [r["over_2_5"] for r in rows] == [True, False, False]
    assert rows[0]["total_goals"] == 3


def test_minimum_history_needs_five_games_each():
    rows = build_match_features([F(f"m{i}", "c", f"2026-01-{i:02d}", None, "A", "B", 1, 0) for i in range(1, 8)])
    assert rows[4]["min_history_ok"] is False  # 5º jogo: cada time só jogou 4 antes
    assert rows[5]["min_history_ok"] is True
