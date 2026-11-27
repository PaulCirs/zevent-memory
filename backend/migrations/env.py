"""Script lancé par Alembic à chaque commande (upgrade, revision, check...)."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Le schéma voulu, décrit par les modèles. `--autogenerate` et `check` le comparent à la base.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Mode hors ligne (`alembic upgrade head --sql`) : affiche le SQL sans se connecter."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # NullPool : pas de pool de connexions, la commande n'utilise qu'une connexion puis s'arrête.
    engine = create_async_engine(get_settings().database_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        # Alembic est synchrone : run_sync lui prête la connexion async.
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
