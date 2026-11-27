# ZEvent Memory

Application web d'ouverture de boosters de cartes.

## Structure

| Dossier       | Contenu                                                                |
| ------------- | ---------------------------------------------------------------------- |
| `backend/`    | API FastAPI                                                            |
| `frontend/`   | Interface React + TypeScript (Vite)                                    |
| `scripts/`    | `fetch_cards.py` : récupère la liste des cartes et leurs images        |
| `data/cards/` | `cards.json` (versionné) ; images dans `large/` et `thumb/` (hors Git) |
| `deploy/`     | Docker, docker-compose, nginx (à venir)                                |

## Lancer en développement

Prérequis : Docker, [uv](https://docs.astral.sh/uv/), Node 24.

```sh
cp .env.example .env              # une seule fois ; les valeurs par défaut suffisent en dev
docker compose up -d --wait       # PostgreSQL, seul service en Docker
cd backend && uv run alembic upgrade head           # met le schéma de la base à jour
cd backend && uv run uvicorn app.main:app --reload  # API sur http://127.0.0.1:8000
cd frontend && npm install && npm run dev           # site sur http://localhost:5173
```

`docker compose down` arrête la base sans perdre les données ; `docker compose down -v` les efface.

### Migrations de la base

Le schéma est décrit par les modèles de `backend/src/app/models.py` et versionné par
[Alembic](https://alembic.sqlalchemy.org/) dans `backend/migrations/versions/`. Après un
changement de modèle, depuis `backend/` :

```sh
uv run alembic revision --autogenerate -m "description"  # génère la migration : à relire !
uv run alembic upgrade head                              # l'applique à la base de dev
uv run alembic check                                     # vérifie qu'aucune migration ne manque
```

Le modèle et sa migration vont dans la même PR. On ne modifie jamais une migration déjà mergée :
on en écrit une nouvelle.

### Vérifications avant commit

Une fois par clone : `uv tool install pre-commit` puis `pre-commit install`.
Ruff, mypy, ESLint, Prettier et gitleaks tournent alors à chaque `git commit`.
Pour tout vérifier à la main : `pre-commit run --all-files`.

## Récupérer les images des cartes

Les images ne sont pas dans le repo. Pour les régénérer :

```sh
pip install pillow
python scripts/fetch_cards.py
```

## Contribuer

- Une branche par tâche (`feat/...`, `fix/...`), puis une PR vers `main`.
- Messages de commit au format [Conventional Commits](https://www.conventionalcommits.org/fr/).
