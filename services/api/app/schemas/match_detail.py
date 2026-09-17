from pydantic import BaseModel

from app.schemas.team import TeamOut


class MatchStatisticOut(BaseModel):
    stat_name: str
    stat_value: float


class TeamStatisticsOut(BaseModel):
    team: TeamOut
    statistics: list[MatchStatisticOut]


class MatchEventOut(BaseModel):
    minute: str | None = None
    event_type: str
    team_id: str | None = None
    player_name: str | None = None
    assisting_player_name: str | None = None
    substituted_player_name: str | None = None


class MatchDetailOut(BaseModel):
    id: str
    match_date: str | None = None
    match_time: str | None = None
    venue: str | None = None
    status: str | None = None
    home_team: TeamOut
    away_team: TeamOut
    home_score: int | None = None
    away_score: int | None = None
    statistics: list[TeamStatisticsOut]
    events: list[MatchEventOut]
