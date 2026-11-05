from calculations.rolling_stats import TeamMatchResult as R
from calculations.streaks import compute_streaks


def test_streaks_from_latest_match_backwards():
    s = compute_streaks([R(2, 0), R(1, 0), R(3, 1), R(1, 1), R(0, 2)])
    assert s["matches_considered"] == 5
    assert s["current_win_streak"] == 3
    assert s["current_loss_streak"] == 0
    assert s["current_unbeaten_streak"] == 4
    assert s["current_winless_streak"] == 0
    assert s["current_clean_sheet_streak"] == 2
    assert s["current_scoring_streak"] == 4


def test_latest_loss_breaks_the_good_streaks():
    s = compute_streaks([R(0, 1), R(1, 0)])
    assert s["current_loss_streak"] == 1
    assert s["current_win_streak"] == 0
    assert s["current_unbeaten_streak"] == 0
    assert s["current_winless_streak"] == 1
    assert s["current_clean_sheet_streak"] == 0
    assert s["current_scoring_streak"] == 0


def test_no_matches():
    s = compute_streaks([])
    assert s["matches_considered"] == 0
    assert s["current_win_streak"] == 0
