"""Modèles SQLAlchemy : chaque classe décrit une table de la base.

Le schéma réel est créé par les migrations Alembic (migrations/versions/), générées à partir
de ces classes. Après une modification ici : `alembic revision --autogenerate`, puis relecture.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Noms des contraintes et index fixés par une convention, au lieu de noms choisis par
# PostgreSQL. Alembic peut ainsi les retrouver pour les modifier ou les supprimer.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Classe mère des modèles."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Type SQL choisi d'après l'annotation Python, pour ne pas le répéter à chaque colonne.
    type_annotation_map = {
        str: Text(),  # PostgreSQL : text est aussi rapide que varchar(n), sans limite arbitraire
        datetime: DateTime(timezone=True),  # toujours avec fuseau horaire (stocké en UTC)
    }


# --- Valeurs fixes -------------------------------------------------------------------------
# Stockées en texte, avec une contrainte CHECK qui refuse toute autre valeur.
# ATTENTION : Alembic ne détecte pas un changement de liste. Ajouter une valeur demande
# d'écrire la migration à la main (supprimer puis recréer la contrainte CHECK).


class Rarity(StrEnum):
    COMMON = "COMMON"
    SPE = "SPE"
    RARE = "RARE"
    EPIC = "EPIC"


class Variant(StrEnum):
    STANDARD = "standard"
    UNIQUE = "unique"  # un seul exemplaire au monde par carte


class BoosterType(StrEnum):
    NORMAL = "normal"
    GOLDEN = "golden"


def enum_texte(enum: type[StrEnum], nom: str) -> Enum:
    return Enum(
        enum,
        name=nom,  # nom de la contrainte CHECK : ck_<table>_<nom>
        native_enum=False,  # texte + CHECK, pas de type ENUM PostgreSQL
        create_constraint=True,
        length=32,
        # Stocke la valeur (« standard ») et non le nom du membre (« STANDARD »).
        values_callable=lambda e: [membre.value for membre in e],
        validate_strings=True,
    )


# --- Tables --------------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("booster_stock >= 0", name="booster_stock_positif"),)

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # Boosters disponibles au moment `booster_stock_at`. La recharge (1 par heure, 48 max)
    # se calcule à partir de ces deux valeurs : pas de tâche planifiée.
    booster_stock: Mapped[int] = mapped_column(server_default=text("24"))
    booster_stock_at: Mapped[datetime] = mapped_column(server_default=func.now())


class UserSession(Base):
    """Session de connexion. Seul le hash du jeton est stocké : une fuite de la base
    ne permet pas de se connecter à la place des joueurs."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    token_hash: Mapped[str] = mapped_column(unique=True)
    # ondelete CASCADE : supprimer un joueur supprime ses sessions.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime]


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    # cards.json ne donne pas d'identifiant aux artistes : l'import les reconnaît par leur nom.
    name: Mapped[str] = mapped_column(unique=True)
    bio: Mapped[str | None]
    # Liste de {"network": "instagram", "url": "https://..."}.
    links: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'"))


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    # Identifiant de la carte dans cards.json : l'import s'en sert pour la retrouver.
    external_id: Mapped[str] = mapped_column(unique=True)
    # Texte (« 12 », « BO1 ») : ne jamais trier dessus, utiliser `position`.
    number: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    rarity: Mapped[Rarity] = mapped_column(enum_texte(Rarity, "rarity"))
    # Chemins relatifs à data/cards/ (ex. « large/12-xxx.webp »), servis par nginx.
    image_large: Mapped[str]
    image_thumb: Mapped[str]
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id"), index=True)
    # Ordre d'affichage (1 à 105, BO1 à BO5, puis 106 et suite).
    position: Mapped[int] = mapped_column(unique=True)


class BoosterOpening(Base):
    __tablename__ = "booster_openings"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    booster_type: Mapped[BoosterType] = mapped_column(enum_texte(BoosterType, "booster_type"))
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CardCopy(Base):
    """Un exemplaire de carte possédé par un joueur (les doublons sont des lignes distinctes)."""

    __tablename__ = "card_copies"
    __table_args__ = (
        # Une seule carte par emplacement dans un booster.
        UniqueConstraint("opening_id", "position"),
        CheckConstraint("position BETWEEN 1 AND 5", name="position_dans_le_booster"),
        # Collection d'un joueur : « ses exemplaires de chaque carte ».
        Index("ix_card_copies_owner_id_card_id", "owner_id", "card_id"),
        # Index unique PARTIEL : il ne porte que sur les lignes « unique ».
        # Résultat : au plus un exemplaire unique par carte, autant de standards qu'on veut.
        Index(
            "uq_card_copies_card_id_variant_unique",
            "card_id",
            unique=True,
            postgresql_where=text("variant = 'unique'"),
        ),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Pas d'index séparé : la contrainte unique (opening_id, position) en sert déjà.
    opening_id: Mapped[int] = mapped_column(ForeignKey("booster_openings.id", ondelete="CASCADE"))
    # Emplacement dans le booster (1 à 5), pour rejouer l'ouverture dans l'ordre.
    position: Mapped[int]
    variant: Mapped[Variant] = mapped_column(
        enum_texte(Variant, "variant"), server_default=Variant.STANDARD.value
    )
    obtained_at: Mapped[datetime] = mapped_column(server_default=func.now())
