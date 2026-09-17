"""
Índice de volatilidade: mede o quão instável é o desempenho recente
de um time, via desvio padrão de pontos e saldo de gols por partida.

Fórmula é uma combinação simples (média dos dois desvios), documentada
como heurística inicial — o próprio plano do projeto previa refinar
isso depois de observar dados reais suficientes.
"""

from __future__ import annotations

import statistics

from calculations.rolling_stats import TeamMatchResult

DEFAULT_WINDOW = 10


def compute_volatility(
    results: list[TeamMatchResult], window: int = DEFAULT_WINDOW
) -> dict[str, float | int | None]:
    window_results = results[:window]
    n = len(window_results)

    if n < 2:
        # desvio padrão não é significativo com menos de 2 amostras
        return {
            "matches_considered": n,
            "points_stddev": None,
            "goal_difference_stddev": None,
            "volatility_index": None,
        }

    points = [r.points for r in window_results]
    goal_diffs = [r.goals_for - r.goals_against for r in window_results]

    points_stddev = statistics.pstdev(points)
    goal_diff_stddev = statistics.pstdev(goal_diffs)

    volatility_index = (points_stddev + goal_diff_stddev) / 2

    return {
        "matches_considered": n,
        "points_stddev": round(points_stddev, 2),
        "goal_difference_stddev": round(goal_diff_stddev, 2),
        "volatility_index": round(volatility_index, 2),
    }
