from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.supabase import get_supabase_client
from app.api.routes import competitions, teams

app = FastAPI(
    title="Data-Driven Brasileirão Insights API",
    description=(
        "Backend para coleta, análise estatística "
        "e Machine Learning aplicado ao futebol brasileiro."
    ),
    version="0.1.0",
)

# CORS liberado para qualquer origem em desenvolvimento. Em produção,
# isso deve ser restrito ao(s) domínio(s) real(is) do frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(competitions.router)
app.include_router(teams.router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "dbi-api",
        "version": "0.1.0",
    }


@app.get("/health/supabase")
async def health_check_supabase():
    try:
        client = get_supabase_client()
        return {
            "status": "ok",
            "supabase_url_configured": bool(client),
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
        }
