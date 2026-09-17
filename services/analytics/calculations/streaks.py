"""
Cálculo de streaks (sequências) a partir de uma lista de resultados
de um time, ordenados do MAIS RECENTE para o mais antigo.

Cada streak conta quantos jogos consecutivos, começando do mais
recente, satisfazem uma condição — parando no primeiro jogo que quebra
a sequência.
"""

from __future__ import annotations

from calculations.rolling_stats import TeamMatchResult


def _count_streak(results: list[TeamMatchResult], condition) -> int:
    count = 0
    for r in results:
        if condition(r):
            count += 1
        else:
            break
    return count


def compute_streaks(results: list[TeamMatchResult]) -> dict[str, int]:
    """
    Retorna um dict com todas as streaks atuais do time, calculadas
    a partir do jogo mais recente pra trás.
    """
    return {
        "matches_considered": len(results),
        "current_win_streak": _count_streak(results, lambda r: r.outcome_letter == "W"),
        "current_loss_streak": _count_streak(results, lambda r: r.outcome_letter == "L"),
        "current_draw_streak": _count_streak(results, lambda r: r.outcome_letter == "D"),
        "current_unbeaten_streak": _count_streak(results, lambda r: r.outcome_letter != "L"),
        "current_winless_streak": _count_streak(results, lambda r: r.outcome_letter != "W"),
        "current_clean_sheet_streak": _count_streak(results, lambda r: r.goals_against == 0),
        "current_scoring_streak": _count_streak(results, lambda r: r.goals_for > 0),
    }
