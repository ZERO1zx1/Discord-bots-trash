# database.py
import aiosqlite
import os
import asyncio

class Database:
    def __init__(self, db_path: str = "database/data.db"):
        self.db_path = db_path
        self._conn = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Create folder, connect, enable WAL and foreign keys."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
        print("✅ SQLite database ready")

    async def _create_tables(self):
        """Create all necessary tables if they don't exist."""
        tables = [
            # Economy
            '''CREATE TABLE IF NOT EXISTS economy (
                user_id TEXT, guild_id TEXT,
                balance INTEGER DEFAULT 1000,
                bank_balance INTEGER DEFAULT 0,
                last_daily INTEGER,
                last_work INTEGER,
                bank_protect_until INTEGER DEFAULT 0,
                prison_until INTEGER DEFAULT 0,
                hunger INTEGER DEFAULT 0,
                mood INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )''',
            # Levels
            '''CREATE TABLE IF NOT EXISTS levels (
                user_id TEXT, guild_id TEXT,
                xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id)
            )''',
            # Temp voice
            '''CREATE TABLE IF NOT EXISTS temp_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT, channel_id INTEGER UNIQUE,
                owner_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS guild_config (
                guild_id TEXT PRIMARY KEY,
                create_channel_id INTEGER,
                max_channels_per_user INTEGER DEFAULT 3,
                category_id INTEGER,
                control_channel_id INTEGER
            )''',
            # Shop stock
            '''CREATE TABLE IF NOT EXISTS shop_stock (
                guild_id TEXT, item_id INTEGER,
                current_stock INTEGER DEFAULT 0,
                last_restock INTEGER,
                PRIMARY KEY (guild_id, item_id)
            )''',
            # Marketplace
            '''CREATE TABLE IF NOT EXISTS marketplace_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT, seller_id TEXT,
                item_id INTEGER, quantity INTEGER,
                price_per_item INTEGER, created_at INTEGER
            )''',
            # Add any other tables your cogs need
        ]
        async with self._lock:
            for sql in tables:
                await self._conn.execute(sql)
            await self._conn.commit()

    # ---------- ЗАСВАРЛАСАН МЕТОДУУД ----------
    async def execute(self, sql: str, *params):
        """Шууд курсор буцаана (context manager БИШ)"""
        return await self._conn.execute(sql, params)

    async def fetch(self, sql: str, *params):
        """Бүх мөрийг буцаана"""
        cur = await self._conn.execute(sql, params)
        return await cur.fetchall()

    async def fetchone(self, sql: str, *params):
        """Нэг мөрийг буцаана"""
        cur = await self._conn.execute(sql, params)
        return await cur.fetchone()

    async def commit(self):
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()