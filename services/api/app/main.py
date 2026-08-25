from fastapi import FastAPI


app = FastAPI(
    title="Data-Driven Brasileirão Insights API",
    description=(
        "Backend para coleta, análise estatística "
        "e Machine Learning aplicado ao futebol brasileiro."
    ),
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "dbi-api",
        "version": "0.1.0",
    }