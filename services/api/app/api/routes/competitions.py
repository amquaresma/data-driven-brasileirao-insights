from fastapi import APIRouter, HTTPException

from app.infrastructure.supabase import get_supabase_client
from app.schemas.competition import CompetitionOut
from app.schemas.match import MatchOut
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
