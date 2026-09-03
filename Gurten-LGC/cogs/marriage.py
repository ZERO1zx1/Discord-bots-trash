import discord
from discord.ext import commands
from discord import app_commands
from discord import ButtonStyle
from discord.ui import View, Button
import time
import datetime
from typing import Optional
import asyncio
import io
import os
import aiohttp
from PIL import Image, ImageDraw, ImageFont

# ---------- Фонт ----------
try:
    from cogs.font_utils import load_font as _load_font
except ImportError:
    def _load_font(size=40, bold=True):
        paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ] if bold else [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except:
                    pass
        return ImageFont.load_default(size)

# ===== COLORS =====
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
PURPLE_COLOR = 0xcba6f7
LOVE_COLOR = 0xff69b4
INFO_COLOR = 0x89b4fa

# Неон өнгөнүүд
NEON_PINK = 0xFF10F0
NEON_GREEN = 0x39FF14
NEON_YELLOW = 0xCCFF00
NEON_BLUE = 0x00BFFF

NEON_PINK_RGB = (255, 16, 240, 255)
NEON_GREEN_RGB = (57, 255, 20, 255)
NEON_YELLOW_RGB = (204, 255, 0, 255)
NEON_BLUE_RGB = (0, 191, 255, 255)

# ===== GIFTS =====
GIFTS = {
    "flower":    {"name": "🌹 Цэцэг",        "emoji": "🌹", "love": 5},
    "chocolate": {"name": "🍫 Шоколад",     "emoji": "🍫", "love": 10},
    "ring":      {"name": "💍 Бөгж",        "emoji": "💍", "love": 50},
    "necklace":  {"name": "📿 Зүүлт",       "emoji": "📿", "love": 30},
    "teddy":     {"name": "🧸 Тедди",       "emoji": "🧸", "love": 15},
}

PROPOSAL_TIMEOUT = 120

# ==================== PROPOSAL BUTTON VIEW ====================
class ProposalView(View):
    def __init__(self, cog, guild_id, proposer_id, target_id, ring_name, ring_emoji, ring_item_id):
        super().__init__(timeout=PROPOSAL_TIMEOUT)
        self.cog = cog
        self.bot = cog.bot
        self.guild_id = guild_id
        self.proposer_id = proposer_id
        self.target_id = target_id
        self.ring_name = ring_name
        self.ring_emoji = ring_emoji
        self.ring_item_id = ring_item_id
        self.accepted = False
        self.message = None

    @discord.ui.button(label="✅ Зөвшөөрөх", style=ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        guild = interaction.guild
        proposer = guild.get_member(self.proposer_id)
        if not proposer:
            return await interaction.response.send_message("❌ Санал тавьсан хүн серверээс гарсан.", ephemeral=True)

        self.accepted = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        await self.cog.add_marriage(self.guild_id, self.proposer_id, self.target_id, self.ring_name, self.ring_emoji)
        shop = self.cog.bot.get_cog("ShopCog")
        if shop and self.ring_item_id:
            await shop.remove_item(self.proposer_id, self.guild_id, self.ring_item_id, 1)

        embed = discord.Embed(
            title="💒 ГЭРЛЭЛТ БҮРТГЭГДЛЭЭ!",
            description=f"{proposer.mention} болон {interaction.user.mention} гэрлэлээ!\n💍 Бөгж: {self.ring_emoji} {self.ring_name}",
            color=NEON_PINK,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.followup.send(embed=embed)
        self.stop()

    @discord.ui.button(label="❌ Татгалзах", style=ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        self.accepted = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        proposer = interaction.guild.get_member(self.proposer_id)
        embed = discord.Embed(
            title="💔 ТАТГАЛЗСАН",
            description=f"{interaction.user.mention} {proposer.mention if proposer else 'хэрэглэгч'}-ийн саналаас татгалзлаа.",
            color=ERROR_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


# ==================== ADOPT BUTTON VIEW ====================
class AdoptView(View):
    def __init__(self, bot, guild_id, parent_id, child_id):
        super().__init__(timeout=PROPOSAL_TIMEOUT)
        self.bot = bot
        self.guild_id = guild_id
        self.parent_id = parent_id
        self.child_id = child_id
        self.message = None

    @discord.ui.button(label="✅ Зөвшөөрөх", style=ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.child_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        # SQLite: санал устгах
        await self.bot.db.execute(
            "DELETE FROM marriage_proposals WHERE guild_id = ? AND to_id = ? AND proposal_type = 'adoption'",
            str(self.guild_id), str(self.child_id)
        )
        await self.bot.db.execute(
            "INSERT INTO adoptions (guild_id, parent_id, child_id, adopted_since) VALUES (?, ?, ?, ?)",
            str(self.guild_id), str(self.parent_id), str(self.child_id), int(time.time())
        )
        parent = interaction.guild.get_member(self.parent_id)
        embed = discord.Embed(
            title="👨‍👧‍👦 ӨРГӨМЖЛӨЛТ БАТЛАГДЛАА",
            description=f"{parent.mention if parent else 'Хэрэглэгч'} {interaction.user.mention}-г хүүхэд болгон өргөмжлөв!",
            color=NEON_GREEN,
            timestamp=discord.utils.utcnow()
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    @discord.ui.button(label="❌ Татгалзах", style=ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.child_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await self.bot.db.execute(
            "DELETE FROM marriage_proposals WHERE guild_id = ? AND to_id = ? AND proposal_type = 'adoption'",
            str(self.guild_id), str(self.child_id)
        )
        embed = discord.Embed(
            title="👶 ТАТГАЛЗСАН",
            description=f"{interaction.user.mention} өргөмжлөх саналаас татгалзлаа.",
            color=WARNING_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


# ==================== MAIN COG ====================
class Marriage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= DATABASE INIT (SQLite) =================
    async def init_db(self):
        # marriages
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS marriages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                partner_id TEXT,
                guild_id TEXT,
                marriage_date INTEGER,
                ring_name TEXT,
                ring_emoji TEXT,
                love_points INTEGER DEFAULT 0,
                UNIQUE(user_id, partner_id, guild_id)
            )
        ''')
        # adoptions
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS adoptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                parent_id TEXT,
                child_id TEXT,
                adopted_since INTEGER,
                UNIQUE(guild_id, parent_id, child_id)
            )
        ''')
        # marriage_proposals
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS marriage_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                from_id TEXT,
                to_id TEXT,
                proposal_type TEXT,
                ring_id INTEGER,
                expires_at INTEGER,
                UNIQUE(guild_id, to_id, proposal_type)
            )
        ''')
        # marriage_user_settings
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS marriage_user_settings (
                guild_id TEXT,
                user_id TEXT,
                blocked INTEGER DEFAULT 0,
                auto_accept_marriage INTEGER DEFAULT 0,
                last_love_daily INTEGER,
                last_gift_daily INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        # marriage_gifts
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS marriage_gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                from_id TEXT,
                to_id TEXT,
                gift_type TEXT,
                love_points INTEGER,
                given_at INTEGER
            )
        ''')
        # marriage_guild_config
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS marriage_guild_config (
                guild_id TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                polygamy INTEGER DEFAULT 0,
                max_spouses INTEGER DEFAULT 1
            )
        ''')

    async def cog_load(self):
        await self.init_db()

    # ================= HELPER METHODS =================
    async def get_marriages(self, guild_id, user_id):
        rows = await self.bot.db.fetch(
            "SELECT user_id, partner_id, love_points, ring_name, ring_emoji, marriage_date FROM marriages WHERE guild_id = ? AND (user_id = ? OR partner_id = ?)",
            str(guild_id), str(user_id), str(user_id)
        )
        result = []
        for uid, pid, love, ring, remoji, mar_date in rows:
            partner = pid if uid == str(user_id) else uid
            result.append({
                "partner": int(partner),
                "love_points": love or 0,
                "ring": f"{remoji} {ring}" if remoji else ring,
                "ring_name": ring,
                "ring_emoji": remoji or "",
                "marriage_date": mar_date
            })
        return result

    async def add_marriage(self, guild_id, u1, u2, ring_name, ring_emoji=""):
        mar_date = int(time.time())
        await self.bot.db.execute(
            "INSERT INTO marriages (user_id, partner_id, guild_id, marriage_date, ring_name, ring_emoji, love_points) VALUES (?, ?, ?, ?, ?, ?, 0)",
            str(u1), str(u2), str(guild_id), mar_date, ring_name, ring_emoji
        )
        await self.bot.db.execute(
            "INSERT INTO marriages (user_id, partner_id, guild_id, marriage_date, ring_name, ring_emoji, love_points) VALUES (?, ?, ?, ?, ?, ?, 0)",
            str(u2), str(u1), str(guild_id), mar_date, ring_name, ring_emoji
        )

    async def remove_marriage(self, guild_id, u1, u2):
        await self.bot.db.execute(
            "DELETE FROM marriages WHERE guild_id = ? AND ((user_id = ? AND partner_id = ?) OR (user_id = ? AND partner_id = ?))",
            str(guild_id), str(u1), str(u2), str(u2), str(u1)
        )

    async def marriage_exists(self, guild_id, u1, u2):
        row = await self.bot.db.fetchone(
            "SELECT 1 FROM marriages WHERE guild_id = ? AND ((user_id = ? AND partner_id = ?) OR (user_id = ? AND partner_id = ?))",
            str(guild_id), str(u1), str(u2), str(u2), str(u1)
        )
        return row is not None

    async def get_spouses(self, guild_id, user_id):
        marriages = await self.get_marriages(guild_id, user_id)
        return [m["partner"] for m in marriages]

    async def get_children(self, guild_id, user_id):
        rows = await self.bot.db.fetch(
            "SELECT child_id FROM adoptions WHERE guild_id = ? AND parent_id = ?",
            str(guild_id), str(user_id)
        )
        return [int(r[0]) for r in rows]

    async def get_parents(self, guild_id, user_id):
        rows = await self.bot.db.fetch(
            "SELECT parent_id FROM adoptions WHERE guild_id = ? AND child_id = ?",
            str(guild_id), str(user_id)
        )
        return [int(r[0]) for r in rows]

    async def get_guild_config(self, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT enabled, polygamy, max_spouses FROM marriage_guild_config WHERE guild_id = ?",
            str(guild_id)
        )
        if not row:
            return {"enabled": True, "polygamy": False, "max_spouses": 1}
        return {"enabled": bool(row[0]), "polygamy": bool(row[1]), "max_spouses": row[2]}

    async def set_guild_config(self, guild_id, **kwargs):
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO marriage_guild_config (guild_id, enabled, polygamy, max_spouses) VALUES (?, 1, 0, 1)",
            str(guild_id)
        )
        for k, v in kwargs.items():
            await self.bot.db.execute(
                f"UPDATE marriage_guild_config SET {k} = ? WHERE guild_id = ?",
                v, str(guild_id)
            )

    async def is_blocked(self, guild_id, user_id):
        row = await self.bot.db.fetchone(
            "SELECT blocked FROM marriage_user_settings WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        return bool(row[0]) if row else False

    async def set_blocked(self, guild_id, user_id, blocked):
        await self.bot.db.execute(
            "INSERT INTO marriage_user_settings (guild_id, user_id, blocked) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET blocked = ?",
            str(guild_id), str(user_id), int(blocked), int(blocked)
        )

    async def get_auto_accept(self, guild_id, user_id):
        row = await self.bot.db.fetchone(
            "SELECT auto_accept_marriage FROM marriage_user_settings WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        return bool(row[0]) if row else False

    async def set_auto_accept(self, guild_id, user_id, auto):
        await self.bot.db.execute(
            "INSERT INTO marriage_user_settings (guild_id, user_id, auto_accept_marriage) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET auto_accept_marriage = ?",
            str(guild_id), str(user_id), int(auto), int(auto)
        )

    async def add_gift(self, guild_id, from_id, to_id, gift_type, love):
        await self.bot.db.execute(
            "INSERT INTO marriage_gifts (guild_id, from_id, to_id, gift_type, love_points, given_at) VALUES (?, ?, ?, ?, ?, ?)",
            str(guild_id), str(from_id), str(to_id), gift_type, love, int(time.time())
        )
        await self.bot.db.execute(
            "UPDATE marriages SET love_points = love_points + ? WHERE guild_id = ? AND ((user_id = ? AND partner_id = ?) OR (user_id = ? AND partner_id = ?))",
            love, str(guild_id), str(from_id), str(to_id), str(to_id), str(from_id)
        )

    async def get_anniversary(self, marriage_date):
        if not marriage_date:
            return None
        try:
            marriage_date = int(marriage_date)
        except (TypeError, ValueError):
            return None
        today = datetime.datetime.now().date()
        mar_date = datetime.datetime.fromtimestamp(marriage_date).date()
        days = (today - mar_date).days
        next_ann = datetime.datetime(today.year, mar_date.month, mar_date.day).date()
        if next_ann < today:
            next_ann = datetime.datetime(today.year + 1, mar_date.month, mar_date.day).date()
        days_until = (next_ann - today).days
        return {"days": days, "next_days": days_until, "date": mar_date.strftime("%Y-%m-%d")}

    async def get_last_gift_time(self, guild_id, user_id):
        row = await self.bot.db.fetchone(
            "SELECT last_gift_daily FROM marriage_user_settings WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        return row[0] if row else 0

    async def update_last_gift_time(self, guild_id, user_id):
        await self.bot.db.execute(
            "INSERT INTO marriage_user_settings (guild_id, user_id, last_gift_daily) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET last_gift_daily = ?",
            str(guild_id), str(user_id), int(time.time()), int(time.time())
        )

    async def get_last_love_time(self, guild_id, user_id):
        row = await self.bot.db.fetchone(
            "SELECT last_love_daily FROM marriage_user_settings WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        return row[0] if row else 0

    async def update_last_love_time(self, guild_id, user_id):
        await self.bot.db.execute(
            "INSERT INTO marriage_user_settings (guild_id, user_id, last_love_daily) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET last_love_daily = ?",
            str(guild_id), str(user_id), int(time.time()), int(time.time())
        )

    async def _send_message(self, ctx, *args, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if not ctx.response.is_done():
                return await ctx.response.send_message(*args, **kwargs)
            else:
                return await ctx.followup.send(*args, **kwargs)
        else:
            return await ctx.send(*args, **kwargs)

    async def _is_ring_item(self, item_id):
        shop = self.bot.get_cog("ShopCog")
        if not shop:
            return False
        item = await shop.get_item(item_id)
        return item is not None and item.get("category") == "ring"

    # ================= COMMANDS =================
    @commands.hybrid_command(name='propose', aliases=['marry', 'санал_тавих'], with_app_command=True,
                             description="Хүнд гэрлэх санал тавих")
    @app_commands.describe(user="Гэрлэх санал тавих хэрэглэгч")
    async def propose(self, ctx, user: discord.Member):
        await self._propose(ctx, ctx.author, user)

    async def _propose(self, ctx, author, target):
        if target.bot or target.id == author.id:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Өөртөө эсвэл ботод санал тавьж болохгүй.", color=ERROR_COLOR))

        cfg = await self.get_guild_config(ctx.guild.id)
        if not cfg["enabled"]:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Гэрлэлтийн систем одоогоор идэвхгүй.", color=ERROR_COLOR))

        if await self.marriage_exists(ctx.guild.id, author.id, target.id):
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Та аль хэдийн энэ хүнтэй гэрлэсэн байна.", color=ERROR_COLOR))

        spouses = await self.get_spouses(ctx.guild.id, author.id)
        if not cfg["polygamy"] and len(spouses) >= 1:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Та аль хэдийн гэрлэсэн байна. Полигами зөвшөөрөгдөөгүй.", color=ERROR_COLOR))
        if len(spouses) >= cfg["max_spouses"]:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description=f"Та хамгийн ихдээ {cfg['max_spouses']} хүнтэй гэрлэх боломжтой.", color=ERROR_COLOR))

        if await self.is_blocked(ctx.guild.id, target.id):
            return await self._send_message(ctx, embed=discord.Embed(title="🚫 ХОРИГЛОГДСОН", description=f"{target.mention} гэрлэх санал авахаас татгалзсан.", color=ERROR_COLOR))

        shop = self.bot.get_cog("ShopCog")
        ring_item_id = None
        ring_name = None
        ring_emoji = None
        if shop:
            inv = await shop.get_user_inventory(author.id, ctx.guild.id)
            for item_id, qty in inv.items():
                if await self._is_ring_item(item_id):
                    item = await shop.get_item(item_id)
                    if item:
                        ring_item_id = item_id
                        ring_name = item.get("name", "Энгийн бөгж")
                        ring_emoji = item.get("emoji", "💍")
                        break
            if not ring_item_id:
                return await self._send_message(ctx, embed=discord.Embed(
                    title="❌ БӨГЖ БАЙХГҮЙ",
                    description="Таны инвентарт гэрлэх бөгж байхгүй байна. Дэлгүүрээс бөгж худалдаж авна уу.",
                    color=ERROR_COLOR
                ))
        else:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Дэлгүүрийн систем ачаалагдаагүй.", color=ERROR_COLOR))

        expires = int(time.time()) + PROPOSAL_TIMEOUT
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO marriage_proposals (guild_id, from_id, to_id, proposal_type, ring_id, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            str(ctx.guild.id), str(author.id), str(target.id), "marriage", 0, expires
        )

        embed = discord.Embed(
            title="💍 ГЭРЛЭХ САНАЛ",
            description=f"{author.mention} {target.mention}-д гэрлэх санал тавьж байна!\n\n"
                        f"💍 Бөгж: {ring_emoji} **{ring_name}**\n\n"
                        f"{PROPOSAL_TIMEOUT} секундын дотор зөвшөөрөх эсвэл татгалзах боломжтой.",
            color=NEON_YELLOW,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        view = ProposalView(self, ctx.guild.id, author.id, target.id, ring_name, ring_emoji, ring_item_id)
        msg = await self._send_message(ctx, content=target.mention, embed=embed, view=view)
        view.message = msg

    @commands.hybrid_command(name='divorce', with_app_command=True, description="Гэрлэлтээ цуцлах")
    @app_commands.describe(user="Цуцлах хэрэглэгч (хоосон бол бүх гэрлэлтийг цуцална)")
    async def divorce(self, ctx, user: discord.Member = None):
        await self._divorce(ctx, ctx.author, user)

    async def _divorce(self, ctx, author, target):
        if target is None:
            marriages = await self.get_marriages(ctx.guild.id, author.id)
            if not marriages:
                return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Танд гэрлэлт байхгүй.", color=ERROR_COLOR))
            for m in marriages:
                await self.remove_marriage(ctx.guild.id, author.id, m["partner"])
            await self._send_message(ctx, embed=discord.Embed(title="💔 Цуцалсан", description="Та бүх гэрлэлтээ цуцаллаа.", color=ERROR_COLOR))
        else:
            if not await self.marriage_exists(ctx.guild.id, author.id, target.id):
                return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description=f"Та {target.mention}-тэй гэрлээгүй байна.", color=ERROR_COLOR))
            await self.remove_marriage(ctx.guild.id, author.id, target.id)
            embed = discord.Embed(
                title="💔 Цуцалсан",
                description=f"{author.mention} болон {target.mention} саллаа.",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            )
            await self._send_message(ctx, embed=embed)

    @commands.hybrid_command(name='spouse', aliases=['хамтрагч', 'эхнэрнөхөр'], with_app_command=True, description="Ханийгаа харах")
    async def spouse(self, ctx):
        spouses = await self.get_spouses(ctx.guild.id, ctx.author.id)
        if not spouses:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Та гэрлээгүй байна.", color=ERROR_COLOR))
        partners = []
        for sid in spouses:
            member = ctx.guild.get_member(sid)
            partners.append(member.mention if member else f"<@{sid}>")
        embed = discord.Embed(title="💑 ХАМТРАГЧ(ИД)", description=", ".join(partners), color=NEON_PINK)
        await self._send_message(ctx, embed=embed)

    @commands.hybrid_command(name='love', with_app_command=True, description="Ханьдаа хайр бэлэглэх")
    @app_commands.describe(target="Хань")
    async def love(self, ctx, target: discord.Member):
        if not await self.marriage_exists(ctx.guild.id, ctx.author.id, target.id):
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description=f"{target.mention} -тай гэрлээгүй байна.", color=ERROR_COLOR))

        last = await self.get_last_love_time(ctx.guild.id, ctx.author.id)
        if last and int(time.time()) - last < 86400:
            remaining = int(86400 - (time.time() - last))
            hours, minutes = divmod(remaining // 60, 60)
            return await self._send_message(ctx, embed=discord.Embed(title="⏰ ХҮЛЭЭГЭЭРЭЙ", description=f"Та өдөрт нэг удаа love бэлэглэх боломжтой. Үлдсэн: {hours}ц {minutes}м", color=WARNING_COLOR))

        await self.bot.db.execute(
            "UPDATE marriages SET love_points = love_points + 10 WHERE guild_id = ? AND ((user_id = ? AND partner_id = ?) OR (user_id = ? AND partner_id = ?))",
            str(ctx.guild.id), str(ctx.author.id), str(target.id), str(target.id), str(ctx.author.id)
        )
        await self.update_last_love_time(ctx.guild.id, ctx.author.id)

        embed = discord.Embed(
            title="💖 ХАЙР +10",
            description=f"{ctx.author.mention} {target.mention} -д 10 love оноо бэлэглэлээ!",
            color=NEON_PINK,
            timestamp=discord.utils.utcnow()
        )
        await self._send_message(ctx, embed=embed)

    @commands.hybrid_command(name='gift', with_app_command=True, description="Ханьдаа бэлэг өгөх")
    @app_commands.describe(gift_type="Бэлгийн төрөл")
    @app_commands.choices(gift_type=[
        app_commands.Choice(name="🌹 Цэцэг", value="flower"),
        app_commands.Choice(name="🍫 Шоколад", value="chocolate"),
        app_commands.Choice(name="💍 Бөгж", value="ring"),
        app_commands.Choice(name="📿 Зүүлт", value="necklace"),
        app_commands.Choice(name="🧸 Тедди", value="teddy"),
    ])
    async def gift(self, ctx, gift_type: str):
        await self._gift(ctx, ctx.author, gift_type)

    async def _gift(self, ctx, author, gift_type):
        gift = GIFTS.get(gift_type)
        if not gift:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Бэлэг олдсонгүй.", color=ERROR_COLOR))

        spouses = await self.get_spouses(ctx.guild.id, author.id)
        if not spouses:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Танд хань байхгүй.", color=ERROR_COLOR))

        last = await self.get_last_gift_time(ctx.guild.id, author.id)
        if last and int(time.time()) - last < 86400:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Та өнөөдөр аль хэдийн бэлэг өгсөн. 24 цаг хүлээнэ үү.", color=ERROR_COLOR))

        partner_id = spouses[0]
        await self.add_gift(ctx.guild.id, author.id, partner_id, gift_type, gift["love"])
        await self.update_last_gift_time(ctx.guild.id, author.id)

        embed = discord.Embed(
            title="🎁 БЭЛЭГ ИЛГЭЭЛЭЭ",
            description=f"{author.mention} ханьдаа {gift['emoji']} **{gift['name']}** бэлэглэж, +{gift['love']}❤️ хайрын оноо нэмлээ!",
            color=NEON_GREEN,
            timestamp=discord.utils.utcnow()
        )
        await self._send_message(ctx, embed=embed)

    @app_commands.command(name="autoaccept", description="Гэрлэх саналыг автоматаар хүлээн авах")
    async def autoaccept(self, interaction: discord.Interaction, enabled: bool):
        await self.set_auto_accept(interaction.guild.id, interaction.user.id, enabled)
        status = "ИДЭВХТЭЙ" if enabled else "ИДЭВХГҮЙ"
        await interaction.response.send_message(f"✅ Автомат хүлээн авалт: **{status}**", ephemeral=True)

    # ================= ADOPTION =================
    @commands.hybrid_command(name='adopt', with_app_command=True, description="Хүүхэд өргөмжлөх санал тавих")
    @app_commands.describe(child="Хүүхэд")
    async def adopt(self, ctx, child: discord.Member):
        await self._adopt(ctx, ctx.author, child)

    async def _adopt(self, ctx, parent, child):
        if child.bot or child.id == parent.id:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description="Бот эсвэл өөрийгөө өргөмжлөх боломжгүй.", color=ERROR_COLOR))
        parents = await self.get_parents(ctx.guild.id, child.id)
        if parent.id in parents:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description=f"{child.mention} аль хэдийн таны хүүхэд.", color=ERROR_COLOR))

        expires = int(time.time()) + PROPOSAL_TIMEOUT
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO marriage_proposals (guild_id, from_id, to_id, proposal_type, ring_id, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            str(ctx.guild.id), str(parent.id), str(child.id), "adoption", 0, expires
        )

        embed = discord.Embed(
            title="👶 ХҮҮХЭД ӨРГӨМЖЛӨХ САНАЛ",
            description=f"{parent.mention} {child.mention}-г хүүхэд болгон өргөмжлөх санал тавьж байна!\n\n{PROPOSAL_TIMEOUT} секундын дотор зөвшөөрөх эсвэл татгалзах боломжтой.",
            color=PURPLE_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        view = AdoptView(self.bot, ctx.guild.id, parent.id, child.id)
        msg = await self._send_message(ctx, content=child.mention, embed=embed, view=view)
        view.message = msg

    @commands.hybrid_command(name='accept_adoption', with_app_command=True, description="Өргөмжлөх саналыг зөвшөөрөх")
    async def accept_adoption(self, ctx):
        await self._handle_adoption_response(ctx, ctx.author, True)

    @commands.hybrid_command(name='decline_adoption', with_app_command=True, description="Өргөмжлөх саналаас татгалзах")
    async def decline_adoption(self, ctx):
        await self._handle_adoption_response(ctx, ctx.author, False)

    async def _handle_adoption_response(self, ctx, user, accept):
        now = int(time.time())
        row = await self.bot.db.fetchone(
            "SELECT id, from_id, guild_id FROM marriage_proposals WHERE guild_id = ? AND to_id = ? AND proposal_type = 'adoption' AND expires_at > ?",
            str(ctx.guild.id), str(user.id), now
        )
        if not row:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ САНАЛ БАЙХГҮЙ", description="Танд идэвхтэй өргөмжлөх санал байхгүй.", color=ERROR_COLOR))

        prop_id, parent_id, guild_id = row
        await self.bot.db.execute("DELETE FROM marriage_proposals WHERE id = ?", prop_id)

        if accept:
            await self.bot.db.execute(
                "INSERT INTO adoptions (guild_id, parent_id, child_id, adopted_since) VALUES (?, ?, ?, ?)",
                str(guild_id), str(parent_id), str(user.id), int(time.time())
            )
            parent_member = ctx.guild.get_member(int(parent_id))
            parent_name = parent_member.mention if parent_member else f"<@{parent_id}>"
            embed = discord.Embed(title="👨‍👧‍👦 ӨРГӨМЖЛӨЛТ БАТЛАГДЛАА", description=f"{parent_name} {user.mention}-г хүүхэд болгон өргөмжлөв!", color=NEON_GREEN, timestamp=discord.utils.utcnow())
        else:
            embed = discord.Embed(title="👶 ТАТГАЛЗСАН", description=f"{user.mention} өргөмжлөх саналаас татгалзлаа.", color=WARNING_COLOR, timestamp=discord.utils.utcnow())
        await self._send_message(ctx, embed=embed)

    @commands.hybrid_command(name='disown', with_app_command=True, description="Хүүхдээс татгалзах")
    @app_commands.describe(child="Хүүхэд")
    async def disown(self, ctx, child: discord.Member):
        children = await self.get_children(ctx.guild.id, ctx.author.id)
        if child.id not in children:
            return await self._send_message(ctx, embed=discord.Embed(title="❌ АЛДАА", description=f"{child.mention} таны хүүхэд биш.", color=ERROR_COLOR))
        await self.bot.db.execute(
            "DELETE FROM adoptions WHERE guild_id = ? AND parent_id = ? AND child_id = ?",
            str(ctx.guild.id), str(ctx.author.id), str(child.id)
        )
        embed = discord.Embed(title="💔 ТАТГАЛЗСАН", description=f"{ctx.author.mention} {child.mention} -аас татгалзлаа.", color=ERROR_COLOR, timestamp=discord.utils.utcnow())
        await self._send_message(ctx, embed=embed)

    # ================= ЗУРГИЙН ТУСЛАХ ФУНКЦУУД =================
    async def _download_avatar(self, sess, url, size):
        try:
            async with sess.get(url) as resp:
                data = await resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
        except:
            img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img

    async def _fetch_small_avatar(self, sess, url):
        return await self._download_avatar(sess, url, 80)

    # ================= ГЭР БҮЛИЙН МОД (НЕОН ХОЛБООСТОЙ) =================
    def _render_family_card(self, member, spouses, children, parents, ava_main, spouse_avas, child_avas, parent_avas):
        W, H = 1100, 650
        RADIUS = 28
        BG = (15, 3, 25, 255)
        TEXT = (255, 245, 220, 255)
        TEXT2 = (200, 200, 210, 255)

        img = Image.new("RGBA", (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)

        # Арын дэвсгэр + неон хүрээ
        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG)
        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, outline=NEON_YELLOW_RGB, width=5)
        draw.rounded_rectangle([4, 4, W-5, H-5], radius=RADIUS-4, outline=NEON_PINK_RGB, width=3)
        draw.rounded_rectangle([8, 8, W-9, H-9], radius=RADIUS-8, outline=NEON_GREEN_RGB, width=1)

        # Гол хэрэглэгч
        main_size = 130
        main_x = W//2 - main_size//2
        main_y = 140
        ring_d = main_size + 14
        ring = Image.new("RGBA", (ring_d, ring_d), (0,0,0,0))
        ImageDraw.Draw(ring).ellipse((0,0,ring_d-1,ring_d-1), outline=NEON_YELLOW_RGB, width=6)
        img.paste(ring, (main_x-7, main_y-7), ring)
        img.paste(ava_main, (main_x, main_y), ava_main)
        draw.text((W//2, main_y + main_size + 15), member.display_name[:18], font=_load_font(32, True), fill=TEXT, anchor="mt")

        def draw_small_avatar(ava, name, x, y, size=70, line_from=None, line_color=None):
            r = size + 10
            ring_img = Image.new("RGBA", (r, r), (0,0,0,0))
            ImageDraw.Draw(ring_img).ellipse((0,0,r-1,r-1), outline=NEON_PINK_RGB, width=4)
            img.paste(ring_img, (x-5, y-5), ring_img)
            img.paste(ava, (x, y), ava)
            draw.text((x+size//2, y+size+5), name[:10], font=_load_font(20, False), fill=TEXT2, anchor="mt")
            if line_from:
                draw.line([line_from, (x+size//2, y)], fill=line_color or NEON_PINK_RGB, width=3)

        # Ханиуд
        spouse_y = main_y + 30
        if spouse_avas:
            draw.text((W//4, main_y - 30), "💑 Ханиуд", font=_load_font(26, True), fill=NEON_PINK_RGB, anchor="mt")
            for i, (ava, sname) in enumerate(spouse_avas[:2]):
                if i == 0:
                    sx, sy = W//2 - 220, spouse_y
                else:
                    sx, sy = W//2 + 120, spouse_y
                draw_small_avatar(ava, sname, sx, sy, size=70,
                                  line_from=(W//2, main_y + main_size//2),
                                  line_color=NEON_PINK_RGB)

        # Хүүхдүүд
        if child_avas:
            child_y = H - 160
            start_x = 80
            draw.text((W//2, child_y - 60), "👶 Хүүхдүүд", font=_load_font(26, True), fill=NEON_GREEN_RGB, anchor="mt")
            for i, (ava, cname) in enumerate(child_avas[:5]):
                cx = start_x + i * 180
                draw_small_avatar(ava, cname, cx, child_y, size=65)
                draw.line([(W//2, main_y + main_size), (W//2, main_y + main_size + 60), (cx+32, main_y + main_size + 60), (cx+32, child_y)], fill=NEON_GREEN_RGB, width=2)

        # Эцэг эх
        if parent_avas:
            parent_y = 30
            draw.text((W//2, parent_y + 100), "👪 Эцэг эх", font=_load_font(26, True), fill=NEON_YELLOW_RGB, anchor="mt")
            for i, (ava, pname) in enumerate(parent_avas[:2]):
                if i == 0:
                    px, py = W//2 - 160, parent_y
                else:
                    px, py = W//2 + 60, parent_y
                draw_small_avatar(ava, pname, px, py, size=70,
                                  line_from=(W//2, main_y),
                                  line_color=NEON_YELLOW_RGB)

        if not spouse_avas and not child_avas and not parent_avas:
            draw.text((W//2, H-100), "Гэр бүлийн мэдээлэл байхгүй", font=_load_font(30, False), fill=TEXT2, anchor="mt")

        draw.text((W//2, H-30), "🌳", font=_load_font(40, False), fill=NEON_PINK_RGB, anchor="mm")

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf

    # ================= ГЭРЛЭЛТИЙН КАРТ (ЗУРАГ) =================
    def _render_marriage_card(self, user, partner, love, ring, anniv, ava1, ava2):
        W, H = 1200, 500
        RADIUS = 28

        BG = (12, 12, 28, 255)
        TEXT = (255, 245, 220, 255)
        TEXT2 = (200, 200, 210, 255)
        PINK_GLOW = (255, 16, 240, 30)
        BLUE_GLOW = (0, 191, 255, 30)

        img = Image.new("RGBA", (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG)
        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, outline=NEON_PINK_RGB, width=5)
        draw.rounded_rectangle([4, 4, W-5, H-5], radius=RADIUS-4, outline=NEON_YELLOW_RGB, width=1)

        font_title = _load_font(60, True)
        font_sub = _load_font(42, True)
        font_info = _load_font(32, False)
        font_small = _load_font(24, False)

        ava_size = 180
        center_y = 190

        # Зүүн аватар
        left_x = 120
        glow_radius = ava_size//2 + 30
        glow_left = left_x + ava_size//2 - glow_radius
        glow_top = center_y - glow_radius
        glow_img = Image.new("RGBA", (glow_radius*2, glow_radius*2), (0,0,0,0))
        ImageDraw.Draw(glow_img).ellipse((0, 0, glow_radius*2-1, glow_radius*2-1), fill=PINK_GLOW)
        img.paste(glow_img, (glow_left, glow_top), glow_img)

        ring_d = ava_size + 14
        ring1 = Image.new("RGBA", (ring_d, ring_d), (0,0,0,0))
        ImageDraw.Draw(ring1).ellipse((0,0,ring_d-1,ring_d-1), outline=NEON_PINK_RGB, width=6)
        img.paste(ring1, (left_x - 7, center_y - ava_size//2 - 7), ring1)
        img.paste(ava1, (left_x, center_y - ava_size//2), ava1)

        name1 = user.display_name[:18]
        draw.text((left_x + ava_size//2, center_y + ava_size//2 + 35), name1, font=font_sub, fill=TEXT, anchor="mt")
        draw.text((left_x + ava_size//2, center_y + ava_size//2 + 70), "🟪 Newbie", font=font_small, fill=NEON_PINK_RGB, anchor="mt")

        # Баруун аватар
        right_x = W - 120 - ava_size
        glow_right = right_x + ava_size//2 - glow_radius
        glow_img2 = Image.new("RGBA", (glow_radius*2, glow_radius*2), (0,0,0,0))
        ImageDraw.Draw(glow_img2).ellipse((0, 0, glow_radius*2-1, glow_radius*2-1), fill=BLUE_GLOW)
        img.paste(glow_img2, (glow_right, glow_top), glow_img2)

        ring2 = Image.new("RGBA", (ring_d, ring_d), (0,0,0,0))
        ImageDraw.Draw(ring2).ellipse((0,0,ring_d-1,ring_d-1), outline=NEON_BLUE_RGB, width=6)
        img.paste(ring2, (right_x - 7, center_y - ava_size//2 - 7), ring2)
        if ava2:
            img.paste(ava2, (right_x, center_y - ava_size//2), ava2)
        else:
            placeholder = Image.new("RGBA", (ava_size, ava_size), (50,50,50,255))
            img.paste(placeholder, (right_x, center_y - ava_size//2), placeholder)

        if partner:
            name2 = partner.display_name[:18]
            draw.text((right_x + ava_size//2, center_y + ava_size//2 + 35), name2, font=font_sub, fill=TEXT, anchor="mt")
            draw.text((right_x + ava_size//2, center_y + ava_size//2 + 70), "🟥 VIP", font=font_small, fill=NEON_BLUE_RGB, anchor="mt")
        else:
            draw.text((right_x + ava_size//2, center_y + ava_size//2 + 35), "???", font=font_sub, fill=TEXT2, anchor="mt")

        heart_x = W // 2
        heart_y = center_y - 60
        draw.text((heart_x, heart_y), "❤️", font=_load_font(100, False), fill=NEON_PINK_RGB, anchor="mm")

        love_level = max(1, love // 100 + 1)
        draw.text((heart_x, heart_y + 70), f"⚡ Lv. {love_level} Love", font=font_title, fill=NEON_YELLOW_RGB, anchor="mm")

        days_text = f"✨ {anniv['days']} хоног хамт" if anniv else "✨ Дөнгөж гэрлэсэн"
        draw.text((heart_x, heart_y + 120), days_text, font=font_info, fill=TEXT, anchor="mm")

        bar_w = 800
        bar_h = 28
        bar_x = W//2 - bar_w//2
        bar_y = H - 120
        max_love = 5000
        progress = min(love / max_love, 1.0)
        fill_w = int(bar_w * progress)
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=14, fill=(30, 20, 40, 200))
        if fill_w > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=14, fill=NEON_PINK_RGB)
        draw.text((bar_x + bar_w//2, bar_y + bar_h//2), f"{love} / {max_love} Love", font=_load_font(22, False), fill=TEXT, anchor="mm")

        next_level_xp = (love_level) * 1000
        draw.text((bar_x + bar_w - 50, bar_y - 30), f"Next Level: Lv.{love_level+1}", font=font_small, fill=TEXT2, anchor="rt")

        custom_status = "✨ Бидний хайр үүрд мөнх... ✨"
        draw.text((W//2, H - 40), custom_status, font=_load_font(26, False), fill=NEON_YELLOW_RGB, anchor="mm")

        draw.text((W//2 - 80, H - 15), "♥", font=_load_font(20, False), fill=NEON_PINK_RGB, anchor="mm")
        draw.text((W//2 + 80, H - 15), "♥", font=_load_font(20, False), fill=NEON_BLUE_RGB, anchor="mm")

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf

    # ================= FAMILY TREE COMMAND =================
    @commands.hybrid_command(name='familytree', aliases=['гэрбүл', 'tree'], with_app_command=True,
                             description="Гэр бүлийн мод харах (зурагт карт)")
    async def family_tree(self, ctx, member: Optional[discord.Member] = None):
        target = member or ctx.author
        await ctx.defer()
        guild = ctx.guild
        spouses_ids = await self.get_spouses(guild.id, target.id)
        children_ids = await self.get_children(guild.id, target.id)
        parents_ids = await self.get_parents(guild.id, target.id)

        spouses = [(guild.get_member(sid), sid) for sid in spouses_ids]
        children = [(guild.get_member(cid), cid) for cid in children_ids]
        parents = [(guild.get_member(pid), pid) for pid in parents_ids]

        async with aiohttp.ClientSession() as sess:
            main_url = target.display_avatar.replace(size=256, format="png").url
            ava_main = await self._download_avatar(sess, main_url, 160)

            async def fetch_ava_list(members):
                avas = []
                for mem, uid in members[:8]:
                    url = mem.display_avatar.replace(size=256, format="png").url if mem else None
                    if url:
                        ava = await self._fetch_small_avatar(sess, url)
                        name = mem.display_name if mem else f"<@{uid}>"
                        avas.append((ava, name))
                return avas

            spouse_avas = await fetch_ava_list(spouses)
            child_avas = await fetch_ava_list(children)
            parent_avas = await fetch_ava_list(parents)

        buf = await asyncio.to_thread(
            self._render_family_card, target, spouses, children, parents,
            ava_main, spouse_avas[:4], child_avas[:4], parent_avas[:4]
        )
        embed = discord.Embed(color=NEON_GREEN)
        embed.set_image(url="attachment://family_tree.png")
        embed.set_footer(text=f"{guild.name} • Гэр бүлийн мод")
        file = discord.File(buf, filename="family_tree.png")
        await self._send_message(ctx, embed=embed, file=file)

    # ================= MARRIAGE CARD COMMAND =================
    async def build_marriage_card(self, member, guild):
        marriages = await self.get_marriages(guild.id, member.id)
        if not marriages:
            return None

        partner_id = marriages[0]["partner"]
        partner = guild.get_member(partner_id)
        love = marriages[0]["love_points"]
        ring = marriages[0]["ring"]
        raw_date = marriages[0]["marriage_date"]
        anniv = await self.get_anniversary(int(raw_date) if raw_date else None)

        async with aiohttp.ClientSession() as sess:
            url1 = member.display_avatar.replace(size=256, format="png").url
            url2 = partner.display_avatar.replace(size=256, format="png").url if partner else None
            ava1 = await self._download_avatar(sess, url1, 180)
            ava2 = await self._download_avatar(sess, url2, 180) if url2 else None

        return await asyncio.to_thread(
            self._render_marriage_card, member, partner, love, ring, anniv, ava1, ava2
        )

    @commands.hybrid_command(name='marriagepro', aliases=['mcard'], with_app_command=True,
                             description="Гэрлэлтийн карт (зураг) үзэх")
    @app_commands.describe(member="Хэний гэрлэлтийн картыг үзэх вэ?")
    async def marriage_card(self, ctx, member: Optional[discord.Member] = None):
        target = member or ctx.author
        await ctx.defer()
        buf = await self.build_marriage_card(target, ctx.guild)
        if buf is None:
            return await self._send_message(ctx, embed=discord.Embed(
                title="💔 Гэрлээгүй",
                description="Энэ хэрэглэгч гэрлээгүй байна.",
                color=ERROR_COLOR
            ))
        embed = discord.Embed(color=NEON_PINK)
        embed.set_image(url="attachment://marriage_card.png")
        embed.set_footer(text=f"{ctx.guild.name} • Гэр бүл")
        file = discord.File(buf, filename="marriage_card.png")
        await self._send_message(ctx, embed=embed, file=file)


async def setup(bot):
    await bot.add_cog(Marriage(bot))