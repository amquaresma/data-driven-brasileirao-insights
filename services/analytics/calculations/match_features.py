"""
Features pré-jogo para ML, sem vazamento de dados: para cada partida, o estado
de cada time (Elo, forma, médias, descanso) é calculado SÓ com jogos anteriores.
Jogos da mesma data usam o mesmo estado (todos calculados antes de atualizar).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from calculations.elo import INITIAL_RATING, K_FACTOR, _expected_score
from calculations.rolling_stats import (
    TeamMatchResult,
    compute_rolling_average,
    compute_weighted_form_score,
)

MIN_HISTORY = 5


@dataclass
class FeatureMatch:
    match_id: str
    competition_id: str
    match_date: str  # YYYY-MM-DD
    match_time: str | None
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int


def _team_block(prefix, team_id, day, history, last_played, ratings) -> dict:
    past = history[team_id]
    r5 = compute_rolling_average(past, 5)
    form = compute_weighted_form_score(past)
    prev = last_played.get(team_id)
    rest = (date.fromisoformat(day) - date.fromisoformat(prev)).days if prev else None
    return {
        f"{prefix}_elo": round(ratings[team_id], 2),
        f"{prefix}_matches_played": len(past),
        f"{prefix}_form": form["weighted_form_score"],
        f"{prefix}_gf_avg5": r5["goals_for_avg"],
        f"{prefix}_ga_avg5": r5["goals_against_avg"],
        f"{prefix}_pts_avg5": r5["points_avg"],
        f"{prefix}_rest_days": rest,
    }


def _row(m: FeatureMatch, history, last_played, ratings) -> dict:
    row = {
        "match_id": m.match_id,
        "competition_id": m.competition_id,
        "match_date": m.match_date,
        "home_team_id": m.home_team_id,
        "away_team_id": m.away_team_id,
    }
    row.update(_team_block("home", m.home_team_id, m.match_date, history, last_played, ratings))
    row.update(_team_block("away", m.away_team_id, m.match_date, history, last_played, ratings))
    row["elo_diff"] = round(row["home_elo"] - row["away_elo"], 2)
    row["min_history_ok"] = (
        row["home_matches_played"] >= MIN_HISTORY and row["away_matches_played"] >= MIN_HISTORY
    )
    total = m.home_score + m.away_score
    row.update(
        home_goals=m.home_score,
        away_goals=m.away_score,
        total_goals=total,
        result="H" if m.home_score > m.away_score else ("D" if m.home_score == m.away_score else "A"),
        over_2_5=total >= 3,
    )
    return row


def _update(m: FeatureMatch, history, last_played, ratings) -> None:
    history[m.home_team_id].insert(0, TeamMatchResult(m.home_score, m.away_score))
    history[m.away_team_id].insert(0, TeamMatchResult(m.away_score, m.home_score))
    last_played[m.home_team_id] = m.match_date
    last_played[m.away_team_id] = m.match_date

    actual_home = 1.0 if m.home_score > m.away_score else (0.5 if m.home_score == m.away_score else 0.0)
    exp_home = _expected_score(ratings[m.home_team_id], ratings[m.away_team_id])
    ratings[m.home_team_id] += K_FACTOR * (actual_home - exp_home)
    ratings[m.away_team_id] += K_FACTOR * ((1.0 - actual_home) - (1.0 - exp_home))


def build_match_features(matches: list[FeatureMatch]) -> list[dict]:
    ordered = sorted(matches, key=lambda m: (m.match_date, m.match_time or ""))
    history: dict[str, list[TeamMatchResult]] = defaultdict(list)  # mais recente primeiro
    last_played: dict[str, str] = {}
    ratings: dict[str, float] = defaultdict(lambda: INITIAL_RATING)

    rows: list[dict] = []
    i = 0
    while i < len(ordered):
        j = i
        while j < len(ordered) and ordered[j].match_date == ordered[i].match_date:
            j += 1
        day = ordered[i:j]
        for m in day:  # 1) features com o estado anterior à data
            rows.append(_row(m, history, last_played, ratings))
        for m in day:  # 2) só então atualiza o estado
            _update(m, history, last_played, ratings)
        i = j
    return rows
