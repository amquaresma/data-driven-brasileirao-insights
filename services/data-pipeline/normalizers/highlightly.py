"""
Normaliza dados crus da Highlightly Football API para os formatos
usados nas tabelas do nosso schema.
"""

from __future__ import annotations

import re
from typing import Any

PROVIDER = "highlightly"


def parse_round_number(round_label: str) -> int | None:
    """
    Extrai o número da rodada de labels como "Regular Season - 4".
    Retorna None se não conseguir extrair (ex: fases de mata-mata
    com nomes não numéricos) — não inventamos um número nesse caso.
    """
    match = re.search(r"(\d+)\s*$", round_label)
    return int(match.group(1)) if match else None


def parse_score(score_str: str | None) -> tuple[int | None, int | None]:
    """Converte "3 - 1" em (3, 1). Retorna (None, None) se vazio/inválido."""
    if not score_str:
        return None, None
    parts = score_str.split(" - ")
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def normalize_match(hl_match: dict[str, Any]) -> dict[str, Any]:
    """Retorna o dict pronto para upsert em `matches` (campos comuns)."""
    date_time = hl_match.get("date")
    match_date = date_time.split("T")[0] if date_time else None
    match_time = date_time.split("T")[1][:5] if date_time else None

    state = hl_match.get("state") or {}
    score = state.get("score") or {}
    home_score, away_score = parse_score(score.get("current"))
    penalties_home, penalties_away = parse_score(score.get("penalties"))

    description = state.get("description")
    not_started_states = {"To be announced", "Not started", "Postponed", "Cancelled"}

    return {
        "provider": PROVIDER,
        "external_id": str(hl_match["id"]),
        "date_time": date_time,
        "match_date": match_date,
        "match_time": match_time,
        "started": description not in not_started_states,
        "status": description,
        "status_code": description,
        "home_score": home_score,
        "away_score": away_score,
        "penalties_home": penalties_home,
        "penalties_away": penalties_away,
    }


def normalize_round(hl_match: dict[str, Any]) -> dict[str, Any]:
    """
    Retorna o dict pronto para get_or_create de `rounds`, a partir do
    campo `round` (string) da partida da Highlightly.
    """
    round_label = hl_match.get("round", "")
    return {
        "external_id": None,  # Highlightly não expõe um id de rodada dedicado
        "number": parse_round_number(round_label),
        "total": None,
        "label": round_label,
    }


def normalize_match_statistics(match_detail: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Recebe o detalhe completo de uma partida e retorna uma lista de
    dicts {highlightly_team_id, stat_name, stat_value}, uma por
    estatística de cada time (formato EAV, já que a fonte usa
    displayName aberto em vez de campos fixos).
    """
    entries: list[dict[str, Any]] = []

    for team_block in match_detail.get("statistics", []):
        team_id = team_block["team"]["id"]
        for stat in team_block.get("statistics", []):
            entries.append(
                {
                    "highlightly_team_id": team_id,
                    "stat_name": stat["displayName"],
                    "stat_value": stat["value"],
                }
            )

    return entries


def normalize_match_events(match_detail: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Recebe o detalhe completo de uma partida e retorna uma lista de
    dicts prontos para a tabela `match_events`.
    """
    events: list[dict[str, Any]] = []

    for event in match_detail.get("events", []):
        team = event.get("team") or {}
        events.append(
            {
                "highlightly_team_id": team.get("id"),
                "minute": event.get("time"),
                "event_type": event.get("type"),
                "player_name": event.get("player"),
                "player_external_id": (
                    str(event["playerId"]) if event.get("playerId") is not None else None
                ),
                "assisting_player_name": event.get("assist"),
                "assisting_player_external_id": (
                    str(event["assistingPlayerId"])
                    if event.get("assistingPlayerId") is not None
                    else None
                ),
                "substituted_player_name": event.get("substituted"),
            }
        )

    return events


def _parse_percentage(value: str | None) -> float | None:
    """Converte "78.57 %" em 78.57. Retorna None se vazio/inválido."""
    if not value:
        return None
    try:
        return float(value.replace("%", "").strip())
    except ValueError:
        return None


def _parse_rating(value: str | None) -> float | None:
    """Converte "6.90" em 6.9. Retorna None se vazio/inválido."""
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def normalize_player_box_score(match_detail_box_score: list[dict]) -> list[dict]:
    """
    Recebe a resposta de /box-score/{matchId} (lista de blocos por
    time) e retorna uma lista achatada de dicts, um por jogador,
    prontos para persistência em player_match_statistics.
    """
    rows: list[dict] = []

    for team_block in match_detail_box_score:
        highlightly_team_id = team_block["team"]["id"]

        for player in team_block.get("players", []):
            stats_list = player.get("statistics") or [{}]
            stats = stats_list[0] if stats_list else {}

            rows.append(
                {
                    "highlightly_team_id": highlightly_team_id,
                    "highlightly_player_id": player["id"],
                    "player_name": player["name"],
                    "player_full_name": player.get("fullName"),
                    "position": player.get("position"),
                    "shirt_number": player.get("shirtNumber"),
                    "is_captain": player.get("isCaptain"),
                    "is_substitute": player.get("isSubstitute"),
                    "minutes_played": player.get("minutesPlayed"),
                    "match_rating": _parse_rating(player.get("matchRating")),
                    "offsides": player.get("offsides"),
                    "goals_scored": stats.get("goalsScored"),
                    "goals_saved": stats.get("goalsSaved"),
                    "goals_conceded": stats.get("goalsConceded"),
                    "assists": stats.get("assists"),
                    "dribbles_total": stats.get("dribblesTotal"),
                    "dribbles_successful": stats.get("dribblesSuccessful"),
                    "dribbles_failed": stats.get("dribblesFailed"),
                    "dribble_success_rate": _parse_percentage(stats.get("dribbleSuccessRate")),
                    "fouled_by_others": stats.get("fouledByOthers"),
                    "fouled_others": stats.get("fouledOthers"),
                    "tackles_total": stats.get("tacklesTotal"),
                    "interceptions_total": stats.get("interceptionsTotal"),
                    "duels_total": stats.get("duelsTotal"),
                    "duels_won": stats.get("duelsWon"),
                    "duels_lost": stats.get("duelsLost"),
                    "duel_success_rate": _parse_percentage(stats.get("duelSuccessRate")),
                    "cards_red": stats.get("cardsRed"),
                    "cards_yellow": stats.get("cardsYellow"),
                    "cards_second_yellow": stats.get("cardsSecondYellow"),
                    "passes_accuracy": _parse_percentage(stats.get("passesAccuracy")),
                    "passes_successful": stats.get("passesSuccessful"),
                    "passes_failed": stats.get("passesFailed"),
                    "passes_total": stats.get("passesTotal"),
                    "passes_key": stats.get("passesKey"),
                    "penalties_scored": stats.get("penaltiesScored"),
                    "penalties_missed": stats.get("penaltiesMissed"),
                    "penalties_total": stats.get("penaltiesTotal"),
                    "penalties_accuracy": _parse_percentage(stats.get("penaltiesAccuracy")),
                    "shots_on_target": stats.get("shotsOnTarget"),
                    "shots_off_target": stats.get("shotsOffTarget"),
                    "shots_total": stats.get("shotsTotal"),
                    "shots_accuracy": _parse_percentage(stats.get("shotsAccuracy")),
                    "expected_goals": stats.get("expectedGoals"),
                    "expected_assists": stats.get("expectedAssists"),
                    "expected_goals_on_target": stats.get("expectedGoalsOnTarget"),
                    "expected_goals_on_target_conceded": stats.get("expectedGoalsOnTargetConceded"),
                    "expected_goals_prevented": stats.get("expectedGoalsPrevented"),
                }
            )

    return rows
