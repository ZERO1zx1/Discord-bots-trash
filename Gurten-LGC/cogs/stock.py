import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import random

EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

# ===== БАРААНЫ НӨӨЦИЙН ХЯЗГААР (MIN, MAX) =====
STOCK_RANGES = {
    1: (50, 150), 2: (50, 150), 3: (40, 120), 4: (30, 90), 5: (35, 105),
    6: (25, 75), 7: (30, 90), 8: (25, 75), 9: (20, 60), 10: (30, 90),
    60: (100, 300),
    11: (10, 30), 12: (10, 30), 13: (5, 20), 14: (5, 20), 15: (3, 15),
    36: (2, 10), 37: (2, 10), 38: (2, 10), 39: (2, 10), 40: (3, 15),
    41: (3, 15), 42: (2, 10), 43: (5, 20), 44: (5, 20), 45: (5, 25),
    46: (1, 8),  47: (8, 30), 48: (5, 25),
    70: (8, 30), 71: (5, 25), 72: (3, 15), 73: (3, 15), 74: (3, 15),
    75: (5, 20), 76: (2, 10), 77: (2, 10), 78: (2, 10), 79: (3, 15),
    80: (5, 20), 81: (3, 15), 82: (3, 15), 83: (2, 10), 84: (3, 15),
    85: (3, 15), 86: (2, 10), 87: (5, 20), 88: (3, 15), 89: (5, 25),
    90: (5, 20), 91: (3, 15), 92: (3, 15), 93: (2, 10), 94: (2, 10),
    95: (3, 15), 96: (3, 15), 97: (5, 20), 98: (5, 20), 99: (2, 10),
    100: (5, 25), 101: (5, 20), 102: (5, 25), 103: (8, 30), 104: (5, 20),
    105: (5, 25), 106: (5, 20), 107: (5, 25), 108: (5, 20), 109: (5, 25),
    110: (5, 20), 111: (3, 15), 112: (2, 10), 113: (3, 15), 114: (3, 15),
    115: (2, 10),
    120: (8, 30), 121: (5, 25), 122: (15, 50), 123: (15, 50), 124: (5, 20),
    125: (5, 25), 126: (3, 15), 127: (3, 15), 128: (8, 30), 129: (5, 25),
    130: (5, 20), 131: (5, 25), 132: (8, 30), 133: (5, 25), 134: (10, 40),
    135: (8, 30),
}

VAPE_RANGE = (30, 80)
CAFE_RANGE = (20, 60)
DEFAULT_RANGE = (10, 50)

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_restock.start()

    def cog_unload(self):
        self.daily_restock.cancel()

    async def init_db(self):
        """SQLite table creation"""
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS shop_stock (
            guild_id TEXT,
            item_id INTEGER,
            current_stock INTEGER DEFAULT 0,
            last_restock INTEGER,
            PRIMARY KEY (guild_id, item_id)
        )''')
        await self.bot.db.commit()

    async def cog_load(self):
        await self.init_db()
        for guild in self.bot.guilds:
            await self.ensure_stocks_for_guild(guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.ensure_stocks_for_guild(guild.id)

    async def _get_all_item_ids(self):
        all_ids = set(STOCK_RANGES.keys())
        shop_cog = self.bot.get_cog("ShopCog")
        if shop_cog and hasattr(shop_cog, 'ALL_VAPE_COMBOS'):
            all_ids.update(shop_cog.ALL_VAPE_COMBOS.keys())
        cafe_cog = self.bot.get_cog("Cafe")
        if cafe_cog and hasattr(cafe_cog, 'menu'):
            for i in range(len(cafe_cog.menu)):
                all_ids.add(6000 + i)
        return all_ids

    async def ensure_stocks_for_guild(self, guild_id: int):
        item_ids = await self._get_all_item_ids()
        for item_id in item_ids:
            await self._ensure_random_stock(guild_id, item_id)

    def get_range(self, item_id):
        if item_id in STOCK_RANGES:
            return STOCK_RANGES[item_id]
        if 4000 <= item_id < 6000:
            return VAPE_RANGE
        if item_id >= 6000:
            return CAFE_RANGE
        return DEFAULT_RANGE

    async def _ensure_random_stock(self, guild_id, item_id):
        # Use fetchone to check existence
        row = await self.bot.db.fetchone(
            "SELECT 1 FROM shop_stock WHERE guild_id = ? AND item_id = ?",
            str(guild_id), item_id
        )
        if not row:
            lo, hi = self.get_range(item_id)
            rand_stock = random.randint(lo, hi)
            await self.bot.db.execute(
                "INSERT INTO shop_stock (guild_id, item_id, current_stock, last_restock) VALUES (?, ?, ?, ?)",
                str(guild_id), item_id, rand_stock, int(datetime.datetime.now().timestamp())
            )
            await self.bot.db.commit()

    # ================== PUBLIC API ==================
    async def get_stock(self, guild_id, item_id):
        await self._ensure_random_stock(guild_id, item_id)
        row = await self.bot.db.fetchone(
            "SELECT current_stock FROM shop_stock WHERE guild_id = ? AND item_id = ?",
            str(guild_id), item_id
        )
        return row[0] if row else 0

    async def consume_stock(self, guild_id, item_id, quantity=1):
        stock = await self.get_stock(guild_id, item_id)
        if stock < quantity:
            return False
        await self.bot.db.execute(
            "UPDATE shop_stock SET current_stock = current_stock - ? WHERE guild_id = ? AND item_id = ?",
            quantity, str(guild_id), item_id
        )
        await self.bot.db.commit()
        return True

    async def set_stock(self, guild_id, item_id, amount):
        await self._ensure_random_stock(guild_id, item_id)
        await self.bot.db.execute(
            "UPDATE shop_stock SET current_stock = ? WHERE guild_id = ? AND item_id = ?",
            amount, str(guild_id), item_id
        )
        await self.bot.db.commit()

    # ================== 24 ЦАГ ТУТАМ САНАМСАРГҮЙ RESET ==================
    @tasks.loop(hours=24)
    async def daily_restock(self):
        await self.bot.wait_until_ready()
        now_ts = int(datetime.datetime.now().timestamp())
        for guild in self.bot.guilds:
            await self.ensure_stocks_for_guild(guild.id)
            rows = await self.bot.db.fetch(
                "SELECT item_id FROM shop_stock WHERE guild_id = ?",
                str(guild.id)
            )
            for (item_id,) in rows:
                lo, hi = self.get_range(item_id)
                rand_val = random.randint(lo, hi)
                await self.bot.db.execute(
                    "UPDATE shop_stock SET current_stock = ?, last_restock = ? WHERE guild_id = ? AND item_id = ?",
                    rand_val, now_ts, str(guild.id), item_id
                )
            await self.bot.db.commit()
        print(f"[Stock] Бүх нөөц санамсаргүй утгаар сэргэлээ. ({datetime.datetime.now()})")

    @daily_restock.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

    # ================== КОМАНДУУД ==================
    @commands.hybrid_group(name='stock', description="Барааны нөөц удирдах")
    async def stock_group(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @stock_group.command(name='status', description="Бүх барааны нөөцийг харах")
    async def stock_status(self, ctx):
        await self.ensure_stocks_for_guild(ctx.guild.id)
        rows = await self.bot.db.fetch(
            "SELECT item_id, current_stock FROM shop_stock WHERE guild_id = ? ORDER BY item_id",
            str(ctx.guild.id)
        )
        if not rows:
            return await ctx.send(embed=discord.Embed(title="📦 Нөөц", description="Бараа байхгүй.", color=WARNING_COLOR))

        embed = discord.Embed(title="📦 Дэлгүүрийн нөөц (санамсаргүй)", color=GOLD_COLOR)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        shop_cog = self.bot.get_cog("ShopCog")
        cafe_cog = self.bot.get_cog("Cafe")
        for item_id, stock in rows[:25]:
            item = None
            if shop_cog and hasattr(shop_cog, 'ALL_VAPE_COMBOS') and item_id in shop_cog.ALL_VAPE_COMBOS:
                item = shop_cog.ALL_VAPE_COMBOS[item_id]
            elif shop_cog and hasattr(shop_cog, 'SHOP_ITEMS'):
                for shop_item in shop_cog.SHOP_ITEMS:
                    if shop_item['id'] == item_id:
                        item = shop_item
                        break
            if not item and cafe_cog and 6000 <= item_id < 7000:
                idx = item_id - 6000
                if 0 <= idx < len(cafe_cog.menu):
                    menu_item = cafe_cog.menu[idx]
                    item = {
                        "name": menu_item["name"],
                        "emoji": menu_item["emoji"],
                        "price": menu_item["price"]
                    }
            name = item['name'] if item else f"ID {item_id}"
            emoji = item.get('emoji', '📦') if item else '📦'
            lo, hi = self.get_range(item_id)
            embed.add_field(name=f"{emoji} {name}", value=f"Үлдэгдэл: **{stock}** (дараагийн reset: {lo}-{hi})", inline=True)
        if len(rows) == 0:
            embed.description = "Одоогоор ямар ч бараа байхгүй."
        await ctx.send(embed=embed)

    @stock_group.command(name='set', description="Барааны нөөцийг гараар тохируулах")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(item_id="Барааны ID", amount="Шинэ үлдэгдэл")
    async def stock_set(self, ctx, item_id: int, amount: int):
        if amount < 0:
            return await ctx.send("❌ Үлдэгдэл 0-ээс бага байж болохгүй.", ephemeral=True)
        await self.set_stock(ctx.guild.id, item_id, amount)
        await ctx.send(f"✅ ID {item_id} барааны үлдэгдэл **{amount}** боллоо. (Гэхдээ 24 цагийн дараа дахин random болно)", ephemeral=True)

    @stock_group.command(name='add', description="Барааны нөөц нэмэх")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(item_id="Барааны ID", amount="Нэмэх тоо")
    async def stock_add(self, ctx, item_id: int, amount: int):
        current = await self.get_stock(ctx.guild.id, item_id)
        await self.set_stock(ctx.guild.id, item_id, current + amount)
        await ctx.send(f"✅ ID {item_id} барааны үлдэгдэл {amount}-р нэмэгдлээ. (Одоо {current + amount})", ephemeral=True)

    @stock_group.command(name='remove', description="Барааны нөөц хасах")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(item_id="Барааны ID", amount="Хасах тоо")
    async def stock_remove(self, ctx, item_id: int, amount: int):
        current = await self.get_stock(ctx.guild.id, item_id)
        if current - amount < 0:
            return await ctx.send("❌ Үлдэгдэл 0-ээс бага болж болохгүй.", ephemeral=True)
        await self.set_stock(ctx.guild.id, item_id, current - amount)
        await ctx.send(f"✅ ID {item_id} барааны үлдэгдэл {amount}-р хасагдлаа. (Одоо {current - amount})", ephemeral=True)

    @stock_group.command(name='reset', description="Бүх нөөцийг яг одоо санамсаргүйгээр сэргээх")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def stock_reset(self, ctx):
        await self.ensure_stocks_for_guild(ctx.guild.id)
        now_ts = int(datetime.datetime.now().timestamp())
        rows = await self.bot.db.fetch(
            "SELECT item_id FROM shop_stock WHERE guild_id = ?",
            str(ctx.guild.id)
        )
        for (item_id,) in rows:
            lo, hi = self.get_range(item_id)
            rand_val = random.randint(lo, hi)
            await self.bot.db.execute(
                "UPDATE shop_stock SET current_stock = ?, last_restock = ? WHERE guild_id = ? AND item_id = ?",
                rand_val, now_ts, str(ctx.guild.id), item_id
            )
        await self.bot.db.commit()
        await ctx.send("✅ Бүх барааны нөөц санамсаргүй утгаар дүүрлээ.", ephemeral=True)

    @stock_group.command(name='refresh', description="Бүх боломжит барааны нөөцийг дахин тохируулах")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def stock_refresh(self, ctx):
        for guild in self.bot.guilds:
            await self.ensure_stocks_for_guild(guild.id)
        await ctx.send("✅ Бүх серверт нөөц дахин тохируулагдлаа.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Stock(bot))