from fastapi import APIRouter, HTTPException

from app.infrastructure.supabase import get_supabase_client
from app.schemas.competition import CompetitionOut
from app.schemas.match import MatchOut
from app.schemas.match_detail import MatchDetailOut
from app.schemas.standings import StandingsEntryOut
from app.schemas.team import TeamOut

router = APIRouter(prefix="/competitions", tags=["competitions"])


def _get_latest_competition(code: str) -> dict:
    """
    Busca a competição mais recente (maior season) para o código
    informado ('a', 'b', 'c', 'd').
    """
    client = get_supabase_client()

    result = (
        client.table("competitions")
        .select("*")
        .eq("code", code)
        .order("season", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Competição '{code}' não encontrada.")

    return result.data[0]


@router.get("", response_model=list[CompetitionOut])
def list_competitions():
    """Lista a edição mais recente de cada série (A, B, C, D)."""
    competitions = []
    for code in ("a", "b", "c", "d"):
        client = get_supabase_client()
        result = (
            client.table("competitions")
            .select("*")
            .eq("code", code)
            .order("season", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            competitions.append(result.data[0])
    return competitions


@router.get("/{code}/standings", response_model=list[StandingsEntryOut])
def get_standings(code: str):
    """
    Retorna a classificação da edição mais recente da série informada.
    Se a competição estiver agrupada, cada entry inclui `group_name`.
    """
    competition = _get_latest_competition(code)

    client = get_supabase_client()
    result = (
        client.table("standings_entries")
        .select("*, team:teams!standings_entries_team_id_fkey(*), group:groups(name)")
        .eq("competition_id", competition["id"])
        .order("position")
        .execute()
    )

    entries = []
    for row in result.data:
        group = row.pop("group", None) or {}
        row["group_name"] = group.get("name")
        entries.append(row)

    return entries


@router.get("/{code}/matches", response_model=list[MatchOut])
def get_matches(code: str, round_number: int | None = None):
    """
    Retorna as partidas da edição mais recente da série informada.
    Filtro opcional por número da rodada via ?round_number=27.
    """
    competition = _get_latest_competition(code)

    client = get_supabase_client()
    query = (
        client.table("matches")
        .select(
            "*, "
            "home_team:teams!matches_home_team_id_fkey(*), "
            "away_team:teams!matches_away_team_id_fkey(*), "
            "round:rounds(number)"
        )
        .eq("competition_id", competition["id"])
    )

    result = query.execute()

    matches = result.data
    if round_number is not None:
        matches = [m for m in matches if (m.get("round") or {}).get("number") == round_number]

    return matches


@router.get("/matches/{match_id}/detail", response_model=MatchDetailOut)
def get_match_detail(match_id: str):
    """
    Retorna o detalhe completo de uma partida: dados básicos,
    estatísticas por time (quando disponíveis via Highlightly) e
    eventos (gols, cartões, substituições).
    """
    client = get_supabase_client()

    match_result = (
        client.table("matches")
        .select(
            "*, "
            "home_team:teams!matches_home_team_id_fkey(*), "
            "away_team:teams!matches_away_team_id_fkey(*)"
        )
        .eq("id", match_id)
        .limit(1)
        .execute()
    )
    if not match_result.data:
        raise HTTPException(status_code=404, detail="Partida não encontrada.")

    match = match_result.data[0]

    stats_result = (
        client.table("match_statistics")
        .select("stat_name, stat_value, team:teams(*)")
        .eq("match_id", match_id)
        .execute()
    )

    stats_by_team: dict[str, dict] = {}
    for row in stats_result.data:
        team = row["team"]
        team_id = team["id"]
        if team_id not in stats_by_team:
            stats_by_team[team_id] = {"team": team, "statistics": []}
        stats_by_team[team_id]["statistics"].append(
            {"stat_name": row["stat_name"], "stat_value": row["stat_value"]}
        )

    events_result = (
        client.table("match_events")
        .select("minute, event_type, team_id, player_name, assisting_player_name, substituted_player_name")
        .eq("match_id", match_id)
        .execute()
    )

    match["statistics"] = list(stats_by_team.values())
    match["events"] = events_result.data

    return match
