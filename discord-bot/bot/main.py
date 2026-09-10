"""Discord bot runtime with slash commands and persistent components."""

from __future__ import annotations

import logging
import os
from uuid import uuid4

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from bot.embeds import BrandEmbeds
from bot.repository import BotRepository
from bot.views import CommunityPanelView, TicketModal
from server.guildpilot.config import Settings

log = logging.getLogger("guildpilot.bot")


class GuildPilotBot(commands.Bot):
    def __init__(self, repository: BotRepository) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.repository = repository

    async def setup_hook(self) -> None:
        self.add_view(CommunityPanelView(self.repository))
        dev_guild_id = os.getenv("DISCORD_DEV_GUILD_ID", "")
        if dev_guild_id:
            guild = discord.Object(id=int(dev_guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Synced commands to development guild %s", dev_guild_id)
        else:
            await self.tree.sync()
            log.info("Synced global commands")

    async def on_ready(self) -> None:
        log.info("GuildPilot connected as %s", self.user)


def rid() -> str:
    return f"GP-{uuid4().hex[:8].upper()}"


def register_commands(bot: GuildPilotBot) -> None:
    @bot.tree.command(name="panel", description="Open the GuildPilot community control panel")
    @app_commands.guild_only()
    async def panel(interaction: discord.Interaction) -> None:
        permissions = getattr(interaction.user, "guild_permissions", None)
        if not permissions or not permissions.manage_guild:
            await interaction.response.send_message(
                embed=BrandEmbeds.permission_denied(request_id=rid()),
                ephemeral=True,
            )
            return
        bot.repository.record_interaction(
            event_name="control_panel_opened",
            guild_id=interaction.guild_id,
            actor_id=interaction.user.id,
        )
        await interaction.response.send_message(
            embed=BrandEmbeds.control_panel(
                guild_name=interaction.guild.name if interaction.guild else "this community",
                request_id=rid(),
            ),
            view=CommunityPanelView(bot.repository),
            ephemeral=True,
        )

    @bot.tree.command(name="status", description="Check GuildPilot's current service status")
    @app_commands.guild_only()
    async def status(interaction: discord.Interaction) -> None:
        embed = BrandEmbeds.create(
            title="Service status",
            description="The bot is online and accepting interactions.",
            tone="success",
            request_id=rid(),
        )
        embed.add_field(
            name="Supabase",
            value="Connected" if bot.repository.configured else "Not configured",
            inline=True,
        )
        embed.add_field(name="Interaction mode", value="Slash commands + components", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="ticket", description="Create a guided support ticket")
    @app_commands.guild_only()
    async def ticket(interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TicketModal(bot.repository))


def build_bot() -> GuildPilotBot:
    settings = Settings.from_env()
    bot = GuildPilotBot(BotRepository(settings))
    register_commands(bot)
    return bot


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    token = os.getenv("DISCORD_TOKEN", "")
    if not token:
        raise SystemExit("DISCORD_TOKEN is required to start the bot")
    build_bot().run(token, log_handler=None)

