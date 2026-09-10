import asyncio

from bot.embeds import THEMES, BrandEmbeds
from bot.repository import BotRepository
from bot.views import CommunityPanelView, ModuleSelect
from server.guildpilot.config import Settings


def empty_settings() -> Settings:
    return Settings(
        flask_secret_key="x" * 40,
        public_base_url="http://localhost:5000",
        internal_api_key="",
        discord_client_id="",
        discord_client_secret="",
        discord_redirect_uri="http://localhost:5000/auth/discord/callback",
        supabase_url="",
        supabase_secret_key="",
    )


def test_control_panel_embed_uses_brand_contract() -> None:
    embed = BrandEmbeds.control_panel(guild_name="Northstar", request_id="GP-TEST")

    assert embed.title == "Community control panel"
    assert embed.color.value == THEMES["info"].color
    assert embed.author.name == "GuildPilot · GUILDPILOT"
    assert embed.footer.text == "GuildPilot • Request ID GP-TEST"
    assert len(embed.fields) == 4


def test_persistent_panel_has_buttons_and_select() -> None:
    async def inspect_view() -> tuple[float | None, bool, set[str | None]]:
        view = CommunityPanelView(BotRepository(empty_settings()))
        result = (
            view.timeout,
            any(isinstance(child, ModuleSelect) for child in view.children),
            {getattr(child, "custom_id", None) for child in view.children},
        )
        view.stop()
        return result

    timeout, has_select, custom_ids = asyncio.run(inspect_view())

    assert timeout is None
    assert has_select
    assert "guildpilot:module-select:v1" in custom_ids
    assert "guildpilot:quick-status:v1" in custom_ids
    assert "guildpilot:new-ticket:v1" in custom_ids
