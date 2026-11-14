"""Application settings, read once from the environment.

Production refuses to start with insecure defaults (missing JWT secret,
wildcard CORS) so misconfiguration fails loudly at deploy time instead of
silently shipping a forgeable token.
"""
from __future__ import annotations

import os
import secrets
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _build_id() -> str:
    """Stable per-deploy asset version used for cache busting."""
    for key in ("ASSET_VERSION", "RAILWAY_GIT_COMMIT_SHA", "GIT_COMMIT_SHA"):
        if os.environ.get(key):
            return os.environ[key][:12]
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=12", "HEAD"], cwd=BASE_DIR, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "dev"


@dataclass(frozen=True)
class Settings:
    env: str = field(default_factory=lambda: os.environ.get("APP_ENV", "development").lower())
    database_url: str | None = field(default_factory=lambda: os.environ.get("DATABASE_URL"))
    sqlite_path: Path = field(
        default_factory=lambda: Path(os.environ.get("SQLITE_PATH", BASE_DIR / "audit_intelligence.db"))
    )
    jwt_secret: str = field(default_factory=lambda: os.environ.get("SITEIQ_JWT_SECRET", ""))
    jwt_ttl_seconds: int = field(default_factory=lambda: int(os.environ.get("JWT_TTL_SECONDS", 60 * 60 * 12)))
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip())
    )
    upload_dir: Path = field(default_factory=lambda: Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "var" / "uploads")))
    max_upload_bytes: int = field(default_factory=lambda: int(os.environ.get("MAX_UPLOAD_MB", 10)) * 1024 * 1024)
    supabase_url: str | None = field(default_factory=lambda: os.environ.get("SUPABASE_URL"))
    supabase_service_key: str | None = field(default_factory=lambda: os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
    supabase_bucket: str = field(default_factory=lambda: os.environ.get("SUPABASE_STORAGE_BUCKET", "inspection-evidence"))
    gemini_api_key: str | None = field(
        default_factory=lambda: os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )
    allow_public_org_signup: bool = field(default_factory=lambda: _env_bool("ALLOW_PUBLIC_ORG_SIGNUP", True))
    asset_version: str = field(default_factory=_build_id)

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def uses_postgres(self) -> bool:
        return bool(self.database_url)

    def validate(self) -> None:
        if self.is_production:
            if len(self.jwt_secret) < 32:
                raise RuntimeError("SITEIQ_JWT_SECRET must be set (>= 32 chars) in production.")
            if "*" in self.cors_origins:
                raise RuntimeError("CORS_ORIGINS must not contain '*' in production.")
            if not self.database_url:
                raise RuntimeError("DATABASE_URL is required in production.")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.jwt_secret and not s.is_production:
        # Ephemeral dev secret: tokens are invalidated on restart, never forgeable from source.
        object.__setattr__(s, "jwt_secret", secrets.token_urlsafe(48))
    s.validate()
    return s
