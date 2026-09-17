"""
Calcula e persiste rolling averages (janelas 3/5/10) e forma
ponderada para todos os times de uma competição.

Uso:
    python compute_rolling_stats.py a
"""

from __future__ import annotations

import argparse

from repositories.matches_repo import get_finished_matches_for_team
from repositories.analytics_repo import (
    get_all_teams_in_competition,
    upsert_rolling_stats,
    upsert_form_score,
    upsert_streaks,
    upsert_volatility,
    upsert_momentum,
    get_all_finished_matches_for_elo,
    upsert_elo_ratings,
)
from calculations.rolling_stats import compute_rolling_average, compute_weighted_form_score
from calculations.streaks import compute_streaks
from calculations.volatility import compute_volatility
from calculations.momentum import compute_momentum
from calculations.elo import compute_elo_ratings, EloMatchInput
from infrastructure.supabase import get_supabase_client

WINDOW_SIZES = [3, 5, 10]


def compute_for_competition(code: str, season: int = 2026) -> None:
    client = get_supabase_client()
    comp = (
        client.table("competitions")
        .select("id")
        .eq("code", code)
        .eq("season", season)
        .limit(1)
        .execute()
    )
    if not comp.data:
        print(f"Competição (code={code}, season={season}) não encontrada.")
        return

    competition_id = comp.data[0]["id"]
    team_ids = get_all_teams_in_competition(competition_id)
    print(f"Processando {len(team_ids)} times da competição {code.upper()}...")

    for team_id in team_ids:
        results = get_finished_matches_for_team(competition_id, team_id)

        for window in WINDOW_SIZES:
            stats = compute_rolling_average(results, window)
            upsert_rolling_stats(competition_id, team_id, window, stats)

        form = compute_weighted_form_score(results)
        upsert_form_score(competition_id, team_id, form)

        streaks = compute_streaks(results)
        upsert_streaks(competition_id, team_id, streaks)

        volatility = compute_volatility(results)
        upsert_volatility(competition_id, team_id, volatility)

        momentum = compute_momentum(results)
        upsert_momentum(competition_id, team_id, momentum, form["weighted_form_score"])

    print("Calculando Elo ratings (processamento cronológico da competição inteira)...")
    raw_matches = get_all_finished_matches_for_elo(competition_id)
    elo_inputs = [
        EloMatchInput(
            home_team_id=m["home_team_id"],
            away_team_id=m["away_team_id"],
            home_score=m["home_score"],
            away_score=m["away_score"],
            match_date=m["match_date"],
        )
        for m in raw_matches
    ]
    elo_ratings = compute_elo_ratings(elo_inputs)
    upsert_elo_ratings(competition_id, elo_ratings)

    print("Concluído.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula rolling stats e forma recente.")
    parser.add_argument("serie", choices=["a", "b", "c", "d"])
    parser.add_argument("--season", type=int, default=2026)
    args = parser.parse_args()

    compute_for_competition(args.serie, args.season)
