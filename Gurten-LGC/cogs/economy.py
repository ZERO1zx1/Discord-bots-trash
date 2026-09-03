import discord
from discord.ext import commands
from discord.ui import View, Button
import random
import time
import asyncio
import io
import os
import aiohttp
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import logging
import json

# ---------- Font helper ----------
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

logger = logging.getLogger(__name__)

# ---------- Colors ----------
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa
NEON_GREEN = (57, 255, 20, 255)
NEON_YELLOW = (204, 255, 0, 255)

STARTING_BALANCE = 5000
DAILY_MIN = 4000
DAILY_MAX = 15000

# ---------- Ажлын түвшин ----------
JOB_LEVELS = {
    1:  {"name": "Гудамжны цас цэвэрлэгч",           "min": 1000,   "max": 3000,   "emoji": "❄️"},
    5:  {"name": "Нарантуул дээр тэрэгчин",          "min": 1500,   "max": 4200,   "emoji": "🛒"},
    10: {"name": "CU / GS25-ын кассчин",             "min": 2000,   "max": 4500,   "emoji": "🏪"},
    15: {"name": "Хүргэлтийн курьер (Пицца)",        "min": 2000,   "max": 4200,   "emoji": "🍕"},
    20: {"name": "Фитнессийн зааварлагч",            "min": 2800,   "max": 4400,   "emoji": "💪"},
    25: {"name": "Компьютер форматлагч",             "min": 3000,   "max": 5500,   "emoji": "💻"},
    30: {"name": "График дизайнер (Freelancer)",      "min": 3200,   "max": 4500,   "emoji": "🎨"},
    40: {"name": "Сошиал контент бүтээгч",           "min": 3500,   "max": 5600,   "emoji": "📱"},
    50: {"name": "Маркетингийн менежер",             "min": 4200,   "max": 5600,   "emoji": "📊"},
    60: {"name": "Төслийн удирдагч (Project Manager)", "min": 4700,  "max": 6300,   "emoji": "📋"},
    70: {"name": "Кибер аюулгүй байдлын мэргэжилтэн", "min": 3300,  "max": 7800,   "emoji": "🔒"},
    80: {"name": "Ахлах Программист (Senior Dev)",    "min": 4600,   "max": 8700,   "emoji": "⌨️"},
    90: {"name": "Алтны уурхайн инженер",             "min": 3000,   "max": 9600,   "emoji": "⛏️"},
    100: {"name": "Хувийн бизнес эрхлэгч",            "min": 8000,   "max": 10000,  "emoji": "🏢"},
    110: {"name": "Хөрөнгийн биржийн брокер",          "min": 4400,   "max": 11200,  "emoji": "📈"},
    120: {"name": "Томоохон банкны захирал",          "min": 8500,   "max": 12300,  "emoji": "🏦"},
    140: {"name": "Олон улсын нисгэгч (Pilot)",        "min": 5600,   "max": 11300,  "emoji": "✈️"},
    160: {"name": "Тэрбумтан хөрөнгө оруулагч",       "min": 6400,   "max": 12700,  "emoji": "💼"},
    180: {"name": "Сансрын нисгэгч (Astronaut)",        "min": 5800,   "max": 14500,  "emoji": "🚀"},
    200: {"name": "Дэлхийн Эзэн",                     "min": 6000,   "max": 18000,  "emoji": "🌍"},
}

# ---------- Гэмт хэрэг ----------
CRIMES = [
    {"name": "Банкны ATM дээрэмдэх", "success_chance": 0.45, "min_reward": 5000, "max_reward": 15000},
    {"name": "Машин хулгайлах", "success_chance": 0.35, "min_reward": 8000, "max_reward": 20000},
    {"name": "Хүн дээрэмдэх", "success_chance": 0.55, "min_reward": 2000, "max_reward": 8000},
    {"name": "Дэлгүүр тонож байна", "success_chance": 0.50, "min_reward": 4000, "max_reward": 12000},
    {"name": "Хакердах", "success_chance": 0.25, "min_reward": 10000, "max_reward": 25000},
    {"name": "Гэмт бүлэгт элсэх", "success_chance": 0.15, "min_reward": 1500, "max_reward": 5000},
]

def _fmt_money(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B ₮"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M ₮"
    return f"{n:,} ₮"

# ---------- Avatar helper ----------
async def _fetch_avatar_small(session, url, size=50):
    try:
        async with session.get(url) as resp:
            data = await resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
    except:
        img = Image.new("RGBA", (size, size), (88, 60, 60, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img

# ---------- LEADERBOARD ЗУРАГЧ ----------
def _render_money_leaderboard(guild_name: str, rows: list[dict], avatars: list[Image.Image],
                              page_offset: int, user_id: int) -> io.BytesIO:
    W = 1000
    TOP3_H = 240
    ROW_H = 64
    HEADER_H = 60
    PAD = 30
    AVA_SIZE = 48
    RADIUS = 20

    BG = (25, 27, 35, 255)
    CARD_BG = (35, 38, 49, 255)
    BORDER = (72, 76, 90, 255)
    TEXT = (255, 255, 255, 255)
    TEXT2 = (170, 175, 190, 255)
    GOLD = (255, 180, 50, 255)
    SILVER = (192, 192, 192, 255)
    BRONZE = (205, 127, 50, 255)
    ACCENT = (114, 137, 218, 255)

    n = len(rows)
    H = HEADER_H + TOP3_H + n * ROW_H + 70

    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG)
    draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, outline=BORDER, width=2)

    font_title = _load_font(30, True)
    font_sub = _load_font(20, True)
    font_small = _load_font(18, False)

    draw.text((W//2, 25), f"🏆 {guild_name} · МӨНГӨНИЙ ЭРХЭМБЭ", font=font_title, fill=TEXT, anchor="mt")

    medals = [("🥇", GOLD), ("🥈", SILVER), ("🥉", BRONZE)]
    top3_start_y = HEADER_H + 10
    col_width = (W - 2*PAD) // 3

    for i in range(3):
        if i >= len(rows):
            break
        r = rows[i]
        ava = avatars[i]
        name = r.get("name", f"ID: {r['user_id']}")[:12]
        total = r['total']
        money_str = _fmt_money(total)

        cx = PAD + col_width * i + col_width//2
        cy = top3_start_y + 10

        ring_d = AVA_SIZE + 6
        ring = Image.new("RGBA", (ring_d, ring_d), (0,0,0,0))
        ImageDraw.Draw(ring).ellipse((0,0,ring_d-1,ring_d-1), outline=medals[i][1], width=3)
        img.paste(ring, (cx - AVA_SIZE//2 - 3, cy - 3), ring)
        img.paste(ava, (cx - AVA_SIZE//2, cy), ava)

        draw.text((cx, cy + AVA_SIZE + 8), f"{medals[i][0]} {name}", font=font_sub, fill=TEXT, anchor="mt")
        draw.text((cx, cy + AVA_SIZE + 30), money_str, font=font_small, fill=TEXT2, anchor="mt")

    list_start_y = top3_start_y + TOP3_H - 10
    draw.line([(PAD, list_start_y), (W-PAD, list_start_y)], fill=BORDER, width=1)

    for i, r in enumerate(rows):
        y = list_start_y + 15 + i * ROW_H
        rank = page_offset + i + 1
        name = r.get("name", f"ID: {r['user_id']}")[:20]
        total = r['total']
        money_str = _fmt_money(total)

        row_color = (40, 43, 55, 255) if i % 2 == 0 else BG
        if r['user_id'] == str(user_id):
            row_color = (55, 62, 85, 255)
        draw.rounded_rectangle([PAD, y-2, W-PAD, y + ROW_H-6], radius=6, fill=row_color)

        rank_color = GOLD if rank <= 3 else TEXT2
        draw.text((PAD + 10, y + ROW_H//2 - 12), f"#{rank}", font=font_sub, fill=rank_color, anchor="lm")

        if i < len(avatars):
            small_ava = avatars[i].resize((32, 32))
            img.paste(small_ava, (PAD + 60, y + ROW_H//2 - 16), small_ava)

        draw.text((PAD + 100, y + ROW_H//2 - 12), name, font=font_small, fill=TEXT, anchor="lm")
        draw.text((W - PAD - 20, y + ROW_H//2 - 12), money_str, font=font_small, fill=TEXT2, anchor="rm")

    your_y = H - 50
    draw.line([(PAD, your_y - 10), (W-PAD, your_y - 10)], fill=BORDER, width=1)
    your_rank = "?"
    your_total = "0"
    for i, r in enumerate(rows):
        if r['user_id'] == str(user_id):
            your_rank = f"#{page_offset + i + 1}"
            your_total = _fmt_money(r['total'])
            break
    draw.text((W//2, your_y + 5), f"{your_rank}  │  💰 Нийт: {your_total}", font=font_small, fill=ACCENT, anchor="mt")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf

# ---------- Leaderboard View ----------
class MoneyLeaderboardView(View):
    def __init__(self, cog, ctx, entries, page, total_money, user_id):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.entries = entries
        self.page = page
        self.per_page = 10
        self.total_money = total_money
        self.user_id = user_id
        self.message = None
        self._refresh()

    def _refresh(self):
        total_pages = max(1, -(-len(self.entries) // self.per_page))
        self.prev_button.disabled = (self.page == 0)
        self.next_button.disabled = (self.page >= total_pages - 1)

    async def update_message(self, interaction):
        await interaction.response.defer()
        start = self.page * self.per_page
        end = start + self.per_page
        page_entries = self.entries[start:end]

        async with aiohttp.ClientSession() as sess:
            avatars = []
            for r in page_entries:
                url = r.get("avatar_url")
                if url:
                    ava = await _fetch_avatar_small(sess, url)
                else:
                    ava = Image.new("RGBA", (50, 50), (88,60,60,255))
                avatars.append(ava)

        buf = await asyncio.to_thread(
            _render_money_leaderboard, self.ctx.guild.name, page_entries, avatars, start, self.user_id
        )
        embed = discord.Embed(color=0x39FF14)
        embed.set_image(url="attachment://leaderboard.png")
        file = discord.File(buf, filename="leaderboard.png")
        self._refresh()
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="◀ Өмнөх", style=discord.ButtonStyle.gray)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Дараах ▶", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        total_pages = max(1, -(-len(self.entries) // self.per_page))
        if self.page < total_pages - 1:
            self.page += 1
            await self.update_message(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except:
                pass

class ConfirmView(View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Тийм ✅", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Үгүй ❌", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()
        await interaction.response.defer()

# ---------- ЭДИЙН ЗАСГИЙН COG ----------
class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.max_balance = bot.config.get("max_balance", 100_000_000)
        self.transfer_tax_percent = bot.config.get("transfer_tax_percent", 10)
        self.bonus_percent = bot.config.get("bonus_percent", 10)
        self.chat_money_cooldown = {}
        self.use_default_replies = True

    async def cog_load(self):
        await self.init_db()
        self.role_income_task = self.bot.loop.create_task(self._role_income_loop())

    async def init_db(self):
        # Үндсэн хүснэгт
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS economy (
            user_id TEXT,
            guild_id TEXT,
            balance INTEGER DEFAULT 0,
            bank_balance INTEGER DEFAULT 0,
            last_daily INTEGER,
            last_work INTEGER,
            bank_protect_until INTEGER DEFAULT 0,
            prison_until INTEGER DEFAULT 0,
            hunger INTEGER DEFAULT 0,
            mood INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )''')
        await self.bot.db.commit()

        # Тохиргооны хүснэгт
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS economy_config (
            guild_id TEXT,
            key TEXT,
            value TEXT,
            PRIMARY KEY (guild_id, key)
        )''')
        await self.bot.db.commit()

        # Custom replies
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS custom_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            command TEXT,
            type TEXT,
            text TEXT
        )''')
        await self.bot.db.commit()

        # Cooldowns тохиргоо
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS economy_cooldowns_config (
            guild_id TEXT,
            command TEXT,
            cooldown_seconds INTEGER,
            PRIMARY KEY (guild_id, command)
        )''')
        await self.bot.db.commit()

        # Торгууль тохиргоо
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS economy_fines_config (
            guild_id TEXT,
            command TEXT,
            fine_min INTEGER,
            fine_max INTEGER,
            fine_type TEXT DEFAULT 'fixed',
            PRIMARY KEY (guild_id, command)
        )''')
        await self.bot.db.commit()

        # Ажлын хөлс тохиргоо
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS economy_payouts_config (
            guild_id TEXT,
            command TEXT,
            payout_min INTEGER,
            payout_max INTEGER,
            PRIMARY KEY (guild_id, command)
        )''')
        await self.bot.db.commit()

        # Бүтэлгүйтэх магадлал
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS economy_fail_rates (
            guild_id TEXT,
            command TEXT,
            fail_rate REAL,
            PRIMARY KEY (guild_id, command)
        )''')
        await self.bot.db.commit()

        # Роль орлого
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS role_income (
            guild_id TEXT,
            role_id INTEGER,
            amount INTEGER,
            interval_seconds INTEGER,
            PRIMARY KEY (guild_id, role_id)
        )''')
        await self.bot.db.commit()

        # Чат мөнгө тохиргоо
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS chat_money_config (
            guild_id TEXT,
            min_amount INTEGER DEFAULT 1,
            max_amount INTEGER DEFAULT 5,
            cooldown INTEGER DEFAULT 60,
            PRIMARY KEY (guild_id)
        )''')
        await self.bot.db.commit()

        # Чат мөнгө сувгууд
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS chat_money_channels (
            guild_id TEXT,
            channel_id INTEGER,
            PRIMARY KEY (guild_id, channel_id)
        )''')
        await self.bot.db.commit()

        # Тоглоомын хөргөлт
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS game_cooldowns (
            guild_id TEXT,
            command TEXT,
            cooldown INTEGER,
            PRIMARY KEY (guild_id, command)
        )''')
        await self.bot.db.commit()

        # Хуучин багана нэмэх
        for col, default in [("bank_balance", 0), ("hunger", 0), ("mood", 0)]:
            try:
                await self.bot.db.execute(f"ALTER TABLE economy ADD COLUMN {col} INTEGER DEFAULT {default}")
                await self.bot.db.commit()
            except:
                pass

    # ---------- Регистр ----------
    async def is_registered(self, user_id, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT 1 FROM economy WHERE user_id = ? AND guild_id = ?",
            str(user_id), str(guild_id)
        )
        return row is not None

    async def check_registration(self, ctx):
        if await self.is_registered(ctx.author.id, ctx.guild.id):
            return True
        embed = discord.Embed(
            title="🎉 **Gurten Network**-д тавтай морил!",
            description=(
                "Та одоогоор бүртгэлгүй байна.\n\n"
                "Gurten-ийн эдийн засаг, түвшин, дэлгүүр, гэрлэлт болон бусад бүх системийг ашиглахын тулд эхлээд бүртгүүлэх шаардлагатай.\n\n"
                "### 🎁 Бүртгүүлсний урамшуулал\n"
                "> 💰 10,000₮ эхлэх бонус\n"
                "> 📈 Level & XP системд нэгдэх\n"
                "> 🛒 Дэлгүүр болон inventory ашиглах\n"
                "> 💍 Marriage систем ашиглах\n"
                "> 🎲 Казино болон тоглоомуудад оролцох\n\n"
                "`/register` командыг ашиглан бүртгүүлнэ үү.\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "✨ Таны аялал эндээс эхэлнэ.\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            color=0xFFD700
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)
        return False

    # ---------- Хэрэглэгчийн баланс ----------
    async def get_balance(self, user_id, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT balance FROM economy WHERE user_id = ? AND guild_id = ?",
            str(user_id), str(guild_id)
        )
        return row[0] if row else 0

    async def update_balance(self, user_id, guild_id, delta):
        current = await self.get_balance(user_id, guild_id)
        new_bal = current + delta
        if new_bal > self.max_balance:
            new_bal = self.max_balance
        if new_bal < 0:
            new_bal = 0
        await self.bot.db.execute(
            "UPDATE economy SET balance = ? WHERE user_id = ? AND guild_id = ?",
            new_bal, str(user_id), str(guild_id)
        )
        await self.bot.db.commit()
        return new_bal

    async def get_bank(self, user_id, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT bank_balance FROM economy WHERE user_id = ? AND guild_id = ?",
            str(user_id), str(guild_id)
        )
        return row[0] if row else 0

    async def update_bank(self, user_id, guild_id, delta):
        current = await self.get_bank(user_id, guild_id)
        new_bal = current + delta
        if new_bal > self.max_balance:
            new_bal = self.max_balance
        if new_bal < 0:
            new_bal = 0
        await self.bot.db.execute(
            "UPDATE economy SET bank_balance = ? WHERE user_id = ? AND guild_id = ?",
            new_bal, str(user_id), str(guild_id)
        )
        await self.bot.db.commit()
        return new_bal

    async def get_hunger_mood(self, user_id, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT hunger, mood FROM economy WHERE user_id = ? AND guild_id = ?",
            str(user_id), str(guild_id)
        )
        return (row[0], row[1]) if row else (0, 0)

    async def set_hunger_mood(self, user_id, guild_id, hunger=None, mood=None):
        sets, params = [], []
        if hunger is not None:
            sets.append("hunger = ?")
            params.append(max(0, min(100, hunger)))
        if mood is not None:
            sets.append("mood = ?")
            params.append(max(0, min(100, mood)))
        if not sets:
            return
        params.extend([str(user_id), str(guild_id)])
        sql = f"UPDATE economy SET {', '.join(sets)} WHERE user_id = ? AND guild_id = ?"
        await self.bot.db.execute(sql, *params)
        await self.bot.db.commit()

    async def get_discord_level(self, user_id, guild_id):
        level_cog = self.bot.get_cog("Leveling")
        if level_cog:
            row = await self.bot.db.fetchone(
                "SELECT level FROM levels WHERE user_id = ? AND guild_id = ?",
                str(user_id), str(guild_id)
            )
            if row:
                return row[0]
        return 1

    def get_job_for_level(self, discord_level):
        for required_level in sorted(JOB_LEVELS.keys(), reverse=True):
            if discord_level >= required_level:
                return required_level, JOB_LEVELS[required_level]
        return 1, JOB_LEVELS[1]

    async def set_prison(self, user_id, guild_id, hours=2):
        until = int(time.time()) + (hours * 3600)
        await self.bot.db.execute(
            "UPDATE economy SET prison_until = ? WHERE user_id = ? AND guild_id = ?",
            until, str(user_id), str(guild_id)
        )
        await self.bot.db.commit()

    async def get_prison_remaining(self, user_id, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT prison_until FROM economy WHERE user_id = ? AND guild_id = ?",
            str(user_id), str(guild_id)
        )
        if row and row[0] and row[0] > int(time.time()):
            return row[0] - int(time.time())
        return 0

    async def is_in_prison(self, user_id, guild_id):
        return await self.get_prison_remaining(user_id, guild_id) > 0

    async def bail_out(self, user_id, guild_id, cost=50000):
        if not await self.is_in_prison(user_id, guild_id):
            return True
        bal = await self.get_balance(user_id, guild_id)
        if bal < cost:
            return False
        await self.update_balance(user_id, guild_id, -cost)
        await self.bot.db.execute(
            "UPDATE economy SET prison_until = 0 WHERE user_id = ? AND guild_id = ?",
            str(user_id), str(guild_id)
        )
        await self.bot.db.commit()
        return True

    async def set_bank_protection(self, user_id, guild_id, hours=2):
        until = int(time.time()) + (hours * 3600)
        await self.bot.db.execute(
            "UPDATE economy SET bank_protect_until = ? WHERE user_id = ? AND guild_id = ?",
            until, str(user_id), str(guild_id)
        )
        await self.bot.db.commit()

    async def get_bank_protection(self, user_id, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT bank_protect_until FROM economy WHERE user_id = ? AND guild_id = ?",
            str(user_id), str(guild_id)
        )
        if row and row[0] and row[0] > int(time.time()):
            return row[0] - int(time.time())
        return 0

    async def is_bank_protected(self, user_id, guild_id):
        return await self.get_bank_protection(user_id, guild_id) > 0

    async def give_xp(self, ctx, amount):
        leveling = self.bot.get_cog("Leveling")
        if leveling:
            try:
                await leveling.add_xp(ctx.author.id, ctx.guild.id, amount, member=ctx.author,
                                      check_mute=True, channel=ctx.channel)
            except AttributeError:
                if hasattr(leveling, 'add_command_xp'):
                    await leveling.add_command_xp(ctx.author.id, ctx.guild.id, ctx.author, ctx.channel)

    # ==================== Role Income Loop ====================
    async def _role_income_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                rows = await self.bot.db.fetch("SELECT guild_id, role_id, amount, interval_seconds FROM role_income")
                for guild_id, role_id, amount, interval in rows:
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        continue
                    role = guild.get_role(int(role_id))
                    if not role:
                        continue
                    for member in role.members:
                        if not member.bot:
                            await self.update_balance(member.id, guild.id, amount)
            except Exception as e:
                logger.error(f"Role income loop error: {e}")
            await asyncio.sleep(60)

    # ==================== Туслах функцүүд (тохиргоо унших) ====================
    async def get_custom_reply(self, guild_id, command, success):
        row = await self.bot.db.fetchone(
            "SELECT text FROM custom_replies WHERE guild_id=? AND command=? AND type=?",
            str(guild_id), command, "success" if success else "fail"
        )
        return row[0] if row else None

    async def get_cooldown_config(self, guild_id, command, default=3600):
        row = await self.bot.db.fetchone(
            "SELECT cooldown_seconds FROM economy_cooldowns_config WHERE guild_id=? AND command=?",
            str(guild_id), command
        )
        return row[0] if row else default

    async def get_fine_config(self, guild_id, command):
        row = await self.bot.db.fetchone(
            "SELECT fine_min, fine_max, fine_type FROM economy_fines_config WHERE guild_id=? AND command=?",
            str(guild_id), command
        )
        if row:
            return {"min": row[0], "max": row[1], "type": row[2]}
        return {"min": 100, "max": 500, "type": "fixed"}

    async def get_payout_config(self, guild_id, command):
        row = await self.bot.db.fetchone(
            "SELECT payout_min, payout_max FROM economy_payouts_config WHERE guild_id=? AND command=?",
            str(guild_id), command
        )
        if row:
            return {"min": row[0], "max": row[1]}
        return None

    async def get_fail_rate(self, guild_id, command, default=0.5):
        row = await self.bot.db.fetchone(
            "SELECT fail_rate FROM economy_fail_rates WHERE guild_id=? AND command=?",
            str(guild_id), command
        )
        return row[0] if row else default

    # ==================== Админ командууд ====================
    @commands.command(name='role-income')
    @commands.has_permissions(administrator=True)
    async def role_income_cmd(self, ctx, role: discord.Role, amount: int, interval_seconds: int):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO role_income (guild_id, role_id, amount, interval_seconds) VALUES (?,?,?,?)",
            str(ctx.guild.id), role.id, amount, interval_seconds
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ {role.mention}-т {interval_seconds}с тутам {amount:,}₮ олгохоор тохирууллаа.")

    @commands.command(name='set-cooldown')
    @commands.has_permissions(administrator=True)
    async def set_cooldown_cmd(self, ctx, command: str, seconds: int):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_cooldowns_config (guild_id, command, cooldown_seconds) VALUES (?,?,?)",
            str(ctx.guild.id), command.lower(), seconds
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{command}` командын хөргөлт {seconds} секунд боллоо.")

    @commands.command(name='add-fail-reply')
    @commands.has_permissions(administrator=True)
    async def add_fail_reply(self, ctx, command: str, *, text: str):
        await self.bot.db.execute(
            "INSERT INTO custom_replies (guild_id, command, type, text) VALUES (?,?,?,?)",
            str(ctx.guild.id), command.lower(), "fail", text
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{command}` бүтэлгүйтэхэд '{text}' гэж хариулах боллоо.")

    @commands.command(name='add-reply')
    @commands.has_permissions(administrator=True)
    async def add_reply(self, ctx, command: str, *, text: str):
        await self.bot.db.execute(
            "INSERT INTO custom_replies (guild_id, command, type, text) VALUES (?,?,?,?)",
            str(ctx.guild.id), command.lower(), "success", text
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{command}` амжилттай бол '{text}' гэж хариулах боллоо.")

    @commands.command(name='list-custom-replies')
    @commands.has_permissions(administrator=True)
    async def list_replies(self, ctx):
        rows = await self.bot.db.fetch(
            "SELECT id, command, type, text FROM custom_replies WHERE guild_id=?",
            str(ctx.guild.id)
        )
        if not rows:
            return await ctx.send("Одоогоор custom reply байхгүй.")
        embed = discord.Embed(title="📋 Custom Replies")
        for r in rows:
            embed.add_field(name=f"ID {r[0]} - {r[1]} ({r[2]})", value=r[3][:100], inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='delete-reply')
    @commands.has_permissions(administrator=True)
    async def delete_reply(self, ctx, reply_id: int):
        await self.bot.db.execute("DELETE FROM custom_replies WHERE id=? AND guild_id=?", reply_id, str(ctx.guild.id))
        await self.bot.db.commit()
        await ctx.send(f"✅ Reply ID {reply_id} устгагдлаа.")

    @commands.command(name='default-replies')
    @commands.has_permissions(administrator=True)
    async def default_replies(self, ctx, toggle: str):
        if toggle.lower() not in ['on', 'off']:
            return await ctx.send("❌ `on` эсвэл `off` гэж бичнэ үү.")
        self.use_default_replies = toggle.lower() == 'on'
        await ctx.send(f"✅ Анхдагч хариу бичвэрүүд {'идэвхтэй' if self.use_default_replies else 'унтарсан'}.")

    @commands.command(name='set-fine-amount')
    @commands.has_permissions(administrator=True)
    async def set_fine_amount(self, ctx, command: str, fine_min: int, fine_max: int):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_fines_config (guild_id, command, fine_min, fine_max) VALUES (?,?,?,?)",
            str(ctx.guild.id), command.lower(), fine_min, fine_max
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{command}` торгууль {fine_min}-{fine_max} боллоо.")

    @commands.command(name='set-payout')
    @commands.has_permissions(administrator=True)
    async def set_payout(self, ctx, command: str, payout_min: int, payout_max: int):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_payouts_config (guild_id, command, payout_min, payout_max) VALUES (?,?,?,?)",
            str(ctx.guild.id), command.lower(), payout_min, payout_max
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{command}` цалин {payout_min}-{payout_max} боллоо.")

    @commands.command(name='set-fail-rate')
    @commands.has_permissions(administrator=True)
    async def set_fail_rate(self, ctx, command: str, rate: float):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_fail_rates (guild_id, command, fail_rate) VALUES (?,?,?)",
            str(ctx.guild.id), command.lower(), rate
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{command}` бүтэлгүйтэх магадлал {rate*100}% боллоо.")

    @commands.command(name='set-fine-type')
    @commands.has_permissions(administrator=True)
    async def set_fine_type(self, ctx, command: str, fine_type: str):
        if fine_type not in ['fixed', 'percent']:
            return await ctx.send("❌ `fixed` эсвэл `percent` гэж бичнэ үү.")
        await self.bot.db.execute(
            "UPDATE economy_fines_config SET fine_type=? WHERE guild_id=? AND command=?",
            fine_type, str(ctx.guild.id), command.lower()
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{command}` торгуулийн төрөл `{fine_type}` боллоо.")

    @commands.command(name='chat-money-amount')
    @commands.has_permissions(administrator=True)
    async def chat_money_amount(self, ctx, min_amt: int, max_amt: int):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO chat_money_config (guild_id, min_amount, max_amount) VALUES (?,?,?)",
            str(ctx.guild.id), min_amt, max_amt
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Чат мөнгө {min_amt}-{max_amt}₮ боллоо.")

    @commands.command(name='chat-money-channels')
    @commands.has_permissions(administrator=True)
    async def chat_money_channels(self, ctx, action: str, channel: discord.TextChannel = None):
        if action == 'add' and channel:
            await self.bot.db.execute("INSERT OR IGNORE INTO chat_money_channels VALUES (?,?)", str(ctx.guild.id), channel.id)
            await self.bot.db.commit()
            await ctx.send(f"✅ {channel.mention} чат мөнгө авах сувагт нэмэгдлээ.")
        elif action == 'remove' and channel:
            await self.bot.db.execute("DELETE FROM chat_money_channels WHERE guild_id=? AND channel_id=?", str(ctx.guild.id), channel.id)
            await self.bot.db.commit()
            await ctx.send(f"✅ {channel.mention} чат мөнгө авах сувгаас хасагдлаа.")
        elif action == 'list':
            rows = await self.bot.db.fetch("SELECT channel_id FROM chat_money_channels WHERE guild_id=?", str(ctx.guild.id))
            if not rows:
                return await ctx.send("Суваг тохируулаагүй.")
            channels = [f"<#{r[0]}>" for r in rows]
            await ctx.send("📋 Чат мөнгө авах сувгууд: " + ", ".join(channels))
        else:
            await ctx.send("❌ `add`, `remove`, эсвэл `list` гэж бичнэ үү.")

    @commands.command(name='chat-money-cooldown')
    @commands.has_permissions(administrator=True)
    async def chat_money_cooldown_cmd(self, ctx, seconds: int):
        await self.bot.db.execute(
            "UPDATE chat_money_config SET cooldown=? WHERE guild_id=?",
            seconds, str(ctx.guild.id)
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Чат мөнгөний хөргөлт {seconds}с боллоо.")

    # ---------- Шинэ админ командууд ----------
    @commands.command(name='set-currency')
    @commands.has_permissions(administrator=True)
    async def set_currency(self, ctx, emoji: str):
        """Валютын тэмдэгтийг тохируулах"""
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'currency', ?)",
            str(ctx.guild.id), emoji
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Валют: {emoji}")

    @commands.command(name='set-start-balance')
    @commands.has_permissions(administrator=True)
    async def set_start_balance(self, ctx, amount: int):
        """Шинэ гишүүдийн анхны баланс"""
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'start_balance', ?)",
            str(ctx.guild.id), str(amount)
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Шинэ гишүүдийн анхны баланс: **{amount:,}** ₮")

    @commands.command(name='money-audit-log')
    @commands.has_permissions(administrator=True)
    async def money_audit_log(self, ctx, channel: discord.TextChannel = None):
        """Мөнгөний гүйлгээний лог суваг тохируулах"""
        if channel:
            await self.bot.db.execute(
                "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'audit_channel', ?)",
                str(ctx.guild.id), str(channel.id)
            )
            await self.bot.db.commit()
            await ctx.send(f"✅ Лог суваг: {channel.mention}")
        else:
            await self.bot.db.execute(
                "DELETE FROM economy_config WHERE guild_id=? AND key='audit_channel'",
                str(ctx.guild.id)
            )
            await self.bot.db.commit()
            await ctx.send("✅ Лог суваг унтарлаа.")

    @commands.command(name='max-balance')
    @commands.has_permissions(administrator=True)
    async def max_balance(self, ctx, amount: int):
        """Хамгийн дээд баланс"""
        self.max_balance = amount
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'max_balance', ?)",
            str(ctx.guild.id), str(amount)
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Хамгийн дээд баланс: **{amount:,}** ₮")

    @commands.command(name='add-money')
    @commands.has_permissions(administrator=True)
    async def add_money(self, ctx, member: discord.Member, amount: int):
        """Тухайн гишүүнд мөнгө нэмэх"""
        await self.update_balance(member.id, ctx.guild.id, amount)
        await ctx.send(f"✅ {member.mention}-д **{amount:,}** ₮ нэмлээ.")

    @commands.command(name='add-money-role')
    @commands.has_permissions(administrator=True)
    async def add_money_role(self, ctx, role: discord.Role, amount: int):
        """Тухайн рольтой бүх гишүүнд мөнгө нэмэх"""
        count = 0
        for member in role.members:
            if not member.bot:
                await self.update_balance(member.id, ctx.guild.id, amount)
                count += 1
        await ctx.send(f"✅ {role.mention} рольтой **{count}** гишүүнд **{amount:,}** ₮ нэмлээ.")

    @commands.command(name='remove-money')
    @commands.has_permissions(administrator=True)
    async def remove_money(self, ctx, member: discord.Member, amount: int):
        """Тухайн гишүүнээс мөнгө хасах"""
        bal = await self.get_balance(member.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(f"❌ {member.mention}-д хангалттай мөнгө байхгүй.")
        await self.update_balance(member.id, ctx.guild.id, -amount)
        await ctx.send(f"✅ {member.mention}-ээс **{amount:,}** ₮ хаслаа.")

    @commands.command(name='remove-money-role')
    @commands.has_permissions(administrator=True)
    async def remove_money_role(self, ctx, role: discord.Role, amount: int):
        """Тухайн рольтой бүх гишүүнээс мөнгө хасах"""
        count = 0
        for member in role.members:
            if not member.bot:
                bal = await self.get_balance(member.id, ctx.guild.id)
                if bal >= amount:
                    await self.update_balance(member.id, ctx.guild.id, -amount)
                    count += 1
        await ctx.send(f"✅ {role.mention} рольтой **{count}** гишүүнээс **{amount:,}** ₮ хаслаа.")

    @commands.command(name='economy-stats')
    @commands.has_permissions(administrator=True)
    async def economy_stats(self, ctx):
        """Серверийн эдийн засгийн статистик"""
        rows = await self.bot.db.fetch(
            "SELECT SUM(balance), SUM(bank_balance), COUNT(*) FROM economy WHERE guild_id=?",
            str(ctx.guild.id)
        )
        total_cash, total_bank, users = rows[0] if rows else (0, 0, 0)
        total = (total_cash or 0) + (total_bank or 0)
        embed = discord.Embed(title="💰 Эдийн засгийн статистик", color=GOLD_COLOR)
        embed.add_field(name="👥 Бүртгэлтэй хэрэглэгчид", value=f"{users or 0}")
        embed.add_field(name="💵 Нийт бэлэн мөнгө", value=f"{total_cash or 0:,} ₮")
        embed.add_field(name="🏦 Нийт банк", value=f"{total_bank or 0:,} ₮")
        embed.add_field(name="💎 Нийт эргэлт", value=f"{total:,} ₮")
        await ctx.send(embed=embed)

    @commands.command(name='set-bet-limit')
    @commands.has_permissions(administrator=True)
    async def set_bet_limit(self, ctx, min_bet: int, max_bet: int):
        """Мөрийн доод/дээд хязгаар тогтоох"""
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'bet_min', ?)",
            str(ctx.guild.id), str(min_bet)
        )
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'bet_max', ?)",
            str(ctx.guild.id), str(max_bet)
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Мөрийн хязгаар: **{min_bet:,} - {max_bet:,}** ₮")

    @commands.command(name='set-blackjack-decks')
    @commands.has_permissions(administrator=True)
    async def set_blackjack_decks(self, ctx, decks: int):
        """Блэкжэкийн хөзрийн багцын тоо"""
        if decks < 1 or decks > 8:
            return await ctx.send("❌ 1-8 хооронд байх ёстой.")
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'bj_decks', ?)",
            str(ctx.guild.id), str(decks)
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Блэкжэк **{decks}** багц хөзөртэй боллоо.")

    @commands.command(name='set-game-cooldown')
    @commands.has_permissions(administrator=True)
    async def set_game_cooldown(self, ctx, game: str, seconds: int):
        """Тоглоомын хөргөлтийн хугацаа"""
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO game_cooldowns (guild_id, command, cooldown) VALUES (?, ?, ?)",
            str(ctx.guild.id), game.lower(), seconds
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{game}` тоглоомын хөргөлт **{seconds}с** боллоо.")

    @commands.command(name='slot-machine-symbol')
    @commands.has_permissions(administrator=True)
    async def slot_machine_symbol(self, ctx, *symbols):
        """Слот машины дүрсүүдийг тохируулах (5 ширхэг эможи)"""
        if len(symbols) < 3:
            return await ctx.send("❌ Хамгийн багадаа 3 тэмдэгт оруулна уу.")
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'slot_symbols', ?)",
            str(ctx.guild.id), json.dumps(list(symbols))
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Слот дүрсүүд: {' '.join(symbols)}")

    @commands.command(name='cock-fight-win-chance')
    @commands.has_permissions(administrator=True)
    async def cock_fight_win_chance(self, ctx, chance: float):
        """Тахианы зодооны ялах магадлал (0-100%)"""
        if chance < 0 or chance > 100:
            return await ctx.send("❌ 0-100 хооронд байх ёстой.")
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO economy_config (guild_id, key, value) VALUES (?, 'cockfight_chance', ?)",
            str(ctx.guild.id), str(chance / 100)
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ Тахианы зодооны ялах магадлал: **{chance}%**")

    # ---------- Үндсэн командууд ----------
    @commands.command(aliases=['bal', 'money', 'wallet', 'bank'])
    async def balance(self, ctx, member: discord.Member = None):
        if not await self.check_registration(ctx):
            return
        target = member or ctx.author
        cash = await self.get_balance(target.id, ctx.guild.id)
        bank = await self.get_bank(target.id, ctx.guild.id)
        total = cash + bank
        prison = await self.get_prison_remaining(target.id, ctx.guild.id)
        disc_level = await self.get_discord_level(target.id, ctx.guild.id)
        job_level, job = self.get_job_for_level(disc_level)

        embed = discord.Embed(title=f"🏦 {target.display_name} - ИЙН САНХҮҮ",
                              color=0xffd700 if total >= 50000 else 0x2b2d31)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💰 ГАР ДЭЭР", value=f"```yaml\n{cash:,} мөнгө```", inline=True)
        embed.add_field(name="🏦 БАНКАНД", value=f"```yaml\n{bank:,} мөнгө```", inline=True)
        embed.add_field(name="💎 НИЙТ", value=f"```fix\n{total:,} мөнгө```", inline=True)
        embed.add_field(name="💼 Ажил", value=f"{job['emoji']} {job['name']} (Lv.{job_level})", inline=False)
        embed.add_field(name="⭐ Discord Lv.", value=f"{disc_level}", inline=True)
        if prison > 0:
            h, m = divmod(prison, 3600)[0], (prison % 3600) // 60
            embed.add_field(name="🚔 ШОРОН", value=f"⛓️ {h}ц {m}мин\n💸 50,000₮ төлж гарах: `g bail`")
        else:
            if total >= 200000: status = "👑 ХЭТ БАЯН"
            elif total >= 100000: status = "💎 МАШ БАЯН"
            elif total >= 30000: status = "💰 БАЯН"
            elif total >= 10000: status = "💵 ДУНДАЖ"
            elif total >= 5000: status = "💰 ЭНГИН"
            else: status = "🥉 ЯДУУ"
            embed.add_field(name="📈 STATS", value=f"```ini\n[{status}]```", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name='bail')
    async def bail_command(self, ctx):
        if not await self.check_registration(ctx):
            return
        prison = await self.get_prison_remaining(ctx.author.id, ctx.guild.id)
        if prison <= 0:
            return await ctx.send(embed=discord.Embed(title="✅ Та шоронд байхгүй!", color=SUCCESS_COLOR))
        success = await self.bail_out(ctx.author.id, ctx.guild.id, 50000)
        if success:
            embed = discord.Embed(title="🔓 ШОРОНГООС ГАРЛАА", description="50,000₮ төлж суллагдлаа.", color=SUCCESS_COLOR)
        else:
            embed = discord.Embed(title="❌ МӨНГӨ ХҮРЭЛЦЭХГҮЙ", description="50,000₮ байхгүй.", color=ERROR_COLOR)
        await ctx.send(embed=embed)

    @commands.command(name='daily')
    async def daily(self, ctx):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд өдрийн урамшуулал авахгүй.")
        now = int(time.time())
        row = await self.bot.db.fetchone(
            "SELECT last_daily FROM economy WHERE user_id = ? AND guild_id = ?",
            str(ctx.author.id), str(ctx.guild.id)
        )
        last = row[0] if row else 0
        if last and now - last < 86400:
            rem = 86400 - (now - last)
            h, m, s = rem // 3600, (rem % 3600) // 60, rem % 60
            embed = discord.Embed(title="⏰ ӨДРИЙН УРАМШУУЛАЛ АВСАН",
                                  description=f"{ctx.author.mention} та өнөөдрийн урамшуулал авсан.", color=0xfee75c)
            embed.add_field(name="Дараагийн урамшуулал", value=f"{h}ц {m}м {s}с")
            return await ctx.send(embed=embed)
        reward = random.randint(DAILY_MIN, DAILY_MAX)
        await self.bot.db.execute(
            "UPDATE economy SET last_daily = ? WHERE user_id = ? AND guild_id = ?",
            now, str(ctx.author.id), str(ctx.guild.id)
        )
        await self.bot.db.commit()
        await self.update_balance(ctx.author.id, ctx.guild.id, reward)
        xp = random.randint(5,10)
        await self.give_xp(ctx, xp)
        embed = discord.Embed(title="🎉 ӨДРИЙН УРАМШУУЛАЛ!", description=f"{ctx.author.mention}")
        embed.add_field(name="💰 ШАГНАЛ", value=f"```diff\n+ {reward:,} мөнгө```", inline=True)
        embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=True)
        embed.add_field(name="📈 ТАНЫ STATS", value=f"```ini\n[{_fmt_money(await self.get_balance(ctx.author.id, ctx.guild.id))}]```", inline=False)
        embed.set_footer(text="Дараагийн урамшуулал 24 цагийн дараа авах боломжтой.")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='jobs', aliases=['joblist'])
    async def jobs(self, ctx):
        embed = discord.Embed(title="💼 АЖЛЫН ЖАГСААЛТ", color=GOLD_COLOR)
        for level in sorted(JOB_LEVELS.keys()):
            job = JOB_LEVELS[level]
            embed.add_field(name=f"{job['emoji']} {job['name']} (Lv.{level})",
                            value=f"```yaml\n{job['min']:,} - {job['max']:,} мөнгө```", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='setjob')
    async def setjob(self, ctx, level: int):
        if not await self.check_registration(ctx):
            return
        disc_level = await self.get_discord_level(ctx.author.id, ctx.guild.id)
        if level not in JOB_LEVELS:
            return await ctx.send("❌ Тухайн түвшний ажил байхгүй. `jobs` командыг ашиглан жагсаалтыг хараарай.")
        if disc_level < level:
            return await ctx.send(f"❌ Та энэ ажлыг авахын тулд Discord Lv.{level} байх шаардлагатай. Одоогоор Lv.{disc_level} байна.")
        job = JOB_LEVELS[level]
        embed = discord.Embed(title="✅ АЖИЛ СОНГОЛТ", description=f"{ctx.author.mention} та одоо {job['emoji']} {job['name']} (Lv.{level}) ажилтай боллоо!", color=SUCCESS_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='removejob')
    async def removejob(self, ctx):
        if not await self.check_registration(ctx):
            return
        embed = discord.Embed(title="✅ АЖИЛААСАА ГАРЛАА", description=f"{ctx.author.mention} та одоо ажилгүй боллоо!", color=SUCCESS_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='stats', aliases=['status', 'mystats'])
    async def stats(self, ctx, member: discord.Member = None):
        if not await self.check_registration(ctx):
            return
        target = member or ctx.author
        cash = await self.get_balance(target.id, ctx.guild.id)
        bank = await self.get_bank(target.id, ctx.guild.id)
        total = cash + bank
        hunger, mood = await self.get_hunger_mood(target.id, ctx.guild.id)
        disc_level = await self.get_discord_level(target.id, ctx.guild.id)
        job_level, job = self.get_job_for_level(disc_level)

        embed = discord.Embed(title=f"📊 {target.display_name} - ТӨЛӨВ", color=GOLD_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💰 Гар дээр", value=f"{cash:,} мөнгө")
        embed.add_field(name="🏦 Банк", value=f"{bank:,} мөнгө")
        embed.add_field(name="💎 Нийт", value=f"{total:,} мөнгө", inline=False)
        embed.add_field(name="💼 Ажил", value=f"{job['emoji']} {job['name']} (Lv.{job_level})", inline=False)
        embed.add_field(name="⭐ Discord Lv.", value=f"{disc_level}", inline=True)
        embed.add_field(name="🍔 Өлсгөлөн", value=f"{hunger}/100")
        embed.add_field(name="😡 Уур", value=f"{mood}/100")
        if hunger >= 80:
            embed.add_field(name="⚠️ Анхаар", value="Та өлссөн байна! `eat` хийгээрэй.")
        if mood >= 80:
            embed.add_field(name="⚠️ Анхаар", value="Та ууртай байна! `relax` хийгээрэй.")
        await ctx.send(embed=embed)

    @commands.command(name='eat')
    async def eat(self, ctx, number: int = None):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Эргэлтээр хоол ирээгүй байна.")
        if number is not None:
            cafe_cog = self.bot.get_cog("Cafe")
            if not cafe_cog:
                return await ctx.send("❌ Cafe систем ачаалагдаагүй.")
            return await cafe_cog.dine(ctx, number)
        bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        cost = 3000
        if bal < cost:
            return await ctx.send(f"❌ Хоолны үнэ {cost:,} мөнгө хүрэлцэхгүй.")
        hunger, _ = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if hunger == 0:
            return await ctx.send("🍔 Та цадсан байна!")
        await self.update_balance(ctx.author.id, ctx.guild.id, -cost)
        new_hunger = max(0, hunger - 50)
        await self.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=new_hunger)
        embed = discord.Embed(title="🍔 ХООЛ ИДЭВ",
                              description=f"{ctx.author.mention} {cost:,} хоол идэж, өлсгөлөн {hunger} → {new_hunger} болж буурдаа!",
                              color=SUCCESS_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='relax')
    async def relax(self, ctx):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Та шоронд амарч байна.")
        _, mood = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if mood == 0:
            return await ctx.send("🧘 Та маш тайван байна!")
        new_mood = max(0, mood - 40)
        await self.set_hunger_mood(ctx.author.id, ctx.guild.id, mood=new_mood)
        embed = discord.Embed(title="🧘 АМРАВ",
                              description=f"{ctx.author.mention} амарч, уур бухимдал тань {mood} → {new_mood} болж буурлаа!",
                              color=SUCCESS_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='work')
    async def work(self, ctx):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд ажил хийхгүй.")
        hunger, mood = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if hunger >= 80:
            return await ctx.send(f"❌ {ctx.author.mention}, та өлсөж байна! `eat` хийгээрэй.")
        if mood >= 80:
            return await ctx.send(f"❌ {ctx.author.mention}, та ууртай байна! `relax` хийгээрэй.")
        now = int(time.time())
        row = await self.bot.db.fetchone(
            "SELECT last_work FROM economy WHERE user_id = ? AND guild_id = ?",
            str(ctx.author.id), str(ctx.guild.id)
        )
        last = row[0] if row else 0
        if last and now - last < 1800:
            rem = 1800 - (now - last)
            m, s = divmod(rem, 60)
            return await ctx.send(embed=discord.Embed(title="⏳ АМРАЛТ", description=f"**{m}м {s}с** хүлээ.", color=0xfee75c))
        disc_level = await self.get_discord_level(ctx.author.id, ctx.guild.id)
        job_level, job = self.get_job_for_level(disc_level)
        pay = random.randint(job["min"], job["max"])
        bonus = min(50, disc_level * 2)
        if bonus:
            pay = int(pay * (1 + bonus/100))
        hunger_inc = random.randint(15,25)
        mood_inc = random.randint(10,20)
        new_hunger = min(100, hunger + hunger_inc)
        new_mood = min(100, mood + mood_inc)
        await self.update_balance(ctx.author.id, ctx.guild.id, pay)
        await self.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=new_hunger, mood=new_mood)
        await self.bot.db.execute(
            "UPDATE economy SET last_work = ? WHERE user_id = ? AND guild_id = ?",
            now, str(ctx.author.id), str(ctx.guild.id)
        )
        await self.bot.db.commit()
        xp = random.randint(10,20)
        await self.give_xp(ctx, xp)

        embed = discord.Embed(title="💼 АЖИЛ АМЖИЛТТАЙ!",
                              description=f"{ctx.author.mention} **{job['emoji']} {job['name']}** -р ажиллаж, **{pay:,}** мөнгө оллоо!\n⭐ Discord түвшингийн урамшуулал: +{bonus}%",
                              color=0x57f287)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="💰 ЦАЛИН", value=f"```diff\n+ {pay:,} мөнгө```", inline=True)
        embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=True)
        embed.add_field(name="🍔 Өлсгөлөн", value=f"+{hunger_inc}% (одоо {new_hunger}/100)", inline=True)
        embed.add_field(name="😡 Уур", value=f"+{mood_inc}% (одоо {new_mood}/100)", inline=True)
        embed.set_footer(text="Дараагийн ажил 30 минутын дараа")
        await ctx.send(embed=embed)

    @commands.command(name='transfer', aliases=['send', 'give'])
    async def transfer(self, ctx, member: discord.Member, amount_str: str):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд мөнгө шилжүүлэх боломжгүй.")
        if amount_str.lower() == 'all':
            amount = await self.get_balance(ctx.author.id, ctx.guild.id)
            if amount <= 0:
                return await ctx.send("❌ Танд мөнгө байхгүй.")
        else:
            try:
                amount = int(amount_str)
            except ValueError:
                return await ctx.send("❌ Дүн нь тоо эсвэл 'all' байх ёстой.")
        if amount <= 0:
            return await ctx.send("❌ Дүн эерэг байх ёстой!")
        if member.id == ctx.author.id:
            return await ctx.send("❌ Өөртөө мөнгө шилжүүлэх боломжгүй.")
        tax = int(amount * self.transfer_tax_percent / 100)
        final_amount = amount - tax
        if final_amount <= 0:
            return await ctx.send("❌ Татварын дараа шилжих мөнгө 0 боллоо.")
        sender_bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        if sender_bal < amount:
            return await ctx.send(f"❌ Танд **{amount:,}** мөнгө хүрэлцэхгүй.")
        receiver_bal = await self.get_balance(member.id, ctx.guild.id)
        if receiver_bal + final_amount > self.max_balance:
            return await ctx.send(f"❌ {member.mention} хязгаарт хүрч байна.")
        embed = discord.Embed(
            title="💰 МӨНГӨ ШИЛЖҮҮЛЭХ БАТАЛГАА",
            description=f"**{ctx.author.display_name}** → **{member.display_name}**\nДүн: **{amount:,}** мөнгө\nТатвар ({self.transfer_tax_percent}%): **{tax:,}** мөнгө\nХүлээн авах дүн: **{final_amount:,}** мөнгө\n\nШилжүүлэх үү?",
            color=0xfab387
        )
        view = ConfirmView(timeout=45)
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not True:
            return await ctx.send("❌ Шилжүүлэг цуцлагдлаа.", ephemeral=True)
        await self.update_balance(ctx.author.id, ctx.guild.id, -amount)
        await self.update_balance(member.id, ctx.guild.id, final_amount)
        success_embed = discord.Embed(title="✅ ГҮЙЛГЭЭ АМЖИЛТТАЙ!",
                                      description=f"{ctx.author.mention} → {member.mention}\n**{amount:,}** мөнгө шилжүүллээ (татвар {tax:,}).",
                                      color=0x57f287)
        success_embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=success_embed)
        await self.give_xp(ctx, 2)
        try:
            await member.send(f"📨 Та {ctx.author.display_name} -аас **{final_amount:,}** мөнгө хүлээн авлаа!")
        except:
            pass

    @commands.command(name='deposit', aliases=['dep'])
    async def deposit(self, ctx, amount_str: str):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд банкны үйлчилгээ ашиглахгүй.")
        cash = await self.get_balance(ctx.author.id, ctx.guild.id)
        if amount_str.lower() == 'all':
            amt = cash
        else:
            try:
                amt = int(amount_str)
            except ValueError:
                return await ctx.send("❌ Дүн нь тоо эсвэл 'all' байх ёстой!")
        if amt <= 0:
            return await ctx.send("❌ Хадгалах дүн 1-ээс их байх ёстой!")
        if cash < amt:
            return await ctx.send(f"❌ Танд **{amt:,}** мөнгө байхгүй!")
        bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        if bank + amt > self.max_balance:
            return await ctx.send("❌ Банкны хязгаарт хүрнэ.")
        await self.update_balance(ctx.author.id, ctx.guild.id, -amt)
        await self.update_bank(ctx.author.id, ctx.guild.id, amt)
        new_bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        embed = discord.Embed(title="🏦 БАНКАНД ХАДГАЛАВ", description=f"{ctx.author.mention} хадгаллаа!", color=0x57f287)
        embed.add_field(name="💰 ХАДГАЛСАН", value=f"```diff\n+ {amt:,} мөнгө```")
        embed.add_field(name="🏦 БАНК", value=f"```yaml\n{new_bank:,} мөнгө```")
        embed.add_field(name="💰 ҮЛДЭГДЭЛ", value=f"```fix\n{cash - amt:,} мөнгө```")
        await ctx.send(embed=embed)
        await self.give_xp(ctx, 2)

    @commands.command(name='withdraw', aliases=['with'])
    async def withdraw(self, ctx, amount_str: str):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Та шоронд байна.")
        bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        if amount_str.lower() == 'all':
            amt = bank
        else:
            try:
                amt = int(amount_str)
            except ValueError:
                return await ctx.send("❌ Дүн нь тоо эсвэл 'all' байх ёстой!")
        if bank < amt:
            return await ctx.send(f"❌ Банканд **{amt:,}** мөнгө байхгүй!")
        cash = await self.get_balance(ctx.author.id, ctx.guild.id)
        if cash + amt > self.max_balance:
            return await ctx.send("❌ Гар дээрх хязгаарт хүрнэ.")
        await self.update_bank(ctx.author.id, ctx.guild.id, -amt)
        await self.update_balance(ctx.author.id, ctx.guild.id, amt)
        new_cash = await self.get_balance(ctx.author.id, ctx.guild.id)
        new_bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        embed = discord.Embed(title="🏦 БАНКНААС АВЛАА", description=f"{ctx.author.mention} авлаа!", color=0x57f287)
        embed.add_field(name="💰 АВСАН", value=f"```diff\n+ {amt:,} мөнгө```")
        embed.add_field(name="🏦 БАНК", value=f"```yaml\n{new_bank:,} мөнгө```")
        embed.add_field(name="💰 ШИНЭ ҮЛДЭГДЭЛ", value=f"```fix\n{new_cash:,} мөнгө```")
        await ctx.send(embed=embed)
        await self.give_xp(ctx, 2)

    @commands.command(name='crime')
    async def crime(self, ctx):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд гэмт хэрэг үйлдэх боломжгүй.")
        if await self.is_bank_protected(ctx.author.id, ctx.guild.id):
            return await ctx.send("🛡️ Та банкны хамгаалалттай байна! Гэмт хэрэг үйлдэж чадахгүй.")
        crime = random.choice(CRIMES)
        if random.random() < crime["success_chance"]:
            reward = random.randint(crime["min_reward"], crime["max_reward"])
            await self.update_balance(ctx.author.id, ctx.guild.id, reward)
            xp = random.randint(10,20)
            await self.give_xp(ctx, xp)
            embed = discord.Embed(title="🎉 ГЭМТ ХЭРЭГ АМЖИЛТТАЙ!",
                                  description=f"{ctx.author.mention} **{crime['name']}** үйлдэж, **{reward:,}** мөнгө оллоо!",
                                  color=0x57f287)
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.add_field(name="💰 ШАГНАЛ", value=f"```diff\n+ {reward:,} мөнгө```", inline=True)
            embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=True)
            await ctx.send(embed=embed)
        else:
            jail_time = random.randint(1,3)
            await self.set_prison(ctx.author.id, ctx.guild.id, hours=jail_time)
            embed = discord.Embed(title="🚔 ТА ЦАГДААД БАРИГДЛАА!",
                                  description=f"{ctx.author.mention} **{crime['name']}** үйлдэх гэж оролдсон боловч баригдлаа! {jail_time} цаг шоронд суух болно.",
                                  color=0xff0000)
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    @commands.command(name='bankprotect', aliases=['bp', 'block'])
    async def bank_protect(self, ctx):
        if not await self.check_registration(ctx):
            return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд банк хамгаалах боломжгүй.")
        remaining = await self.get_bank_protection(ctx.author.id, ctx.guild.id)
        if remaining > 0:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            embed = discord.Embed(title="🛡️ БАНК ХАМГААЛАГДСАН", description=f"Үлдсэн: {hours}ц {minutes}м",
                                  color=0xfee75c)
            return await ctx.send(embed=embed)
        await self.set_bank_protection(ctx.author.id, ctx.guild.id, hours=2)
        embed = discord.Embed(title="🛡️ БАНК АМЖИЛТТАЙ ХАМГААЛАГДЛАА",
                              description="2 цагийн турш хулгай, татвараас хамгаалагдлаа!", color=0x57f287)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="⏱️ ХАМГААЛАЛТ", value="```yaml\n2 цаг```")
        await ctx.send(embed=embed)

    @commands.command(name='lb', aliases=['serverlb'])
    async def server_leaderboard(self, ctx):
        if not await self.check_registration(ctx):
            return
        await ctx.defer()
        rows = await self.bot.db.fetch(
            "SELECT user_id, balance + bank_balance as total FROM economy WHERE guild_id = ? ORDER BY total DESC",
            str(ctx.guild.id)
        )
        if not rows:
            return await ctx.send("Энэ server ийн хамгийн их мөнгөтэй хэрэглэгч байхгүй.")
        all_entries = []
        for uid, total in rows:
            member = ctx.guild.get_member(int(uid))
            if member:
                name = member.display_name[:20]
                avatar_url = str(member.display_avatar.replace(size=64, format="png").url) if member.avatar else None
            else:
                try:
                    user = await self.bot.fetch_user(int(uid))
                    name = user.display_name[:20] if user else f"ID: {uid}"
                    avatar_url = str(user.display_avatar.replace(size=64, format="png").url) if user and user.avatar else None
                except:
                    name = f"ID: {uid}"
                    avatar_url = None
            all_entries.append({"user_id": str(uid), "total": total, "name": name, "avatar_url": avatar_url})
        total_money = sum(e["total"] for e in all_entries)
        page = 0
        start = page * 10
        end = start + 10
        page_entries = all_entries[start:end]
        async with aiohttp.ClientSession() as sess:
            avatars = []
            for r in page_entries:
                url = r.get("avatar_url")
                if url:
                    ava = await _fetch_avatar_small(sess, url)
                else:
                    ava = Image.new("RGBA", (50, 50), (88,60,60,255))
                avatars.append(ava)
        buf = await asyncio.to_thread(_render_money_leaderboard, ctx.guild.name, page_entries, avatars, start, ctx.author.id)
        embed = discord.Embed(color=0x39FF14)
        embed.set_image(url="attachment://leaderboard.png")
        file = discord.File(buf, filename="leaderboard.png")
        view = MoneyLeaderboardView(self, ctx, all_entries, 0, total_money, ctx.author.id)
        msg = await ctx.send(embed=embed, file=file, view=view)
        view.message = msg

    @commands.command(name='globaltop', aliases=['worldlb'])
    async def global_leaderboard(self, ctx):
        if not await self.check_registration(ctx):
            return
        await ctx.defer()
        rows = await self.bot.db.fetch(
            "SELECT user_id, SUM(balance + bank_balance) as total FROM economy GROUP BY user_id ORDER BY total DESC LIMIT 100"
        )
        if not rows:
            return await ctx.send("Глобал мэдээлэл байхгүй.")
        all_entries = []
        for uid, total in rows:
            try:
                user = await self.bot.fetch_user(int(uid))
            except:
                user = None
            name = user.display_name if user else f"ID: {uid}"
            avatar_url = str(user.display_avatar.replace(size=64, format="png").url) if user and user.avatar else None
            all_entries.append({"user_id": str(uid), "total": total, "name": name[:20], "avatar_url": avatar_url})
        total_money = sum(e["total"] for e in all_entries)
        page = 0
        start = page * 10
        end = start + 10
        page_entries = all_entries[start:end]
        async with aiohttp.ClientSession() as sess:
            avatars = []
            for r in page_entries:
                url = r.get("avatar_url")
                if url:
                    ava = await _fetch_avatar_small(sess, url)
                else:
                    ava = Image.new("RGBA", (50, 50), (88,60,60,255))
                avatars.append(ava)
        buf = await asyncio.to_thread(_render_money_leaderboard, "Global Leaderboard", page_entries, avatars, start, ctx.author.id)
        embed = discord.Embed(color=0x39FF14)
        embed.set_image(url="attachment://leaderboard.png")
        file = discord.File(buf, filename="leaderboard.png")
        view = MoneyLeaderboardView(self, ctx, all_entries, 0, total_money, ctx.author.id)
        msg = await ctx.send(embed=embed, file=file, view=view)
        view.message = msg

    # ---------- Error handlers (class inside) ----------
    async def _handle_error(self, ctx, error, cmd_name):
        if isinstance(error, commands.CommandError):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Зөв хэлбэр: `{ctx.prefix}{cmd_name} ...`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Буруу аргумент.")
        else:
            raise error

    @transfer.error
    async def transfer_error(self, ctx, error):
        await self._handle_error(ctx, error, 'transfer')

    @deposit.error
    async def deposit_error(self, ctx, error):
        await self._handle_error(ctx, error, 'deposit')

    @withdraw.error
    async def withdraw_error(self, ctx, error):
        await self._handle_error(ctx, error, 'withdraw')

    @work.error
    async def work_error(self, ctx, error):
        await self._handle_error(ctx, error, 'work')

    @daily.error
    async def daily_error(self, ctx, error):
        await self._handle_error(ctx, error, 'daily')

async def setup(bot):
    await bot.add_cog(Economy(bot))
