import discord
from discord import app_commands
from discord.ext import commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Ботны хариу хурд")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! `{round(self.bot.latency * 1000)}ms`")

    @app_commands.command(name="reload", description="Ког дахин ачаалах (зөвхөн админ)")
    @app_commands.default_permissions(administrator=True)
    async def reload(self, interaction: discord.Interaction, extension: str):
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            await interaction.response.send_message(f"✅ `{extension}` амжилттай дахин ачаалагдлаа.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Алдаа: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
