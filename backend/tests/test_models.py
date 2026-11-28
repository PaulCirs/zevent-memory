"""Tests des contraintes du schéma : la base elle-même refuse les données incohérentes."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BoosterOpening,
    BoosterType,
    Card,
    CardCopy,
    Rarity,
    User,
    UserSession,
    Variant,
)

pytestmark = pytest.mark.anyio


async def creer_joueur(session: AsyncSession, username: str = "alice") -> User:
    user = User(username=username, password_hash="hash")
    session.add(user)
    await session.flush()  # envoie l'INSERT : la base attribue l'id et les valeurs par défaut
    await session.refresh(user)
    return user


async def creer_carte(session: AsyncSession, numero: int = 1) -> Card:
    card = Card(
        external_id=f"ext-{numero}",
        number=str(numero),
        name=f"Carte {numero}",
        rarity=Rarity.COMMON,
        image_large=f"large/{numero}.webp",
        image_thumb=f"thumb/{numero}.webp",
        position=numero,
    )
    session.add(card)
    await session.flush()
    return card


async def creer_ouverture(session: AsyncSession, user: User) -> BoosterOpening:
    opening = BoosterOpening(user_id=user.id, booster_type=BoosterType.NORMAL)
    session.add(opening)
    await session.flush()
    return opening


def exemplaire(
    user: User,
    card: Card,
    opening: BoosterOpening,
    position: int,
    variant: Variant = Variant.STANDARD,
) -> CardCopy:
    return CardCopy(
        card_id=card.id,
        owner_id=user.id,
        opening_id=opening.id,
        position=position,
        variant=variant,
    )


async def test_un_nouveau_joueur_a_24_boosters_et_n_est_pas_admin(session: AsyncSession) -> None:
    user = await creer_joueur(session)

    assert user.booster_stock == 24
    assert user.is_admin is False


async def test_deux_joueurs_ne_peuvent_pas_avoir_le_meme_nom(session: AsyncSession) -> None:
    await creer_joueur(session, "alice")

    with pytest.raises(IntegrityError, match="uq_users_username"):
        await creer_joueur(session, "alice")


async def test_le_stock_de_boosters_ne_peut_pas_etre_negatif(session: AsyncSession) -> None:
    user = await creer_joueur(session)
    user.booster_stock = -1

    with pytest.raises(IntegrityError, match="ck_users_booster_stock_positif"):
        await session.flush()


async def test_la_base_refuse_une_rarete_inconnue(session: AsyncSession) -> None:
    # SQL brut : on contourne la vérification Python pour tester la contrainte de la base.
    with pytest.raises(IntegrityError, match="ck_cards_rarity"):
        await session.execute(
            text(
                "INSERT INTO cards (external_id, number, name, rarity, image_large, image_thumb, "
                "position) VALUES ('x', '1', 'X', 'LEGENDAIRE', 'l', 't', 1)"
            )
        )


async def test_plusieurs_exemplaires_standard_d_une_meme_carte(session: AsyncSession) -> None:
    alice, bob = await creer_joueur(session, "alice"), await creer_joueur(session, "bob")
    card = await creer_carte(session)
    session.add(exemplaire(alice, card, await creer_ouverture(session, alice), 1))
    session.add(exemplaire(alice, card, await creer_ouverture(session, alice), 1))
    session.add(exemplaire(bob, card, await creer_ouverture(session, bob), 1))

    await session.flush()

    assert await session.scalar(select(func.count()).select_from(CardCopy)) == 3


async def test_une_seule_version_unique_par_carte(session: AsyncSession) -> None:
    alice, bob = await creer_joueur(session, "alice"), await creer_joueur(session, "bob")
    card = await creer_carte(session)
    unique = Variant.UNIQUE
    session.add(exemplaire(alice, card, await creer_ouverture(session, alice), 5, unique))
    await session.flush()

    session.add(exemplaire(bob, card, await creer_ouverture(session, bob), 5, unique))
    with pytest.raises(IntegrityError, match="uq_card_copies_card_id_variant_unique"):
        await session.flush()


async def test_des_cartes_differentes_peuvent_chacune_avoir_leur_unique(
    session: AsyncSession,
) -> None:
    alice = await creer_joueur(session)
    opening = await creer_ouverture(session, alice)
    carte_1, carte_2 = await creer_carte(session, 1), await creer_carte(session, 2)
    session.add(exemplaire(alice, carte_1, opening, 4, Variant.UNIQUE))
    session.add(exemplaire(alice, carte_2, opening, 5, Variant.UNIQUE))

    await session.flush()


async def test_un_seul_exemplaire_par_emplacement_du_booster(session: AsyncSession) -> None:
    alice = await creer_joueur(session)
    opening = await creer_ouverture(session, alice)
    carte_1, carte_2 = await creer_carte(session, 1), await creer_carte(session, 2)
    session.add(exemplaire(alice, carte_1, opening, 1))
    session.add(exemplaire(alice, carte_2, opening, 1))

    with pytest.raises(IntegrityError, match="uq_card_copies_opening_id_position"):
        await session.flush()


@pytest.mark.parametrize("position", [0, 6])
async def test_l_emplacement_est_entre_1_et_5(session: AsyncSession, position: int) -> None:
    alice = await creer_joueur(session)
    card = await creer_carte(session)
    session.add(exemplaire(alice, card, await creer_ouverture(session, alice), position))

    with pytest.raises(IntegrityError, match="ck_card_copies_position_dans_le_booster"):
        await session.flush()


async def test_supprimer_un_joueur_supprime_ses_donnees(session: AsyncSession) -> None:
    alice = await creer_joueur(session)
    card = await creer_carte(session)
    session.add(exemplaire(alice, card, await creer_ouverture(session, alice), 1))
    expire = datetime.now(UTC) + timedelta(days=1)
    session.add(UserSession(token_hash="h", user_id=alice.id, expires_at=expire))
    await session.flush()

    await session.delete(alice)
    await session.flush()

    for modele in (CardCopy, BoosterOpening, UserSession):
        assert await session.scalar(select(func.count()).select_from(modele)) == 0
    # La carte, elle, appartient au jeu et reste en base.
    assert await session.scalar(select(func.count()).select_from(Card)) == 1
