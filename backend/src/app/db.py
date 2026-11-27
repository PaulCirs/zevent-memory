from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Moteur SQLAlchemy partagé : il garde un pool de connexions à PostgreSQL."""
    # pool_pre_ping : vérifie qu'une connexion du pool est encore vivante avant de la donner.
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False : les objets restent lisibles après un commit.
    # En async, les relire déclencherait une requête implicite, interdite hors `await`.
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dépendance FastAPI : une session par requête HTTP, fermée à la fin de la requête."""
    async with get_sessionmaker()() as session:
        yield session
