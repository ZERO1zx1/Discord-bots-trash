import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import datetime
from typing import Optional
import asyncio
import time

EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

# ---------- Staff тохиргооны модал ----------
class AddStaffModal(ui.Modal, title="Staff нэмэх"):
    user_id = ui.TextInput(label="Хэрэглэгчийн ID", placeholder="123456789", required=True)
    group = ui.TextInput(label="Staff бүлэг", placeholder="Moderator", default="Moderator", required=True)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
        except ValueError:
            return await interaction.response.send_message("❌ ID тоо байх ёстой.", ephemeral=True)
        member = interaction.guild.get_member(uid)
        if not member:
            return await interaction.response.send_message("❌ Хэрэглэгч серверт байхгүй.", ephemeral=True)
        async with self.view.cog.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO staff_members (user_id, guild_id, staff_group) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, guild_id) DO UPDATE SET staff_group = ?",
                (str(uid), str(interaction.guild.id), self.group.value, self.group.value)
            )
            await conn.commit()
        await interaction.response.send_message(f"✅ {member.mention} **{self.group.value}** бүлэгт нэмэгдлээ.", ephemeral=True)

class RemoveStaffModal(ui.Modal, title="Staff хасах"):
    user_id = ui.TextInput(label="Хэрэглэгчийн ID", placeholder="123456789", required=True)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
        except ValueError:
            return await interaction.response.send_message("❌ ID тоо байх ёстой.", ephemeral=True)
        async with self.view.cog.bot.db.acquire() as conn:
            await conn.execute("DELETE FROM staff_members WHERE user_id=? AND guild_id=?",
                                  (str(uid), str(interaction.guild.id)))
            await conn.execute("DELETE FROM staff_activity WHERE user_id=? AND guild_id=?",
                                  (str(uid), str(interaction.guild.id)))
            await conn.commit()
        member = interaction.guild.get_member(uid)
        await interaction.response.send_message(f"✅ {member.mention if member else f'<@{uid}>'} Staff-ээс хасагдлаа.", ephemeral=True)

# ---------- Staff тохиргооны самбар (View) ----------
class StaffSetupView(ui.View):
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
        embed = await self.build_embed(interaction.guild)
        await interaction.edit_original_response(embed=embed, view=self)

    async def build_embed(self, guild):
        guild_id = str(guild.id)
        async with self.cog.bot.db.acquire() as conn:
            async with conn.execute("SELECT log_channel, announcement_channel, stats_channel FROM staff_config WHERE guild_id = ?", (guild_id,)) as cur:
                row = await cur.fetchone()
        log_ch = guild.get_channel(int(row[0])) if row and row[0] else None
        ann_ch = guild.get_channel(int(row[1])) if row and row[1] else None
        stats_ch = guild.get_channel(int(row[2])) if row and row[2] else None

        embed = discord.Embed(title="🛡️ Staff тохиргоо", color=INFO_COLOR)
        embed.add_field(name="📋 Лог суваг", value=log_ch.mention if log_ch else "Тохируулаагүй", inline=False)
        embed.add_field(name="🏆 Зарлалын суваг", value=ann_ch.mention if ann_ch else "Тохируулаагүй", inline=False)
        embed.add_field(name="📊 Статистик суваг", value=stats_ch.mention if stats_ch else "Тохируулаагүй", inline=False)
        embed.set_footer(text="Доорх сонголтуудаар тохиргоог өөрчилнө үү.")
        return embed

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📋 Лог суваг", row=0)
    async def select_log_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        await self.cog._set_config_field(interaction.guild_id, "log_channel", str(select.values[0].id))
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="🏆 Зарлалын суваг", row=1)
    async def select_announcement_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        await self.cog._set_config_field(interaction.guild_id, "announcement_channel", str(select.values[0].id))
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📊 Статистик суваг", row=2)
    async def select_stats_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        await self.cog._set_config_field(interaction.guild_id, "stats_channel", str(select.values[0].id))
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="➕ Staff нэмэх", style=discord.ButtonStyle.success, row=3)
    async def add_staff_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AddStaffModal(self))

    @ui.button(label="➖ Staff хасах", style=discord.ButtonStyle.danger, row=3)
    async def remove_staff_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RemoveStaffModal(self))

    @ui.button(label="📋 Staff жагсаалт", style=discord.ButtonStyle.secondary, row=3)
    async def list_staff_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild.id)
        async with self.cog.bot.db.acquire() as conn:
            async with conn.execute("SELECT user_id, staff_group FROM staff_members WHERE guild_id=? ORDER BY staff_group, user_id", (guild_id,)) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await interaction.followup.send("❌ Staff хоосон.", ephemeral=True)
        embed = discord.Embed(title="👥 Staff жагсаалт", color=INFO_COLOR)
        current_group = None
        text = ""
        for user_id, group in rows:
            if group != current_group:
                if text:
                    embed.add_field(name=f"**{current_group}**", value=text, inline=False)
                text = ""
                current_group = group
            member = interaction.guild.get_member(int(user_id))
            text += f"{member.mention if member else f'<@{user_id}>'} - `{user_id}`\n"
        if text:
            embed.add_field(name=f"**{current_group}**", value=text, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=4)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.refresh(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try: await self.message.edit(view=self)
            except Exception: pass

# ==================== ҮНДСЭН COG ====================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_times = {}
        self.weekly_task.start()
        self.leaderboard_task.start()

    async def cog_load(self):
        async with self.bot.db.acquire() as conn:
            await conn.execute('''CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                guild_id TEXT,
                moderator_id TEXT,
                reason TEXT,
                timestamp INTEGER
            )''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS staff_members (
                user_id TEXT,
                guild_id TEXT,
                staff_group TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS staff_activity (
                user_id TEXT,
                guild_id TEXT,
                messages INTEGER DEFAULT 0,
                voice_seconds INTEGER DEFAULT 0,
                tickets_closed INTEGER DEFAULT 0,
                actions INTEGER DEFAULT 0,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS staff_weekly_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                user_id TEXT,
                week_start DATE,
                kpi_score REAL,
                announced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS staff_config (
                guild_id TEXT PRIMARY KEY,
                log_channel TEXT,
                announcement_channel TEXT,
                stats_channel TEXT,
                leaderboard_message_id TEXT
            )''')
            # Хуучин хүснэгтэнд нэмэлт багана
            for col in ['log_channel', 'stats_channel', 'leaderboard_message_id']:
                try: await conn.execute(f"ALTER TABLE staff_config ADD COLUMN {col} TEXT")
                except Exception: pass
            await conn.commit()

    async def _set_config_field(self, guild_id: int, field: str, value: str):
        gid = str(guild_id)
        async with self.bot.db.acquire() as conn:
            # SQLite-д ON CONFLICT ... DO UPDATE
            await conn.execute(
                f"INSERT INTO staff_config (guild_id, {field}) VALUES (?, ?) "
                f"ON CONFLICT(guild_id) DO UPDATE SET {field} = ?",
                (gid, value, value)
            )
            await conn.commit()

    # ================== Долоо хоногийн шилдэг ==================
    @tasks.loop(seconds=30)
    async def weekly_task(self):
        now = datetime.datetime.utcnow()
        if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
            for guild in self.bot.guilds:
                await self.process_weekly_winner(guild)
            await asyncio.sleep(60)

    @weekly_task.before_loop
    async def before_weekly_task(self):
        await self.bot.wait_until_ready()

    async def process_weekly_winner(self, guild: discord.Guild):
        guild_id = str(guild.id)
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT sm.user_id, sa.messages, sa.voice_seconds, sa.tickets_closed, sa.actions "
                "FROM staff_members sm "
                "JOIN staff_activity sa ON sm.user_id = sa.user_id AND sm.guild_id = sa.guild_id "
                "WHERE sm.guild_id = ?",
                (guild_id,)
            ) as cur:
                rows = await cur.fetchall()

        if not rows: return

        scores = []
        for row in rows:
            user_id, messages, voice_seconds, tickets_closed, actions = row
            voice_hours = voice_seconds / 3600.0
            kpi = (messages * 0.1) + (tickets_closed * 5) + (actions * 3) + (voice_hours * 10)
            scores.append((user_id, kpi))

        if not scores: return

        top_user_id, top_score = max(scores, key=lambda x: x[1])
        week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())

        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO staff_weekly_winners (guild_id, user_id, week_start, kpi_score) VALUES (?, ?, ?, ?)",
                (guild_id, top_user_id, week_start, top_score)
            )
            await conn.execute("UPDATE staff_activity SET messages=0, voice_seconds=0, tickets_closed=0, actions=0 WHERE guild_id=?", (guild_id,))
            await conn.commit()

        channel = await self._get_configured_channel(guild, "announcement")
        if not channel:
            channel = discord.utils.get(guild.text_channels, name="mod-log")
        if not channel: return

        top_member = guild.get_member(int(top_user_id))
        top_name = top_member.display_name if top_member else f"<@{top_user_id}>"
        embed = discord.Embed(
            title="🏆 ДОЛОО ХОНОГИЙН ШИЛДЭГ STAFF",
            description=f"**{top_name}** энэ долоо хоногт хамгийн өндөр **{top_score:.1f} KPI оноо** цуглууллаа!",
            color=GOLD_COLOR
        )
        embed.add_field(name="📅 Долоо хоног", value=f"{week_start} - {week_start + datetime.timedelta(days=6)}")
        if top_member: embed.set_thumbnail(url=top_member.display_avatar.url)
        embed.set_footer(text="Дараагийн долоо хоногт та илүү хичээгээрэй!")
        await channel.send(embed=embed)

    # ================== Лидерборд автомат шинэчлэл ==================
    @tasks.loop(minutes=5)
    async def leaderboard_task(self):
        for guild in self.bot.guilds:
            await self.update_leaderboard(guild)

    @leaderboard_task.before_loop
    async def before_leaderboard_task(self):
        await self.bot.wait_until_ready()

    async def update_leaderboard(self, guild: discord.Guild):
        guild_id = str(guild.id)
        channel = await self._get_configured_channel(guild, "stats")
        if not channel: return

        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT sm.user_id, sm.staff_group, sa.messages, sa.voice_seconds, sa.tickets_closed, sa.actions "
                "FROM staff_members sm "
                "JOIN staff_activity sa ON sm.user_id = sa.user_id AND sm.guild_id = sa.guild_id "
                "WHERE sm.guild_id = ?",
                (guild_id,)
            ) as cur:
                rows = await cur.fetchall()

        scores = []
        for row in rows:
            user_id, group, messages, voice_seconds, tickets, actions = row
            voice_hours = voice_seconds / 3600.0
            kpi = (messages * 0.1) + (tickets * 5) + (actions * 3) + (voice_hours * 10)
            scores.append((user_id, group, kpi, messages, voice_hours, tickets, actions))
        scores.sort(key=lambda x: x[2], reverse=True)

        embed = discord.Embed(
            title="📊 **ДОЛОО ХОНОГИЙН STAFF ОНООНЫ ЭРЭМБЭ**",
            description=f"Шинэчлэгдсэн: {discord.utils.format_dt(datetime.datetime.now(), style='R')}",
            color=GOLD_COLOR
        )
        if scores:
            for rank, (user_id, group, kpi, msg, vh, tickets, actions) in enumerate(scores[:15], 1):
                member = guild.get_member(int(user_id))
                name = member.display_name if member else f"<@{user_id}>"
                embed.add_field(
                    name=f"#{rank} {name} ({group})",
                    value=f"⭐ **{kpi:.1f}** KPI | 💬 {msg} | 🎙️ {vh:.1f}ч | 🔨 {actions} | 🎫 {tickets}",
                    inline=False
                )
        else:
            embed.description = "Одоогоор Staff-ийн идэвх бүртгэгдээгүй байна."

        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT leaderboard_message_id FROM staff_config WHERE guild_id = ?", (guild_id,)) as cur:
                row = await cur.fetchone()

        if row and row[0]:
            try:
                msg_id = int(row[0])
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed)
                return
            except Exception: pass

        msg = await channel.send(embed=embed)
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO staff_config (guild_id, stats_channel, leaderboard_message_id) VALUES (?, ?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET stats_channel = ?, leaderboard_message_id = ?",
                (guild_id, str(channel.id), str(msg.id), str(channel.id), str(msg.id))
            )
            await conn.commit()

    # ================== Staff тохиргоо ==================
    @app_commands.command(name="staff_setup", description="Staff тохиргооны самбар нээх")
    @app_commands.default_permissions(administrator=True)
    async def staff_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = StaffSetupView(self, interaction.guild_id, interaction.user.id)
        embed = await view.build_embed(interaction.guild)
        msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = msg

    async def _get_configured_channel(self, guild: discord.Guild, channel_type: str):
        column = {"log": "log_channel", "announcement": "announcement_channel", "stats": "stats_channel"}[channel_type]
        async with self.bot.db.acquire() as conn:
            async with conn.execute(f"SELECT {column} FROM staff_config WHERE guild_id = ?", (str(guild.id),)) as cur:
                row = await cur.fetchone()
        if row and row[0]:
            return guild.get_channel(int(row[0]))
        return None

    # ================== Хэрэглэгчийн командууд ==================
    @app_commands.command(name="staff_counts", description="Долоо хоногийн Staff онооны эрэмбэ")
    async def staff_counts(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT sm.user_id, sm.staff_group, sa.messages, sa.voice_seconds, sa.tickets_closed, sa.actions "
                "FROM staff_members sm "
                "JOIN staff_activity sa ON sm.user_id = sa.user_id AND sm.guild_id = sa.guild_id "
                "WHERE sm.guild_id = ?",
                (guild_id,)
            ) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await interaction.response.send_message("❌ Одоогоор Staff-ийн идэвх бүртгэгдээгүй байна.", ephemeral=True)

        scores = []
        for row in rows:
            user_id, group, messages, voice_seconds, tickets, actions = row
            voice_hours = voice_seconds / 3600.0
            kpi = (messages * 0.1) + (tickets * 5) + (actions * 3) + (voice_hours * 10)
            scores.append((user_id, group, kpi, messages, voice_hours, tickets, actions))
        scores.sort(key=lambda x: x[2], reverse=True)

        embed = discord.Embed(title="📊 **ДОЛОО ХОНОГИЙН STAFF ОНООНЫ ЭРЭМБЭ**", color=GOLD_COLOR)
        for rank, (user_id, group, kpi, msg, vh, tickets, actions) in enumerate(scores[:15], 1):
            member = interaction.guild.get_member(int(user_id))
            name = member.display_name if member else f"<@{user_id}>"
            embed.add_field(
                name=f"#{rank} {name} ({group})",
                value=f"⭐ **{kpi:.1f}** KPI оноо\n💬 {msg} мессеж | 🎙️ {vh:.1f} цаг | 🔨 {actions} арга хэмжээ | 🎫 {tickets} тикет",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="staff_status", description="Тухайн Staff-ийн дэлгэрэнгүй үзүүлэлт")
    @app_commands.describe(member="Харах Staff гишүүн")
    async def staff_status(self, interaction: discord.Interaction, member: discord.Member):
        guild_id = str(interaction.guild.id)
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT staff_group FROM staff_members WHERE user_id=? AND guild_id=?", (str(member.id), guild_id)) as cur:
                staff_row = await cur.fetchone()
            if not staff_row:
                return await interaction.response.send_message(f"❌ {member.mention} нь Staff-д бүртгэлтэй биш байна.", ephemeral=True)
            group = staff_row[0]

            async with conn.execute("SELECT messages, voice_seconds, tickets_closed, actions FROM staff_activity WHERE user_id=? AND guild_id=?", (str(member.id), guild_id)) as cur:
                activity_row = await cur.fetchone()
            if not activity_row:
                return await interaction.response.send_message(f"ℹ️ {member.mention} идэвхийн мэдээлэл олдсонгүй.", ephemeral=True)
            messages, voice_seconds, tickets, actions = activity_row

        voice_hours = voice_seconds / 3600.0
        kpi = (messages * 0.1) + (tickets * 5) + (actions * 3) + (voice_hours * 10)

        embed = discord.Embed(title=f"🔍 **{member.display_name}** STAFF МЭДЭЭЛЭЛ", color=INFO_COLOR)
        embed.add_field(name="👥 Бүлэг", value=group, inline=True)
        embed.add_field(name="🟢 Төлөв", value="Идэвхтэй" if member.status != discord.Status.offline else "Чөлөөтэй", inline=True)
        embed.add_field(name="💬 Мессеж", value=messages, inline=True)
        embed.add_field(name="🎙️ Дуут цаг", value=f"{voice_hours:.1f} цаг ({voice_seconds} сек)", inline=True)
        embed.add_field(name="🔨 Арга хэмжээ", value=actions, inline=True)
        embed.add_field(name="🎫 Тикет", value=tickets, inline=True)
        embed.add_field(name="⭐ KPI оноо", value=f"**{kpi:.1f}**", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ================== Идэвх бүртгэл ==================
    async def increment_staff_activity(self, user_id: int, guild_id: int, field: str, amount=1):
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT 1 FROM staff_members WHERE user_id=? AND guild_id=?", (str(user_id), str(guild_id))) as cur:
                if not await cur.fetchone():
                    return
            # Мөр байхгүй бол үүсгэх
            await conn.execute("INSERT OR IGNORE INTO staff_activity (user_id, guild_id) VALUES (?, ?)", (str(user_id), str(guild_id)))
            if field == "voice_seconds":
                await conn.execute("UPDATE staff_activity SET voice_seconds = voice_seconds + ? WHERE user_id=? AND guild_id=?",
                                      (amount, str(user_id), str(guild_id)))
            else:
                await conn.execute(f"UPDATE staff_activity SET {field} = {field} + ? WHERE user_id=? AND guild_id=?",
                                      (amount, str(user_id), str(guild_id)))
            await conn.commit()

    async def add_staff_action(self, user_id: int, guild_id: int):
        await self.increment_staff_activity(user_id, guild_id, "actions")

    async def add_ticket_closed(self, user_id: int, guild_id: int):
        await self.increment_staff_activity(user_id, guild_id, "tickets_closed")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        await self.increment_staff_activity(message.author.id, message.guild.id, "messages")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        guild_id = member.guild.id
        user_id = member.id
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT 1 FROM staff_members WHERE user_id=? AND guild_id=?", (str(user_id), str(guild_id))) as cur:
                if not await cur.fetchone():
                    return
        now = time.time()
        if before.channel is None and after.channel is not None:
            if not after.self_mute and not after.deaf:
                self.voice_times[user_id] = now
        elif before.channel is not None and after.channel is None:
            if user_id in self.voice_times:
                elapsed = now - self.voice_times[user_id]
                await self.increment_staff_activity(user_id, guild_id, "voice_seconds", int(elapsed))
                del self.voice_times[user_id]
        elif before.channel == after.channel:
            was_muted = before.self_mute or before.deaf
            now_muted = after.self_mute or after.deaf
            if not was_muted and now_muted:
                if user_id in self.voice_times:
                    elapsed = now - self.voice_times[user_id]
                    await self.increment_staff_activity(user_id, guild_id, "voice_seconds", int(elapsed))
                    del self.voice_times[user_id]
            elif was_muted and not now_muted:
                if after.channel is not None:
                    self.voice_times[user_id] = now

    # ================== Лог илгээх ==================
    async def log_to_mod_channel(self, guild, action, target, moderator, reason):
        channel = await self._get_configured_channel(guild, "log")
        if not channel:
            channel = discord.utils.get(guild.text_channels, name="mod-log")
        if not channel: return
        embed = discord.Embed(
            title=f"🛠️ **{action}**",
            description=f"**Хэрэглэгч:** {target.mention if hasattr(target, 'mention') else target}\n"
                        f"**Модератор:** {moderator.mention}\n"
                        f"**Шалтгаан:** {reason or 'Тодорхойгүй'}",
            timestamp=datetime.datetime.now(),
            color=EMBED_COLOR
        )
        if hasattr(target, 'display_avatar'):
            embed.set_thumbnail(url=target.display_avatar.url)
        await channel.send(embed=embed)

    # ================== МОДЕРАЦИОННЫЕ КОМАНДЫ ==================
    @commands.hybrid_command(name='lock', with_app_command=True, description="Сувгийг түгжих")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(channel="Түгжих суваг (хоосон бол одоогийн суваг)", reason="Шалтгаан")
    async def lock(self, ctx, channel: Optional[discord.TextChannel] = None, *, reason: str = "Тодорхойгүй"):
        target_channel = channel or ctx.channel
        await ctx.defer(ephemeral=False)
        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send("❌ Ботод `Manage Channels` зөвшөөрөл байхгүй!", ephemeral=True)
        overwrite = target_channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await target_channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="🔒 СУВАГ ТҮГЖИГДЛЭЭ", description=f"{target_channel.mention} түгжигдлээ.\n**Шалтгаан:** {reason}\n**Түгжсэн:** {ctx.author.mention}", color=WARNING_COLOR)
        await ctx.send(embed=embed)
        await self.log_to_mod_channel(ctx.guild, "Lock", target_channel, ctx.author, reason)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='unlock', with_app_command=True, description="Сувгийн түгжээг тайлах")
    @commands.has_permissions(manage_channels=True)
    @app_commands.describe(channel="Нээх суваг (хоосон бол одоогийн суваг)", reason="Шалтгаан")
    async def unlock(self, ctx, channel: Optional[discord.TextChannel] = None, *, reason: str = "Тодорхойгүй"):
        target_channel = channel or ctx.channel
        await ctx.defer(ephemeral=False)
        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send("❌ Ботод `Manage Channels` зөвшөөрөл байхгүй!", ephemeral=True)
        overwrite = target_channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await target_channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="🔓 СУВАГ НЭЭГДЛЭЭ", description=f"{target_channel.mention} нээгдлээ.\n**Шалтгаан:** {reason}\n**Нээсэн:** {ctx.author.mention}", color=SUCCESS_COLOR)
        await ctx.send(embed=embed)
        await self.log_to_mod_channel(ctx.guild, "Unlock", target_channel, ctx.author, reason)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='kick', with_app_command=True, description="Хэрэглэгчийг хөөх")
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(member="Хөөх хэрэглэгч", reason="Шалтгаан")
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Шалтгаан тодорхойгүй"):
        await ctx.defer(ephemeral=False)
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.send("❌ Ботод `Kick Members` зөвшөөрөл байхгүй!", ephemeral=True)
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ Та энэ хэрэглэгчийг хөөх эрхгүй!", ephemeral=True)
        await member.kick(reason=reason)
        embed = discord.Embed(title="👢 ХАСАГДЛАА", description=f"{member.mention} хасагдлаа.", color=SUCCESS_COLOR)
        embed.add_field(name="📝 Шалтгаан", value=f"```fix\n{reason}```", inline=False)
        embed.add_field(name="👮 Гүйцэтгэсэн", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await self.log_to_mod_channel(ctx.guild, "Kick", member, ctx.author, reason)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='ban', with_app_command=True, description="Хэрэглэгчийг бан хийх")
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(member="Бан хийх хэрэглэгч", reason="Шалтгаан")
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Шалтгаан тодорхойгүй"):
        await ctx.defer(ephemeral=False)
        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.send("❌ Ботод `Ban Members` зөвшөөрөл байхгүй!", ephemeral=True)
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ Та энэ хэрэглэгчийг баних эрхгүй!", ephemeral=True)
        await member.ban(reason=reason)
        embed = discord.Embed(title="🔨 БАН ХИЙГДЛЭЭ", description=f"{member.mention} бан хийгдлээ.", color=ERROR_COLOR)
        embed.add_field(name="📝 Шалтгаан", value=f"```fix\n{reason}```", inline=False)
        embed.add_field(name="👮 Гүйцэтгэсэн", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await self.log_to_mod_channel(ctx.guild, "Ban", member, ctx.author, reason)
        await self.add_staff_action(ctx.author.id, ctx.guild.id)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='unban', with_app_command=True, description="Бан цуцлах")
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(user_id="Хэрэглэгчийн ID (тоо)", reason="Шалтгаан")
    async def unban(self, ctx, user_id: str, *, reason: str = "Шалтгаан тодорхойгүй"):
        await ctx.defer(ephemeral=False)
        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.send("❌ Ботод `Ban Members` зөвшөөрөл байхгүй!", ephemeral=True)
        try:
            user_id_int = int(user_id)
            user = await self.bot.fetch_user(user_id_int)
            await ctx.guild.unban(user, reason=reason)
        except ValueError:
            return await ctx.send("❌ ID нь тоо байх ёстой!", ephemeral=True)
        except discord.NotFound:
            return await ctx.send("❌ Энэ серверт ийм ID-тай хэрэглэгч бандаагүй.", ephemeral=True)
        embed = discord.Embed(title="🔓 БАН ЦУЦЛАГДЛАА", description=f"{user.mention} (ID:{user_id}) бан цуцлагдлаа.", color=SUCCESS_COLOR)
        embed.add_field(name="📝 Шалтгаан", value=f"```fix\n{reason}```", inline=False)
        embed.add_field(name="👮 Гүйцэтгэсэн", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
        await self.log_to_mod_channel(ctx.guild, "Unban", user, ctx.author, reason)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='banlist', with_app_command=True, description="Бан хийгдсэн хэрэглэгчдийн жагсаалт")
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx):
        await ctx.defer(ephemeral=False)
        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.send("❌ Ботод `Ban Members` зөвшөөрөл байхгүй!", ephemeral=True)
        bans = [entry async for entry in ctx.guild.bans()]
        if not bans:
            return await ctx.send("🚫 Бан хийгдсэн хэрэглэгч байхгүй.", ephemeral=True)
        embed = discord.Embed(title=f"🚫 {ctx.guild.name} -ИЙН БАН ЖАГСААЛТ", description=f"Нийт {len(bans)} хэрэглэгч", color=ERROR_COLOR)
        for entry in bans[:20]:
            embed.add_field(name=f"👤 {entry.user.name}", value=f"🆔 `{entry.user.id}`\n📝 Шалтгаан: `{entry.reason or 'Тодорхойгүй'}`", inline=False)
        if len(bans) > 20:
            embed.set_footer(text=f"+ {len(bans)-20} бусад...")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='clear', aliases=['purge'], with_app_command=True, description="Мессеж устгах")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(amount="Устгах мессежийн тоо (1-100)")
    async def clear(self, ctx, amount: int):
        await ctx.defer(ephemeral=True)
        if amount < 1 or amount > 100:
            return await ctx.send("❌ 1-100 хооронд тоо оруулна уу.", ephemeral=True)
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.send("❌ Танд `Manage Messages` зөвшөөрөл байхгүй!", ephemeral=True)
        if not ctx.guild.me.guild_permissions.manage_messages:
            return await ctx.send("❌ Ботод `Manage Messages` зөвшөөрөл байхгүй!", ephemeral=True)
        try:
            deleted = await ctx.channel.purge(limit=amount)
        except Exception as e:
            return await ctx.send(f"❌ Алдаа: {e}", ephemeral=True)
        embed = discord.Embed(title="🗑️ МЕССЭЖ УСТГАГДЛАА", description=f"✅ {len(deleted)} мессэж устгагдсан.", color=SUCCESS_COLOR)
        embed.add_field(name="📍 Суваг", value=ctx.channel.mention, inline=True)
        embed.add_field(name="👮 Гүйцэтгэсэн", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed, ephemeral=True)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='timeout', with_app_command=True, description="Хэрэглэгчийг түр хаах")
    @commands.has_permissions(moderate_members=True)
    @app_commands.choices(duration=[
        app_commands.Choice(name="30 секунд", value="30s"),
        app_commands.Choice(name="1 минут", value="1m"),
        app_commands.Choice(name="5 минут", value="5m"),
        app_commands.Choice(name="10 минут", value="10m"),
        app_commands.Choice(name="30 минут", value="30m"),
        app_commands.Choice(name="1 цаг", value="1h"),
        app_commands.Choice(name="3 цаг", value="3h"),
        app_commands.Choice(name="6 цаг", value="6h"),
        app_commands.Choice(name="12 цаг", value="12h"),
        app_commands.Choice(name="1 өдөр", value="1d"),
        app_commands.Choice(name="3 өдөр", value="3d"),
        app_commands.Choice(name="7 өдөр", value="7d"),
    ])
    @app_commands.describe(member="Түр хаах хэрэглэгч", duration="Хугацаа", reason="Шалтгаан")
    async def timeout(self, ctx, member: discord.Member, duration: str, *, reason: str = "Шалтгаан тодорхойгүй"):
        await ctx.defer(ephemeral=False)
        if not ctx.guild.me.guild_permissions.moderate_members:
            return await ctx.send("❌ Ботод `Moderate Members` зөвшөөрөл байхгүй!", ephemeral=True)
        duration_map = {
            "30s":30,"1m":60,"5m":300,"10m":600,"30m":1800,
            "1h":3600,"3h":10800,"6h":21600,"12h":43200,
            "1d":86400,"3d":259200,"7d":604800
        }
        seconds = duration_map.get(duration.lower())
        if seconds is None:
            return await ctx.send("❌ Хүчингүй хугацаа.", ephemeral=True)
        if seconds > 2419200:
            return await ctx.send("❌ Хамгийн их хугацаа 28 хоног.", ephemeral=True)
        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason=reason)
        except discord.Forbidden:
            return await ctx.send("❌ Ботод эрх хүрэхгүй.", ephemeral=True)
        embed = discord.Embed(title="⏲️ ТҮР ХААГДЛАА", description=f"{member.mention} **{duration}** хугацаагаар түр хаагдлаа.", color=WARNING_COLOR)
        embed.add_field(name="⏱️ Хугацаа", value=f"```fix\n{duration}```", inline=True)
        embed.add_field(name="📝 Шалтгаан", value=f"```fix\n{reason}```", inline=True)
        embed.add_field(name="👮 Гүйцэтгэсэн", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await self.log_to_mod_channel(ctx.guild, "Timeout", member, ctx.author, reason)
        await self.add_staff_action(ctx.author.id, ctx.guild.id)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='untimeout', aliases=['unmute'], with_app_command=True, description="Түр хаалтыг цуцлах")
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(member="Түр хаалтыг цуцлах хэрэглэгч")
    async def untimeout(self, ctx, member: discord.Member):
        await ctx.defer(ephemeral=False)
        if not ctx.guild.me.guild_permissions.moderate_members:
            return await ctx.send("❌ Ботод `Moderate Members` зөвшөөрөл байхгүй!", ephemeral=True)
        if member.is_timed_out():
            await member.timeout(None, reason=f"Хүсэлт гаргасан: {ctx.author}")
            embed = discord.Embed(title="🔊 ТҮР ХААЛТ ЦУЦЛАГДЛАА", description=f"{member.mention} timeout арилгалаа.", color=SUCCESS_COLOR)
            embed.add_field(name="👮 Гүйцэтгэсэн", value=ctx.author.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            await self.log_to_mod_channel(ctx.guild, "Untimeout", member, ctx.author, "Хугацаанаас өмнө арилгасан")
            quests_cog = self.bot.get_cog("Quests")
            if quests_cog:
                try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
                except Exception: pass
        else:
            await ctx.send(f"ℹ️ {member.mention} timeout төлөвт байхгүй.", ephemeral=True)

    @commands.hybrid_command(name='warn', with_app_command=True, description="Анхааруулга өгөх")
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(member="Анхааруулга өгөх хэрэглэгч", reason="Шалтгаан")
    async def warn(self, ctx, member: discord.Member, *, reason: str):
        await ctx.defer(ephemeral=False)
        now_ts = int(datetime.datetime.now().timestamp())
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO warnings (user_id, guild_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
                (str(member.id), str(ctx.guild.id), str(ctx.author.id), reason, now_ts)
            )
            await conn.commit()
        warn_count = await self.get_warn_count(member.id, ctx.guild.id)
        embed = discord.Embed(title="⚠️ АНХААРУУЛГА ӨГЛӨӨ", description=f"{member.mention} -д анхааруулга өглөө.", color=WARNING_COLOR)
        embed.add_field(name="📝 Шалтгаан", value=f"```fix\n{reason}```", inline=False)
        embed.add_field(name="👮 Гүйцэтгэсэн", value=ctx.author.mention, inline=True)
        embed.add_field(name="⚠️ НИЙТ АНХААРУУЛГА", value=f"```yaml\n{warn_count}```", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await self.log_to_mod_channel(ctx.guild, "Warn", member, ctx.author, reason)
        await self.add_staff_action(ctx.author.id, ctx.guild.id)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='unwarn', with_app_command=True, description="Анхааруулгыг устгах")
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(warning_id="Устгах анхааруулгын ID")
    async def unwarn(self, ctx, warning_id: int):
        await ctx.defer(ephemeral=False)
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT user_id, moderator_id, reason FROM warnings WHERE id=? AND guild_id=?", (warning_id, str(ctx.guild.id))) as cur:
                row = await cur.fetchone()
        if not row:
            return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description=f"`{warning_id}` ID-тай анхааруулга олдсонгүй.", color=ERROR_COLOR))
        user_id, mod_id, reason = row
        async with self.bot.db.acquire() as conn:
            await conn.execute("DELETE FROM warnings WHERE id=?", (warning_id,))
            await conn.commit()
        user = ctx.guild.get_member(int(user_id))
        user_mention = user.mention if user else f"<@{user_id}>"
        mod = ctx.guild.get_member(int(mod_id))
        mod_name = mod.name if mod else f"ID: {mod_id}"
        embed = discord.Embed(
            title="✅ АНХААРУУЛГА УСТГАГДЛАА",
            description=f"**Хэрэглэгч:** {user_mention}\n**ID:** `#{warning_id}`\n**Шалтгаан:** {reason}\n**Өгсөн модератор:** {mod_name}",
            color=SUCCESS_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Устгасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        await self.log_to_mod_channel(ctx.guild, "Unwarn", user_mention, ctx.author, f"Анхааруулга #{warning_id} устгасан")
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            try: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "mod_action", 1)
            except Exception: pass

    @commands.hybrid_command(name='warnings', with_app_command=True, description="Хэрэглэгчийн анхааруулгыг харах")
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(member="Анхааруулгыг харах хэрэглэгч")
    async def warnings(self, ctx, member: discord.Member):
        await ctx.defer(ephemeral=False)
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT id, moderator_id, reason, timestamp FROM warnings WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC", (str(member.id), str(ctx.guild.id))) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await ctx.send(f"📋 {member.mention} -д анхааруулга байхгүй.", ephemeral=True)
        embed = discord.Embed(title=f"📋 **{member.display_name} -ИЙН АНХААРУУЛГУУД**", description=f"Нийт {len(rows)} анхааруулга", color=WARNING_COLOR)
        embed.set_thumbnail(url=member.display_avatar.url)
        for i, (wid, mod_id, reason, ts) in enumerate(rows[:10], 1):
            ts_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            try:
                mod = await self.bot.fetch_user(int(mod_id))
                mod_name = mod.name
            except Exception:
                mod_name = "Тодорхойгүй"
            embed.add_field(name=f"#{wid} | {ts_str}", value=f"👮 Модератор: `{mod_name}`\n📝 Шалтгаан: `{reason}`", inline=False)
        if len(rows) > 10:
            embed.set_footer(text=f"+ {len(rows)-10} бусад...")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='warnedusers', aliases=['warnlist'], with_app_command=True, description="Анхааруулга авсан хэрэглэгчдийн жагсаалт")
    @commands.has_permissions(kick_members=True)
    async def warned_users(self, ctx):
        await ctx.defer(ephemeral=False)
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT user_id, COUNT(*) as cnt, MAX(timestamp) as last FROM warnings WHERE guild_id=? GROUP BY user_id ORDER BY cnt DESC LIMIT 50", (str(ctx.guild.id),)) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await ctx.send("⚠️ Анхааруулга авсан хэрэглэгч байхгүй.", ephemeral=True)
        embed = discord.Embed(title="⚠️ АНХААРУУЛГА АВСАН ХЭРЭГЛЭГЧИД", color=WARNING_COLOR)
        for user_id, cnt, last_ts in rows[:20]:
            last_str = datetime.datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d %H:%M:%S")
            try:
                user = await self.bot.fetch_user(int(user_id))
                name = user.name
            except Exception:
                name = "Тодорхойгүй"
            embed.add_field(name=f"👤 {name}", value=f"🆔 ID: `{user_id}`\n⚠️ Анхааруулга: **{cnt}**\n📅 Сүүлийн: `{last_str}`", inline=False)
        embed.set_footer(text="Хамгийн их 20 хэрэглэгч")
        await ctx.send(embed=embed)

    async def get_warn_count(self, user_id, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT COUNT(*) FROM warnings WHERE user_id=? AND guild_id=?", (str(user_id), str(guild_id))) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

async def setup(bot):
    await bot.add_cog(Moderation(bot))