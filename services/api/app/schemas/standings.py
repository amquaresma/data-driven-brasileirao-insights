from pydantic import BaseModel

from app.schemas.team import TeamOut


class StandingsEntryOut(BaseModel):
    position: int
    team: TeamOut
    group_name: str | None = None
    points: int | None = None
    matches_played: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None
    goal_difference: int | None = None
    efficiency: float | None = None
    recent_form: list[str] | None = None
    legend: str | None = None
