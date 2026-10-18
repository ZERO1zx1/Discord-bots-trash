import discord
from discord.ext import commands
from discord import app_commands
import time

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
INFO_COLOR = 0x89b4fa

class Sticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_update = {}

    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    CREATE TABLE IF NOT EXISTS sticky_messages (
                        guild_id BIGINT,
                        channel_id BIGINT,
                        message_id BIGINT,
                        content TEXT,
                        updated_at BIGINT,
                        PRIMARY KEY (guild_id, channel_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                ''')

    async def get_sticky(self, guild_id: int, channel_id: int):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT message_id, content FROM sticky_messages WHERE guild_id = %s AND channel_id = %s",
                    (guild_id, channel_id)
                )
                row = await cur.fetchone()
                if row:
                    return {"message_id": row[0], "content": row[1]}
        return None

    async def set_sticky(self, guild_id: int, channel_id: int, message_id: int, content: str):
        now = int(time.time())
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    'REPLACE INTO sticky_messages (guild_id, channel_id, message_id, content, updated_at) '
                    'VALUES (%s, %s, %s, %s, %s)',
                    (guild_id, channel_id, message_id, content, now)
                )

    async def delete_sticky(self, guild_id: int, channel_id: int):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM sticky_messages WHERE guild_id = %s AND channel_id = %s",
                    (guild_id, channel_id)
                )

    # ----------------- HYBRID STICK -----------------
    @commands.command(name='stick', with_app_command=True, description="Sticky мессеж тохируулах")
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
                color=INFO_COLOR
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

        # Шинэ sticky илгээх
        new_msg = await ctx.send(f"📌 {content}")
        await self.set_sticky(guild.id, channel.id, new_msg.id, content)

        confirm_embed = discord.Embed(
            title="✅ Sticky амжилттай тохируулагдлаа",
            description="Энэ сувагт шинэ мессеж бичих бүр sticky автоматаар шинэчлэгдэж, хамгийн доор гарч ирнэ.\n`gunstick` командаар цуцлах боломжтой.",
            color=SUCCESS_COLOR
        )
        await ctx.send(embed=confirm_embed, delete_after=5)

        # === Даалгаврын прогресс ===
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "sticky_set", 1)

    # ----------------- HYBRID UNSTICK -----------------
    @commands.command(name='unstick', with_app_command=True, description="Sticky мессежийг цуцлах")
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

        # Дахин илгээх
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
