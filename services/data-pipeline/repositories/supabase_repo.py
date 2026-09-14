"""
Camada de persistência: recebe dados já normalizados e faz upsert
no Supabase, respeitando as chaves únicas definidas em
database/migrations/0001_core_schema.sql.

Não conhece nada sobre a fonte (campeonato-brasileiro-api) — recebe
apenas dicts já no formato das tabelas.
"""

from __future__ import annotations

from typing import Any

from infrastructure.supabase import get_supabase_client


def upsert_competition(competition: dict[str, Any]) -> str:
    """Upsert em `competitions` por (code, season). Retorna o id (UUID)."""
    client = get_supabase_client()

    result = (
        client.table("competitions")
        .upsert(competition, on_conflict="code,season")
        .execute()
    )
    return result.data[0]["id"]


def upsert_group(competition_id: str, external_id: str, name: str) -> str:
    """Upsert em `groups` por (competition_id, external_id). Retorna o id (UUID)."""
    client = get_supabase_client()

    payload = {
        "competition_id": competition_id,
        "external_id": external_id,
        "name": name,
    }

    result = (
        client.table("groups")
        .upsert(payload, on_conflict="competition_id,external_id")
        .execute()
    )
    return result.data[0]["id"]


def upsert_team(team_data: dict[str, Any], external_id_data: dict[str, Any]) -> str:
    """
    Upsert de time + reconciliação de external_id.

    Estratégia:
    1. Verifica se já existe um team_external_ids para (provider, external_id).
    2. Se existir, reaproveita o team_id e atualiza os dados do time.
    3. Se não existir, cria o time e o external_id vinculado.

    Retorna o id (UUID) do time.
    """
    client = get_supabase_client()

    existing = (
        client.table("team_external_ids")
        .select("team_id")
        .eq("provider", external_id_data["provider"])
        .eq("external_id", external_id_data["external_id"])
        .execute()
    )

    if existing.data:
        team_id = existing.data[0]["team_id"]
        client.table("teams").update(team_data).eq("id", team_id).execute()
        return team_id

    team_result = client.table("teams").insert(team_data).execute()
    team_id = team_result.data[0]["id"]

    client.table("team_external_ids").insert(
        {**external_id_data, "team_id": team_id}
    ).execute()

    return team_id


def upsert_standings_entry(
    *,
    competition_id: str,
    team_id: str,
    group_id: str | None,
    entry: dict[str, Any],
) -> None:
    """Upsert em `standings_entries` por (competition_id, group_id, team_id)."""
    client = get_supabase_client()

    payload = {
        "competition_id": competition_id,
        "group_id": group_id,
        "team_id": team_id,
        "table_name": entry["table_name"],
        "position": entry["position"],
        "points": entry["points"],
        "matches_played": entry["matches_played"],
        "wins": entry["wins"],
        "draws": entry["draws"],
        "losses": entry["losses"],
        "goals_for": entry["goals_for"],
        "goals_against": entry["goals_against"],
        "goal_difference": entry["goal_difference"],
        "efficiency": entry["efficiency"],
        "movement": entry["movement"],
        "recent_form": entry["recent_form"],
        "legend": entry["legend"],
        "source_provider": entry["source_provider"],
    }

    client.table("standings_entries").upsert(
        payload,
        on_conflict="competition_id,group_id,team_id",
    ).execute()


def upsert_round(
    *,
    competition_id: str,
    group_id: str | None,
    round_data: dict[str, Any],
) -> str:
    """Upsert em `rounds` por (competition_id, group_id, number). Retorna o id (UUID)."""
    client = get_supabase_client()

    payload = {
        "competition_id": competition_id,
        "group_id": group_id,
        "external_id": round_data["external_id"],
        "number": round_data["number"],
        "total": round_data["total"],
        "label": round_data["label"],
    }

    result = (
        client.table("rounds")
        .upsert(payload, on_conflict="competition_id,group_id,number")
        .execute()
    )
    return result.data[0]["id"]


def upsert_match(
    *,
    match_data: dict[str, Any],
    competition_id: str,
    round_id: str,
    home_team_id: str,
    away_team_id: str,
) -> str:
    """Upsert em `matches` por (provider, external_id). Retorna o id (UUID)."""
    client = get_supabase_client()

    payload = {
        **match_data,
        "competition_id": competition_id,
        "round_id": round_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
    }

    result = (
        client.table("matches")
        .upsert(payload, on_conflict="provider,external_id")
        .execute()
    )
    return result.data[0]["id"]
