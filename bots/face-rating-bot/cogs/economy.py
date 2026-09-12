import discord
from discord.ext import commands
import datetime
import random
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

    # ──  үлдэгдэл  ──
    @commands.command(name="balance", aliases=["bal", "money"], description="Үлдэгдлийг харах")
    async def balance(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        # guild_id-тай ажиллах
        bal = await get_balance(target.id, ctx.guild.id)
        embed = discord.Embed(
            title=f"💰 {target.display_name} • Үлдэгдэл",
            description=f"**{format_currency(bal)}**",
            color=0x57f287
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"{ctx.author.name} хүсэлт гаргасан", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ──  өдөр бүр  ──
    @commands.command(name="daily", aliases=["day"], description="Өдөр бүрийн урамшуулал 🌅")
    async def daily(self, ctx: commands.Context):
        # guild_id-тай cooldown шалгах
        last = await get_cooldown(ctx.author.id, ctx.guild.id, "daily")
        now = datetime.datetime.now()
        ok, remaining = check_cooldown(last, 86400)
        if ok:
            await add_balance(ctx.author.id, ctx.guild.id, DAILY_BONUS)
            await set_cooldown(ctx.author.id, ctx.guild.id, "daily", now.isoformat())
            embed = discord.Embed(
                title="🌅 Өдөр бүрийн урамшуулал",
                description=f"{ctx.author.mention} та өдөр тутмын бонусаа авлаа!",
                color=0xfab387
            )
            embed.add_field(name="💰 Хүлээн авсан", value=format_currency(DAILY_BONUS), inline=False)
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Маргааш дахин ирээрэй!")
            await ctx.send(embed=embed)
        else:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            embed = discord.Embed(
                title="⏳ Түр хүлээнэ үү",
                description=f"Та дараагийн өдөр тутмын бонусоо **{hours}ц {minutes}м** дараа авах боломжтой.",
                color=0xf9e2af
            )
            await ctx.send(embed=embed)

    # ──  долоо хоног  ──
    @commands.command(name="weekly", aliases=["week"], description="Долоо хоног тутмын урамшуулал 🎉")
    async def weekly(self, ctx: commands.Context):
        last = await get_cooldown(ctx.author.id, ctx.guild.id, "weekly")
        now = datetime.datetime.now()
        ok, remaining = check_cooldown(last, 604800)
        if ok:
            await add_balance(ctx.author.id, ctx.guild.id, WEEKLY_BONUS)
            await set_cooldown(ctx.author.id, ctx.guild.id, "weekly", now.isoformat())
            embed = discord.Embed(
                title="🎉 Долоо хоног тутмын урамшуулал",
                description=f"{ctx.author.mention} долоо хоногийн бонусоо авлаа!",
                color=0xfab387
            )
            embed.add_field(name="💰 Хүлээн авсан", value=format_currency(WEEKLY_BONUS), inline=False)
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Дараа долоо хоногт дахин ирээрэй!")
            await ctx.send(embed=embed)
        else:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            embed = discord.Embed(
                title="⏳ Түр хүлээнэ үү",
                description=f"Та дараагийн долоо хоногийн бонусоо **{hours}ц {minutes}м** дараа авах боломжтой.",
                color=0xf9e2af
            )
            await ctx.send(embed=embed)

    # ──  цаг тутам  ──
    @commands.command(name="hourly", aliases=["hour"], description="Цаг тутмын урамшуулал ⏰")
    async def hourly(self, ctx: commands.Context):
        last = await get_cooldown(ctx.author.id, ctx.guild.id, "hourly")
        now = datetime.datetime.now()
        ok, remaining = check_cooldown(last, 3600)
        if ok:
            await add_balance(ctx.author.id, ctx.guild.id, HOURLY_BONUS)
            await set_cooldown(ctx.author.id, ctx.guild.id, "hourly", now.isoformat())
            embed = discord.Embed(
                title="⏰ Цаг тутмын урамшуулал",
                description=f"{ctx.author.mention} цагийн бонусоо авлаа!",
                color=0xfab387
            )
            embed.add_field(name="💰 Хүлээн авсан", value=format_currency(HOURLY_BONUS), inline=False)
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="1 цагийн дараа дахин ирээрэй")
            await ctx.send(embed=embed)
        else:
            minutes = int(remaining // 60)
            embed = discord.Embed(
                title="⏳ Түр хүлээнэ үү",
                description=f"Та дараагийн цагийн бонусоо **{minutes}м** дараа авах боломжтой.",
                color=0xf9e2af
            )
            await ctx.send(embed=embed)

    # ──  шилжүүлэг  ──
    @commands.command(name="pay", aliases=["give"], description="Өөр хэрэглэгчид мөнгө шилжүүлэх")
    async def pay(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send(embed=discord.Embed(
                title="❌ Алдаа", description="Дүн эерэг байх ёстой.", color=0xed4245))
        if member.id == ctx.author.id:
            return await ctx.send(embed=discord.Embed(
                title="❌ Алдаа", description="Өөртөө шилжүүлэх боломжгүй.", color=0xed4245))
        bal = await get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(embed=discord.Embed(
                title="❌ Хүрэлцэхгүй", description="Таны үлдэгдэл хангалтгүй байна.", color=0xed4245))

        await add_balance(ctx.author.id, ctx.guild.id, -amount)
        await add_balance(member.id, ctx.guild.id, amount)

        embed = discord.Embed(
            title="✅ Шилжүүлэг амжилттай",
            description=f"{ctx.author.mention} → {member.mention}",
            color=0x57f287
        )
        embed.add_field(name="💸 Дүн", value=format_currency(amount), inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"{ctx.author.name} шилжүүлэв", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ──  ажил  ──
    @commands.command(name="work", aliases=["job"], description="Ажиллаад мөнгө олох 🛠️")
    async def work(self, ctx: commands.Context):
        last = await get_cooldown(ctx.author.id, ctx.guild.id, "work")
        now = datetime.datetime.now()
        ok, remaining = check_cooldown(last, 3600)
        if not ok:
            minutes = int(remaining // 60)
            return await ctx.send(embed=discord.Embed(
                title="⏳ Түр хүлээнэ үү",
                description=f"Та дараагийн ажлаа **{minutes}м** дараа хийх боломжтой.",
                color=0xf9e2af
            ))

        earn = random.randint(WORK_MIN, WORK_MAX)
        await add_balance(ctx.author.id, ctx.guild.id, earn)
        await set_cooldown(ctx.author.id, ctx.guild.id, "work", now.isoformat())

        embed = discord.Embed(
            title="🛠️ Ажил",
            description=f"{ctx.author.mention} ажиллаад мөнгө оллоо!",
            color=0x3498db
        )
        embed.add_field(name="💼 Олсон мөнгө", value=format_currency(earn), inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="1 цагийн дараа дахин ажиллах боломжтой")
        await ctx.send(embed=embed)

    # ──  дээрэм  ──
    @commands.command(name="rob", aliases=["steal"], description="Өөр хэрэглэгчийг дээрэмдэх (эрсдэлтэй ⚠️)")
    async def rob(self, ctx: commands.Context, member: discord.Member):
        if member.id == ctx.author.id:
            return await ctx.send(embed=discord.Embed(
                title="❌ Алдаа", description="Өөрийгөө дээрэмдэж болохгүй.", color=0xed4245))
        bal = await get_balance(ctx.author.id, ctx.guild.id)
        if bal < 100:
            return await ctx.send(embed=discord.Embed(
                title="❌ Хангалтгүй", description="Дээрэмдэхэд хамгийн багадаа 100 төгрөг шаардлагатай.", color=0xed4245))
        target_bal = await get_balance(member.id, ctx.guild.id)
        if target_bal < 50:
            return await ctx.send(embed=discord.Embed(
                title="❌ Хоосон", description=f"{member.mention} дээрэмдэхэд хангалттай мөнгөгүй.", color=0xed4245))

        success = random.random() < ROB_SUCCESS_RATE
        if success:
            stolen = min(target_bal, random.randint(50, min(200, target_bal)))
            await add_balance(ctx.author.id, ctx.guild.id, stolen)
            await add_balance(member.id, ctx.guild.id, -stolen)
            embed = discord.Embed(
                title="🦹 Дээрэм амжилттай",
                description=f"{ctx.author.mention} {member.mention} -г дээрэмдлээ!",
                color=0x57f287
            )
            embed.add_field(name="💰 Олз", value=format_currency(stolen), inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"{ctx.author.name} дээрэмдсэн")
        else:
            penalty = random.randint(50, 200)
            await add_balance(ctx.author.id, ctx.guild.id, -penalty)
            embed = discord.Embed(
                title="🚔 Баригдлаа",
                description=f"{ctx.author.mention} дээрэм хийх гэж байгаад цагдаад баригдлаа!",
                color=0xed4245
            )
            embed.add_field(name="💸 Торгууль", value=f"-{format_currency(penalty)}", inline=False)
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Дараа нь илүү болгоомжтой байгаарай")
        await ctx.send(embed=embed)

    # ──  банкны үйлдлүүд  ──
    @commands.command(name="deposit", aliases=["dep"], description="Банкинд мөнгө хадгалуулах")
    async def deposit(self, ctx: commands.Context, amount: int):
        if amount <= 0:
            return await ctx.send(embed=discord.Embed(
                title="❌ Алдаа", description="Дүн эерэг байх ёстой.", color=0xed4245))
        bal = await get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(embed=discord.Embed(
                title="❌ Хүрэлцэхгүй", description="Таны үлдэгдэл хангалтгүй.", color=0xed4245))

        await add_balance(ctx.author.id, ctx.guild.id, -amount)
        await add_bank(ctx.author.id, ctx.guild.id, amount)

        embed = discord.Embed(
            title="🏦 Хадгалуулсан",
            description=f"{ctx.author.mention} банкинд мөнгөө хадгаллаа.",
            color=0x57f287
        )
        embed.add_field(name="💰 Дүн", value=format_currency(amount), inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Банкинд мөнгө хадгалах нь аюулгүй")
        await ctx.send(embed=embed)

    @commands.command(name="withdraw", aliases=["with"], description="Банкнаас мөнгө авах")
    async def withdraw(self, ctx: commands.Context, amount: int):
        if amount <= 0:
            return await ctx.send(embed=discord.Embed(
                title="❌ Алдаа", description="Дүн эерэг байх ёстой.", color=0xed4245))
        bank = await get_bank(ctx.author.id, ctx.guild.id)
        if bank < amount:
            return await ctx.send(embed=discord.Embed(
                title="❌ Хүрэлцэхгүй", description="Банкинд хангалттай мөнгө байхгүй.", color=0xed4245))

        await add_bank(ctx.author.id, ctx.guild.id, -amount)
        await add_balance(ctx.author.id, ctx.guild.id, amount)

        embed = discord.Embed(
            title="🏦 Татсан",
            description=f"{ctx.author.mention} банкнаас мөнгөө татлаа.",
            color=0x57f287
        )
        embed.add_field(name="💰 Дүн", value=format_currency(amount), inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Гар дээр мөнгөө бэлэн болголоо")
        await ctx.send(embed=embed)

    @commands.command(name="bank", description="Банкны үлдэгдэл харах")
    async def bank(self, ctx: commands.Context):
        bank = await get_bank(ctx.author.id, ctx.guild.id)
        bal = await get_balance(ctx.author.id, ctx.guild.id)
        embed = discord.Embed(
            title=f"🏦 {ctx.author.display_name} • Банк",
            color=0x3498db
        )
        embed.add_field(name="💵 Гарт байгаа", value=format_currency(bal), inline=True)
        embed.add_field(name="🏧 Банкинд байгаа", value=format_currency(bank), inline=True)
        embed.add_field(name="💰 Нийт", value=format_currency(bal + bank), inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"{ctx.author.name} асуусан")
        await ctx.send(embed=embed)

    # ──  Leaderboard-д ашиглах функц  ──
    async def get_top_balances(self, guild_id, limit=10, offset=0):
        """Leaderboard-д ашиглах — нийт мөнгө (balance + bank)"""
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT user_id, balance + bank as total FROM economy WHERE guild_id=? ORDER BY total DESC LIMIT ? OFFSET ?",
                (str(guild_id), limit, offset)
            ) as cur:
                rows = await cur.fetchall()
        return [(int(r[0]), r[1]) for r in rows]

    async def update_balance(self, user_id, guild_id, amount):
        """Бусад cog-оос дуудах"""
        await add_balance(user_id, guild_id, amount)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))