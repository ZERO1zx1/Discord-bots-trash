"""Bot-side event repository using the shared Supabase table contract."""

from __future__ import annotations

from typing import Any

from server.guildpilot.config import Settings
from server.guildpilot.supabase_gateway import SupabaseGateway


class BotRepository:
    def __init__(self, settings: Settings) -> None:
        self.gateway = SupabaseGateway(settings)

    @property
    def configured(self) -> bool:
        return self.gateway.configured

    def record_interaction(
        self,
        *,
        event_name: str,
        guild_id: int | None,
        actor_id: int,
        properties: dict[str, Any] | None = None,
    ) -> None:
        if not self.configured:
            return
        self.gateway.record_event(
            event_name=event_name,
            guild_id=str(guild_id) if guild_id else None,
            actor_id=str(actor_id),
            properties=properties,
        )

