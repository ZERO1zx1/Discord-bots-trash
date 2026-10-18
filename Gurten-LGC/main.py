import discord
from discord.ext import commands
import os
import sys
import asyncio
from config_manager import load_config
from dotenv import load_dotenv
from database import Database

# ==================== CONFIG ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN not found! Check .env file.")
    sys.exit(1)

PREFIX = ["g", "G"]

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

print(f"📍 Working directory: {os.getcwd()}")

config = load_config()

# ==================== DATABASE INIT ====================
async def init_db(bot):
    bot.db = Database("database/data.db")
    await bot.db.initialize()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        super().__init__(command_prefix=PREFIX, intents=intents, help_command=None)
        self.config = config
        self.owner_id = config.get("owner_id")
        self.co_owners = config.get("co_owner_ids", [])

    async def setup_hook(self):
        await init_db(self)
        print("✅ SQLite connected")

        print("\n📂 Loading cogs...")
        cogs_path = "./cogs"
        if not os.path.exists(cogs_path):
            os.makedirs(cogs_path)
            print("📁 'cogs' folder created.")

        cogs_to_load = [
            "economy",
            "register",
            "registration_checker",
            "admin", "announcement", "avatar_check", "cafe", "carts", "casino",
            "confessions", "counting", "fun", "games", "giveaway", "greetings",
            "help", "invite_tracker", "levels", "lottery", "mafia", "marriage",
            "mines", "moderation", "pvp", "roles", "shop",
            "sticky", "stock", "tempvoice", "trade"
        ]

        for cog in cogs_to_load:
            try:
                await self.load_extension(f"cogs.{cog}")
                print(f"  ✅ {cog}.py loaded")
            except Exception as e:
                print(f"  ❌ {cog}.py error: {e}")

        print("✅ Cog loading finished!\n")

        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"⚠️ Slash sync error: {e}")

    async def on_command_error(self, ctx, error):
        async def safe_send(embed, delete_after=None):
            try:
                if delete_after:
                    await ctx.send(embed=embed, delete_after=delete_after)
                else:
                    await ctx.send(embed=embed)
            except Exception:
                pass

        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(title="⏳ COOLDOWN", description=f"Try again in **{error.retry_after:.1f}s**.", color=0xf9e2af)
            await safe_send(embed, delete_after=5)
            return
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(title="❌ MISSING ARGUMENT", description=f"`{ctx.command.name}` requires **{error.param.name}**.", color=0xf38ba8)
            await safe_send(embed)
            return
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(title="❌ INVALID ARGUMENT", description=f"`{error}`", color=0xf38ba8)
            await safe_send(embed)
            return
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="🚫 MISSING PERMISSIONS", description=f"Need: `{', '.join(error.missing_permissions)}`", color=0xf38ba8)
            await safe_send(embed)
            return
        if isinstance(error, commands.NotOwner):
            embed = discord.Embed(title="🚫 OWNER ONLY", description="This command is owner-only.", color=0xf38ba8)
            await safe_send(embed)
            return
        embed = discord.Embed(title="⚠️ UNEXPECTED ERROR", description=f"`{error}`", color=0xf38ba8)
        await safe_send(embed)

    async def on_ready(self):
        print(f'✅ {self.user} is now online!')
        print(f'📊 Connected to {len(self.guilds)} servers:')
        for guild in self.guilds:
            print(f'  - {guild.name}')
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=f"{PREFIX[0]}help | Gurten|LGC"
            )
        )

    async def on_close(self):
        """Gracefully close database connection."""
        await self.db.close()
        print("🔒 Database connection closed.")

if __name__ == "__main__":
    bot = MyBot()
    bot.run(TOKEN)
