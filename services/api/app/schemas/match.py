from pydantic import BaseModel

from app.schemas.team import TeamOut


class MatchOut(BaseModel):
    id: str
    match_date: str | None = None
    match_time: str | None = None
    venue: str | None = None
    status: str | None = None
    home_team: TeamOut
    away_team: TeamOut
    home_score: int | None = None
    away_score: int | None = None
    penalties_home: int | None = None
    penalties_away: int | None = None
    phase_name: str | None = None
    phase_order: int | None = None
    tie_key: str | None = None
    leg: int | None = None
