from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env à la racine du repo. En prod, les variables viennent de Docker Compose
# et ce fichier n'existe pas dans le conteneur : pydantic-settings l'ignore alors.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Configuration lue dans les variables d'environnement (puis dans .env).

    Une variable obligatoire absente fait échouer le démarrage de l'API.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # les valeurs viennent de l'environnement
