"""Environment-backed configuration with safe readiness checks."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    flask_secret_key: str
    public_base_url: str
    internal_api_key: str
    discord_client_id: str
    discord_client_secret: str
    discord_redirect_uri: str
    supabase_url: str
    supabase_secret_key: str

    @classmethod
    def from_env(cls) -> Settings:
        public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000").rstrip("/")
        return cls(
            flask_secret_key=os.getenv("FLASK_SECRET_KEY", "development-only-change-me"),
            public_base_url=public_base_url,
            internal_api_key=os.getenv("INTERNAL_API_KEY", ""),
            discord_client_id=os.getenv("DISCORD_CLIENT_ID", ""),
            discord_client_secret=os.getenv("DISCORD_CLIENT_SECRET", ""),
            discord_redirect_uri=os.getenv(
                "DISCORD_REDIRECT_URI",
                f"{public_base_url}/auth/discord/callback",
            ),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_secret_key=os.getenv("SUPABASE_SECRET_KEY", ""),
        )

    @property
    def discord_oauth_ready(self) -> bool:
        return bool(self.discord_client_id and self.discord_client_secret)

    @property
    def supabase_ready(self) -> bool:
        return bool(self.supabase_url and self.supabase_secret_key)

    @property
    def production_safe(self) -> bool:
        return (
            len(self.flask_secret_key) >= 32
            and self.flask_secret_key != "development-only-change-me"
        )
