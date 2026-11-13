"""Settings, read from the environment or backend/.env. Secrets are never hard-coded."""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KYD_", env_file=ROOT / "backend" / ".env", extra="ignore")

    data_mode: str = "sqlite"                       # sqlite (bundled real ACS) | fixture (synthetic) | live (Postgres+Neo4j)
    database_url: str = "postgresql://kyd:kyd_dev@127.0.0.1:5433/kyd"
    neo4j_uri: str = "bolt://127.0.0.1:7688"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "kyd_dev_pw"

    llm_provider: str = "none"                      # none | anthropic | openai | local
    llm_model: str = ""
    llm_base_url: str = ""                          # OpenAI-compatible local server (llama.cpp, vLLM)
    llm_api_key: str = ""

    cv_suppress: float = 0.30                       # §9.2
    stale_after_days: int = 540                     # §6.4
    fixtures_dir: Path = ROOT / "backend" / "fixtures"
    data_dir: Path = ROOT / "data"
    frontend_dist: Path = ROOT / "frontend" / "dist"


@lru_cache
def settings() -> Settings:
    return Settings()
