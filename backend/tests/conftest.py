from collections.abc import AsyncIterator

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.db import get_engine
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    # Les tests async tournent sous asyncio uniquement (anyio essaierait aussi trio).
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Client HTTP qui appelle l'application directement, sans lancer de serveur."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    # Chaque test a sa propre boucle d'événements : on vide le pool pour ne pas
    # réutiliser dans le test suivant une connexion ouverte dans cette boucle.
    await get_engine().dispose()
