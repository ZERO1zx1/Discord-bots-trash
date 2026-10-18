import discord
from discord.ext import commands
from discord import app_commands
import random
import time
from datetime import datetime, timedelta

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa
EMBED_COLOR = 0x2b2d31

COOLDOWN_SECONDS = 300  # 5 минут

class Lottery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================== ӨГӨГДЛИЙН САН (SQLite) ==================
    async def init_db(self):
        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS lottery_pool (
                guild_id TEXT PRIMARY KEY,
                pool INTEGER DEFAULT 0
            )
        """)
        await self.bot.db.commit()

        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS lottery_entries (
                guild_id TEXT,
                user_id TEXT,
                tickets INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await self.bot.db.commit()

        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS lottery_cooldowns (
                guild_id TEXT,
                user_id TEXT,
                last_used INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await self.bot.db.commit()

    async def cog_load(self):
        await self.init_db()

    # ================== ТУСЛАХ МЕТОДУУД ==================
    async def get_pool(self, guild_id: int) -> int:
        row = await self.bot.db.fetchone(
            "SELECT pool FROM lottery_pool WHERE guild_id = ?",
            str(guild_id)
        )
        if row:
            return row[0]
        # Байхгүй бол 0-ээр үүсгэх
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO lottery_pool (guild_id, pool) VALUES (?, 0)",
            str(guild_id)
        )
        await self.bot.db.commit()
        return 0

    async def set_pool(self, guild_id: int, amount: int):
        await self.bot.db.execute(
            "INSERT INTO lottery_pool (guild_id, pool) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET pool = excluded.pool",
            str(guild_id), amount
        )
        await self.bot.db.commit()

    async def add_tickets(self, guild_id: int, user_id: int, tickets: int):
        await self.bot.db.execute(
            "INSERT INTO lottery_entries (guild_id, user_id, tickets) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET tickets = tickets + excluded.tickets",
            str(guild_id), str(user_id), tickets
        )
        await self.bot.db.commit()

    async def clear_entries(self, guild_id: int):
        await self.bot.db.execute(
            "DELETE FROM lottery_entries WHERE guild_id = ?",
            str(guild_id)
        )
        await self.bot.db.commit()

    async def get_entries(self, guild_id: int):
        return await self.bot.db.fetch(
            "SELECT user_id, tickets FROM lottery_entries WHERE guild_id = ? AND tickets > 0",
            str(guild_id)
        )

    async def is_on_cooldown(self, guild_id: int, user_id: int) -> bool:
        row = await self.bot.db.fetchone(
            "SELECT last_used FROM lottery_cooldowns WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        if not row or not row[0]:
            return False
        last = row[0]
        now = int(time.time())
        return (now - last) < COOLDOWN_SECONDS

    async def set_cooldown(self, guild_id: int, user_id: int):
        now = int(time.time())
        await self.bot.db.execute(
            "INSERT INTO lottery_cooldowns (guild_id, user_id, last_used) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET last_used = excluded.last_used",
            str(guild_id), str(user_id), now
        )
        await self.bot.db.commit()

    async def get_cooldown_remaining(self, guild_id: int, user_id: int) -> int:
        row = await self.bot.db.fetchone(
            "SELECT last_used FROM lottery_cooldowns WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        if not row or not row[0]:
            return 0
        elapsed = int(time.time()) - row[0]
        return max(0, COOLDOWN_SECONDS - elapsed)

    # ================== SLASH COMMANDS (GROUP) ==================
    lottery_group = app_commands.Group(name="lottery", description="Сугалааны систем")

    @lottery_group.command(name="buy", description="Тасалбар худалдан авах")
    @app_commands.describe(tickets="Тасалбарын тоо (тоо эсвэл 'all')")
    async def slash_buy(self, interaction: discord.Interaction, tickets: str = "1"):
        await self._buy_tickets(interaction, tickets, is_slash=True)

    @commands.command(name='lottery', aliases=['lotto', 'сугалаа'])
    async def prefix_buy(self, ctx, tickets_str: str = "1"):
        await self._buy_tickets(ctx, tickets_str)

    async def _buy_tickets(self, ctx_or_interaction, tickets_str: str, is_slash=False):
        # Нэгдсэн логик
        if is_slash:
            ctx = ctx_or_interaction
            author = ctx.user
            guild = ctx.guild
            respond = ctx.response.send_message
        else:
            ctx = ctx_or_interaction
            author = ctx.author
            guild = ctx.guild
            respond = ctx.send

        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна!", color=ERROR_COLOR)
            return await respond(embed=embed, ephemeral=is_slash)

        guild_id = guild.id

        # Хөргөлт шалгах
        if await self.is_on_cooldown(guild_id, author.id):
            rem = await self.get_cooldown_remaining(guild_id, author.id)
            minutes, seconds = divmod(rem, 60)
            embed = discord.Embed(
                title="⏳ ХҮЛЭЭГЭЭРЭЙ",
                description=f"Дараагийн худалдан авалт **{minutes} мин {seconds} сек** дараа.",
                color=WARNING_COLOR
            )
            return await respond(embed=embed, ephemeral=is_slash)

        # Тасалбарын тоог шийдэх
        try:
            if tickets_str.lower() == 'all':
                balance = await economy.get_balance(author.id, guild_id)
                if balance < 100:
                    msg = "❌ Тасалбарын үнэ 100 мөнгө. Таны үлдэгдэл хүрэлцэхгүй."
                    return await respond(msg, ephemeral=is_slash)
                tickets = min(balance // 100, 100)
            else:
                tickets = int(tickets_str)
        except ValueError:
            msg = "❌ Тасалбарын тоо нь бүхэл тоо эсвэл 'all' байх ёстой."
            return await respond(msg, ephemeral=is_slash)

        if tickets < 1 or tickets > 100:
            msg = "❌ Тасалбарын тоо 1-100 хооронд байх ёстой."
            return await respond(msg, ephemeral=is_slash)

        total_cost = tickets * 100
        balance = await economy.get_balance(author.id, guild_id)
        if balance < total_cost:
            msg = f"❌ **{total_cost:,}** мөнгө шаардлагатай. Таны үлдэгдэл: **{balance:,}**"
            return await respond(msg, ephemeral=is_slash)

        # Мөнгө хасах
        await economy.update_balance(author.id, guild_id, -total_cost)

        # Сан болон тасалбар шинэчлэх
        pool = await self.get_pool(guild_id)
        await self.set_pool(guild_id, pool + total_cost)
        await self.add_tickets(guild_id, author.id, tickets)
        await self.set_cooldown(guild_id, author.id)

        new_pool = await self.get_pool(guild_id)

        embed = discord.Embed(
            title="🎫 ТАСАЛБАР ХУДАЛДАН АВАЛТ",
            description=f"{author.mention} амжилттай **{tickets}** тасалбар авлаа!",
            color=SUCCESS_COLOR
        )
        embed.set_thumbnail(url=author.display_avatar.url)
        embed.add_field(name="🎟️ Таны тасалбар", value=f"```{tickets}```", inline=True)
        embed.add_field(name="💰 Нийт сан", value=f"```{new_pool:,}```", inline=True)
        embed.add_field(name="💸 Зардал", value=f"```{total_cost:,}```", inline=True)
        embed.set_footer(text="5 минутын дараа дахин худалдан авах боломжтой")
        embed.timestamp = discord.utils.utcnow()

        await respond(embed=embed, ephemeral=is_slash)

    # ================== DRAW (Admin) ==================
    @commands.command(name='draw', aliases=['сугалах', 'winner'], with_app_command=True)
    @app_commands.default_permissions(administrator=True)
    async def draw_lottery(self, ctx):
        is_slash = isinstance(ctx, discord.Interaction)
        if is_slash:
            guild = ctx.guild
            respond = ctx.response.send_message
            user = ctx.user
            await ctx.defer(ephemeral=False)
        else:
            guild = ctx.guild
            respond = ctx.send
            user = ctx.author
            await ctx.defer()

        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна!", color=ERROR_COLOR)
            return await respond(embed=embed)

        guild_id = guild.id
        pool = await self.get_pool(guild_id)
        if pool < 100:
            return await respond(f"❌ Сугалаа хийх боломжгүй. Сан хангалтгүй (одоо: **{pool:,}** мөнгө).")

        entries = await self.get_entries(guild_id)
        if not entries:
            return await respond("❌ Сугалаанд нэг ч хэрэглэгч оролцоогүй байна.")

        # Тасалбарын сангаас ялагч сонгох
        ticket_pool = []
        for uid, t in entries:
            ticket_pool.extend([uid] * t)
        winner_id = random.choice(ticket_pool)

        winner = guild.get_member(int(winner_id))
        if not winner:
            try:
                winner = await guild.fetch_member(int(winner_id))
            except:
                return await respond(f"❌ Ялагч (ID: {winner_id}) олдсонгүй.")

        await economy.update_balance(int(winner_id), guild_id, pool)

        total_tickets = sum(t for _, t in entries)
        unique = len(entries)

        embed = discord.Embed(
            title="🎉 СУГАЛААНЫ ЯЛАГЧ ТОДОРХОЙЛОГДЛОО!",
            description=f"🏆 {winner.mention} **{pool:,}** мөнгө хожлоо!",
            color=GOLD_COLOR
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1043/1043290.png")
        embed.add_field(name="👥 Оролцогчид", value=f"```{unique}```", inline=True)
        embed.add_field(name="🎟️ Нийт тасалбар", value=f"```{total_tickets}```", inline=True)
        embed.add_field(name="💰 Хожил", value=f"```{pool:,}```", inline=True)
        embed.set_footer(text=f"Зохион байгуулагч: {user.display_name}")

        await respond(embed=embed)

        # Сан цэвэрлэх
        await self.set_pool(guild_id, 0)
        await self.clear_entries(guild_id)

    # ================== МЭДЭЭЛЭЛ, ЖАГСААЛТ, ХӨРГӨЛТ ==================
    @commands.command(name='lottery_info', aliases=['lotto_info', 'сугалаа_мэдээлэл'], with_app_command=True)
    async def lottery_info(self, ctx):
        is_slash = isinstance(ctx, discord.Interaction)
        if is_slash:
            guild_id = ctx.guild_id
            respond = ctx.response.send_message
        else:
            guild_id = ctx.guild.id
            respond = ctx.send

        pool = await self.get_pool(guild_id)
        entries = await self.get_entries(guild_id)
        total_tickets = sum(t for _, t in entries)

        embed = discord.Embed(title="🎰 СУГАЛААНЫ МЭДЭЭЛЭЛ", color=INFO_COLOR)
        embed.add_field(name="💰 Нийт сан", value=f"```{pool:,}```", inline=True)
        embed.add_field(name="👥 Оролцогч", value=f"```{len(entries)}```", inline=True)
        embed.add_field(name="🎟️ Нийт тасалбар", value=f"```{total_tickets}```", inline=True)
        embed.add_field(name="💎 Тасалбарын үнэ", value="```100 мөнгө```", inline=True)
        embed.set_footer(text="Тасалбар авах: /lottery buy <тоо/all> эсвэл !lottery <тоо>")
        embed.timestamp = discord.utils.utcnow()

        await respond(embed=embed)

    @commands.command(name='lottery_participants', aliases=['lotto_users', 'сугалаа_оролцогчид'], with_app_command=True)
    async def lottery_participants(self, ctx):
        is_slash = isinstance(ctx, discord.Interaction)
        if is_slash:
            guild_id = ctx.guild_id
            respond = ctx.response.send_message
        else:
            guild_id = ctx.guild.id
            respond = ctx.send

        entries = await self.get_entries(guild_id)
        if not entries:
            embed = discord.Embed(
                title="📋 СУГАЛААНЫ ОРОЛЦОГЧИД",
                description="Одоогоор оролцогч байхгүй.",
                color=EMBED_COLOR
            )
            return await respond(embed=embed)

        entries.sort(key=lambda x: x[1], reverse=True)
        embed = discord.Embed(title="📋 СУГАЛААНЫ ОРОЛЦОГЧИД", color=INFO_COLOR)
        lines = []
        for user_id, tickets in entries[:15]:
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"ID:{user_id}"
            lines.append(f"• **{name}** — {tickets} тасалбар")
        embed.description = "\n".join(lines)
        if len(entries) > 15:
            embed.set_footer(text=f"+ {len(entries)-15} бусад оролцогч")
        embed.timestamp = discord.utils.utcnow()

        await respond(embed=embed)

    @commands.command(name='lottery_cooldown', aliases=['lotto_cd', 'хөргөлт'], with_app_command=True)
    async def cooldown_check(self, ctx):
        is_slash = isinstance(ctx, discord.Interaction)
        if is_slash:
            guild_id = ctx.guild_id
            author = ctx.user
            respond = ctx.response.send_message
        else:
            guild_id = ctx.guild.id
            author = ctx.author
            respond = ctx.send

        if not await self.is_on_cooldown(guild_id, author.id):
            embed = discord.Embed(
                title="✅ БЭЛЭН",
                description="Та яг одоо тасалбар худалдан авч болно.",
                color=SUCCESS_COLOR
            )
            return await respond(embed=embed)

        rem = await self.get_cooldown_remaining(guild_id, author.id)
        minutes, seconds = divmod(rem, 60)
        embed = discord.Embed(
            title="⏳ ХӨРГӨЛТИЙН ҮЕ",
            description=f"**{minutes} мин {seconds} сек** дараа дахин худалдан авах боломжтой.",
            color=WARNING_COLOR
        )
        embed.timestamp = discord.utils.utcnow()
        await respond(embed=embed)


async def setup(bot):
    await bot.add_cog(Lottery(bot))