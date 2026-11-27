"""Vérifie le dispositif de test lui-même : bonne base, migrations appliquées, isolation."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.anyio


async def test_les_tests_tournent_sur_la_base_de_test(session: AsyncSession) -> None:
    nom = await session.scalar(text("SELECT current_database()"))

    assert nom is not None
    assert nom.endswith("_test")


async def test_les_migrations_sont_appliquees(session: AsyncSession) -> None:
    # Table créée par Alembic pour noter la dernière migration appliquée.
    table = await session.scalar(text("SELECT to_regclass('alembic_version')"))

    assert table is not None


async def test_les_ecritures_d_un_test_sont_annulees(
    nouvelle_transaction: Callable[[], AbstractAsyncContextManager[AsyncSession]],
) -> None:
    async with nouvelle_transaction() as session:
        await session.execute(text("CREATE TABLE essai (id integer)"))
        await session.commit()  # même commitée, l'écriture doit disparaître

    async with nouvelle_transaction() as session:
        table = await session.scalar(text("SELECT to_regclass('essai')"))

    assert table is None
