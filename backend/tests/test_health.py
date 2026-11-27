from collections.abc import AsyncIterator

import pytest
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
async def base_injoignable() -> AsyncIterator[None]:
    """Remplace la session par une qui pointe vers un port où rien n'écoute."""
    engine = create_async_engine(
        "postgresql+asyncpg://x:x@127.0.0.1:1/x", connect_args={"timeout": 1}
    )

    async def session_injoignable() -> AsyncIterator[AsyncSession]:
        async with async_sessionmaker(engine)() as session:
            yield session

    app.dependency_overrides[get_session] = session_injoignable
    yield
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_health_renvoie_ok_quand_la_base_repond(client: AsyncClient) -> None:
    # Nécessite PostgreSQL lancé (docker compose up -d) et un .env rempli.
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


@pytest.mark.usefixtures("base_injoignable")
async def test_health_renvoie_503_quand_la_base_ne_repond_pas(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "injoignable"}
