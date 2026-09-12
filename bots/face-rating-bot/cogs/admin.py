import discord
from discord import app_commands
from discord.ext import commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping", description="Ботны хариу хурдыг шалгах ⚡")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Хариу хурд:** `{latency}ms`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="info", description="Ботын мэдээллийг харуулах ℹ️")
    async def info(self, ctx):
        embed = discord.Embed(
            title="ℹ️ Ботын мэдээлэл",
            description=f"**Нэр:** {self.bot.user.name}\n**ID:** {self.bot.user.id}\n**Хувь нэмэр:** {len(self.bot.guilds)}\n**Хэрэглэгчид:** {len(self.bot.users)}\n**Верс:** 1.0.0\n**time:** {self.bot.latency * 1000:.2f}ms",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))