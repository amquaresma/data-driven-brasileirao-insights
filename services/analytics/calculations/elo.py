"""
Sistema de Elo rating global e simples (sem ajuste de mando de campo
ainda — conforme o plano original: "Inicialmente: Elo global").

Processa todas as partidas finalizadas de uma competição em ORDEM
CRONOLÓGICA, atualizando os ratings de ambos os times a cada jogo.
"""

from __future__ import annotations

from dataclasses import dataclass

INITIAL_RATING = 1500.0
K_FACTOR = 20.0  # constante inicial; ajustável conforme calibração futura


@dataclass
class EloMatchInput:
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    match_date: str


def _expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def compute_elo_ratings(
    matches: list[EloMatchInput],
    initial_rating: float = INITIAL_RATING,
    k_factor: float = K_FACTOR,
) -> dict[str, dict[str, float | int]]:
    """
    Retorna {team_id: {"rating": float, "matches_considered": int}}.

    A função ordena as partidas por match_date internamente, então
    não depende da ordem em que foram passadas.
    """
    sorted_matches = sorted(matches, key=lambda m: m.match_date)

    ratings: dict[str, float] = {}
    matches_played: dict[str, int] = {}

    for m in sorted_matches:
        home_rating = ratings.setdefault(m.home_team_id, initial_rating)
        away_rating = ratings.setdefault(m.away_team_id, initial_rating)

        if m.home_score > m.away_score:
            actual_home = 1.0
        elif m.home_score == m.away_score:
            actual_home = 0.5
        else:
            actual_home = 0.0
        actual_away = 1.0 - actual_home

        expected_home = _expected_score(home_rating, away_rating)
        expected_away = 1.0 - expected_home

        ratings[m.home_team_id] = home_rating + k_factor * (actual_home - expected_home)
        ratings[m.away_team_id] = away_rating + k_factor * (actual_away - expected_away)

        matches_played[m.home_team_id] = matches_played.get(m.home_team_id, 0) + 1
        matches_played[m.away_team_id] = matches_played.get(m.away_team_id, 0) + 1

    return {
        team_id: {
            "rating": round(rating, 2),
            "matches_considered": matches_played.get(team_id, 0),
        }
        for team_id, rating in ratings.items()
    }
