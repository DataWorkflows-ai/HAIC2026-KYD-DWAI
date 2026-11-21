"""Settings, read from the environment or backend/.env. Secrets are never hard-coded."""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KYD_", env_file=ROOT / "backend" / ".env", extra="ignore")

    data_mode: str = "sqlite"                       # sqlite (bundled real data) | fixture (synthetic) | live (Postgres / Supabase)
    database_url: str = "postgresql://kyd:kyd_dev@127.0.0.1:5433/kyd"
    neo4j_uri: str = "bolt://127.0.0.1:7688"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "kyd_dev_pw"
    graph_mode: str = "auto"                        # auto (Neo4j if reachable, else in-memory) | neo4j | fixture

    llm_provider: str = "none"                      # none | anthropic | openai | local
    llm_model: str = ""
    llm_base_url: str = ""                          # OpenAI-compatible local server (llama.cpp, vLLM)
    llm_api_key: str = ""

    auth_secret: str = ""                           # HMAC key for bearer tokens (app/auth.py); empty = random per process
    auth_required: bool = True                      # every /api call except health and /api/auth/* needs a signed-in account
    owner_email: str = ""                           # this account is the owner; empty = the first account registered
    token_days: float = 7
    app_db: Path = ROOT / "backend" / "var" / "app.sqlite"   # accounts and chats when not serving from Postgres
    google_client_id: str = ""                      # "Continue with Google" (OAuth web client ID); empty = button hidden
    smtp_host: str = ""                             # forgot-password codes by email; empty = reset by email is off
    smtp_port: int = 587                            # 465 = implicit TLS, otherwise STARTTLS
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""                             # e.g. "KYD <admin@dataworkflows.ai>"; empty = smtp_user
    reset_code_minutes: int = 15
    trust_proxy_headers: bool = False               # only behind an SSO proxy that strips client x-kyd-* headers

    # Abuse limits (app/security.py). Per client; a venue's shared wifi counts as one client.
    rate_api_per_minute: int = 600                  # data endpoints
    rate_ask_per_minute: int = 20                   # chat questions
    rate_ask_per_day: int = 500
    rate_login_per_minute: int = 30                 # sign-in and registration attempts (a venue's wifi is one client)
    llm_daily_calls: int = 2000                     # all callers; over budget, chat answers fall back to templates
    csp_mode: str = "enforce"                       # enforce | report (Report-Only header) | off

    cache_ttl_seconds: float = 300                  # live mode only; bundled data never changes in-process
    pg_pool_max: int = 4                            # Postgres connection pool size (live mode); data is read once at start-up
    pg_connect_timeout: float = 10                  # seconds to wait for Postgres at start-up before falling back
    live_fallback: bool = True                      # live mode: serve bundled SQLite if Postgres is unreachable (shown in /api/health)
    audit_strict: bool = False                      # true: a failed audit write fails the request; false: write to the local file and flag it
    cv_suppress: float = 0.30                       # §9.2
    stale_after_days: int = 540                     # §6.4
    fixtures_dir: Path = ROOT / "backend" / "fixtures"
    data_dir: Path = ROOT / "data"
    frontend_dist: Path = ROOT / "frontend" / "dist"


@lru_cache
def settings() -> Settings:
    return Settings()
