# ZEvent Memory

Application web d'ouverture de boosters de cartes.

## Structure

| Dossier       | Contenu                                                                |
| ------------- | ---------------------------------------------------------------------- |
| `backend/`    | API FastAPI (à venir)                                                  |
| `frontend/`   | Interface React + TypeScript (à venir)                                 |
| `scripts/`    | `fetch_cards.py` : récupère la liste des cartes et leurs images        |
| `data/cards/` | `cards.json` (versionné) ; images dans `large/` et `thumb/` (hors Git) |
| `deploy/`     | Docker, docker-compose, nginx (à venir)                                |

## Récupérer les images des cartes

Les images ne sont pas dans le repo. Pour les régénérer :

```sh
pip install pillow
python scripts/fetch_cards.py
```

## Contribuer

- Une branche par tâche (`feat/...`, `fix/...`), puis une PR vers `main`.
- Messages de commit au format [Conventional Commits](https://www.conventionalcommits.org/fr/).
