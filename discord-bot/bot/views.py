"""Buttons, selects, and modals for the GuildPilot interaction system."""

from __future__ import annotations

from uuid import uuid4

import discord

from .embeds import BrandEmbeds
from .repository import BotRepository


def request_id() -> str:
    return f"GP-{uuid4().hex[:8].upper()}"


class TicketModal(discord.ui.Modal, title="Create a support ticket"):
    subject = discord.ui.TextInput(
        label="What do you need help with?",
        placeholder="A short, specific summary",
        max_length=100,
    )
    details = discord.ui.TextInput(
        label="Details",
        style=discord.TextStyle.paragraph,
        placeholder="Include the outcome you expected and what happened.",
        max_length=1000,
    )

    def __init__(self, repository: BotRepository) -> None:
        super().__init__(timeout=300)
        self.repository = repository

    async def on_submit(self, interaction: discord.Interaction) -> None:
        rid = request_id()
        self.repository.record_interaction(
            event_name="ticket_submitted",
            guild_id=interaction.guild_id,
            actor_id=interaction.user.id,
            properties={"subject_length": len(str(self.subject))},
        )
        embed = BrandEmbeds.create(
            title="Ticket received",
            description=(
                f"**{self.subject}**\n\nYour request is queued for the staff team. "
                "You can close this message; updates will arrive in the ticket channel."
            ),
            tone="success",
            request_id=rid,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ModuleSelect(discord.ui.Select):
    def __init__(self, repository: BotRepository) -> None:
        self.repository = repository
        super().__init__(
            custom_id="guildpilot:module-select:v1",
            placeholder="Choose a module…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label="Welcome & onboarding",
                    value="welcome",
                    description="Greetings, roles, and first steps",
                    emoji="👋",
                ),
                discord.SelectOption(
                    label="Tickets & support",
                    value="tickets",
                    description="Member requests and staff queues",
                    emoji="🎫",
                ),
                discord.SelectOption(
                    label="Moderation & safety",
                    value="safety",
                    description="Rules, cases, and audit history",
                    emoji="🛡️",
                ),
                discord.SelectOption(
                    label="Community insights",
                    value="insights",
                    description="Value, activation, and retention",
                    emoji="📈",
                ),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        rid = request_id()
        module = self.values[0]
        copy = {
            "welcome": (
                "Welcome & onboarding",
                "Configure a greeting, a starter role, and a clear next step.",
            ),
            "tickets": (
                "Tickets & support",
                "Create a guided member request and route it to the right staff role.",
            ),
            "safety": (
                "Moderation & safety",
                "Review permissions and audit coverage before enabling enforcement.",
            ),
            "insights": (
                "Community insights",
                "Metrics appear after real production value events are recorded.",
            ),
        }
        title, description = copy[module]
        self.repository.record_interaction(
            event_name="module_selected",
            guild_id=interaction.guild_id,
            actor_id=interaction.user.id,
            properties={"module": module},
        )
        embed = BrandEmbeds.create(
            title=title,
            description=description,
            tone="info",
            request_id=rid,
        )
        await interaction.response.send_message(
            embed=embed,
            view=ModuleActionView(self.repository, module),
            ephemeral=True,
        )


class ModuleActionView(discord.ui.View):
    def __init__(self, repository: BotRepository, module: str) -> None:
        super().__init__(timeout=300)
        self.repository = repository
        self.module = module

    @discord.ui.button(label="Start guided setup", style=discord.ButtonStyle.primary)
    async def start_setup(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        rid = request_id()
        embed = BrandEmbeds.create(
            title="Guided setup started",
            description=(
                "The web dashboard will hold the full configuration form. "
                "Nothing has been changed in this server yet."
            ),
            tone="success",
            request_id=rid,
        )
        await interaction.response.edit_message(embed=embed, view=ConfirmOpenDashboardView())

    @discord.ui.button(label="Create ticket", style=discord.ButtonStyle.secondary)
    async def create_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketModal(self.repository))


class ConfirmOpenDashboardView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=120)
        self.add_item(
            discord.ui.Button(
                label="Open dashboard",
                style=discord.ButtonStyle.link,
                url="http://localhost:3000",
            )
        )

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.secondary)
    async def dismiss(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(view=None)


class CommunityPanelView(discord.ui.View):
    def __init__(self, repository: BotRepository) -> None:
        super().__init__(timeout=None)
        self.repository = repository
        self.add_item(ModuleSelect(repository))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        permissions = getattr(interaction.user, "guild_permissions", None)
        if permissions and permissions.manage_guild:
            return True
        await interaction.response.send_message(
            embed=BrandEmbeds.permission_denied(request_id=request_id()),
            ephemeral=True,
        )
        return False

    @discord.ui.button(
        label="Quick status",
        style=discord.ButtonStyle.secondary,
        custom_id="guildpilot:quick-status:v1",
        row=1,
    )
    async def quick_status(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        rid = request_id()
        database = "Connected" if self.repository.configured else "Awaiting Supabase credentials"
        embed = BrandEmbeds.create(
            title="GuildPilot status",
            description="The bot process is online and Discord components are responding.",
            tone="success",
            request_id=rid,
        )
        embed.add_field(name="Database", value=database, inline=True)
        embed.add_field(
            name="Guild",
            value=interaction.guild.name if interaction.guild else "Direct message",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="New ticket",
        style=discord.ButtonStyle.primary,
        custom_id="guildpilot:new-ticket:v1",
        row=1,
    )
    async def new_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketModal(self.repository))
