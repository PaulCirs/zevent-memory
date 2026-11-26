from fastapi import FastAPI

app = FastAPI(title="ZEvent Memory")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Indique que l'API répond. Sert aux tests, à la CI et plus tard au monitoring."""
    return {"status": "ok"}
