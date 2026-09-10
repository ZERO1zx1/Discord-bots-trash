"""Small server-only boundary around Supabase's Python client."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from supabase import Client, create_client

from .config import Settings


class SupabaseNotConfigured(RuntimeError):
    """Raised when a database operation is attempted without credentials."""


class SupabaseGateway:
    """Owns privileged database calls; this object must never run in a browser."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Client | None = None

    @property
    def configured(self) -> bool:
        return self._settings.supabase_ready

    @property
    def client(self) -> Client:
        if not self.configured:
            raise SupabaseNotConfigured("Supabase server credentials are not configured")
        if self._client is None:
            self._client = create_client(
                self._settings.supabase_url,
                self._settings.supabase_secret_key,
            )
        return self._client

    def upsert_guild(self, guild: dict[str, Any]) -> None:
        payload = {
            "id": str(guild["id"]),
            "name": str(guild.get("name") or "Unknown guild")[:100],
            "owner_id": str(guild.get("owner_id") or ""),
            "bot_installed": bool(guild.get("bot_installed", False)),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.client.table("guilds").upsert(payload, on_conflict="id").execute()

    def record_event(
        self,
        *,
        event_name: str,
        guild_id: str | None,
        actor_id: str | None,
        properties: dict[str, Any] | None = None,
    ) -> str:
        event_id = str(uuid4())
        payload = {
            "event_id": event_id,
            "event_name": event_name,
            "guild_id": guild_id,
            "actor_id": actor_id,
            "properties": properties or {},
            "occurred_at": datetime.now(UTC).isoformat(),
        }
        self.client.table("analytics_events").insert(payload).execute()
        return event_id

    def analytics_summary(self, guild_id: str) -> dict[str, Any]:
        since = (datetime.now(UTC) - timedelta(days=28)).isoformat()
        response = (
            self.client.table("analytics_events")
            .select("event_name,occurred_at")
            .eq("guild_id", guild_id)
            .gte("occurred_at", since)
            .limit(1000)
            .execute()
        )
        rows = response.data or []
        counts: dict[str, int] = {}
        for row in rows:
            name = str(row["event_name"])
            counts[name] = counts.get(name, 0) + 1
        return {
            "guild_id": guild_id,
            "window_days": 28,
            "event_count": len(rows),
            "events_by_name": counts,
            "source": "supabase.analytics_events",
            "fresh_at": datetime.now(UTC).isoformat(),
        }

