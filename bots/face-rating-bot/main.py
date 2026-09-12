import discord, os, aiosqlite, logging
from discord.ext import commands
from config import TOKEN, PREFIX, owner_id, co_owner_ids, DB_PATH
from database import init_db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, path):
        self.path = path
    def acquire(self):
        return _AcquireContext(self.path)

class _AcquireContext:
    def __init__(self, path):
        self.path = path
    async def __aenter__(self):
        try:
            self.conn = await aiosqlite.connect(self.path)
            return self.conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    async def __aexit__(self, *a):
        try:
            await self.conn.close()
        except Exception as e:
            logger.error(f"Database close error: {e}")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = intents.members = intents.voice_states = True
        super().__init__(command_prefix=PREFIX, intents=intents, help_command=None)
        self.config = {"owner_id": owner_id, "co_owners": co_owner_ids}
        self.synced_commands = 0

    async def setup_hook(self):
        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            self.db = Database(DB_PATH)
            await init_db(self.db)
            logger.info("✅ Database initialized")
        except Exception as e:
            logger.error(f"❌ Database init failed: {e}")
            raise

        print("\n📂 Cogs ачаалагдаж байна...")
        cogs = [
            "economy", "leveling", "games", "admin", "leaderboard",
            "shop", "face_rating", "moderation", "face_tournament", "help",
            "invite", "welcome"
        ]
        
        loaded_count = 0
        for cog in cogs:
            try:
                await self.load_extension(f"cogs.{cog}")
                print(f"  ✅ {cog}.py")
                loaded_count += 1
            except Exception as e:
                logger.error(f"  ❌ {cog}.py алдаа: {e}")
                print(f"  ❌ {cog}.py алдаа: {e}")

        print(f"\n✅ {loaded_count}/{len(cogs)} cogs ачаалагдлаа.")
        
        try:
            synced = await self.tree.sync()
            self.synced_commands = len(synced)
            print(f"✅ {len(synced)} slash команд синк хийгдлээ.")
        except Exception as e:
            logger.error(f"❌ Slash command sync failed: {e}")

    async def on_ready(self):
        logger.info(f"✅ {self.user} ажиллаж байна. Сервер: {len(self.guilds)}")
        print(f"✅ {self.user} ажиллаж байна. Сервер: {len(self.guilds)}")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.playing, name=f"{PREFIX}help | Looksmax.mn"
        ))

    async def on_error(self, event, *args, **kwargs):
        logger.error(f"Error in {event}: {args} {kwargs}", exc_info=True)

if __name__ == "__main__":
    bot = MyBot()
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        raise
