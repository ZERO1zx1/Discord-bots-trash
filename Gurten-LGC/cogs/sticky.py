import discord
from discord.ext import commands
from discord import app_commands
import time

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af

class Sticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_update = {}

    async def init_db(self):
        # SQLite table: PRIMARY KEY (guild_id, channel_id)
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS sticky_messages (
                guild_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                content TEXT,
                updated_at INTEGER,
                PRIMARY KEY (guild_id, channel_id)
            )
        ''')
        await self.bot.db.commit()

    async def get_sticky(self, guild_id: int, channel_id: int):
        row = await self.bot.db.fetchone(
            "SELECT message_id, content FROM sticky_messages WHERE guild_id = ? AND channel_id = ?",
            guild_id, channel_id
        )
        if row:
            return {"message_id": row[0], "content": row[1]}
        return None

    async def set_sticky(self, guild_id: int, channel_id: int, message_id: int, content: str):
        now = int(time.time())
        # INSERT OR REPLACE because of PRIMARY KEY
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO sticky_messages (guild_id, channel_id, message_id, content, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            guild_id, channel_id, message_id, content, now
        )
        await self.bot.db.commit()

    async def delete_sticky(self, guild_id: int, channel_id: int):
        await self.bot.db.execute(
            "DELETE FROM sticky_messages WHERE guild_id = ? AND channel_id = ?",
            guild_id, channel_id
        )
        await self.bot.db.commit()

    # ----------------- HYBRID STICK -----------------
    @commands.hybrid_command(name='stick', with_app_command=True, description="Sticky мессеж тохируулах")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(content="Sticky дээр харуулах текст (хоосон бол одоогийн sticky-г харна)")
    async def stick_command(self, ctx: commands.Context, *, content: str = None):
        guild = ctx.guild
        channel = ctx.channel

        if content is None:
            sticky = await self.get_sticky(guild.id, channel.id)
            if not sticky:
                embed = discord.Embed(
                    title="📌 Sticky Message",
                    description="Энэ сувагт sticky тохируулаагүй байна.\n`gstick <текст>` командаар тохируулна уу.",
                    color=ERROR_COLOR
                )
                return await ctx.send(embed=embed)
            embed = discord.Embed(
                title="📌 Одоогийн sticky message",
                description=sticky["content"],
                color=0x89b4fa
            )
            return await ctx.send(embed=embed)

        # Хуучин sticky-г устгах
        old = await self.get_sticky(guild.id, channel.id)
        if old:
            try:
                old_msg = await channel.fetch_message(old["message_id"])
                await old_msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
            await self.delete_sticky(guild.id, channel.id)

        # Шинэ sticky мессеж илгээх
        msg_content = f"📌 {content}"
        new_msg = await ctx.send(msg_content)
        await self.set_sticky(guild.id, channel.id, new_msg.id, content)

        confirm_embed = discord.Embed(
            title="✅ Sticky амжилттай тохируулагдлаа",
            description="Энэ сувагт шинэ мессеж бичих бүр sticky автоматаар шинэчлэгдэж, хамгийн доор гарч ирнэ.\n`gunstick` командаар цуцлах боломжтой.",
            color=SUCCESS_COLOR
        )
        await ctx.send(embed=confirm_embed, delete_after=5)

    # ----------------- HYBRID UNSTICK -----------------
    @commands.hybrid_command(name='unstick', with_app_command=True, description="Sticky мессежийг цуцлах")
    @commands.has_permissions(manage_channels=True)
    async def unstick_command(self, ctx: commands.Context):
        guild = ctx.guild
        channel = ctx.channel

        sticky = await self.get_sticky(guild.id, channel.id)
        if not sticky:
            embed = discord.Embed(title="❌ Алдаа", description="Энэ сувагт sticky тохируулаагүй байна.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        await self.delete_sticky(guild.id, channel.id)
        try:
            msg = await channel.fetch_message(sticky["message_id"])
            await msg.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

        embed = discord.Embed(
            title="🗑️ Sticky устгагдлаа",
            description="Энэ сувагт sticky message идэвхгүй боллоо.",
            color=WARNING_COLOR
        )
        await ctx.send(embed=embed)

    # ----------------- AUTO UPDATE -----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        # Ignore commands
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        guild = message.guild
        channel = message.channel

        sticky = await self.get_sticky(guild.id, channel.id)
        if not sticky:
            return

        # Rate‑limit: 3 секунд
        now = time.time()
        key = f"{guild.id}:{channel.id}"
        if key in self.last_update and now - self.last_update[key] < 3:
            return
        self.last_update[key] = now

        # Хуучин мессежийг устгах
        try:
            old_msg = await channel.fetch_message(sticky["message_id"])
            await old_msg.delete()
        except (discord.NotFound, discord.Forbidden):
            pass
        except Exception:
            pass

        # Шинэ sticky мессеж илгээх
        try:
            new_content = f"📌 {sticky['content']}"
            new_msg = await channel.send(new_content)
            await self.set_sticky(guild.id, channel.id, new_msg.id, sticky["content"])
        except discord.Forbidden:
            pass

    async def cog_load(self):
        await self.init_db()

async def setup(bot):
    await bot.add_cog(Sticky(bot))