from fastapi import APIRouter

from app.infrastructure.supabase import get_supabase_client
from app.schemas.team import TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamOut])
def list_teams():
    """Lista todos os times cadastrados."""
    client = get_supabase_client()
    result = client.table("teams").select("*").order("name").execute()
    return result.data
