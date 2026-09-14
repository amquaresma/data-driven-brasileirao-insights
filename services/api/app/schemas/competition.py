from pydantic import BaseModel


class CompetitionOut(BaseModel):
    id: str
    code: str
    season: int
    name: str
    grouped: bool
    phase_description: str | None = None
