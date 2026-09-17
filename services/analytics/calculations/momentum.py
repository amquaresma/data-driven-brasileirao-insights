"""
Índice de Momentum: combina tendência ofensiva, defensiva e de
pontos, comparando uma janela recente contra uma janela mais antiga
do mesmo time — mede se o desempenho está melhorando ou piorando.

Conforme o plano original, o cálculo exato é uma heurística inicial,
documentada e ajustável depois de observar dados reais.
"""

from __future__ import annotations

from calculations.rolling_stats import TeamMatchResult, compute_rolling_average

RECENT_WINDOW = 5
BASELINE_WINDOW = 10


def compute_momentum(results: list[TeamMatchResult]) -> dict[str, float | None]:
    """
    Compara a janela recente (últimos 5) contra a baseline (últimos
    10) para medir se o time está em ascensão ou queda.

    Trend positivo = melhorando na janela recente vs baseline.
    """
    recent = compute_rolling_average(results, RECENT_WINDOW)
    baseline = compute_rolling_average(results, BASELINE_WINDOW)

    if recent["matches_considered"] == 0 or baseline["matches_considered"] == 0:
        return {
            "attacking_trend": None,
            "defensive_trend": None,
            "points_trend": None,
            "momentum_score": None,
        }

    attacking_trend = round(recent["goals_for_avg"] - baseline["goals_for_avg"], 2)
    # defensivo: menos gols sofridos é melhor, então invertemos o sinal
    defensive_trend = round(baseline["goals_against_avg"] - recent["goals_against_avg"], 2)
    points_trend = round(recent["points_avg"] - baseline["points_avg"], 2)

    # Momentum score: soma ponderada simples das três tendências.
    # Pontos pesam mais (é o resultado que importa), ataque e defesa
    # entram com peso igual.
    momentum_score = round(points_trend * 2 + attacking_trend + defensive_trend, 2)

    return {
        "attacking_trend": attacking_trend,
        "defensive_trend": defensive_trend,
        "points_trend": points_trend,
        "momentum_score": momentum_score,
    }
