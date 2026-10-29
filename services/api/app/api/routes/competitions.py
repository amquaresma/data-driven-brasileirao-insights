import re
from fastapi import APIRouter, HTTPException

from app.infrastructure.supabase import get_supabase_client
from app.schemas.competition import CompetitionOut
from app.schemas.match import MatchOut
from app.schemas.match_detail import MatchDetailOut
from app.schemas.analytics import TeamMetricsOut
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
        .select("*, team:teams!standings_entries_team_id_fkey(*), group:groups(name), phase:phases(name, phase_order)")
        .eq("competition_id", competition["id"])
        .order("position")
        .execute()
    )

    entries = []
    for row in result.data:
        group = row.pop("group", None) or {}
        row["group_name"] = group.get("name")
        phase = row.pop("phase", None) or {}
        row["phase_name"] = phase.get("name")
        row["phase_order"] = phase.get("phase_order")
        entries.append(row)

    def natural(text):
        return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text or "")]

    entries.sort(key=lambda e: (-(e["phase_order"] or 0), e["phase_name"] or "", natural(e["group_name"]), e["position"]))
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
            "round:rounds(number), "
            "phase:phases(name, phase_order)"
        )
        .eq("competition_id", competition["id"])
    )

    result = query.execute()

    matches = result.data
    if round_number is not None:
        matches = [m for m in matches if (m.get("round") or {}).get("number") == round_number]

    for m in matches:
        phase = m.pop("phase", None) or {}
        m["phase_name"] = phase.get("name")
        m["phase_order"] = phase.get("phase_order")

    # Só ordena quando há fases (mata-mata); séries sem fase mantêm a ordem atual.
    if any(m["phase_order"] for m in matches):
        matches.sort(
            key=lambda m: (
                -(m["phase_order"] or 0),
                m["phase_name"] or "",
                m.get("tie_key") or "",
                m.get("leg") or 0,
                m.get("match_date") or "",
            )
        )

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



def _rows_by_team(table: str, competition_id: str, extra_filter: tuple[str, int] | None = None) -> dict[str, dict]:
    client = get_supabase_client()
    query = (
        client.table(table)
        .select("*, team:teams(*)")
        .eq("competition_id", competition_id)
    )
    if extra_filter:
        query = query.eq(*extra_filter)
    return {row["team_id"]: row for row in query.execute().data}


@router.get("/{code}/team-metrics", response_model=list[TeamMetricsOut])
def get_team_metrics(code: str):
    """
    Métricas de Analytics por time (Elo, momentum, forma, streaks,
    volatilidade, médias dos últimos 5 jogos), ordenadas por Elo.
    Times sem alguma métrica vêm com o campo nulo, sem valor inventado.
    """
    competition = _get_latest_competition(code)
    cid = competition["id"]

    elo = _rows_by_team("team_elo_ratings", cid)
    momentum = _rows_by_team("team_momentum", cid)
    form = _rows_by_team("team_form_scores", cid)
    streaks = _rows_by_team("team_streaks", cid)
    volatility = _rows_by_team("team_volatility", cid)
    rolling5 = _rows_by_team("team_rolling_stats", cid, ("window_size", 5))

    team_ids = set(elo) | set(momentum) | set(form) | set(streaks) | set(volatility) | set(rolling5)

    result = []
    for team_id in team_ids:
        source = next(t[team_id] for t in (elo, momentum, form, streaks, volatility, rolling5) if team_id in t)
        m, f, s = momentum.get(team_id, {}), form.get(team_id, {}), streaks.get(team_id, {})
        v, r = volatility.get(team_id, {}), rolling5.get(team_id, {})
        result.append(
            {
                "team": source["team"],
                "elo": elo.get(team_id, {}).get("rating"),
                "momentum_score": m.get("momentum_score"),
                "attacking_trend": m.get("attacking_trend"),
                "defensive_trend": m.get("defensive_trend"),
                "points_trend": m.get("points_trend"),
                "weighted_form_score": f.get("weighted_form_score"),
                "recent_form": f.get("recent_form"),
                "win_streak": s.get("current_win_streak"),
                "unbeaten_streak": s.get("current_unbeaten_streak"),
                "clean_sheet_streak": s.get("current_clean_sheet_streak"),
                "scoring_streak": s.get("current_scoring_streak"),
                "volatility_index": v.get("volatility_index"),
                "goals_for_avg_5": r.get("goals_for_avg"),
                "goals_against_avg_5": r.get("goals_against_avg"),
                "points_avg_5": r.get("points_avg"),
            }
        )

    result.sort(key=lambda x: x["elo"] if x["elo"] is not None else 0, reverse=True)
    return result
