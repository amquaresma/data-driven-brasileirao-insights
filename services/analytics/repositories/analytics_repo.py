"""Persistência dos resultados de analytics."""

from __future__ import annotations

from typing import Any

from infrastructure.supabase import get_supabase_client


def get_all_teams_in_competition(competition_id: str) -> list[str]:
    """Retorna os team_ids distintos que já jogaram na competição."""
    client = get_supabase_client()
    result = (
        client.table("matches")
        .select("home_team_id, away_team_id")
        .eq("competition_id", competition_id)
        .execute()
    )
    team_ids = set()
    for m in result.data:
        team_ids.add(m["home_team_id"])
        team_ids.add(m["away_team_id"])
    return list(team_ids)


def upsert_rolling_stats(
    competition_id: str, team_id: str, window_size: int, stats: dict[str, Any]
) -> None:
    if stats["matches_considered"] == 0:
        return  # nada a persistir sem dados

    client = get_supabase_client()
    client.table("team_rolling_stats").upsert(
        {
            "competition_id": competition_id,
            "team_id": team_id,
            "window_size": window_size,
            "matches_considered": stats["matches_considered"],
            "goals_for_avg": stats["goals_for_avg"],
            "goals_against_avg": stats["goals_against_avg"],
            "points_avg": stats["points_avg"],
        },
        on_conflict="competition_id,team_id,window_size",
    ).execute()


def upsert_form_score(competition_id: str, team_id: str, form: dict[str, Any]) -> None:
    if form["matches_considered"] == 0:
        return

    client = get_supabase_client()
    client.table("team_form_scores").upsert(
        {
            "competition_id": competition_id,
            "team_id": team_id,
            "recent_form": form["recent_form"],
            "weighted_form_score": form["weighted_form_score"],
            "matches_considered": form["matches_considered"],
        },
        on_conflict="competition_id,team_id",
    ).execute()


def upsert_streaks(competition_id: str, team_id: str, streaks: dict) -> None:
    if streaks["matches_considered"] == 0:
        return

    client = get_supabase_client()
    client.table("team_streaks").upsert(
        {
            "competition_id": competition_id,
            "team_id": team_id,
            **streaks,
        },
        on_conflict="competition_id,team_id",
    ).execute()


def upsert_volatility(competition_id: str, team_id: str, volatility: dict) -> None:
    if volatility["matches_considered"] < 2:
        return

    client = get_supabase_client()
    client.table("team_volatility").upsert(
        {
            "competition_id": competition_id,
            "team_id": team_id,
            **volatility,
        },
        on_conflict="competition_id,team_id",
    ).execute()


def upsert_momentum(competition_id: str, team_id: str, momentum: dict, weighted_form_score: float | None) -> None:
    if momentum["momentum_score"] is None:
        return

    client = get_supabase_client()
    client.table("team_momentum").upsert(
        {
            "competition_id": competition_id,
            "team_id": team_id,
            **momentum,
            "weighted_form_score": weighted_form_score,
        },
        on_conflict="competition_id,team_id",
    ).execute()


def get_all_finished_matches_for_elo(competition_id: str) -> list[dict]:
    """Todas as partidas finalizadas da competição, para cálculo de Elo global."""
    client = get_supabase_client()
    result = (
        client.table("matches")
        .select("home_team_id, away_team_id, home_score, away_score, match_date, status")
        .eq("competition_id", competition_id)
        .not_.is_("home_score", "null")
        .not_.is_("away_score", "null")
        .execute()
    )
    return [
        m for m in result.data
        if m["status"] and ("Finish" in m["status"] or m["status"] == "finished")
    ]


def upsert_elo_ratings(competition_id: str, ratings: dict[str, dict]) -> None:
    client = get_supabase_client()
    rows = [
        {
            "competition_id": competition_id,
            "team_id": team_id,
            "rating": data["rating"],
            "matches_considered": data["matches_considered"],
        }
        for team_id, data in ratings.items()
    ]
    if rows:
        client.table("team_elo_ratings").upsert(rows, on_conflict="competition_id,team_id").execute()
