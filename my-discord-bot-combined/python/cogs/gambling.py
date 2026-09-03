import discord
from discord import app_commands
from discord.ext import commands
import random
from database import get_balance, add_balance
from utils.helpers import format_currency

class GamblingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="coinflip", description="Зоос шидэх")
    @app_commands.describe(amount="Бооцоо", choice="heads/tails")
    async def coinflip(self, interaction: discord.Interaction, amount: int, choice: str):
        if amount <= 0:
            return await interaction.response.send_message("❌ Бооцоо эерэг байх ёстой.", ephemeral=True)
        bal = await get_balance(interaction.user.id)
        if bal < amount:
            return await interaction.response.send_message("❌ Хүрэлцэхгүй байна.", ephemeral=True)
        result = random.choice(["heads", "tails"])
        if choice.lower() == result:
            await add_balance(interaction.user.id, amount)
            embed = discord.Embed(title="🎉 Зоос шидэлт", description=f"Тааж: **{choice}** | Результат: **{result}**", color=discord.Color.green())
            embed.add_field(name="Хожлоо!", value=format_currency(amount))
        else:
            await add_balance(interaction.user.id, -amount)
            embed = discord.Embed(title="😢 Зоос шидэлт", description=f"Тааж: **{choice}** | Результат: **{result}**", color=discord.Color.red())
            embed.add_field(name="Алдлаа", value=format_currency(-amount))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slots", description="Слот машин")
    @app_commands.describe(amount="Бооцоо")
    async def slots(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Бооцоо эерэг байх ёстой.", ephemeral=True)
        bal = await get_balance(interaction.user.id)
        if bal < amount:
            return await interaction.response.send_message("❌ Хүрэлцэхгүй байна.", ephemeral=True)
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]
        result = [random.choice(symbols) for _ in range(3)]
        result_str = ' | '.join(result)
        if result[0] == result[1] == result[2]:
            win = amount * 5
            await add_balance(interaction.user.id, win)
            embed = discord.Embed(title="🎰 JACKPOT!", description=result_str, color=discord.Color.gold())
            embed.add_field(name="Хожсон мөнгө", value=format_currency(win))
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            win = amount * 2
            await add_balance(interaction.user.id, win)
            embed = discord.Embed(title="🎰 Таарлаа!", description=result_str, color=discord.Color.green())
            embed.add_field(name="Хожсон мөнгө", value=format_currency(win))
        else:
            await add_balance(interaction.user.id, -amount)
            embed = discord.Embed(title="🎰 Таарсангүй", description=result_str, color=discord.Color.red())
            embed.add_field(name="Алдсан мөнгө", value=format_currency(-amount))
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GamblingCog(bot))
