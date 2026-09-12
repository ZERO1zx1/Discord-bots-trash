import discord
from discord.ext import commands
from discord import app_commands
import datetime

EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

class AvatarLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== ӨГӨГДЛИЙН САН (SQLite) ====================
    async def init_db(self):
        """Хүснэгт байхгүй бол үүсгэх"""
        await self.bot.db.execute(
            '''CREATE TABLE IF NOT EXISTS avatar_log_config (
                guild_id TEXT PRIMARY KEY,
                log_channel_id INTEGER,
                enabled INTEGER DEFAULT 1
            )'''
        )
        await self.bot.db.commit()  # Өөрчлөлтийг баталгаажуулах

    async def get_config(self, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT log_channel_id, enabled FROM avatar_log_config WHERE guild_id = ?",
            str(guild_id)
        )
        if not row:
            return None
        return {"channel_id": row[0], "enabled": bool(row[1])}

    async def set_config(self, guild_id, channel_id=None, enabled=None):
        """Тохиргоог шинэчлэх (channel_id болон/эсвэл enabled)"""
        current = await self.get_config(guild_id)
        if current:
            new_channel = channel_id if channel_id is not None else current["channel_id"]
            new_enabled = enabled if enabled is not None else current["enabled"]
            await self.bot.db.execute(
                "UPDATE avatar_log_config SET log_channel_id = ?, enabled = ? WHERE guild_id = ?",
                new_channel, 1 if new_enabled else 0, str(guild_id)
            )
        else:
            if channel_id is None:
                return  # суваг заагдаагүй бол шинэ мөр үүсгэхгүй
            await self.bot.db.execute(
                "INSERT INTO avatar_log_config (guild_id, log_channel_id, enabled) VALUES (?, ?, ?)",
                str(guild_id), channel_id, 1 if enabled is None or enabled else 0
            )
        await self.bot.db.commit()  # Чухал: UPDATE/INSERT-ийн дараа commit

    # ==================== КОМАНДУУД (HYBRID) ====================
    @commands.hybrid_command(name="avatar_log", description="Аватар өөрчлөлтийн мэдэгдэл илгээх сувгийг тохируулах")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def avatar_log_set(self, ctx: commands.Context, channel: discord.TextChannel, enabled: bool = True):
        """Тохируулах"""
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
        await self.set_config(ctx.guild.id, channel_id=channel.id, enabled=enabled)

        embed = discord.Embed(
            title="✅ Аватар лог тохируулагдлаа",
            description=f"Аватар өөрчлөлтийн мэдэгдэл {channel.mention} сувагт ирнэ.\nТөлөв: {'Идэвхтэй' if enabled else 'Унтарсан'}",
            color=SUCCESS_COLOR
        )
        if ctx.interaction:
            await ctx.interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar_log_toggle", description="Аватар логыг түр идэвхжүүлэх/унтраах")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def avatar_log_toggle(self, ctx: commands.Context):
        """Төлөв солих"""
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
        cfg = await self.get_config(ctx.guild.id)
        if not cfg:
            embed = discord.Embed(
                title="❌ Алдаа",
                description="Эхлээд `/avatar_log` командаар суваг тохируулна уу.",
                color=ERROR_COLOR
            )
            if ctx.interaction:
                await ctx.interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
            return
        new_state = not cfg["enabled"]
        await self.set_config(ctx.guild.id, enabled=new_state)
        embed = discord.Embed(
            title="🔄 Аватар логын төлөв өөрчлөгдлөө",
            description=f"Аватар өөрчлөлтийн мэдэгдэл **{'идэвхжсэн' if new_state else 'унтарсан'}**.",
            color=SUCCESS_COLOR if new_state else WARNING_COLOR
        )
        if ctx.interaction:
            await ctx.interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar_log_status", description="Одоогийн аватар логын тохиргоог харах")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def avatar_log_status(self, ctx: commands.Context):
        """Төлөв харах"""
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
        cfg = await self.get_config(ctx.guild.id)
        if not cfg:
            embed = discord.Embed(title="ℹ️ Тохируулагдаагүй", description="`/avatar_log` ашиглана уу.", color=INFO_COLOR)
            if ctx.interaction:
                await ctx.interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
            return
        channel = ctx.guild.get_channel(cfg["channel_id"])
        channel_mention = channel.mention if channel else "Суваг олдсонгүй"
        embed = discord.Embed(
            title="📊 Аватар логын тохиргоо",
            description=f"**Лог суваг:** {channel_mention}\n**Төлөв:** {'✅ Идэвхтэй' if cfg['enabled'] else '❌ Унтарсан'}",
            color=INFO_COLOR
        )
        if ctx.interaction:
            await ctx.interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)

    # ==================== EVENT ====================
    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        # Аватар өөрчлөгдөөгүй бол гарах
        if before.display_avatar.url == after.display_avatar.url:
            return

        for guild in self.bot.guilds:
            member = guild.get_member(after.id)
            if not member:
                continue
            cfg = await self.get_config(guild.id)
            if not cfg or not cfg["enabled"]:
                continue
            channel = guild.get_channel(cfg["channel_id"])
            if not channel:
                continue

            embed = discord.Embed(
                title="🔄 Аватар өөрчлөгдлөө",
                description=f"{member.mention} (`{member}`) аватараа шинэчлэв.",
                color=GOLD_COLOR,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_author(name=member.display_name, icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=before.display_avatar.url)
            embed.set_image(url=after.display_avatar.url)
            embed.add_field(name="🖼️ Хуучин аватар", value=f"[Харах]({before.display_avatar.url})", inline=True)
            embed.add_field(name="🆕 Шинэ аватар", value=f"[Харах]({after.display_avatar.url})", inline=True)
            embed.set_footer(text=f"ID: {after.id}")
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    async def cog_load(self):
        await self.init_db()

async def setup(bot):
    await bot.add_cog(AvatarLogger(bot))