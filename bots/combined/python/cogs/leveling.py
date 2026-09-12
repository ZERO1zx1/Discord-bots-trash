import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
from config import DB_PATH, LEVEL_MULTIPLIER, get_text, DEFAULT_LANGUAGE
from database import get_rank, add_xp

class LevelingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._msg_cooldown = {}
        self._react_cooldown = {}

    def _t(self, key, lang=None):
        if lang is None:
            lang = DEFAULT_LANGUAGE
        return get_text(key, lang)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        # message_count шинэчлэх
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET message_count = message_count + 1 WHERE user_id = ?",
                (str(message.author.id),)
            )
            await db.commit()
        # XP нэмэх
        xp_gain = random.randint(10, 20)
        await add_xp(message.author.id, xp_gain)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET reaction_count = reaction_count + 1 WHERE user_id = ?",
                (str(payload.user_id),)
            )
            await db.commit()
        await add_xp(payload.user_id, 1)

    @app_commands.command(name="rank", description="Түвшин / XP харах")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        xp, level = await get_rank(target.id)
        embed = discord.Embed(
            title=f"🏅 {target.display_name} | {self._t('rank')} {level}",
            color=discord.Color.purple()
        )
        embed.add_field(name="XP", value=f"{xp} XP")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="xp", description="XP оноо харах")
    async def xp(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        xp, _ = await get_rank(target.id)
        embed = discord.Embed(
            title=f"⭐ {target.display_name} - {self._t('xp')}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Одоогийн XP", value=str(xp))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="xpleaderboard", description="Түвшингээр жагсаалт")
    async def leaderboard(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id, xp, level FROM users ORDER BY xp DESC LIMIT 10") as cursor:
                rows = await cursor.fetchall()
        if not rows:
            return await interaction.response.send_message("Одоогоор өгөгдөл байхгүй.")
        embed = discord.Embed(
            title=f"🏆 {self._t('xpleaderboard')}",
            color=discord.Color.gold()
        )
        for i, (uid, xp, lvl) in enumerate(rows, 1):
            user = await self.bot.fetch_user(int(uid)) if uid.isdigit() else None
            name = user.display_name if user else uid
            embed.add_field(name=f"#{i} {name}", value=f"Түвшин {lvl} | {xp} XP", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(LevelingCog(bot))
