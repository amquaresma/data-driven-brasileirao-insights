from pydantic import BaseModel

from app.schemas.team import TeamOut


class TeamMetricsOut(BaseModel):
    team: TeamOut

    elo: float | None = None

    momentum_score: float | None = None
    attacking_trend: float | None = None
    defensive_trend: float | None = None
    points_trend: float | None = None

    weighted_form_score: float | None = None
    recent_form: list[str] | None = None

    win_streak: int | None = None
    unbeaten_streak: int | None = None
    clean_sheet_streak: int | None = None
    scoring_streak: int | None = None

    volatility_index: float | None = None

    goals_for_avg_5: float | None = None
    goals_against_avg_5: float | None = None
    points_avg_5: float | None = None
