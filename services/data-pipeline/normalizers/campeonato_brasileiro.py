"""
Normaliza o JSON cru retornado pela campeonato-brasileiro-api em
estruturas prontas para persistência, alinhadas ao schema definido em
database/migrations/0001_core_schema.sql.

Cada função aqui é pura: recebe o dict cru e devolve dict(s) normalizados.
Nenhuma chamada de rede ou banco acontece neste módulo.
"""

from __future__ import annotations

from typing import Any

PROVIDER = "campeonato-brasileiro-api"


def normalize_competition(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Recebe o objeto `competition` (de dentro do payload de
    getStandings/getCompetition) e retorna o dict pronto para
    upsert na tabela `competitions`.
    """
    competition = raw["competition"]
    phase = competition.get("phase") or {}
    edition = competition.get("edition") or {}
    source = competition.get("source") or {}

    return {
        "code": competition["code"],
        "season": competition["season"],
        "name": competition["name"],
        "slug": competition.get("slug"),
        "sport": competition.get("sport"),
        "grouped": raw.get("grouped", competition.get("grouped", False)),
        "phase_slug": phase.get("slug"),
        "phase_description": phase.get("description"),
        "phase_type_id": phase.get("typeId"),
        "edition_name": edition.get("name"),
        "edition_location": edition.get("location"),
        "edition_starts_at": edition.get("startsAt"),
        "edition_ends_at": edition.get("endsAt"),
        "source_provider": source.get("provider"),
        "source_url": source.get("url"),
        "source_resource_id": source.get("resourceId"),
    }


def normalize_team(team: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Recebe um objeto `team` (como aparece dentro de standings entries
    ou matches) e retorna uma tupla:
      (dados_do_team, dados_do_team_external_id)

    O external_id vem como int na fonte — convertemos para str, já
    que nossa coluna é text (outros providers podem usar strings).
    """
    team_data = {
        "name": team["name"],
        "short_name": team.get("shortName"),
        "badge_url": team.get("badge"),
    }
    external_id_data = {
        "provider": PROVIDER,
        "external_id": str(team["id"]),
    }
    return team_data, external_id_data


def normalize_standings_entries(
    standings_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Recebe o payload completo de getStandings()/getCompetition() e
    retorna uma lista de dicts, um por entry de classificação, com
    os dados ainda "crus" de time (a resolução do team_id UUID
    interno acontece na camada de persistência, depois do upsert
    de teams/team_external_ids).

    Cada item retornado tem o formato:
    {
        "table_name": str,
        "team": {...},              # objeto team cru da fonte
        "position": int,
        "points": int | None,
        ...
    }
    """
    entries: list[dict[str, Any]] = []

    for table in standings_payload.get("tables", []):
        table_name = table.get("name")

        for entry in table.get("entries", []):
            legend = entry.get("legend") or {}

            entries.append(
                {
                    "table_name": table_name,
                    "team": entry["team"],
                    "position": entry["position"],
                    "points": entry.get("points"),
                    "matches_played": entry.get("matches"),
                    "wins": entry.get("wins"),
                    "draws": entry.get("draws"),
                    "losses": entry.get("losses"),
                    "goals_for": entry.get("goalsFor"),
                    "goals_against": entry.get("goalsAgainst"),
                    "goal_difference": entry.get("goalDifference"),
                    "efficiency": entry.get("efficiency"),
                    "movement": str(entry["movement"]) if entry.get("movement") is not None else None,
                    "recent_form": entry.get("recentForm"),
                    "legend": legend.get("name"),
                    "source_provider": PROVIDER,
                }
            )

    return entries
