import discord
from discord import app_commands
from discord.ext import commands
import datetime
import random
import aiosqlite
from config import (
    DAILY_BONUS, WEEKLY_BONUS, HOURLY_BONUS,
    WORK_MIN, WORK_MAX, ROB_SUCCESS_RATE, DB_PATH,
    get_text, DEFAULT_LANGUAGE
)
from database import (
    get_user, get_balance, add_balance, get_bank, add_bank,
    set_cooldown, get_cooldown
)
from utils.helpers import format_currency
from utils.cooldown import check_cooldown

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _t(self, key, lang=None):
        if lang is None:
            lang = DEFAULT_LANGUAGE
        return get_text(key, lang)

    @app_commands.command(name="balance", description="Үлдэгдлээ харах")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        bal = await get_balance(target.id)
        embed = discord.Embed(title=f"💰 {self._t('balance')}", color=discord.Color.green())
        embed.add_field(name=target.display_name, value=format_currency(bal))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Өдөр тутмын урамшуулал")
    async def daily(self, interaction: discord.Interaction):
        row = await get_user(interaction.user.id)
        last = row[5]
        now = datetime.datetime.now()
        ok, remaining = check_cooldown(last, 86400)
        if ok:
            await add_balance(interaction.user.id, DAILY_BONUS)
            await set_cooldown(interaction.user.id, "daily", now.isoformat())
            embed = discord.Embed(title=f"🎁 {self._t('daily')}", color=discord.Color.gold())
            embed.add_field(name="Хүлээн авлаа", value=format_currency(DAILY_BONUS))
            await interaction.response.send_message(embed=embed)
        else:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await interaction.response.send_message(f"⏳ {hours}ц {minutes}м хүлээнэ үү.", ephemeral=True)

    @app_commands.command(name="weekly", description="Долоо хоногт нэг удаагийн урамшуулал")
    async def weekly(self, interaction: discord.Interaction):
        row = await get_user(interaction.user.id)
        last = row[6]
        now = datetime.datetime.now()
        ok, remaining = check_cooldown(last, 604800)
        if ok:
            await add_balance(interaction.user.id, WEEKLY_BONUS)
            await set_cooldown(interaction.user.id, "weekly", now.isoformat())
            embed = discord.Embed(title=f"🎁 {self._t('weekly')}", color=discord.Color.gold())
            embed.add_field(name="Хүлээн авлаа", value=format_currency(WEEKLY_BONUS))
            await interaction.response.send_message(embed=embed)
        else:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await interaction.response.send_message(f"⏳ {hours}ц {minutes}м хүлээнэ үү.", ephemeral=True)

    @app_commands.command(name="hourly", description="Цагт нэг удаагийн урамшуулал")
    async def hourly(self, interaction: discord.Interaction):
        row = await get_user(interaction.user.id)
        last = row[7]
        now = datetime.datetime.now()
        ok, remaining = check_cooldown(last, 3600)
        if ok:
            await add_balance(interaction.user.id, HOURLY_BONUS)
            await set_cooldown(interaction.user.id, "hourly", now.isoformat())
            embed = discord.Embed(title=f"🎁 {self._t('hourly')}", color=discord.Color.gold())
            embed.add_field(name="Хүлээн авлаа", value=format_currency(HOURLY_BONUS))
            await interaction.response.send_message(embed=embed)
        else:
            minutes = int(remaining // 60)
            await interaction.response.send_message(f"⏳ {minutes}м хүлээнэ үү.", ephemeral=True)

    @app_commands.command(name="pay", description="Өөр хэрэглэгчид мөнгө шилжүүлэх")
    @app_commands.describe(member="Хүлээн авагч", amount="Дүн")
    async def pay(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Дүн эерэг байх ёстой.", ephemeral=True)
        if member.id == interaction.user.id:
            return await interaction.response.send_message("❌ Өөртөө шилжүүлэх боломжгүй.", ephemeral=True)
        bal = await get_balance(interaction.user.id)
        if bal < amount:
            return await interaction.response.send_message("❌ Хүрэлцэхгүй байна.", ephemeral=True)
        await add_balance(interaction.user.id, -amount)
        await add_balance(member.id, amount)
        await interaction.response.send_message(f"✅ {member.mention} {format_currency(amount)} шилжүүллээ.")

    @app_commands.command(name="work", description="Ажиллаж мөнгө олох")
    async def work(self, interaction: discord.Interaction):
        row = await get_user(interaction.user.id)
        last = row[8]
        now = datetime.datetime.now()
        ok, remaining = check_cooldown(last, 3600)
        if not ok:
            minutes = int(remaining // 60)
            return await interaction.response.send_message(f"⏳ {minutes}м хүлээнэ үү.", ephemeral=True)
        earn = random.randint(WORK_MIN, WORK_MAX)
        await add_balance(interaction.user.id, earn)
        await set_cooldown(interaction.user.id, "work", now.isoformat())
        embed = discord.Embed(title=f"💼 {self._t('work')}", color=discord.Color.blue())
        embed.add_field(name="Олсон мөнгө", value=format_currency(earn))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rob", description="Өөр хэрэглэгчийг дээрэмдэх (эрсдэлтэй)")
    @app_commands.describe(member="Бай")
    async def rob(self, interaction: discord.Interaction, member: discord.Member):
        if member.id == interaction.user.id:
            return await interaction.response.send_message("❌ Өөрийгөө дээрэмдэж болохгүй.", ephemeral=True)
        bal = await get_balance(interaction.user.id)
        if bal < 100:
            return await interaction.response.send_message("❌ Дээрэмдэхэд хангалттай мөнгө байхгүй (хамгийн багадаа 100).", ephemeral=True)
        target_bal = await get_balance(member.id)
        if target_bal < 50:
            return await interaction.response.send_message("❌ Тэр хүн дээрэмдэхэд хангалттай мөнгөгүй байна.", ephemeral=True)
        success = random.random() < ROB_SUCCESS_RATE
        if success:
            stolen = min(target_bal, random.randint(50, min(200, target_bal)))
            await add_balance(interaction.user.id, stolen)
            await add_balance(member.id, -stolen)
            await interaction.response.send_message(f"✅ Та {member.mention}-с {format_currency(stolen)} дээрэмдлээ!")
        else:
            penalty = random.randint(50, 200)
            await add_balance(interaction.user.id, -penalty)
            await interaction.response.send_message(f"❌ Бүтэлгүйтлээ! Та {format_currency(penalty)} алдлаа.")

    @app_commands.command(name="deposit", description="Банкинд мөнгө хадгалуулах")
    @app_commands.describe(amount="Дүн")
    async def deposit(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Дүн эерэг байх ёстой.", ephemeral=True)
        bal = await get_balance(interaction.user.id)
        if bal < amount:
            return await interaction.response.send_message("❌ Хүрэлцэхгүй байна.", ephemeral=True)
        await add_balance(interaction.user.id, -amount)
        await add_bank(interaction.user.id, amount)
        await interaction.response.send_message(f"🏦 {format_currency(amount)} банкинд хадгаллаа.")

    @app_commands.command(name="withdraw", description="Банкнаас мөнгө авах")
    @app_commands.describe(amount="Дүн")
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Дүн эерэг байх ёстой.", ephemeral=True)
        bank = await get_bank(interaction.user.id)
        if bank < amount:
            return await interaction.response.send_message("❌ Банкинд хүрэлцэхгүй байна.", ephemeral=True)
        await add_bank(interaction.user.id, -amount)
        await add_balance(interaction.user.id, amount)
        await interaction.response.send_message(f"🏦 {format_currency(amount)} банкнаас авлаа.")

    @app_commands.command(name="bank", description="Банкны үлдэгдэл харах")
    async def bank(self, interaction: discord.Interaction):
        bank = await get_bank(interaction.user.id)
        bal = await get_balance(interaction.user.id)
        embed = discord.Embed(title=f"🏦 {self._t('bank')}", color=discord.Color.blue())
        embed.add_field(name="Гарт байгаа", value=format_currency(bal))
        embed.add_field(name="Банкинд байгаа", value=format_currency(bank))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Хамгийн баян хэрэглэгчид")
    async def leaderboard(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10") as cursor:
                rows = await cursor.fetchall()
        if not rows:
            return await interaction.response.send_message("Одоогоор өгөгдөл байхгүй.")
        embed = discord.Embed(title=f"🏆 {self._t('leaderboard')}", color=discord.Color.gold())
        for i, (uid, bal) in enumerate(rows, 1):
            user = await self.bot.fetch_user(int(uid)) if uid.isdigit() else None
            name = user.display_name if user else uid
            embed.add_field(name=f"#{i} {name}", value=format_currency(bal), inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
