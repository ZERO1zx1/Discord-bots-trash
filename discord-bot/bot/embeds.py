"""One visual system for every GuildPilot Discord response."""

from __future__ import annotations

from dataclasses import dataclass

import discord


@dataclass(frozen=True, slots=True)
class EmbedTheme:
    color: int
    label: str


THEMES = {
    "success": EmbedTheme(0x57F287, "SUCCESS"),
    "info": EmbedTheme(0x5865F2, "GUILDPILOT"),
    "warning": EmbedTheme(0xFEE75C, "ACTION RECOMMENDED"),
    "danger": EmbedTheme(0xED4245, "ATTENTION REQUIRED"),
}


class BrandEmbeds:
    """Creates compact, accessible embeds with consistent recovery copy."""

    @staticmethod
    def create(
        *,
        title: str,
        description: str,
        tone: str = "info",
        request_id: str = "pending",
    ) -> discord.Embed:
        theme = THEMES.get(tone, THEMES["info"])
        embed = discord.Embed(
            title=title[:256],
            description=description[:4096],
            color=theme.color,
        )
        embed.set_author(name=f"GuildPilot · {theme.label}")
        embed.set_footer(text=f"GuildPilot • Request ID {request_id}")
        return embed

    @classmethod
    def control_panel(cls, *, guild_name: str, request_id: str) -> discord.Embed:
        embed = cls.create(
            title="Community control panel",
            description=(
                f"Manage **{guild_name}** through guided actions. Choose a module below; "
                "high-risk changes ask for confirmation before they run."
            ),
            request_id=request_id,
        )
        embed.add_field(name="Setup", value="Welcome, roles, and safe defaults", inline=True)
        embed.add_field(name="Support", value="Member tickets and staff routing", inline=True)
        embed.add_field(name="Safety", value="Moderation rules and audit history", inline=True)
        embed.add_field(
            name="Current state",
            value="Waiting for the first configured production workflow.",
            inline=False,
        )
        return embed

    @classmethod
    def permission_denied(cls, *, request_id: str) -> discord.Embed:
        return cls.create(
            title="Manage Guild permission required",
            description=(
                "This control changes community configuration. Ask a server owner or a member "
                "with **Manage Server** to run it, then try again."
            ),
            tone="warning",
            request_id=request_id,
        )

