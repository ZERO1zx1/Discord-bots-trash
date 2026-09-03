import aiosqlite
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
