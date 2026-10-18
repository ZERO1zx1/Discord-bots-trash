import discord
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
