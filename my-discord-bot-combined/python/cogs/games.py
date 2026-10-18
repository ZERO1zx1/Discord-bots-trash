import discord
from discord import app_commands
from discord.ext import commands

class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trivia", description="Асуулт-хариулт тоглоом")
    async def trivia(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🧠 Trivia", description="Тун удахгүй...", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GamesCog(bot))
