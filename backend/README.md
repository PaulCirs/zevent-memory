# Backend

API FastAPI de ZEvent Memory, gérée avec [uv](https://docs.astral.sh/uv/).

```sh
uv sync                                         # installe les dépendances
uv run uvicorn app.main:app --reload            # lance l'API sur http://127.0.0.1:8000
uv run pytest                                   # tests
uv run ruff check . && uv run ruff format .     # lint et formatage
uv run mypy src tests                           # vérification des types
```

Documentation interactive de l'API : http://127.0.0.1:8000/docs
