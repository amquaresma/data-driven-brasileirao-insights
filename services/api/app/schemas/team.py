from pydantic import BaseModel


class TeamOut(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    badge_url: str | None = None
