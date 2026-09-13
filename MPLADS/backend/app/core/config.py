import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    api_prefix: str
    cors_origins: str
    max_upload_bytes: int
    gemini_api_key: str | None
    gemini_model: str
    allow_dev_headers: bool = True
    gateway_shared_secret: str | None = None


@lru_cache
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    # The backend-only local environment file is ignored by Git. Existing process
    # variables take precedence, so deployment environments remain authoritative.
    load_dotenv(project_root / "backend" / ".env", override=False)
    default_database = f"sqlite:///{(project_root / 'data' / 'processed' / 'mplads_ai.sqlite').as_posix()}"
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    raw_allow_dev = os.getenv("ALLOW_DEV_HEADERS")
    if raw_allow_dev is not None:
        allow_dev_headers = raw_allow_dev.strip().lower() in {"true", "1", "yes"}
    else:
        allow_dev_headers = (app_env == "development")

    gateway_shared_secret = os.getenv("GATEWAY_SHARED_SECRET")
    if gateway_shared_secret:
        gateway_shared_secret = gateway_shared_secret.strip()
        if not gateway_shared_secret:
            gateway_shared_secret = None
    else:
        gateway_shared_secret = None

    return Settings(
        app_env=app_env,
        database_url=os.getenv("DATABASE_URL", default_database),
        api_prefix=os.getenv("API_PREFIX", "/api/v1"),
        cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", "209715200")),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        allow_dev_headers=allow_dev_headers,
        gateway_shared_secret=gateway_shared_secret,
    )
