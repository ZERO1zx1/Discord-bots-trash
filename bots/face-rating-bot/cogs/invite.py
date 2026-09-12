import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
import time
import random
import logging
import traceback
from io import BytesIO
from typing import Optional

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

# ==================== МОДАЛ: ХУУРАМЧ ХОНОГ ТОХИРУУЛАХ ====================
class FakeDelayModal(ui.Modal, title="Хуурамч бүртгэлийн хязгаар"):
    days = ui.TextInput(
        label="Хоногийн тоо (0-300)",
        placeholder="3",
        default="3",
        required=True
    )
    def __init__(self, view):
        super().__init__()
        self.view = view
    async def on_submit(self, interaction: discord.Interaction):
        try:
            d = int(self.days.value)
            if d < 0 or d > 300:
                return await interaction.response.send_message("❌ 0-300 хооронд тоо оруулна уу.", ephemeral=True)
            await self.view.cog.set_config(interaction.guild_id, fake_delay=d)
            await interaction.response.send_message(f"✅ Хуурамч хязгаар: {d} хоног", ephemeral=True)
            await self.view.refresh(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Зөвхөн тоо оруулна уу.", ephemeral=True)

# ==================== ТОХИРГООНЫ САМБАР (VIEW) ====================
class InviteSetupView(ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: discord.Interaction):
        cfg = await self.cog.get_config(self.guild_id)
        embed = self.build_embed(cfg, interaction.guild)
        await interaction.edit_original_response(embed=embed, view=self)

    def build_embed(self, cfg, guild):
        if cfg is None:
            desc = "⚠️ **Тохиргоо хийгдээгүй.**\nДоорх сонголтоор лог сувгаа тохируулна уу."
            channel_text = "❌ Сонгогдоогүй"
            enabled = False
            fake_delay = 3
        else:
            channel = guild.get_channel(cfg['channel_id'])
            channel_text = channel.mention if channel else "❌ Устгагдсан"
            enabled = cfg['enabled']
            fake_delay = cfg['fake_delay']
            desc = None

        embed = discord.Embed(
            title="🔧 Урилгын логын тохиргоо",
            description=desc,
            color=INFO_COLOR
        )
        embed.add_field(name="📢 Лог суваг", value=channel_text, inline=False)
        embed.add_field(name="🔘 Төлөв", value="✅ Идэвхтэй" if enabled else "❌ Унтарсан", inline=True)
        embed.add_field(name="⏱️ Хуурамч хязгаар", value=f"{fake_delay} хоног", inline=True)
        embed.set_footer(text="Дээрх сонголтуудаар тохиргоог өөрчилнө үү.")
        return embed

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Лог суваг сонго...", min_values=1, max_values=1, row=0)
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        channel = select.values[0]
        await self.cog.set_config(self.guild_id, channel_id=channel.id, enabled=True)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="🔘 Идэвхжүүлэх/Унтраах", style=discord.ButtonStyle.primary, row=1)
    async def toggle_enabled(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        if cfg is None:
            return await interaction.response.send_message("❌ Эхлээд лог сувгаа сонгоно уу.", ephemeral=True)
        new_state = not cfg['enabled']
        await self.cog.set_config(self.guild_id, enabled=new_state)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="⏱️ Хуурамч хязгаар", style=discord.ButtonStyle.secondary, row=1)
    async def fake_delay_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FakeDelayModal(self))

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=1)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.refresh(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try: await self.message.edit(view=self)
            except: pass


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}

    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS invite_log_config (
                    guild_id TEXT PRIMARY KEY,
                    log_channel_id INTEGER,
                    enabled INTEGER DEFAULT 1,
                    fake_delay INTEGER DEFAULT 3
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS invite_stats (
                    guild_id TEXT,
                    user_id INTEGER,
                    regular INTEGER DEFAULT 0,
                    bonus INTEGER DEFAULT 0,
                    fake INTEGER DEFAULT 0,
                    `left` INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS invite_joins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    user_id INTEGER,
                    invited_by INTEGER,
                    invite_code TEXT,
                    joined_at INTEGER,
                    left_at INTEGER,
                    is_fake INTEGER DEFAULT 0
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    guild_id TEXT,
                    date TEXT,
                    joins INTEGER DEFAULT 0,
                    leaves INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, date)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS invite_labels (
                    guild_id TEXT,
                    invite_code TEXT,
                    label TEXT,
                    role_id INTEGER,
                    PRIMARY KEY (guild_id, invite_code)
                )
            """)
            await conn.commit()

    async def get_config(self, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT log_channel_id, enabled, fake_delay FROM invite_log_config WHERE guild_id = ?",
                (str(guild_id),)
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        return {"channel_id": row[0], "enabled": bool(row[1]), "fake_delay": row[2] or 3}

    async def set_config(self, guild_id, channel_id=None, enabled=None, fake_delay=None):
        gid = str(guild_id)
        async with self.bot.db.acquire() as conn:
            # Эхлээд мөр байгаа эсэхийг шалгана
            async with conn.execute("SELECT 1 FROM invite_log_config WHERE guild_id = ?", (gid,)) as cur:
                exists = await cur.fetchone()
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
                    await conn.execute(
                        f"UPDATE invite_log_config SET {', '.join(updates)} WHERE guild_id = ?",
                        params
                    )
            else:
                await conn.execute(
                    "INSERT INTO invite_log_config (guild_id, log_channel_id, enabled, fake_delay) VALUES (?, ?, ?, ?)",
                    (gid, channel_id or 0, 1 if enabled else 0, fake_delay or 3)
                )
            await conn.commit()

    async def log_to_channel(self, guild, embed):
        cfg = await self.get_config(guild.id)
        if not cfg or not cfg["enabled"]:
            return
        channel = guild.get_channel(cfg["channel_id"])
        if channel:
            try: await channel.send(embed=embed)
            except Exception as e: logger.error(f"log_to_channel error: {e}")

    async def get_invite_count(self, guild_id, user_id, exclude_fake: bool = False):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT regular, bonus, fake, `left` FROM invite_stats WHERE guild_id = ? AND user_id = ?",
                (str(guild_id), user_id)
            ) as cursor:
                row = await cursor.fetchone()
        if not row: return 0
        regular, bonus, fake, left = row
        return regular + bonus - left + (0 if exclude_fake else fake)

    # ========== PUBLIC API: LEADERBOARD ХОЛБОЛТ ==========
    async def get_top_inviters(self, guild_id: int, limit=10, offset=0):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                """SELECT user_id, regular + bonus - `left` + fake AS total
                   FROM invite_stats
                   WHERE guild_id = ?
                   ORDER BY total DESC
                   LIMIT ? OFFSET ?""",
                (str(guild_id), limit, offset)
            ) as cursor:
                rows = await cursor.fetchall()
        return [(int(row[0]), row[1]) for row in rows]

    # ========== INVITES GROUP ==========
    invites_group = app_commands.Group(name="invites", description="Урилгын удирдлага")

    @invites_group.command(name="setup", description="Урилгын логын тохиргооны самбар нээх")
    @app_commands.default_permissions(manage_guild=True)
    async def invites_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.init_db()
        cfg = await self.get_config(interaction.guild_id)
        view = InviteSetupView(self, interaction.guild_id, interaction.user.id)
        embed = view.build_embed(cfg, interaction.guild)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @invites_group.command(name="info", description="Хэрэглэгчийн урилгын мэдээлэл")
    async def invites_info(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        await self.init_db()
        count = await self.get_invite_count(interaction.guild.id, target.id)
        embed = discord.Embed(title=f"🔗 {target.display_name}", description=f"**{count}** урилга", color=SUCCESS_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @invites_group.command(name="stats", description="Урилгын статистик")
    async def invite_stats(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        await self.init_db()
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT regular, bonus, fake, `left` FROM invite_stats WHERE guild_id = ? AND user_id = ?",
                (str(interaction.guild.id), target.id)
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            regular = bonus = fake = left = 0
        else:
            regular, bonus, fake, left = row
        total = regular + bonus - left + fake
        embed = discord.Embed(title=f"📊 {target.display_name} - УРИЛГЫН СТАТИСТИК", color=INFO_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🎯 Жинхэнэ", value=f"`{regular}`", inline=True)
        embed.add_field(name="🎁 Бонус", value=f"`{bonus}`", inline=True)
        embed.add_field(name="⚠️ Хуурамч", value=f"`{fake}`", inline=True)
        embed.add_field(name="👋 Гарсан", value=f"`{left}`", inline=True)
        embed.add_field(name="📈 Нийт", value=f"`{total}`", inline=True)
        await interaction.response.send_message(embed=embed)

    @invites_group.command(name="codes", description="Идэвхтэй урилгууд")
    async def invite_codes(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        if not interaction.guild.me.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Ботод **Manage Server** эрх байхгүй.")
        try:
            invites = await interaction.guild.invites()
            user_invites = [inv for inv in invites if inv.inviter and inv.inviter.id == target.id]
            if not user_invites:
                return await interaction.response.send_message(f"🔗 {target.mention} урилга үүсгээгүй байна.")
            embed = discord.Embed(title=f"🔗 {target.display_name} - ИДЭВХТЭЙ УРИЛГУУД", color=INFO_COLOR)
            embed.set_thumbnail(url=target.display_avatar.url)
            for inv in user_invites[:15]:
                expiry = f"<t:{int(inv.expires_at.timestamp())}:R>" if inv.expires_at else "Хэзээ ч"
                embed.add_field(name=f"#{inv.channel.name}", value=f"🔗 [{inv.code}]({inv.url})\n👥 {inv.uses}\n⏱️ {expiry}\n🔢 {inv.max_uses if inv.max_uses else 'Хязгааргүй'}", inline=False)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message("❌ Урилгуудыг харах боломжгүй.")

    @invites_group.command(name="list", description="Урьсан хэрэглэгчид")
    async def invited_list(self, interaction: discord.Interaction, user: discord.Member):
        await self.init_db()
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT user_id FROM invite_joins WHERE guild_id = ? AND invited_by = ? AND left_at IS NULL",
                (str(interaction.guild.id), user.id)
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            return await interaction.response.send_message(f"🔍 {user.mention} хэн ч урьсангүй.")
        members = []
        for (uid,) in rows[:20]:
            m = interaction.guild.get_member(int(uid))
            members.append(m.mention if m else f"ID: {uid}")
        embed = discord.Embed(title=f"👥 {user.display_name} - ИЙН УРЬСАН ХҮМҮҮС", color=SUCCESS_COLOR)
        embed.add_field(name=f"Урсан хүмүүс ({len(rows)})", value="\n".join(members), inline=False)
        await interaction.response.send_message(embed=embed)

    @invites_group.command(name="inviter", description="Хэн урьсан")
    async def inviter(self, interaction: discord.Interaction, member: discord.Member):
        await self.init_db()
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT invited_by FROM invite_joins WHERE guild_id = ? AND user_id = ? ORDER BY joined_at DESC LIMIT 1",
                (str(interaction.guild.id), member.id)
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return await interaction.response.send_message(f"🔍 {member.mention} -г хэн урьсны мэдээлэл олдсонгүй.")
        inviter_user = interaction.guild.get_member(int(row[0])) or await self.bot.fetch_user(int(row[0]))
        embed = discord.Embed(title="👤 ХЭН УРЬСАН БЭ?", color=SUCCESS_COLOR)
        embed.add_field(name="Хэрэглэгч", value=member.mention, inline=True)
        embed.add_field(name="Урьсан", value=inviter_user.mention if inviter_user else f"ID: {row[0]}", inline=True)
        await interaction.response.send_message(embed=embed)

    @invites_group.command(name="addlabel", description="Урилгын шошго нэмэх")
    @app_commands.default_permissions(administrator=True)
    async def add_invite_label(self, interaction: discord.Interaction, invite_code: str, label: str, role: Optional[discord.Role] = None):
        await self.init_db()
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO invite_labels (guild_id, invite_code, label, role_id) VALUES (?, ?, ?, ?)",
                (str(interaction.guild.id), invite_code, label, role.id if role else None)
            )
            await conn.commit()
        embed = discord.Embed(title="✅ Урилгын шошго нэмэгдлээ",
                              description=f"`{invite_code}`: `{label}`" + (f" + {role.mention}" if role else ""),
                              color=SUCCESS_COLOR)
        await interaction.response.send_message(embed=embed)

    @invites_group.command(name="removelabel", description="Урилгын шошго устгах")
    @app_commands.default_permissions(administrator=True)
    async def remove_invite_label(self, interaction: discord.Interaction, invite_code: str):
        await self.init_db()
        async with self.bot.db.acquire() as conn:
            await conn.execute("DELETE FROM invite_labels WHERE guild_id = ? AND invite_code = ?",
                               (str(interaction.guild.id), invite_code))
            await conn.commit()
        await interaction.response.send_message(f"✅ `{invite_code}` шошго устгагдлаа.")

    @invites_group.command(name="graph", description="Статистик график")
    async def stats_graph(self, interaction: discord.Interaction, days: int = 7):
        if not MATPLOTLIB_AVAILABLE:
            return await interaction.response.send_message("⚠️ matplotlib суулгаагүй.")
        await self.init_db()
        end_date = datetime.datetime.now(datetime.timezone.utc).date()
        start_date = end_date - datetime.timedelta(days=days - 1)
        dates, joins, leaves = [], [], []
        for i in range(days):
            date = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            async with self.bot.db.acquire() as conn:
                async with conn.execute(
                    "SELECT joins, leaves FROM daily_stats WHERE guild_id = ? AND date = ?",
                    (str(interaction.guild.id), date)
                ) as cursor:
                    row = await cursor.fetchone()
            dates.append(date)
            joins.append(row[0] if row else 0)
            leaves.append(row[1] if row else 0)
        plt.figure(figsize=(10, 5))
        plt.plot(dates, joins, marker='o', label='Нэгдсэн', color='green', linewidth=2)
        plt.plot(dates, leaves, marker='o', label='Гарсан', color='red', linewidth=2)
        plt.xlabel('Огноо')
        plt.ylabel('Тоо')
        plt.title(f'{interaction.guild.name} - Гишүүдийн статистик')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()
        file = discord.File(buffer, filename='stats.png')
        embed = discord.Embed(title="📊 Серверийн статистик", description=f"Сүүлийн {days} хоног", color=INFO_COLOR)
        embed.set_image(url="attachment://stats.png")
        await interaction.response.send_message(embed=embed, file=file)

    # ========== EVENTS ==========
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                if guild.me.guild_permissions.manage_guild:
                    invites = await guild.invites()
                    self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites}
            except Exception as e:
                logger.error(f"Failed to cache invites for guild {guild.id}: {e}")

    @commands.Cog.listener()
    async def on_member_leave(self, member: discord.Member):
        if member.bot: return
        await self.init_db()
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "UPDATE invite_joins SET left_at = ? WHERE guild_id = ? AND user_id = ? AND left_at IS NULL",
                (int(time.time()), str(member.guild.id), member.id)
            )
            async with conn.execute(
                "SELECT invited_by FROM invite_joins WHERE guild_id = ? AND user_id = ? ORDER BY joined_at DESC LIMIT 1",
                (str(member.guild.id), member.id)
            ) as cursor:
                row = await cursor.fetchone()
        if row:
            async with self.bot.db.acquire() as conn:
                await conn.execute(
                    "UPDATE invite_stats SET `left` = `left` + 1 WHERE guild_id = ? AND user_id = ?",
                    (str(member.guild.id), row[0])
                )
        cfg = await self.get_config(member.guild.id)
        if cfg and cfg["enabled"]:
            channel = member.guild.get_channel(cfg["channel_id"])
            if channel:
                embed = discord.Embed(title="🚪 Гишүүн гарлаа", description=f"{member.mention} (`{member}`) серверээс гарлаа.",
                                      color=WARNING_COLOR, timestamp=datetime.datetime.now(datetime.timezone.utc))
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        await self.init_db()
        cfg = await self.get_config(member.guild.id)
        if not member.guild.me.guild_permissions.manage_guild:
            if cfg and cfg["enabled"]:
                embed = discord.Embed(title="⚠️ Эрх дутагдал", description="Ботод **Manage Server** эрх хэрэгтэй.", color=WARNING_COLOR)
                channel = member.guild.get_channel(cfg["channel_id"])
                if channel:
                    await channel.send(embed=embed)
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

                # Даалгаврын системд мэдэгдэх (урьсан хүн)
                quests_cog = self.bot.get_cog("Quests")
                if quests_cog:
                    await quests_cog.trigger_event(used.inviter.id, member.guild.id, "invite_create", 1)

                async with self.bot.db.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO invite_joins (guild_id, user_id, invited_by, invite_code, joined_at, is_fake) VALUES (?, ?, ?, ?, ?, ?)",
                        (str(member.guild.id), member.id, used.inviter.id, used.code, int(time.time()), 1 if is_fake else 0)
                    )
                    await conn.execute(
                        "INSERT INTO invite_stats (guild_id, user_id, regular, fake) VALUES (?, ?, 1, ?) "
                        "ON CONFLICT(guild_id, user_id) DO UPDATE SET regular = regular + 1, fake = fake + ?",
                        (str(member.guild.id), used.inviter.id, 1 if is_fake else 0, 1 if is_fake else 0)
                    )
                    await conn.commit()

                    async with conn.execute(
                        "SELECT label, role_id FROM invite_labels WHERE guild_id = ? AND invite_code = ?",
                        (str(member.guild.id), used.code)
                    ) as cursor:
                        label_row = await cursor.fetchone()

                label_text = f"\n🏷️ Шошго: {label_row[0]}" if label_row else ""
                if label_row and label_row[1]:
                    role = member.guild.get_role(label_row[1])
                    if role and member.guild.me.guild_permissions.manage_roles:
                        try: await member.add_roles(role, reason=f"Урилгын шошго: {used.code}")
                        except Exception as e: logger.error(f"Failed to assign role: {e}")

                today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
                async with self.bot.db.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO daily_stats (guild_id, date, joins) VALUES (?, ?, 1) "
                        "ON CONFLICT(guild_id, date) DO UPDATE SET joins = joins + 1",
                        (str(member.guild.id), today)
                    )
                    await conn.commit()

                if cfg and cfg["enabled"]:
                    channel = member.guild.get_channel(cfg["channel_id"])
                    if channel:
                        invite_count = await self.get_invite_count(member.guild.id, used.inviter.id)
                        fake_tag = "⚠️ **ХУУРАМЧ БҮРТГЭЛ** ⚠️\n" if is_fake else ""
                        embed = discord.Embed(
                            title="➕ Гишүүн нэгдлээ",
                            description=f"{fake_tag}{member.mention} (`{member}`)\n**Урьсан:** {used.inviter.mention}\n**Код:** `{used.code}`{label_text}\n**Нийт:** {invite_count}",
                            color=WARNING_COLOR if is_fake else SUCCESS_COLOR,
                            timestamp=datetime.datetime.now(datetime.timezone.utc)
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        await channel.send(embed=embed)
            else:
                if cfg and cfg["enabled"]:
                    channel = member.guild.get_channel(cfg["channel_id"])
                    if channel:
                        embed = discord.Embed(title="➕ Гишүүн нэгдлээ", description=f"{member.mention} нэгдлээ, урилгын код тодорхойгүй.",
                                              color=INFO_COLOR, timestamp=datetime.datetime.now(datetime.timezone.utc))
                        embed.set_thumbnail(url=member.display_avatar.url)
                        await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"on_member_join error: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if not invite.guild: return
        if invite.guild.id not in self.invite_cache:
            self.invite_cache[invite.guild.id] = {}
        self.invite_cache[invite.guild.id][invite.code] = invite.uses
        cfg = await self.get_config(invite.guild.id)
        if cfg and cfg["enabled"]:
            channel = invite.guild.get_channel(cfg["channel_id"])
            if channel:
                embed = discord.Embed(
                    title="🔗 Урилга үүсгэгдлээ",
                    description=f"**Код:** `{invite.code}`\n**Үүсгэсэн:** {invite.inviter.mention if invite.inviter else 'Хүн биш'}",
                    color=GOLD_COLOR,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                await channel.send(embed=embed)

    async def cog_load(self):
        await self.init_db()

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))