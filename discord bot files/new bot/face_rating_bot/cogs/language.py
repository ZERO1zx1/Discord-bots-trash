import discord
from discord import app_commands
from discord.ext import commands
from database import set_language, get_language

class LanguageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setlang", description="Хэрэглэгчийн хэл солих")
    @app_commands.describe(language="mn (Монгол) эсвэл en (English)")
    async def setlang(self, interaction: discord.Interaction, language: str):
        if language not in ("mn", "en"):
            return await interaction.response.send_message(
                "❌ Зөвхөн `mn` эсвэл `en` сонгоно уу.", ephemeral=True
            )
        await set_language(interaction.user.id, language)
        embed = discord.Embed(
            title="🌐 Хэл солигдлоо",
            description=f"Таны хэл **{language}** боллоо!" if language == "mn" else f"Your language is now **English**!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LanguageCog(bot))