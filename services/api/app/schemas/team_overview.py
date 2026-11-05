from pydantic import BaseModel

from app.schemas.analytics import TeamMetricsOut
from app.schemas.match import MatchOut
from app.schemas.team import TeamOut


class TeamStandingOut(BaseModel):
    position: int | None = None
    points: int | None = None
    matches_played: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None
    goal_difference: int | None = None
    legend: str | None = None
    group_name: str | None = None
    phase_name: str | None = None


class UpcomingOut(MatchOut):
    p_home: float | None = None
    p_draw: float | None = None
    p_away: float | None = None
    p_over_2_5: float | None = None


class EloPointOut(BaseModel):
    match_date: str
    elo: float


class TeamOverviewOut(BaseModel):
    team: TeamOut
    standing: TeamStandingOut | None = None
    metrics: TeamMetricsOut | None = None
    recent: list[MatchOut] = []
    upcoming: list[UpcomingOut] = []
    elo_series: list[EloPointOut] = []
