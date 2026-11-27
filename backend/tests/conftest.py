"""Fixtures communes aux tests.

Les tests tournent sur une base dédiée (`<base de dev>_test`), recréée et migrée au début
de chaque lancement de pytest. Chaque test travaille dans une transaction annulée à la fin :
rien de ce qu'il écrit n'est visible par les autres tests, et la base de dev n'est jamais touchée.
"""

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import URL, make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.db import get_engine, get_session
from app.main import app

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

# Exécuté au chargement de ce fichier, avant que l'appli ne lise sa configuration :
# toute l'appli (moteur, sessions, Alembic) utilisera la base de test.
URL_DEV = make_url(get_settings().database_url)
URL_TEST = URL_DEV.set(database=f"{URL_DEV.database}_test")
os.environ["DATABASE_URL"] = URL_TEST.render_as_string(hide_password=False)
get_settings.cache_clear()
get_engine.cache_clear()


@pytest.fixture
def anyio_backend() -> str:
    # Les tests async tournent sous asyncio uniquement (anyio essaierait aussi trio).
    return "asyncio"


async def _recreer_base(url_serveur: URL, nom: str) -> None:
    # Garde-fou : cette fonction efface une base, elle ne doit jamais viser autre chose.
    assert nom.endswith("_test"), f"refus d'effacer la base {nom!r}"
    # CREATE/DROP DATABASE ne peuvent pas tourner dans une transaction : mode AUTOCOMMIT.
    engine = create_async_engine(url_serveur, isolation_level="AUTOCOMMIT")
    async with engine.connect() as connection:
        # WITH (FORCE) : coupe les connexions restées ouvertes (ex. pytest interrompu).
        await connection.execute(text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'))
        await connection.execute(text(f'CREATE DATABASE "{nom}"'))
    await engine.dispose()


@pytest.fixture(scope="session")
def base_de_test() -> None:
    """Une fois par lancement de pytest : base de test vide, puis toutes les migrations."""
    assert URL_TEST.database is not None
    asyncio.run(_recreer_base(URL_DEV, URL_TEST.database))

    # Config sans fichier alembic.ini : pas de configuration des logs qui perturberait pytest.
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    command.upgrade(config, "head")


@asynccontextmanager
async def _transaction_annulee() -> AsyncIterator[AsyncSession]:
    """Session dont tout le travail est annulé à la sortie, même ce qui a été commité."""
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        # create_savepoint : un session.commit() du code testé ne valide qu'un point de
        # sauvegarde à l'intérieur de notre transaction, qu'on annule ensuite en entier.
        session = AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
async def nouvelle_transaction(
    base_de_test: None,
) -> AsyncIterator[Callable[[], AbstractAsyncContextManager[AsyncSession]]]:
    """Pour les tests qui ont besoin de plusieurs transactions successives."""
    yield _transaction_annulee
    # Chaque test a sa propre boucle d'événements : on vide le pool pour ne pas
    # réutiliser dans le test suivant une connexion ouverte dans cette boucle.
    await get_engine().dispose()


@pytest.fixture
async def session(
    nouvelle_transaction: Callable[[], AbstractAsyncContextManager[AsyncSession]],
) -> AsyncIterator[AsyncSession]:
    """Session du test, annulée à la fin."""
    async with nouvelle_transaction() as session:
        yield session


@pytest.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Client HTTP qui appelle l'application directement, sans lancer de serveur.

    L'appli utilise la session du test : le test voit ce que l'API écrit, et inversement.
    """

    async def session_du_test() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = session_du_test
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
