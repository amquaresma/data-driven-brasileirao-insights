import random

import pytest

from calculations.elo import EloMatchInput, compute_elo_ratings


def m(home, away, hs, as_, date):
    return EloMatchInput(home, away, hs, as_, date)


def test_equal_teams_winner_gains_half_k():
    r = compute_elo_ratings([m("A", "B", 2, 0, "2026-01-01")])
    assert r["A"]["rating"] == pytest.approx(1510.0)
    assert r["B"]["rating"] == pytest.approx(1490.0)


def test_draw_between_equals_changes_nothing():
    r = compute_elo_ratings([m("A", "B", 1, 1, "2026-01-01")])
    assert r["A"]["rating"] == pytest.approx(1500.0)
    assert r["B"]["rating"] == pytest.approx(1500.0)


def test_known_sequence_win_then_draw():
    r = compute_elo_ratings([m("A", "B", 2, 0, "2026-01-01"), m("B", "A", 1, 1, "2026-01-08")])
    assert r["A"]["rating"] == pytest.approx(1509.42)
    assert r["B"]["rating"] == pytest.approx(1490.58)
    assert r["A"]["matches_considered"] == 2


def test_ratings_sum_is_conserved():
    games = [
        m("A", "B", 2, 0, "2026-01-01"),
        m("B", "C", 1, 3, "2026-01-08"),
        m("C", "A", 0, 0, "2026-01-15"),
        m("A", "C", 1, 2, "2026-01-22"),
        m("B", "A", 4, 1, "2026-01-29"),
        m("C", "B", 2, 2, "2026-02-05"),
    ]
    r = compute_elo_ratings(games)
    assert sum(v["rating"] for v in r.values()) == pytest.approx(4500, abs=0.05)


def test_upset_gives_more_than_an_expected_win():
    r = compute_elo_ratings([m("A", "B", 2, 0, "2026-01-01"), m("B", "A", 1, 0, "2026-01-08")])
    assert r["B"]["rating"] > 1500  # venceu o favorito: sobe mais do que os 10 pontos que perdeu


def test_input_order_does_not_matter():
    games = [m("A", "B", 2, 0, f"2026-01-{d:02d}") for d in range(1, 9)]
    games[3] = m("B", "A", 3, 1, "2026-01-04")
    shuffled = games[:]
    random.Random(0).shuffle(shuffled)
    assert compute_elo_ratings(games) == compute_elo_ratings(shuffled)
