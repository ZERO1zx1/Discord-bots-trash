import aiosqlite
from config import DB_PATH, LEVEL_MULTIPLIER

async def init_db(db):
    """Бүх хүснэгтийг үүсгэх"""
    async with db.acquire() as conn:
        # Economy + Leveling хосолсон хүснэгт
        await conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT,
            guild_id TEXT,
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
            reaction_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )''')

        # Battles
        await conn.execute('''CREATE TABLE IF NOT EXISTS battles (
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

        # Battle votes
        await conn.execute('''CREATE TABLE IF NOT EXISTS battle_votes (
            battle_id INTEGER,
            voter_id TEXT,
            choice INTEGER,
            PRIMARY KEY (battle_id, voter_id)
        )''')

        # Shop items (server-wide)
        await conn.execute('''CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            name TEXT,
            price INTEGER,
            description TEXT,
            role_id TEXT,
            UNIQUE(guild_id, name)
        )''')

        # User inventory (server-wide)
        await conn.execute('''CREATE TABLE IF NOT EXISTS user_inventory (
            user_id TEXT,
            guild_id TEXT,
            item_id INTEGER,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, guild_id, item_id)
        )''')

        # Cooldowns (server-wide)
        await conn.execute('''CREATE TABLE IF NOT EXISTS cooldowns (
            user_id TEXT,
            guild_id TEXT,
            command TEXT,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, guild_id, command)
        )''')

        await conn.commit()

# ========== USER ==========
async def get_user(user_id, guild_id):
    """Хэрэглэгчийн мэдээлэл авах (guild-specific)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            row = await cur.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO users (user_id, guild_id) VALUES (?, ?)",
                (str(user_id), str(guild_id))
            )
            await db.commit()
            return await get_user(user_id, guild_id)
        return row

# ========== BALANCE ==========
async def get_balance(user_id, guild_id):
    """Гар дээрх мөнгө авах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT balance FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            row = await cur.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO users (user_id, guild_id, balance) VALUES (?, ?, 0)",
                (str(user_id), str(guild_id))
            )
            await db.commit()
            return 0
        return row[0]

async def add_balance(user_id, guild_id, amount):
    """Мөнгө нэмэх/хасах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            exists = await cur.fetchone()
        if not exists:
            await db.execute(
                "INSERT INTO users (user_id, guild_id, balance) VALUES (?, ?, ?)",
                (str(user_id), str(guild_id), amount)
            )
        else:
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ? AND guild_id = ?",
                (amount, str(user_id), str(guild_id))
            )
        await db.commit()

# ========== BANK ==========
async def get_bank(user_id, guild_id):
    """Банкны мөнгө авах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT bank FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            row = await cur.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO users (user_id, guild_id, bank) VALUES (?, ?, 0)",
                (str(user_id), str(guild_id))
            )
            await db.commit()
            return 0
        return row[0]

async def add_bank(user_id, guild_id, amount):
    """Банканд мөнгө нэмэх/хасах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            exists = await cur.fetchone()
        if not exists:
            await db.execute(
                "INSERT INTO users (user_id, guild_id, bank) VALUES (?, ?, ?)",
                (str(user_id), str(guild_id), amount)
            )
        else:
            await db.execute(
                "UPDATE users SET bank = bank + ? WHERE user_id = ? AND guild_id = ?",
                (amount, str(user_id), str(guild_id))
            )
        await db.commit()

# ========== COOLDOWN ==========
async def set_cooldown(user_id, guild_id, command, timestamp):
    """Cooldown хадгалах"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO cooldowns (user_id, guild_id, command, last_used) VALUES (?, ?, ?, ?)",
            (str(user_id), str(guild_id), command, timestamp)
        )
        await db.commit()

async def get_cooldown(user_id, guild_id, command):
    """Cooldown авах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_used FROM cooldowns WHERE user_id = ? AND guild_id = ? AND command = ?",
            (str(user_id), str(guild_id), command)
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

# ========== XP / LEVEL ==========
async def add_xp(user_id, guild_id, amount):
    """XP нэмэх, level-up шалгах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            row = await cur.fetchone()

        if not row:
            await db.execute(
                "INSERT INTO users (user_id, guild_id, xp, level) VALUES (?, ?, ?, 1)",
                (str(user_id), str(guild_id), amount)
            )
            await db.commit()
            return 1, False

        xp, level = row
        xp += amount
        needed = level * LEVEL_MULTIPLIER
        leveled_up = False

        while xp >= needed:
            level += 1
            xp -= needed
            needed = level * LEVEL_MULTIPLIER
            leveled_up = True

        await db.execute(
            "UPDATE users SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
            (xp, level, str(user_id), str(guild_id))
        )
        await db.commit()
    return level, leveled_up

async def get_rank(user_id, guild_id):
    """XP болон Level авах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return 0, 1
        return row[0], row[1]

async def get_leaderboard(guild_id, limit=10):
    """Leaderboard авах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, level, xp, balance + bank as total FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?",
            (str(guild_id), limit)
        ) as cur:
            rows = await cur.fetchall()
    return rows

# ========== STATS ==========
async def get_stats(user_id, guild_id):
    """Бүх статистик авах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT balance, bank, xp, level, message_count, voice_seconds, reaction_count FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return {
                "balance": 0, "bank": 0, "xp": 0, "level": 1,
                "message_count": 0, "voice_seconds": 0, "reaction_count": 0
            }
        return {
            "balance": row[0], "bank": row[1], "xp": row[2], "level": row[3],
            "message_count": row[4], "voice_seconds": row[5], "reaction_count": row[6]
        }

async def update_stats(user_id, guild_id, **kwargs):
    """Статистик шинэчлэх"""
    if not kwargs:
        return

    columns = []
    values = []
    for key, value in kwargs.items():
        if key in ["balance", "bank", "xp", "level", "message_count", "voice_seconds", "reaction_count"]:
            columns.append(f"{key} = {key} + ?")
            values.append(value)

    if not columns:
        return

    values.extend([str(user_id), str(guild_id)])

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE user_id = ? AND guild_id = ?",
            (str(user_id), str(guild_id))
        ) as cur:
            exists = await cur.fetchone()

        if not exists:
            await db.execute(
                "INSERT INTO users (user_id, guild_id) VALUES (?, ?)",
                (str(user_id), str(guild_id))
            )

        await db.execute(
            f"UPDATE users SET {', '.join(columns)} WHERE user_id = ? AND guild_id = ?",
            values
        )
        await db.commit()