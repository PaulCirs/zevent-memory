from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_engine, get_session


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    # À l'arrêt du serveur : ferme proprement les connexions du pool.
    await get_engine().dispose()


app = FastAPI(title="ZEvent Memory", lifespan=lifespan)


@app.get("/api/health")
async def health(
    response: Response, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, str]:
    """Indique si l'API et la base répondent. Sert aux tests, à la CI et plus tard au monitoring."""
    try:
        await session.execute(text("SELECT 1"))
    except OSError:
        # Base injoignable : connexion refusée, hôte introuvable ou délai dépassé
        # (TimeoutError et ConnectionRefusedError héritent tous deux d'OSError).
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "injoignable"}
    return {"status": "ok", "database": "ok"}
