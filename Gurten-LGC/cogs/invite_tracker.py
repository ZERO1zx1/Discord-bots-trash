import discord
from discord.ext import commands
from discord import app_commands
import datetime
import time
import random
import logging
import traceback
from io import BytesIO

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib not installed, graph commands will be disabled.")

logger = logging.getLogger(__name__)

EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}

    # ==================== DATABASE (SQLite) ====================
    async def init_db(self):
        """Хүснэгтүүд байхгүй бол үүсгэх"""
        await self.bot.db.execute(
            '''CREATE TABLE IF NOT EXISTS invite_log_config (
                guild_id TEXT PRIMARY KEY,
                log_channel_id INTEGER,
                enabled INTEGER DEFAULT 1,
                fake_delay INTEGER DEFAULT 3
            )'''
        )
        await self.bot.db.commit()
        await self.bot.db.execute(
            '''CREATE TABLE IF NOT EXISTS invite_stats (
                guild_id TEXT,
                user_id INTEGER,
                regular INTEGER DEFAULT 0,
                bonus INTEGER DEFAULT 0,
                fake INTEGER DEFAULT 0,
                `left` INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )'''
        )
        await self.bot.db.commit()
        await self.bot.db.execute(
            '''CREATE TABLE IF NOT EXISTS invite_joins (
                guild_id TEXT,
                user_id INTEGER,
                invited_by INTEGER,
                invite_code TEXT,
                joined_at INTEGER,
                left_at INTEGER,
                is_fake INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, invite_code)
            )'''
        )
        await self.bot.db.commit()
        await self.bot.db.execute(
            '''CREATE TABLE IF NOT EXISTS daily_stats (
                guild_id TEXT,
                date TEXT,
                joins INTEGER DEFAULT 0,
                leaves INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, date)
            )'''
        )
        await self.bot.db.commit()
        await self.bot.db.execute(
            '''CREATE TABLE IF NOT EXISTS invite_labels (
                guild_id TEXT,
                invite_code TEXT,
                label TEXT,
                role_id INTEGER,
                PRIMARY KEY (guild_id, invite_code)
            )'''
        )
        await self.bot.db.commit()

    # ==================== CONFIGURATION METHODS ====================
    async def get_config(self, guild_id):
        """Серверийн тохиргоог авах"""
        row = await self.bot.db.fetchone(
            "SELECT log_channel_id, enabled, fake_delay FROM invite_log_config WHERE guild_id = ?",
            str(guild_id)
        )
        if not row:
            return None
        return {"channel_id": row[0], "enabled": bool(row[1]), "fake_delay": row[2]}

    async def set_config(self, guild_id, channel_id=None, enabled=None, fake_delay=None):
        """Тохиргоог шинэчлэх (SQLite, commit-тэй)"""
        gid = str(guild_id)
        exists = await self.bot.db.fetchone(
            "SELECT 1 FROM invite_log_config WHERE guild_id = ?", gid
        )
        if exists:
            updates = []
            params = []
            if channel_id is not None:
                updates.append("log_channel_id = ?")
                params.append(channel_id)
            if enabled is not None:
                updates.append("enabled = ?")
                params.append(1 if enabled else 0)
            if fake_delay is not None:
                updates.append("fake_delay = ?")
                params.append(fake_delay)
            if updates:
                params.append(gid)
                await self.bot.db.execute(
                    f"UPDATE invite_log_config SET {', '.join(updates)} WHERE guild_id = ?",
                    *params
                )
        else:
            await self.bot.db.execute(
                "INSERT INTO invite_log_config (guild_id, log_channel_id, enabled, fake_delay) VALUES (?, ?, ?, ?)",
                gid, channel_id, 1 if enabled else 0, fake_delay or 3
            )
        await self.bot.db.commit()

    async def log_to_channel(self, guild, embed):
        """Лог сувагт embed илгээх"""
        cfg = await self.get_config(guild.id)
        if not cfg or not cfg["enabled"]:
            return
        channel = guild.get_channel(cfg["channel_id"])
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"log_to_channel error: {e}")

    async def get_invite_count(self, guild_id, user_id, exclude_fake: bool = False):
        """Урилгын тоог буцаах"""
        row = await self.bot.db.fetchone(
            "SELECT regular, bonus, fake, `left` FROM invite_stats WHERE guild_id = ? AND user_id = ?",
            str(guild_id), user_id
        )
        if not row:
            return 0
        regular, bonus, fake, left = row
        if exclude_fake:
            return regular + bonus - left
        else:
            return regular + bonus - left + fake

    async def check_bot_permissions(self, guild):
        """Ботод урилга хянах эрх байгаа эсэхийг шалгах"""
        if not guild.me.guild_permissions.manage_guild:
            cfg = await self.get_config(guild.id)
            if cfg and cfg["enabled"]:
                channel = guild.get_channel(cfg["channel_id"])
                if channel:
                    embed = discord.Embed(
                        title="⚠️ Эрх дутагдал",
                        description="Урилгын бүртгэлийг зөв ажиллуулахын тулд ботод **Manage Server** эрх хэрэгтэй.",
                        color=WARNING_COLOR
                    )
                    await channel.send(embed=embed)
            return False
        return True

    # ========== INVITES GROUP ==========
    @commands.hybrid_group(name='invites', description="Урилгын командууд", invoke_without_command=True)
    @app_commands.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def invites_group(self, ctx):
        embed = discord.Embed(
            title="🔗 Урилгын тусламж",
            description=(
                "**Урилгын командууд:**\n"
                "`invites` – өөрийн урилгуудыг харах\n"
                "`invites <@user>` – хэрэглэгчийн урилгуудыг харах\n"
                "`invites leaderboard` – урилгын самбар\n"
                "`invites codes [@user]` – идэвхтэй урилгууд\n"
                "`invites list <@user>` – урьсан хүмүүс\n"
                "`invites inviter <@user>` – хэн урьсан\n"
                "`invites addlabel` / `invites removelabel` – шошго\n\n"
                "**Тохиргоо:**\n"
                "`invitelog_set`, `invitelog_toggle`, `invitelog_status`, `fakedelay`\n"
                "`statsgraph` – гишүүдийн график"
            ),
            color=INFO_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    # ========== BASIC INVITE COUNT ==========
    @invites_group.command(name='info', description="Хэрэглэгчийн урилгын мэдээлэл")
    async def invites_info(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        count = await self.get_invite_count(ctx.guild.id, target.id)
        embed = discord.Embed(
            title=f"🔗 {target.display_name}",
            description=f"**{count}** урилга",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"{ctx.guild.name}")
        await ctx.send(embed=embed)

    # ========== INVITE LEADERBOARD ==========
    @invites_group.command(name='leaderboard', description="Урилгын шилдэг 15")
    async def invite_leaderboard(self, ctx):
        rows = await self.bot.db.fetch(
            "SELECT user_id, regular + bonus - `left` + fake as total FROM invite_stats WHERE guild_id = ? ORDER BY total DESC LIMIT 15",
            str(ctx.guild.id)
        )
        if not rows:
            return await ctx.send("🏆 Одоогоор урилгын мэдээлэл байхгүй байна.")
        embed = discord.Embed(
            title="🏆 УРИЛГЫН ШИЛДЭГ 15",
            color=GOLD_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "11️⃣", "12️⃣", "13️⃣", "14️⃣", "15️⃣"]
        for i, (uid, val) in enumerate(rows):
            user = ctx.guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
            name = user.display_name if user else f"ID: {uid}"
            embed.add_field(name=f"{medals[i]} {name}", value=f"**{val}** урилга", inline=False)
            if i >= 14:
                break
        await ctx.send(embed=embed)

    # ========== INVITE STATS ==========
    @commands.hybrid_command(name='invitestats', description="Таны урилгын статистик")
    async def invite_stats(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        row = await self.bot.db.fetchone(
            "SELECT regular, bonus, fake, `left` FROM invite_stats WHERE guild_id = ? AND user_id = ?",
            str(ctx.guild.id), target.id
        )
        if not row:
            regular = bonus = fake = left = 0
        else:
            regular, bonus, fake, left = row
        total = regular + bonus - left + fake
        embed = discord.Embed(
            title=f"📊 {target.display_name} - УРИЛГЫН СТАТИСТИК",
            color=INFO_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🎯 Жинхэнэ урилга", value=f"`{regular}`", inline=True)
        embed.add_field(name="🎁 Бонус урилга", value=f"`{bonus}`", inline=True)
        embed.add_field(name="⚠️ Хуурамч урилга", value=f"`{fake}`", inline=True)
        embed.add_field(name="👋 Гарсан хэрэглэгчид", value=f"`{left}`", inline=True)
        embed.add_field(name="📈 Нийт урилга", value=f"`{total}`", inline=True)
        embed.set_footer(text=f"{ctx.guild.name}")
        await ctx.send(embed=embed)

    # ========== INVITE CODES ==========
    @invites_group.command(name='codes', description="Идэвхтэй урилгууд")
    async def invite_codes(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        if not ctx.guild.me.guild_permissions.manage_guild:
            return await ctx.send("❌ Ботод урилгуудыг харах эрх (**Manage Server**) байхгүй байна.")
        try:
            invites = await ctx.guild.invites()
            user_invites = [inv for inv in invites if inv.inviter and inv.inviter.id == target.id]
            if not user_invites:
                return await ctx.send(f"🔗 {target.mention} энэ серверт урилга үүсгээгүй байна.")
            embed = discord.Embed(
                title=f"🔗 {target.display_name} - ИДЭВХТЭЙ УРИЛГУУД",
                color=INFO_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            for inv in user_invites[:15]:
                expiry = f"<t:{int(inv.expires_at.timestamp())}:R>" if inv.expires_at else "Хэзээ ч"
                embed.add_field(
                    name=f"#{inv.channel.name}",
                    value=f"🔗 [{inv.code}]({inv.url})\n👥 Ашиглагдсан: {inv.uses}\n⏱️ Дуусах: {expiry}\n🔢 Хязгаар: {inv.max_uses if inv.max_uses else 'Хязгааргүй'}",
                    inline=False
                )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"invite_codes error: {e}")
            await ctx.send("❌ Урилгуудыг харах боломжгүй байна. Ботод **Manage Server** эрх хэрэгтэй.")

    # ========== INVITED LIST ==========
    @invites_group.command(name='list', description="Урьсан хэрэглэгчид")
    async def invited_list(self, ctx, user: discord.Member):
        rows = await self.bot.db.fetch(
            "SELECT user_id FROM invite_joins WHERE guild_id = ? AND invited_by = ? AND left_at IS NULL",
            str(ctx.guild.id), user.id
        )
        if not rows:
            return await ctx.send(f"🔍 {user.mention} хэн ч урьсангүй эсвэл бүгд гарсан байна.")
        members = []
        for (uid,) in rows[:20]:
            m = ctx.guild.get_member(int(uid))
            members.append(m.mention if m else f"ID: {uid}")
        embed = discord.Embed(
            title=f"👥 {user.display_name} - ИЙН УРЬСАН ХҮМҮҮС",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name=f"Урсан хүмүүс ({len(rows)})", value="\n".join(members[:20]) + (f"\n... болон {len(rows)-20} бусад" if len(rows) > 20 else ""), inline=False)
        embed.set_footer(text="Зөвхөн одоо серверт байгаа гишүүд харуулагдана.")
        await ctx.send(embed=embed)

    # ========== WHO INVITED ==========
    @invites_group.command(name='inviter', description="Хэн урьсан")
    async def inviter(self, ctx, member: discord.Member):
        row = await self.bot.db.fetchone(
            "SELECT invited_by FROM invite_joins WHERE guild_id = ? AND user_id = ? ORDER BY joined_at DESC LIMIT 1",
            str(ctx.guild.id), member.id
        )
        if not row:
            return await ctx.send(f"🔍 {member.mention} -г хэн урьсны мэдээлэл олдсонгүй.")
        inviter = ctx.guild.get_member(int(row[0])) or await self.bot.fetch_user(int(row[0]))
        embed = discord.Embed(
            title="👤 ХЭН УРЬСАН БЭ?",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Хэрэглэгч", value=member.mention, inline=True)
        embed.add_field(name="Урьсан", value=inviter.mention if inviter else f"ID: {row[0]}", inline=True)
        await ctx.send(embed=embed)

    # ========== INVITE LABELS ==========
    @invites_group.command(name='addlabel', description="Урилгын шошго нэмэх")
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def add_invite_label(self, ctx, invite_code: str, label: str, role: discord.Role = None):
        await self.bot.db.execute(
            "INSERT INTO invite_labels (guild_id, invite_code, label, role_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, invite_code) DO UPDATE SET label = excluded.label, role_id = excluded.role_id",
            str(ctx.guild.id), invite_code, label, role.id if role else None
        )
        await self.bot.db.commit()
        embed = discord.Embed(
            title="✅ Урилгын шошго нэмэгдлээ",
            description=f"`{invite_code}` код: `{label}`" + (f" + {role.mention}" if role else ""),
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(embed=embed)

    @invites_group.command(name='removelabel', description="Урилгын шошго устгах")
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def remove_invite_label(self, ctx, invite_code: str):
        await self.bot.db.execute(
            "DELETE FROM invite_labels WHERE guild_id = ? AND invite_code = ?",
            str(ctx.guild.id), invite_code
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ `{invite_code}` шошго амжилттай устгагдлаа.")

    # ========== CONFIGURATION COMMANDS ==========
    @commands.hybrid_command(name='invitelog_set', description="Урилгын логын сувгийг тохируулах")
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def invitelog_set(self, ctx, channel: discord.TextChannel):
        await ctx.defer(ephemeral=True)
        await self.set_config(ctx.guild.id, channel_id=channel.id, enabled=True)
        embed = discord.Embed(
            title="✅ Урилгын лог тохируулагдлаа",
            description=f"Урилгын бүх үйлдэл {channel.mention} сувагт логлогдоно.",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name='invitelog_toggle', description="Урилгын логыг идэвхжүүлэх/унтраах")
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def invitelog_toggle(self, ctx):
        await ctx.defer(ephemeral=True)
        cfg = await self.get_config(ctx.guild.id)
        if not cfg:
            return await ctx.send("❌ Эхлээд `/invitelog_set` ашиглан суваг тохируулна уу.", ephemeral=True)
        new_state = not cfg["enabled"]
        await self.set_config(ctx.guild.id, enabled=new_state)
        status = "идэвхжсэн" if new_state else "унтарсан"
        embed = discord.Embed(
            title="🔄 Урилгын лог төлөв өөрчлөгдлөө",
            description=f"Урилгын лог **{status}**.",
            color=SUCCESS_COLOR if new_state else WARNING_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name='fakedelay', description="Хуурамч бүртгэл илрүүлэх хоногийн тоог тохируулах")
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def set_fake_delay(self, ctx, days: int):
        if days < 0 or days > 300:
            return await ctx.send("❌ Хугацаа 0-300 хоног байх ёстой.", ephemeral=True)
        await self.set_config(ctx.guild.id, fake_delay=days)
        embed = discord.Embed(
            title="✅ Хуурамч бүртгэлийн илрүүлэлт тохируулагдлаа",
            description=f"{days} хоногоос бага насны бүртгэлийг хуурамч гэж тэмдэглэнэ.",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name='invitelog_status', description="Урилгын логын одоогийн төлөв")
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def invitelog_status(self, ctx):
        await ctx.defer(ephemeral=True)
        cfg = await self.get_config(ctx.guild.id)
        if not cfg:
            return await ctx.send("❌ Тохируулаагүй байна. `/invitelog_set` ашиглана уу.", ephemeral=True)
        channel = ctx.guild.get_channel(cfg["channel_id"])
        channel_mention = channel.mention if channel else "Суваг олдсонгүй"
        embed = discord.Embed(
            title="📊 Урилгын лог тохиргоо",
            description=f"**Лог суваг:** {channel_mention}\n**Төлөв:** {'✅ Идэвхтэй' if cfg['enabled'] else '❌ Унтарсан'}\n**Хуурамч хязгаар:** {cfg['fake_delay']} хоног",
            color=INFO_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(embed=embed, ephemeral=True)

    # ========== GRAPH ==========
    @commands.hybrid_command(name='statsgraph', description="Статистикийн графикийг харах")
    async def stats_graph(self, ctx, days: int = 7):
        if not MATPLOTLIB_AVAILABLE:
            return await ctx.send("⚠️ График ажиллуулахын тулд `matplotlib` суулгана уу: `pip install matplotlib`")
        end_date = datetime.datetime.now(datetime.timezone.utc).date()
        start_date = end_date - datetime.timedelta(days=days - 1)
        dates = []
        joins = []
        leaves = []
        for i in range(days):
            date = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            row = await self.bot.db.fetchone(
                "SELECT joins, leaves FROM daily_stats WHERE guild_id = ? AND date = ?",
                str(ctx.guild.id), date
            )
            dates.append(date)
            joins.append(row[0] if row else 0)
            leaves.append(row[1] if row else 0)
        plt.figure(figsize=(10, 5))
        plt.plot(dates, joins, marker='o', label='Нэгдсэн', color='green', linewidth=2)
        plt.plot(dates, leaves, marker='o', label='Гарсан', color='red', linewidth=2)
        plt.xlabel('Огноо')
        plt.ylabel('Тоо')
        plt.title(f'{ctx.guild.name} - Гишүүдийн нэгдэл/гарлын статистик')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()
        file = discord.File(buffer, filename='stats.png')
        embed = discord.Embed(
            title="📊 Серверийн статистик",
            description=f"Сүүлийн {days} хоног",
            color=INFO_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_image(url="attachment://stats.png")
        await ctx.send(embed=embed, file=file)

    # ========== EVENTS ==========
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                if guild.me.guild_permissions.manage_guild:
                    invites = await guild.invites()
                    self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites}
                else:
                    logger.warning(f"Missing manage_guild permission in guild {guild.id}, invite tracking disabled.")
                    await self.check_bot_permissions(guild)
            except Exception as e:
                logger.error(f"Failed to cache invites for guild {guild.id}: {e}")

    @commands.Cog.listener()
    async def on_member_leave(self, member: discord.Member):
        if member.bot:
            return
        now = int(time.time())
        # left_at тэмдэглэх
        await self.bot.db.execute(
            "UPDATE invite_joins SET left_at = ? WHERE guild_id = ? AND user_id = ? AND left_at IS NULL",
            now, str(member.guild.id), member.id
        )
        await self.bot.db.commit()
        # Урьсан хүнийг олох
        row = await self.bot.db.fetchone(
            "SELECT invited_by FROM invite_joins WHERE guild_id = ? AND user_id = ? ORDER BY joined_at DESC LIMIT 1",
            str(member.guild.id), member.id
        )
        if row:
            await self.bot.db.execute(
                "UPDATE invite_stats SET `left` = `left` + 1 WHERE guild_id = ? AND user_id = ?",
                str(member.guild.id), row[0]
            )
            await self.bot.db.commit()
        cfg = await self.get_config(member.guild.id)
        if cfg and cfg["enabled"]:
            channel = member.guild.get_channel(cfg["channel_id"])
            if channel:
                embed = discord.Embed(
                    title="🚪 Гишүүн гарлаа",
                    description=f"{member.mention} (`{member}`) серверээс гарлаа.",
                    color=WARNING_COLOR,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        cfg = await self.get_config(member.guild.id)
        if not member.guild.me.guild_permissions.manage_guild:
            if cfg and cfg["enabled"]:
                embed = discord.Embed(
                    title="⚠️ Эрх дутагдал",
                    description="Урилгын бүртгэлийг зөв ажиллуулахын тулд ботод **Manage Server** эрх хэрэгтэй.",
                    color=WARNING_COLOR
                )
                await member.guild.get_channel(cfg["channel_id"]).send(embed=embed)
            return
        try:
            current = await member.guild.invites()
            old = self.invite_cache.get(member.guild.id, {})
            used = None
            for inv in current:
                if inv.uses > old.get(inv.code, 0):
                    used = inv
                    break
            self.invite_cache[member.guild.id] = {inv.code: inv.uses for inv in current}
            if used and used.inviter:
                is_fake = False
                if cfg and cfg["fake_delay"] > 0:
                    account_age_days = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
                    is_fake = account_age_days < cfg["fake_delay"]
                now = int(time.time())
                await self.bot.db.execute(
                    "INSERT INTO invite_joins (guild_id, user_id, invited_by, invite_code, joined_at, is_fake) VALUES (?, ?, ?, ?, ?, ?)",
                    str(member.guild.id), member.id, used.inviter.id, used.code, now, 1 if is_fake else 0
                )
                await self.bot.db.commit()
                await self.bot.db.execute(
                    "INSERT INTO invite_stats (guild_id, user_id, regular, fake) VALUES (?, ?, 1, ?) "
                    "ON CONFLICT(guild_id, user_id) DO UPDATE SET regular = regular + 1, fake = fake + ?",
                    str(member.guild.id), used.inviter.id, 1 if is_fake else 0, 1 if is_fake else 0
                )
                await self.bot.db.commit()
                # Шошго шалгах
                label_row = await self.bot.db.fetchone(
                    "SELECT label, role_id FROM invite_labels WHERE guild_id = ? AND invite_code = ?",
                    str(member.guild.id), used.code
                )
                label_text = f"\n🏷️ Шошго: {label_row[0]}" if label_row else ""
                if label_row and label_row[1]:
                    role = member.guild.get_role(label_row[1])
                    if role and member.guild.me.guild_permissions.manage_roles:
                        try:
                            await member.add_roles(role, reason=f"Урилгын шошго: {used.code}")
                        except Exception as e:
                            logger.error(f"Failed to assign role: {e}")
                today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
                await self.bot.db.execute(
                    "INSERT INTO daily_stats (guild_id, date, joins) VALUES (?, ?, 1) "
                    "ON CONFLICT(guild_id, date) DO UPDATE SET joins = joins + 1",
                    str(member.guild.id), today
                )
                await self.bot.db.commit()
                if cfg and cfg["enabled"]:
                    channel = member.guild.get_channel(cfg["channel_id"])
                    if channel:
                        invite_count = await self.get_invite_count(member.guild.id, used.inviter.id)
                        fake_tag = "⚠️ **ХУУРАМЧ БҮРТГЭЛ** ⚠️\n" if is_fake else ""
                        embed = discord.Embed(
                            title="➕ Гишүүн нэгдлээ",
                            description=f"{fake_tag}{member.mention} (`{member}`)\n"
                                        f"**Урьсан:** {used.inviter.mention}\n"
                                        f"**Урилгын код:** `{used.code}`{label_text}\n"
                                        f"**Суваг:** {used.channel.mention}\n"
                                        f"**Нийт урилга:** {invite_count}",
                            color=WARNING_COLOR if is_fake else SUCCESS_COLOR,
                            timestamp=datetime.datetime.now(datetime.timezone.utc)
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        await channel.send(embed=embed)
            else:
                if cfg and cfg["enabled"]:
                    channel = member.guild.get_channel(cfg["channel_id"])
                    if channel:
                        embed = discord.Embed(
                            title="➕ Гишүүн нэгдлээ",
                            description=f"{member.mention} (`{member}`) серверт нэгдлээ, урилгын код тодорхойгүй.",
                            color=INFO_COLOR,
                            timestamp=datetime.datetime.now(datetime.timezone.utc)
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"on_member_join error for guild {member.guild.id}: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if not invite.guild:
            return
        if invite.guild.id not in self.invite_cache:
            self.invite_cache[invite.guild.id] = {}
        self.invite_cache[invite.guild.id][invite.code] = invite.uses
        cfg = await self.get_config(invite.guild.id)
        if cfg and cfg["enabled"]:
            channel = invite.guild.get_channel(cfg["channel_id"])
            if channel:
                embed = discord.Embed(
                    title="🔗 Урилга үүсгэгдлээ",
                    description=f"**Суваг:** {invite.channel.mention}\n**Үүсгэсэн:** {invite.inviter.mention if invite.inviter else 'Хүн биш'}\n**Код:** `{invite.code}`\n**Хугацаа:** {invite.max_age} сек\n**Хязгаар:** {invite.max_uses if invite.max_uses else 'Хязгааргүй'}\n**Түр:** {'Тийм' if invite.temporary else 'Үгүй'}",
                    color=GOLD_COLOR,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.set_author(name=invite.guild.name, icon_url=invite.guild.icon.url if invite.guild.icon else None)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if not invite.guild:
            return
        if invite.guild.id in self.invite_cache and invite.code in self.invite_cache[invite.guild.id]:
            del self.invite_cache[invite.guild.id][invite.code]
        cfg = await self.get_config(invite.guild.id)
        if cfg and cfg["enabled"]:
            channel = invite.guild.get_channel(cfg["channel_id"])
            if channel:
                embed = discord.Embed(
                    title="🗑️ Урилга устгагдлаа",
                    description=f"**Суваг:** {invite.channel.mention}\n**Код:** `{invite.code}`\n**Ашиглагдсан:** {invite.uses}",
                    color=WARNING_COLOR,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.set_author(name=invite.guild.name, icon_url=invite.guild.icon.url if invite.guild.icon else None)
                await channel.send(embed=embed)

    async def cog_load(self):
        await self.init_db()


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))