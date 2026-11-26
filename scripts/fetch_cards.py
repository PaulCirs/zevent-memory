"""
Récupère les cartes ZEVENT x LittleBigWhale depuis la galerie Memoka.

- Lit le JSON des cartes embarqué dans la page (id, numéro, nom, rareté, artiste, image).
- Télécharge chaque image originale, puis génère deux versions WebP :
    large/  (800 px de large)  -> pour l'animation d'ouverture
    thumb/  (300 px de large)  -> pour la galerie / collection
- Écrit cards.json avec les métadonnées et les chemins locaux.

Les originaux (~1,5 Mo chacun) ne sont pas conservés, sauf avec --keep-originals.
Le script peut être relancé : les cartes déjà traitées sont ignorées.

Usage :
    python scripts/fetch_cards.py                  # tout récupérer
    python scripts/fetch_cards.py --limit 3        # tester sur 3 cartes
    python scripts/fetch_cards.py --keep-originals # garder aussi les JPG originaux
"""

import argparse
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

GALLERY_URL = "https://www.memoka.gg/galerie/zevent-x-littlebigwhale"
USER_AGENT = "Mozilla/5.0 (personal card-collection script)"
SIZES = {"large": 800, "thumb": 300}
RARITY_FR = {"COMMON": "Classique", "SPE": "Spé", "RARE": "Rare", "EPIC": "Épique"}

# Rareté propre à notre jeu, absente de Memoka : les cartes 222 à 249 (rares chez eux)
# deviennent « Spé », entre Classique et Rare.
SPE_NUMBERS = {str(n) for n in range(222, 250)}


def game_rarity(card: dict) -> str:
    if card["number"] in SPE_NUMBERS:
        return "SPE"
    return card["rarity"]


def display_key(number: str) -> tuple[int, int]:
    """Ordre d'affichage : 1 à 105, puis BO1 à BO5 (rares sans numéro), puis 106 et suite.
    `number` est du texte : trié tel quel, on aurait 1, 10, 100, 101..."""
    if number.startswith("BO"):
        return (105, int(number[2:]))
    return (int(number), 0)


def add_positions(cards: list[dict]) -> None:
    """Ajoute `position` (1, 2, 3...) : l'appli trie les cartes sur ce champ."""
    for position, card in enumerate(sorted(cards, key=lambda c: display_key(c["number"])), 1):
        card["position"] = position

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "cards"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def extract_cards(html: str) -> list[dict]:
    """La page (Next.js) embarque ses données dans des appels self.__next_f.push([1, "..."])."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)</script>', html, re.S)
    payload = "".join(json.loads(c) for c in chunks)
    start = payload.find('"cards":[')
    if start == -1:
        sys.exit("Liste des cartes introuvable : la structure de la page a peut-être changé.")
    cards, _ = json.JSONDecoder().raw_decode(payload, start + len('"cards":'))
    return cards


def clean_artist(artist) -> dict | None:
    if not isinstance(artist, dict):  # "$undefined" quand pas d'artiste
        return None
    bio = artist.get("bio")
    if bio:  # U+2028/U+2029 (séparateurs de ligne/paragraphe Unicode) -> espace
        bio = bio.replace(" ", " ").replace(" ", " ")
    return {
        "name": artist.get("name"),
        "bio": bio,
        "links": [{"network": l.get("network"), "url": l.get("url")} for l in artist.get("links", [])],
    }


def process_card(card: dict, keep_originals: bool) -> dict:
    slug = f"{card['number']}-{card['id']}"
    paths = {name: OUT_DIR / name / f"{slug}.webp" for name in SIZES}

    if not all(p.exists() for p in paths.values()):
        raw = fetch(card["frontImageUrl"])
        if keep_originals:
            orig = OUT_DIR / "originals" / f"{slug}.jpg"
            orig.parent.mkdir(parents=True, exist_ok=True)
            orig.write_bytes(raw)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        for name, width in SIZES.items():
            height = round(img.height * width / img.width)
            paths[name].parent.mkdir(parents=True, exist_ok=True)
            img.resize((width, height), Image.LANCZOS).save(paths[name], "WEBP", quality=85)
        time.sleep(0.3)  # rester poli avec leur serveur

    rarity = game_rarity(card)
    return {
        "id": card["id"],
        "number": card["number"],
        "name": card["name"],
        "rarity": rarity,
        "rarityLabel": RARITY_FR.get(rarity, rarity),
        "artist": clean_artist(card.get("artist")),
        "images": {name: p.relative_to(OUT_DIR).as_posix() for name, p in paths.items()},
        "sourceUrl": card["frontImageUrl"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="ne traiter que les N premières cartes")
    parser.add_argument("--keep-originals", action="store_true", help="garder les JPG originaux")
    args = parser.parse_args()

    print(f"Lecture de {GALLERY_URL}")
    cards = extract_cards(fetch(GALLERY_URL).decode("utf-8"))
    print(f"{len(cards)} cartes trouvées")
    if args.limit:
        cards = cards[: args.limit]

    result, failures = [], []
    for i, card in enumerate(cards, 1):
        try:
            result.append(process_card(card, args.keep_originals))
            print(f"[{i}/{len(cards)}] #{card['number']} {card['name']}")
        except Exception as e:  # une image en échec ne doit pas tout arrêter
            failures.append(card["number"])
            print(f"[{i}/{len(cards)}] ÉCHEC #{card['number']} : {e}")

    add_positions(result)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "cards.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    size_mb = sum(f.stat().st_size for f in OUT_DIR.rglob("*") if f.is_file()) / 1e6
    print(f"\nTerminé : {len(result)} cartes, {size_mb:.1f} Mo dans {OUT_DIR}")
    if failures:
        print(f"Échecs (relance le script pour réessayer) : {failures}")


if __name__ == "__main__":
    main()
