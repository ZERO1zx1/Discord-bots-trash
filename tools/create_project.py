import os
import shutil

# Үндсэн хавтасны нэр
ROOT_DIR = "my-discord-bot-combined"

# Хавтасны бүтэц
folders = [
    "data",
    "python/cogs",
    "python/utils",
    "javascript/src/commands/economy",
    "javascript/src/commands/admin",
    "javascript/src/events",
    "javascript/src/handlers",
    "javascript/utils"
]

# Файлуудын агуулга
files = {
    # Root .env
    ".env": """# Хоёр ботын токеныг тус тусад нь хадгална
PYTHON_BOT_TOKEN=YOUR_PYTHON_BOT_TOKEN_HERE
JS_BOT_TOKEN=YOUR_JS_BOT_TOKEN_HERE

# Нийтлэг тохиргоо
BATTLE_ROLE_NAME=BattleFans
DAILY_BONUS=1000
""",

    # Python files
    "python/requirements.txt": """discord.py
python-dotenv
aiosqlite
""",

    "python/config.py": """import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("PYTHON_BOT_TOKEN")
BATTLE_ROLE_NAME = os.getenv("BATTLE_ROLE_NAME", "BattleFans")
DAILY_BONUS = int(os.getenv("DAILY_BONUS", 1000))
DB_PATH = "data/discord.db"

XP_MIN = 10
XP_MAX = 20
LEVEL_MULTIPLIER = 100
""",

    "python/database.py": """import aiosqlite
from config import DB_PATH, LEVEL_MULTIPLIER

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            daily_last TIMESTAMP DEFAULT '1970-01-01'
        )''')
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

async def set_daily(user_id, timestamp):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET daily_last = ? WHERE user_id = ?", (timestamp, str(user_id)))
        await db.commit()

async def get_daily_last(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT daily_last FROM users WHERE user_id = ?", (str(user_id),)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else '1970-01-01'

# ---------- XP / LEVEL ----------
async def add_xp(user_id, amount):
    row = await get_user(user_id)
    xp, level = row[2], row[3]
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
    return row[2], row[3]

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
""",

    "python/utils/helpers.py": """import random

def random_xp():
    from config import XP_MIN, XP_MAX
    return random.randint(XP_MIN, XP_MAX)

def format_currency(amount):
    return f"💰 {amount:,} монет"
""",

    "python/cogs/__init__.py": "",

    "python/cogs/economy.py": """import discord
from discord import app_commands
from discord.ext import commands
import datetime
import random
from config import DAILY_BONUS
from database import get_balance, add_balance, set_daily, get_daily_last
from utils.helpers import format_currency

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Үлдэгдлээ харах")
    async def balance(self, interaction: discord.Interaction):
        bal = await get_balance(interaction.user.id)
        await interaction.response.send_message(f"{interaction.user.mention} {format_currency(bal)}")

    @app_commands.command(name="daily", description="Өдөр тутмын урамшуулал")
    async def daily(self, interaction: discord.Interaction):
        last = await get_daily_last(interaction.user.id)
        last_dt = datetime.datetime.fromisoformat(last)
        now = datetime.datetime.now()
        if (now - last_dt).days >= 1:
            await add_balance(interaction.user.id, DAILY_BONUS)
            await set_daily(interaction.user.id, now.isoformat())
            await interaction.response.send_message(f"🎁 {format_currency(DAILY_BONUS)} хүлээн авлаа!")
        else:
            left = (last_dt + datetime.timedelta(days=1)) - now
            await interaction.response.send_message(f"⏳ {left.seconds//3600}ц { (left.seconds//60)%60 }м хүлээнэ үү.")

    @app_commands.command(name="coinflip", description="Зоос хаях")
    @app_commands.describe(amount="Мөнгө", choice="heads / tails")
    async def coinflip(self, interaction: discord.Interaction, amount: int, choice: str):
        bal = await get_balance(interaction.user.id)
        if bal < amount:
            return await interaction.response.send_message("❌ Хүрэлцэхгүй байна.", ephemeral=True)
        result = random.choice(["heads", "tails"])
        if choice.lower() == result:
            await add_balance(interaction.user.id, amount)
            await interaction.response.send_message(f"🎉 {result}! +{amount}")
        else:
            await add_balance(interaction.user.id, -amount)
            await interaction.response.send_message(f"😢 {result}! -{amount}")

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
""",

    "python/cogs/admin.py": """import discord
from discord.ext import commands
from discord import app_commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Slash командыг синхрончлох (Зөвхөн админ)")
    @app_commands.default_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        await self.bot.tree.sync()
        await interaction.response.send_message("✅ Синхрончлогдлоо!", ephemeral=True)

    @app_commands.command(name="clear", description="Мессеж цэвэрлэх")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(amount="Тоо")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            return await interaction.response.send_message("1-100 хооронд тоо оруулна уу.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 {len(deleted)} мессеж цэвэрлэгдлээ.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
""",

    "python/bot.py": """import discord
from discord.ext import commands
import asyncio
from config import TOKEN
from database import init_db

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        await init_db()
        await self.load_extension("cogs.economy")
        await self.load_extension("cogs.admin")
        await self.tree.sync()
        print("🐍 Python бот ачаалагдлаа!")

    async def on_ready(self):
        print(f"✅ Python бот {self.user} аслаа!")

if __name__ == "__main__":
    bot = MyBot()
    bot.run(TOKEN)
""",

    # JavaScript files
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

// Tables create (sync)
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    daily_last TIMESTAMP DEFAULT '1970-01-01'
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
`);

// ---------- USER ----------
function getBalance(userId) {
    const row = db.prepare('SELECT balance FROM users WHERE user_id = ?').get(String(userId));
    if (!row) {
        db.prepare('INSERT INTO users (user_id) VALUES (?)').run(String(userId));
        return 0;
    }
    return row.balance;
}

function addBalance(userId, amount) {
    db.prepare('UPDATE users SET balance = balance + ? WHERE user_id = ?').run(amount, String(userId));
}

function setDaily(userId, timestamp) {
    db.prepare('UPDATE users SET daily_last = ? WHERE user_id = ?').run(timestamp, String(userId));
}

function getDailyLast(userId) {
    const row = db.prepare('SELECT daily_last FROM users WHERE user_id = ?').get(String(userId));
    return row ? row.daily_last : '1970-01-01';
}

// ---------- BATTLE ----------
function createBattle(channelId, messageId, p1, p2) {
    const info = db.prepare('INSERT INTO battles (channel_id, message_id, player1_id, player2_id) VALUES (?, ?, ?, ?)')
        .run(String(channelId), String(messageId), String(p1), String(p2));
    return info.lastInsertRowid;
}

function getActiveBattle(messageId) {
    return db.prepare('SELECT id, player1_id, player2_id, status FROM battles WHERE message_id = ? AND status = "active"')
        .get(String(messageId));
}

function addVote(battleId, voterId, choice) {
    const existing = db.prepare('SELECT * FROM battle_votes WHERE battle_id = ? AND voter_id = ?')
        .get(battleId, String(voterId));
    if (existing) return false;

    if (choice === 1) {
        db.prepare('UPDATE battles SET vote1 = vote1 + 1 WHERE id = ?').run(battleId);
    } else {
        db.prepare('UPDATE battles SET vote2 = vote2 + 1 WHERE id = ?').run(battleId);
    }
    db.prepare('INSERT INTO battle_votes (battle_id, voter_id, choice) VALUES (?, ?, ?)')
        .run(battleId, String(voterId), choice);
    return true;
}

module.exports = {
    getBalance,
    addBalance,
    setDaily,
    getDailyLast,
    createBattle,
    getActiveBattle,
    addVote
};
""",

    "javascript/utils/formatter.js": """module.exports = {
    formatCurrency: (amount) => `💰 ${amount.toLocaleString()} монет`
};
""",

    "javascript/src/handlers/loader.js": """const fs = require('fs');
const path = require('path');

function loadCommands(client) {
    const folders = fs.readdirSync(path.join(__dirname, '../commands'));
    for (const folder of folders) {
        const files = fs.readdirSync(path.join(__dirname, `../commands/${folder}`)).filter(f => f.endsWith('.js'));
        for (const file of files) {
            const command = require(`../commands/${folder}/${file}`);
            if (command.data && command.execute) {
                client.commands.set(command.data.name, command);
                console.log(`✅ JS Command loaded: ${command.data.name}`);
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
        // Global commands register
        const commands = [];
        client.commands.forEach(cmd => commands.push(cmd.data.toJSON()));
        client.application.commands.set(commands);
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
            await interaction.reply({ content: '❌ Алдаа гарлаа.', ephemeral: true });
        }
    }
};
""",

    "javascript/src/commands/economy/balance.js": """const { SlashCommandBuilder } = require('discord.js');
const db = require('../../../database');
const { formatCurrency } = require('../../../utils/formatter');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('balance')
        .setDescription('Үлдэгдлээ харах'),
    async execute(interaction) {
        const bal = db.getBalance(interaction.user.id);
        await interaction.reply(`${interaction.user} ${formatCurrency(bal)}`);
    }
};
""",

    "javascript/src/commands/admin/clear.js": """const { SlashCommandBuilder, PermissionsBitField } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('clear')
        .setDescription('Мессеж цэвэрлэх')
        .addIntegerOption(opt => opt.setName('amount').setDescription('Тоо').setMinValue(1).setMaxValue(100).setRequired(true))
        .setDefaultMemberPermissions(PermissionsBitField.Flags.ManageMessages),
    async execute(interaction) {
        const amount = interaction.options.getInteger('amount');
        await interaction.reply({ content: 'Цэвэрлэж байна...', ephemeral: true });
        const deleted = await interaction.channel.bulkDelete(amount, true);
        await interaction.editReply(`🧹 ${deleted.size} мессеж цэвэрлэгдлээ.`);
    }
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

// Load Handlers
const { loadCommands } = require('./src/handlers/loader');
loadCommands(client);

// Load Events
const eventsPath = path.join(__dirname, 'src/events');
const eventFiles = fs.readdirSync(eventsPath).filter(f => f.endsWith('.js'));
for (const file of eventFiles) {
    const event = require(`./src/events/${file}`);
    if (event.once) {
        client.once(event.name, (...args) => event.execute(...args));
    } else {
        client.on(event.name, (...args) => event.execute(...args));
    }
}

client.login(process.env.JS_BOT_TOKEN);
""",
}


def create_project():
    # Хавтас үүсгэх
    for folder in folders:
        os.makedirs(os.path.join(ROOT_DIR, folder), exist_ok=True)

    # data/discord.db хоосон файл үүсгэх (SQLite автоматаар үүсгэнэ)
    db_path = os.path.join(ROOT_DIR, "data", "discord.db")
    if not os.path.exists(db_path):
        open(db_path, 'w').close()

    # Файлууд үүсгэх
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