import os
import shutil

ROOT_DIR = "my-discord-bot-combined"

folders = [
    "data",
    "python/cogs",
    "python/utils",
    "javascript/src/commands/economy",
    "javascript/src/commands/admin",
    "javascript/src/commands/gambling",
    "javascript/src/commands/leveling",
    "javascript/src/commands/games",
    "javascript/src/events",
    "javascript/src/handlers",
    "javascript/utils"
]

files = {
    ".env": """# Хоёр ботын токен
PYTHON_BOT_TOKEN=YOUR_PYTHON_BOT_TOKEN_HERE
JS_BOT_TOKEN=YOUR_JS_BOT_TOKEN_HERE

# Нийтлэг тохиргоо
BATTLE_ROLE_NAME=BattleFans
DAILY_BONUS=1000
WEEKLY_BONUS=5000
HOURLY_BONUS=100
WORK_MIN=50
WORK_MAX=200
ROB_SUCCESS_RATE=0.4
BANK_SAFE=True

# Локализацийн тохиргоо
DEFAULT_LANGUAGE=mn
FALLBACK_LANGUAGE=en
# Хэрэв та ботыг англиар ажиллуулахыг хүсвэл DEFAULT_LANGUAGE=en болгоно уу
""",

    "python/requirements.txt": """discord.py
python-dotenv
aiosqlite
Pillow
aiohttp
""",

    "python/config.py": """import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("PYTHON_BOT_TOKEN")
BATTLE_ROLE_NAME = os.getenv("BATTLE_ROLE_NAME", "BattleFans")
DAILY_BONUS = int(os.getenv("DAILY_BONUS", 1000))
WEEKLY_BONUS = int(os.getenv("WEEKLY_BONUS", 5000))
HOURLY_BONUS = int(os.getenv("HOURLY_BONUS", 100))
WORK_MIN = int(os.getenv("WORK_MIN", 50))
WORK_MAX = int(os.getenv("WORK_MAX", 200))
ROB_SUCCESS_RATE = float(os.getenv("ROB_SUCCESS_RATE", 0.4))
BANK_SAFE = os.getenv("BANK_SAFE", "True").lower() == "true"
DB_PATH = "data/discord.db"

XP_MIN = 10
XP_MAX = 20
LEVEL_MULTIPLIER = 100

# Локализаци
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "mn")
FALLBACK_LANGUAGE = os.getenv("FALLBACK_LANGUAGE", "en")

# Орчуулгын толь (энгийн жишээ)
TRANSLATIONS = {
    "mn": {
        "balance": "Үлдэгдэл",
        "daily": "Өдөр тутмын бонус",
        "weekly": "Долоо хоногийн бонус",
        "hourly": "Цагийн бонус",
        "pay": "Мөнгө шилжүүлэх",
        "work": "Ажил",
        "rob": "Дээрэм",
        "deposit": "Хадгалуулах",
        "withdraw": "Авах",
        "bank": "Банк",
        "leaderboard": "Лидерборд",
        "rank": "Түвшин",
        "xp": "XP оноо",
        "xpleaderboard": "XP лидерборд",
        "coins": "монет",
    },
    "en": {
        "balance": "Balance",
        "daily": "Daily Bonus",
        "weekly": "Weekly Bonus",
        "hourly": "Hourly Bonus",
        "pay": "Pay",
        "work": "Work",
        "rob": "Rob",
        "deposit": "Deposit",
        "withdraw": "Withdraw",
        "bank": "Bank",
        "leaderboard": "Leaderboard",
        "rank": "Rank",
        "xp": "XP",
        "xpleaderboard": "XP Leaderboard",
        "coins": "coins",
    }
}

def get_text(key, lang=None):
    if lang is None:
        lang = DEFAULT_LANGUAGE
    if lang not in TRANSLATIONS:
        lang = FALLBACK_LANGUAGE
    return TRANSLATIONS.get(lang, {}).get(key, key)
""",

    "python/database.py": """import aiosqlite
from config import DB_PATH, LEVEL_MULTIPLIER

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Users
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            daily_last TIMESTAMP DEFAULT '1970-01-01',
            weekly_last TIMESTAMP DEFAULT '1970-01-01',
            hourly_last TIMESTAMP DEFAULT '1970-01-01',
            work_last TIMESTAMP DEFAULT '1970-01-01',
            message_count INTEGER DEFAULT 0,
            voice_seconds INTEGER DEFAULT 0,
            reaction_count INTEGER DEFAULT 0
        )''')
        # Battles
        await db.execute('''CREATE TABLE IF NOT EXISTS battles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            message_id TEXT UNIQUE,
            player1_id TEXT,
            player2_id TEXT,
            vote1 INTEGER DEFAULT 0,
            vote2 INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS battle_votes (
            battle_id INTEGER,
            voter_id TEXT,
            choice INTEGER,
            PRIMARY KEY (battle_id, voter_id)
        )''')
        # Shop
        await db.execute('''CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            price INTEGER,
            description TEXT,
            role_id TEXT
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS user_inventory (
            user_id TEXT,
            item_id INTEGER,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, item_id)
        )''')
        # Cooldowns
        await db.execute('''CREATE TABLE IF NOT EXISTS cooldowns (
            user_id TEXT,
            command TEXT,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, command)
        )''')
        await db.commit()

# ---------- USER ----------
async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO users (user_id) VALUES (?)", (str(user_id),))
                await db.commit()
                return await get_user(user_id)
            return row

async def get_balance(user_id):
    row = await get_user(user_id)
    return row[1]

async def add_balance(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, str(user_id)))
        await db.commit()

async def get_bank(user_id):
    row = await get_user(user_id)
    return row[2]

async def add_bank(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET bank = bank + ? WHERE user_id = ?", (amount, str(user_id)))
        await db.commit()

async def set_cooldown(user_id, command, timestamp):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO cooldowns (user_id, command, last_used) VALUES (?, ?, ?)",
            (str(user_id), command, timestamp)
        )
        await db.commit()

async def get_cooldown(user_id, command):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_used FROM cooldowns WHERE user_id = ? AND command = ?",
            (str(user_id), command)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

# ---------- XP / LEVEL ----------
async def add_xp(user_id, amount):
    row = await get_user(user_id)
    xp, level = row[3], row[4]
    xp += amount
    needed = level * LEVEL_MULTIPLIER
    leveled_up = False
    while xp >= needed:
        level += 1
        xp -= needed
        needed = level * LEVEL_MULTIPLIER
        leveled_up = True
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (xp, level, str(user_id)))
        await db.commit()
    return level, leveled_up

async def get_rank(user_id):
    row = await get_user(user_id)
    return row[3], row[4]

# ---------- BATTLE ----------
async def create_battle(channel_id, message_id, p1_id, p2_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO battles (channel_id, message_id, player1_id, player2_id) VALUES (?, ?, ?, ?)",
            (str(channel_id), str(message_id), str(p1_id), str(p2_id))
        )
        await db.commit()
        return cursor.lastrowid

async def get_active_battle(message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, player1_id, player2_id, status FROM battles WHERE message_id = ? AND status = 'active'",
            (str(message_id),)
        ) as cursor:
            return await cursor.fetchone()

async def add_vote(battle_id, voter_id, choice):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM battle_votes WHERE battle_id = ? AND voter_id = ?", (battle_id, str(voter_id))
        ) as cursor:
            if await cursor.fetchone():
                return False
        if choice == 1:
            await db.execute("UPDATE battles SET vote1 = vote1 + 1 WHERE id = ?", (battle_id,))
        else:
            await db.execute("UPDATE battles SET vote2 = vote2 + 1 WHERE id = ?", (battle_id,))
        await db.execute("INSERT INTO battle_votes (battle_id, voter_id, choice) VALUES (?, ?, ?)",
                         (battle_id, str(voter_id), choice))
        await db.commit()
        return True

async def finish_battle(battle_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE battles SET status = 'finished' WHERE id = ?", (battle_id,))
        await db.commit()

# ---------- SHOP ----------
async def get_shop_items():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name, price, description, role_id FROM shop_items") as cursor:
            return await cursor.fetchall()

async def add_shop_item(name, price, description, role_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shop_items (name, price, description, role_id) VALUES (?, ?, ?, ?)",
            (name, price, description, role_id)
        )
        await db.commit()

async def get_inventory(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT item_id, quantity FROM user_inventory WHERE user_id = ?",
            (str(user_id),)
        ) as cursor:
            return await cursor.fetchall()

async def add_inventory(user_id, item_id, quantity=1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_inventory (user_id, item_id, quantity) VALUES (?, ?, COALESCE((SELECT quantity FROM user_inventory WHERE user_id = ? AND item_id = ?), 0) + ?)",
            (str(user_id), item_id, str(user_id), item_id, quantity)
        )
        await db.commit()
""",

    "python/utils/cooldown.py": """import datetime

def check_cooldown(last_used, cooldown_seconds):
    if last_used is None:
        return True, None
    last_dt = datetime.datetime.fromisoformat(last_used)
    now = datetime.datetime.now()
    diff = (now - last_dt).total_seconds()
    if diff >= cooldown_seconds:
        return True, None
    return False, cooldown_seconds - diff
""",

    "python/utils/helpers.py": """import random
from config import XP_MIN, XP_MAX, get_text

def random_xp():
    return random.randint(XP_MIN, XP_MAX)

def format_currency(amount, lang=None):
    coin_text = get_text("coins", lang)
    return f"💰 {amount:,} {coin_text}"
""",

    "python/cogs/__init__.py": "",

    "python/cogs/economy.py": """import discord
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
""",

    "python/cogs/gambling.py": """import discord
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
""",

    "python/cogs/leveling.py": """import discord
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
""",

    "python/cogs/games.py": """import discord
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
""",

    "python/cogs/admin.py": """import discord
from discord import app_commands
from discord.ext import commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Ботны хариу хурд")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! `{round(self.bot.latency * 1000)}ms`")

    @app_commands.command(name="reload", description="Ког дахин ачаалах (зөвхөн админ)")
    @app_commands.default_permissions(administrator=True)
    async def reload(self, interaction: discord.Interaction, extension: str):
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            await interaction.response.send_message(f"✅ `{extension}` амжилттай дахин ачаалагдлаа.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Алдаа: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
""",

    "python/cogs/leaderboard.py": """import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
import aiosqlite
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import os
from config import DB_PATH
from utils.helpers import format_currency

# ---------- Фонт туслах ----------
def get_font(size: int, bold: bool = False):
    try:
        font_paths = []
        if bold:
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ]
        else:
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ]
        for path in font_paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    except:
        pass
    return ImageFont.load_default()

def format_number(num: int) -> str:
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

# ---------- Аватар татах ----------
async def fetch_avatar(session, url: str, size: int = 64):
    try:
        async with session.get(url) as resp:
            data = await resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
    except:
        img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img

# ==================== VIEW ====================
class LeaderboardView(View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.guild_id = ctx.guild.id
        self.current_category = "level"
        self.page = 0
        self.per_page = 10

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Энэ лидерборд таны биш.", ephemeral=True)
            return False
        return True

    @Select(
        placeholder="🏆 Лидербордын төрөл сонгох",
        options=[
            discord.SelectOption(label="🏆 Түвшин", value="level", description="Түвшнээр эрэмбэлэх"),
            discord.SelectOption(label="💬 Мессеж", value="messages", description="Илгээсэн мессежийн тоогоор"),
            discord.SelectOption(label="🎤 Дуут цаг", value="voice_time", description="Дуут сувагт зарцуулсан хугацаа"),
            discord.SelectOption(label="❤️ Реакц", value="reactions", description="Реакц дарах тоогоор"),
            discord.SelectOption(label="💰 Мөнгө", value="money", description="Валютын хэмжээгээр"),
            discord.SelectOption(label="📨 Урилга", value="invites", description="Урилгын тоогоор (хэрэв байгаа бол)"),
            discord.SelectOption(label="🔢 Тоололт", value="counting", description="Counting тоглоомын зөв тоололт"),
            discord.SelectOption(label="🎮 Тоглоом", value="games", description="Тоглоомын ялалт/хожил"),
        ]
    )
    async def category_select(self, interaction, select):
        self.current_category = select.values[0]
        self.page = 0
        embed, file = await self.build_embed()
        await interaction.response.edit_message(embed=embed, attachments=[file] if file else [], view=self)

    @Button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction, button):
        self.page = max(0, self.page - 1)
        embed, file = await self.build_embed()
        await interaction.response.edit_message(embed=embed, attachments=[file] if file else [], view=self)

    @Button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction, button):
        self.page += 1
        embed, file = await self.build_embed()
        await interaction.response.edit_message(embed=embed, attachments=[file] if file else [], view=self)

    @Button(label="📸 Карт", style=discord.ButtonStyle.success)
    async def show_card(self, interaction, button):
        await interaction.response.defer()
        rows, title, label_func = await self.fetch_data(self.page * self.per_page, self.per_page)
        if not rows:
            return await interaction.edit_original_response(
                embed=discord.Embed(description="Энэ төрөлд өгөгдөл байхгүй.", color=0xff0000),
                view=self
            )
        file = await self.generate_card(rows, title, label_func)
        embed = discord.Embed(color=0x2f3136)
        embed.set_image(url="attachment://leaderboard_card.png")
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

    # ---------- Өгөгдөл татах ----------
    async def fetch_data(self, offset, limit):
        cat = self.current_category
        if cat == "level":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            return rows, "🏆 ТҮВШНИЙ ЛИДЕРБОРД", lambda lvl, xp: f"Түв.{lvl} • {format_number(xp)} XP"

        elif cat == "messages":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, message_count FROM users ORDER BY message_count DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            return rows, "💬 МЕССЕЖИЙН ЛИДЕРБОРД", lambda cnt: f"{format_number(cnt)} мессеж"

        elif cat == "voice_time":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, voice_seconds FROM users ORDER BY voice_seconds DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            def voice_label(sec):
                h, m = divmod(sec, 3600)
                return f"{h} цаг {m//60} мин"
            return rows, "🎤 ДУУТ ЦАГИЙН ЛИДЕРБОРД", voice_label

        elif cat == "reactions":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, reaction_count FROM users ORDER BY reaction_count DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            return rows, "❤️ РЕАКЦЫН ЛИДЕРБОРД", lambda cnt: f"{format_number(cnt)} реакц"

        elif cat == "money":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, balance + bank AS total FROM users ORDER BY total DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            return rows, "💰 ВАЛЮТЫН ЛИДЕРБОРД", lambda bal: f"{format_number(bal)} ₮"

        elif cat == "invites":
            inv = self.cog.bot.get_cog("InviteTracker")
            if inv and hasattr(inv, "get_top_inviters"):
                rows = await inv.get_top_inviters(self.guild_id, limit, offset)
                return rows, "📨 УРИЛГЫН ЛИДЕРБОРД", lambda cnt: f"{format_number(cnt)} урилга"
            return None, None, None

        elif cat == "counting":
            cnt = self.cog.bot.get_cog("Counting")
            if cnt and hasattr(cnt, "get_top_counters"):
                rows = await cnt.get_top_counters(self.guild_id, limit, offset)
                return rows, "🔢 ТООЛОЛТЫН ЛИДЕРБОРД", lambda c: f"{format_number(c)} зөв тоололт"
            return None, None, None

        elif cat == "games":
            g = self.cog.bot.get_cog("Games")
            if g and hasattr(g, "get_top_games"):
                rows = await g.get_top_games(self.guild_id, limit, offset)
                return rows, "🎮 ТОГЛООМЫН ЛИДЕРБОРД", lambda sc: f"{format_number(sc)} ₮ хожил"
            return None, None, None

        return None, None, None

    # ---------- Карт зурах ----------
    async def generate_card(self, rows, title, label_func):
        W, H = 900, 560
        img = Image.new("RGBA", (W, H), "#2f3136")
        draw = ImageDraw.Draw(img)

        font_title = get_font(34, bold=True)
        font_name = get_font(22, bold=True)
        font_small = get_font(18, bold=False)

        draw.text(((W - draw.textlength(title, font=font_title)) // 2, 25), title, fill="#fab387", font=font_title)
        draw.line((40, 75, W - 40, 75), fill="#484b51", width=2)

        row_height = 45
        start_y = 90
        avatar_size = 38

        async with aiohttp.ClientSession() as session:
            for i, row in enumerate(rows):
                y = start_y + i * row_height
                uid = str(row[0])
                value = row[1]
                member = self.ctx.guild.get_member(int(uid))
                if not member:
                    try:
                        member = await self.cog.bot.fetch_user(int(uid))
                    except:
                        continue
                name = member.display_name if member else "Тодорхойгүй"

                avatar_url = member.display_avatar.replace(size=128, format="png").url
                avatar_img = await fetch_avatar(session, avatar_url, avatar_size)
                img.paste(avatar_img, (35, y + 3), avatar_img)

                rank_text = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"#{i+1}")
                draw.text((85, y + 6), rank_text, fill="#ffffff", font=font_name)
                draw.text((120, y + 6), name[:20], fill="#ffffff", font=font_name)

                if isinstance(value, tuple):
                    label = label_func(*value)
                else:
                    label = label_func(value)
                draw.text((450, y + 6), label, fill="#a6a6a6", font=font_small)

        draw.text((W // 2 - 100, H - 30), "Powered by Discord Leveling", fill="#666666", font=get_font(14))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="leaderboard_card.png")

    # ---------- Embed үүсгэх ----------
    async def build_embed(self):
        offset = self.page * self.per_page
        rows, title, label_func = await self.fetch_data(offset, self.per_page)
        embed = discord.Embed(title=title, color=0x7289da)
        if not rows:
            embed.description = "Одоогоор өгөгдөл байхгүй."
            return embed, None

        desc = []
        for i, row in enumerate(rows, start=offset + 1):
            uid = str(row[0])
            value = row[1]
            member = self.ctx.guild.get_member(int(uid))
            if not member:
                try:
                    member = await self.cog.bot.fetch_user(int(uid))
                except:
                    continue
            name = member.display_name if member else "Тодорхойгүй"
            if isinstance(value, tuple):
                label = label_func(*value)
            else:
                label = label_func(value)
            desc.append(f"`#{i}` **{name}** – {label}")

        embed.description = "\\n".join(desc[:self.per_page])
        embed.set_footer(text=f"Хуудас {self.page + 1}  •  Нийт {len(rows)} харуулж байна")
        return embed, None


# ==================== COG ====================
class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Олон төрлийн лидерборд харах")
    async def slash_leaderboard(self, interaction: discord.Interaction):
        view = LeaderboardView(self, interaction)
        embed, file = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @commands.hybrid_command(name="lb", aliases=["leaderboard"], description="Лидерборд харах")
    async def prefix_leaderboard(self, ctx):
        view = LeaderboardView(self, ctx)
        embed, file = await view.build_embed()
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
""",

    "python/bot.py": """import discord
from discord.ext import commands
from config import TOKEN, DEFAULT_LANGUAGE
from database import init_db

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.default_lang = DEFAULT_LANGUAGE

    async def setup_hook(self):
        await init_db()
        await self.load_extension("cogs.economy")
        await self.load_extension("cogs.gambling")
        await self.load_extension("cogs.leveling")
        await self.load_extension("cogs.games")
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.leaderboard")
        await self.tree.sync()
        print(f"🐍 Python бот ачаалагдлаа! Хэл: {self.default_lang}")

    async def on_ready(self):
        print(f"✅ Python бот {self.user} аслаа!")

if __name__ == "__main__":
    bot = MyBot()
    bot.run(TOKEN)
""",

    "javascript/package.json": """{
  "name": "my-discord-bot-js",
  "version": "1.0.0",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "discord.js": "^14.15.3",
    "better-sqlite3": "^9.6.0",
    "dotenv": "^16.4.5"
  }
}
""",

    "javascript/database.js": """const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, '..', 'data', 'discord.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    daily_last TIMESTAMP DEFAULT '1970-01-01',
    weekly_last TIMESTAMP DEFAULT '1970-01-01',
    hourly_last TIMESTAMP DEFAULT '1970-01-01',
    work_last TIMESTAMP DEFAULT '1970-01-01',
    message_count INTEGER DEFAULT 0,
    voice_seconds INTEGER DEFAULT 0,
    reaction_count INTEGER DEFAULT 0
  );
  CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    message_id TEXT UNIQUE,
    player1_id TEXT,
    player2_id TEXT,
    vote1 INTEGER DEFAULT 0,
    vote2 INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS battle_votes (
    battle_id INTEGER,
    voter_id TEXT,
    choice INTEGER,
    PRIMARY KEY (battle_id, voter_id)
  );
  CREATE TABLE IF NOT EXISTS shop_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    price INTEGER,
    description TEXT,
    role_id TEXT
  );
  CREATE TABLE IF NOT EXISTS user_inventory (
    user_id TEXT,
    item_id INTEGER,
    quantity INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, item_id)
  );
  CREATE TABLE IF NOT EXISTS cooldowns (
    user_id TEXT,
    command TEXT,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, command)
  );
`);

function getUser(userId) {
    const row = db.prepare('SELECT * FROM users WHERE user_id = ?').get(String(userId));
    if (!row) {
        db.prepare('INSERT INTO users (user_id) VALUES (?)').run(String(userId));
        return getUser(userId);
    }
    return row;
}

function getBalance(userId) {
    return getUser(userId).balance;
}
function addBalance(userId, amount) {
    db.prepare('UPDATE users SET balance = balance + ? WHERE user_id = ?').run(amount, String(userId));
}

function getBank(userId) {
    return getUser(userId).bank;
}
function addBank(userId, amount) {
    db.prepare('UPDATE users SET bank = bank + ? WHERE user_id = ?').run(amount, String(userId));
}

function setCooldown(userId, command, timestamp) {
    db.prepare('INSERT OR REPLACE INTO cooldowns (user_id, command, last_used) VALUES (?, ?, ?)')
        .run(String(userId), command, timestamp);
}
function getCooldown(userId, command) {
    const row = db.prepare('SELECT last_used FROM cooldowns WHERE user_id = ? AND command = ?')
        .get(String(userId), command);
    return row ? row.last_used : null;
}

function addXp(userId, amount) {
    const user = getUser(userId);
    let xp = user.xp + amount;
    let level = user.level;
    const LEVEL_MULTIPLIER = 100;
    let needed = level * LEVEL_MULTIPLIER;
    let leveledUp = false;
    while (xp >= needed) {
        level++;
        xp -= needed;
        needed = level * LEVEL_MULTIPLIER;
        leveledUp = true;
    }
    db.prepare('UPDATE users SET xp = ?, level = ? WHERE user_id = ?').run(xp, level, String(userId));
    return { level, leveledUp };
}

function getRank(userId) {
    const user = getUser(userId);
    return { xp: user.xp, level: user.level };
}

// Battle functions
function createBattle(channelId, messageId, p1Id, p2Id) {
    const stmt = db.prepare('INSERT INTO battles (channel_id, message_id, player1_id, player2_id) VALUES (?, ?, ?, ?)');
    const info = stmt.run(String(channelId), String(messageId), String(p1Id), String(p2Id));
    return info.lastInsertRowid;
}
function getActiveBattle(messageId) {
    return db.prepare('SELECT id, player1_id, player2_id, status FROM battles WHERE message_id = ? AND status = ?').get(String(messageId), 'active');
}
function addVote(battleId, voterId, choice) {
    const existing = db.prepare('SELECT * FROM battle_votes WHERE battle_id = ? AND voter_id = ?').get(battleId, String(voterId));
    if (existing) return false;
    if (choice === 1) {
        db.prepare('UPDATE battles SET vote1 = vote1 + 1 WHERE id = ?').run(battleId);
    } else {
        db.prepare('UPDATE battles SET vote2 = vote2 + 1 WHERE id = ?').run(battleId);
    }
    db.prepare('INSERT INTO battle_votes (battle_id, voter_id, choice) VALUES (?, ?, ?)').run(battleId, String(voterId), choice);
    return true;
}
function finishBattle(battleId) {
    db.prepare('UPDATE battles SET status = ? WHERE id = ?').run('finished', battleId);
}

module.exports = {
    getBalance, addBalance, getBank, addBank, setCooldown, getCooldown,
    addXp, getRank, createBattle, getActiveBattle, addVote, finishBattle
};
""",

    "javascript/index.js": """const { Client, Collection, GatewayIntentBits } = require('discord.js');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');

dotenv.config({ path: path.join(__dirname, '..', '.env') });

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers
    ]
});

client.commands = new Collection();
const { loadCommands } = require('./src/handlers/loader');
loadCommands(client);

const eventsPath = path.join(__dirname, 'src/events');
const eventFiles = fs.readdirSync(eventsPath).filter(f => f.endsWith('.js'));
for (const file of eventFiles) {
    const event = require(`./src/events/${file}`);
    if (event.once) client.once(event.name, (...args) => event.execute(...args));
    else client.on(event.name, (...args) => event.execute(...args));
}

client.login(process.env.JS_BOT_TOKEN);
""",

    "javascript/src/handlers/loader.js": """const fs = require('fs');
const path = require('path');

function loadCommands(client) {
    const commandsPath = path.join(__dirname, '..', 'commands');
    const commandFolders = fs.readdirSync(commandsPath);
    for (const folder of commandFolders) {
        const commandFiles = fs.readdirSync(path.join(commandsPath, folder)).filter(file => file.endsWith('.js'));
        for (const file of commandFiles) {
            const command = require(path.join(commandsPath, folder, file));
            if ('data' in command && 'execute' in command) {
                client.commands.set(command.data.name, command);
            }
        }
    }
}

module.exports = { loadCommands };
""",

    "javascript/src/events/ready.js": """module.exports = {
    name: 'ready',
    once: true,
    execute(client) {
        console.log(`✅ JS бот ${client.user.tag} аслаа!`);
    }
};
""",

    "javascript/src/events/interactionCreate.js": """module.exports = {
    name: 'interactionCreate',
    async execute(interaction) {
        if (!interaction.isChatInputCommand()) return;
        const command = interaction.client.commands.get(interaction.commandName);
        if (!command) return;
        try {
            await command.execute(interaction);
        } catch (error) {
            console.error(error);
            await interaction.reply({ content: 'Алдаа гарлаа!', ephemeral: true });
        }
    }
};
""",

    "javascript/utils/formatter.js": """function formatCurrency(amount) {
    return `💰 ${amount.toLocaleString()} монет`;
}

module.exports = { formatCurrency };
""",

    "javascript/src/commands/economy/balance.js": """const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const db = require('../../../database');
const { formatCurrency } = require('../../../utils/formatter');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('balance')
        .setDescription('Үлдэгдлээ харах')
        .addUserOption(option => option.setName('user').setDescription('Хэрэглэгч')),
    async execute(interaction) {
        const target = interaction.options.getUser('user') || interaction.user;
        const bal = db.getBalance(target.id);
        const embed = new EmbedBuilder()
            .setTitle('💰 Үлдэгдэл')
            .setColor('Green')
            .addFields({ name: target.username, value: formatCurrency(bal) });
        await interaction.reply({ embeds: [embed] });
    }
};
""",

    "javascript/src/commands/economy/daily.js": """const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const db = require('../../../database');
const { formatCurrency } = require('../../../utils/formatter');

const DAILY_BONUS = 1000;
const COOLDOWN_MS = 86400000; // 24h

function checkCooldown(last, cd) {
    if (!last) return true;
    const diff = Date.now() - new Date(last).getTime();
    return diff >= cd ? true : cd - diff;
}

module.exports = {
    data: new SlashCommandBuilder()
        .setName('daily')
        .setDescription('Өдөр тутмын урамшуулал'),
    async execute(interaction) {
        const last = db.getCooldown(interaction.user.id, 'daily');
        const ok = checkCooldown(last, COOLDOWN_MS);
        if (ok === true) {
            db.addBalance(interaction.user.id, DAILY_BONUS);
            db.setCooldown(interaction.user.id, 'daily', new Date().toISOString());
            const embed = new EmbedBuilder()
                .setTitle('🎁 Өдөр тутмын бонус')
                .setColor('Gold')
                .addFields({ name: 'Хүлээн авлаа', value: formatCurrency(DAILY_BONUS) });
            await interaction.reply({ embeds: [embed] });
        } else {
            const hours = Math.floor(ok / 3600000);
            const minutes = Math.floor((ok % 3600000) / 60000);
            await interaction.reply(`⏳ ${hours}ц ${minutes}м хүлээнэ үү.`);
        }
    }
};
""",

    "javascript/src/commands/gambling/coinflip.js": """const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const db = require('../../../database');
const { formatCurrency } = require('../../../utils/formatter');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('coinflip')
        .setDescription('Зоос шидэх')
        .addIntegerOption(option => option.setName('amount').setDescription('Бооцоо').setRequired(true))
        .addStringOption(option => option.setName('choice').setDescription('heads эсвэл tails').setRequired(true).addChoices(
            { name: 'heads', value: 'heads' },
            { name: 'tails', value: 'tails' }
        )),
    async execute(interaction) {
        const amount = interaction.options.getInteger('amount');
        const choice = interaction.options.getString('choice');
        if (amount <= 0) return interaction.reply({ content: '❌ Бооцоо эерэг байх ёстой.', ephemeral: true });
        const bal = db.getBalance(interaction.user.id);
        if (bal < amount) return interaction.reply({ content: '❌ Хүрэлцэхгүй байна.', ephemeral: true });
        const result = Math.random() < 0.5 ? 'heads' : 'tails';
        const win = choice === result;
        if (win) {
            db.addBalance(interaction.user.id, amount);
            const embed = new EmbedBuilder()
                .setTitle('🎉 Зоос шидэлт')
                .setDescription(`Тааж: ${choice} | Результат: ${result}`)
                .setColor('Green')
                .addFields({ name: 'Хожлоо!', value: formatCurrency(amount) });
            await interaction.reply({ embeds: [embed] });
        } else {
            db.addBalance(interaction.user.id, -amount);
            const embed = new EmbedBuilder()
                .setTitle('😢 Зоос шидэлт')
                .setDescription(`Тааж: ${choice} | Результат: ${result}`)
                .setColor('Red')
                .addFields({ name: 'Алдлаа', value: formatCurrency(-amount) });
            await interaction.reply({ embeds: [embed] });
        }
    }
};
""",
}

def create_project():
    for folder in folders:
        os.makedirs(os.path.join(ROOT_DIR, folder), exist_ok=True)

    db_path = os.path.join(ROOT_DIR, "data", "discord.db")
    if not os.path.exists(db_path):
        open(db_path, 'w').close()

    for filepath, content in files.items():
        full_path = os.path.join(ROOT_DIR, filepath)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Үүсгэгдлээ: {filepath}")

    print(f"\n🎉 Бүх файл амжилттай үүслээ! '{ROOT_DIR}' хавтас руу орж ажиллуулна уу.")
    print("🐍 Python бот: cd python && pip install -r requirements.txt && python bot.py")
    print("🟨 JS бот: cd javascript && npm install && npm start")

if __name__ == "__main__":
    create_project()