from pydantic import BaseModel

from app.schemas.team import TeamOut


class PredictionOut(BaseModel):
    match_id: str
    match_date: str | None = None
    match_time: str | None = None
    venue: str | None = None
    home_team: TeamOut
    away_team: TeamOut
    p_home: float
    p_draw: float
    p_away: float
    elo_diff: float | None = None
    model_version: str
    trained_on: int
    generated_at: str
