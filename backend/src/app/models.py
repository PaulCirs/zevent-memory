from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Noms des contraintes et index fixés par une convention, au lieu de noms choisis par
# PostgreSQL. Alembic peut ainsi les retrouver pour les modifier ou les supprimer.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Classe mère des modèles : chaque sous-classe décrit une table."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
