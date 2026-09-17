"""Busca de partidas finalizadas para alimentar os cálculos de analytics."""

from __future__ import annotations

from infrastructure.supabase import get_supabase_client
from calculations.rolling_stats import TeamMatchResult


def get_finished_matches_for_team(competition_id: str, team_id: str) -> list[TeamMatchResult]:
    """
    Retorna os resultados de um time numa competição, do ponto de
    vista dele (goals_for/goals_against relativos ao próprio time),
    ordenados do mais recente para o mais antigo.
    """
    client = get_supabase_client()

    result = (
        client.table("matches")
        .select("home_team_id, away_team_id, home_score, away_score, match_date, status")
        .eq("competition_id", competition_id)
        .or_(f"home_team_id.eq.{team_id},away_team_id.eq.{team_id}")
        .not_.is_("home_score", "null")
        .not_.is_("away_score", "null")
        .order("match_date", desc=True)
        .execute()
    )

    matches = [
        m for m in result.data
        if m["status"] and ("Finish" in m["status"] or m["status"] == "finished")
    ]

    results: list[TeamMatchResult] = []
    for m in matches:
        if m["home_team_id"] == team_id:
            results.append(TeamMatchResult(goals_for=m["home_score"], goals_against=m["away_score"]))
        else:
            results.append(TeamMatchResult(goals_for=m["away_score"], goals_against=m["home_score"]))

    return results
