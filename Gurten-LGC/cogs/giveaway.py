import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import random
import re
from typing import Optional

# ===== COLOR SCHEME =====
EMBED_COLOR   = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR   = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x89b4fa
# =============================

COLOR_CHOICES = [
    app_commands.Choice(name="🟡 Алтан (анхдагч)", value="gold"),
    app_commands.Choice(name="🔵 Хөх", value="blue"),
    app_commands.Choice(name="🔴 Улаан", value="red"),
    app_commands.Choice(name="🟢 Ногоон", value="green"),
    app_commands.Choice(name="🟣 Ягаан", value="purple"),
    app_commands.Choice(name="⚫ Бараан", value="dark"),
    app_commands.Choice(name="⚪ Саарал", value="grey"),
]

COLOR_MAP = {
    "gold":   GOLD_COLOR,
    "blue":   INFO_COLOR,
    "red":    ERROR_COLOR,
    "green":  SUCCESS_COLOR,
    "purple": 0xcba6f7,
    "dark":   EMBED_COLOR,
    "grey":   0x6c7086,
}


class GiveawayEnterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Оролцох", style=discord.ButtonStyle.success, custom_id="giveaway_enter")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway = await interaction.client.db.fetchone(
            "SELECT id, prize, end_time, required_role_id, ended FROM giveaways WHERE message_id = ?",
            interaction.message.id
        )

        if not giveaway:
            await interaction.response.send_message("❌ Энэ giveaway олдсонгүй.", ephemeral=True)
            return

        gid, prize, end_time, req_role_id, ended = giveaway

        if ended:
            await interaction.response.send_message("❌ Энэ giveaway аль хэдийн дууссан.", ephemeral=True)
            return

        if datetime.datetime.now(datetime.timezone.utc).timestamp() >= end_time:
            await interaction.response.send_message("❌ Энэ giveaway дууссан байна.", ephemeral=True)
            return

        if req_role_id:
            role = interaction.guild.get_role(req_role_id)
            if role and role not in interaction.user.roles:
                await interaction.response.send_message(f"❌ Танд {role.mention} роль байхгүй.", ephemeral=True)
                return

        existing = await interaction.client.db.fetchone(
            "SELECT 1 FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
            gid, str(interaction.user.id)
        )
        if existing:
            await interaction.response.send_message("⚠️ Та аль хэдийн оролцсон!", ephemeral=True)
            return

        await interaction.client.db.execute(
            "INSERT INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
            gid, str(interaction.user.id)
        )
        await interaction.client.db.commit()  # чухал commit
        await interaction.response.send_message("✅ Амжилттай оролцлоо! Амжилт хүсье 🎉", ephemeral=True)


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_check.start()

    def cog_unload(self):
        self.giveaway_check.cancel()

    async def init_db(self):
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            message_id INTEGER,
            prize TEXT,
            winner_count INTEGER,
            end_time INTEGER,
            host_id INTEGER,
            required_role_id INTEGER DEFAULT NULL,
            ended INTEGER DEFAULT 0
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS giveaway_entries (
            giveaway_id INTEGER,
            user_id TEXT,
            PRIMARY KEY (giveaway_id, user_id)
        )''')
        await self.bot.db.commit()

    async def cog_load(self):
        await self.init_db()
        self.bot.add_view(GiveawayEnterView())

    def parse_duration(self, duration: str) -> int:
        match = re.match(r"(\d+)\s*([smhdw])", duration.lower())
        if not match:
            return None
        value = int(match.group(1))
        unit = match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return value * multipliers.get(unit, 1)

    async def get_entries(self, giveaway_id: int, required_role_id: int, guild: discord.Guild):
        rows = await self.bot.db.fetch(
            "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", giveaway_id
        )
        entries = [uid for (uid,) in rows]
        if required_role_id:
            role = guild.get_role(required_role_id)
            if role:
                entries = [uid for uid in entries if (member := guild.get_member(int(uid))) and role in member.roles]
        return entries

    async def finish_giveaway(self, message: discord.Message, giveaway_id: int, winners: list, prize: str, host: discord.Member):
        winner_mentions = " ".join(f"<@{uid}>" for uid in winners)
        embed = discord.Embed(
            title="🎉 **GIVEAWAY ДУУСЛАА** 🎉",
            description=f"**Шагнал:** {prize}\n**Ялагч(ид):** {winner_mentions}\n**Зохион байгуулагч:** {host.mention}",
            color=SUCCESS_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await message.edit(embed=embed, view=None)
        await message.channel.send(embed=embed)

        await self.bot.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", giveaway_id)
        await self.bot.db.commit()

    async def _get_giveaway_by_message(self, message_id: int):
        return await self.bot.db.fetchone(
            "SELECT id, channel_id, message_id, prize, winner_count, host_id, required_role_id, ended, end_time, guild_id FROM giveaways WHERE message_id = ?",
            message_id
        )

    # ==================== ГРУП КОМАНД ====================
    @commands.hybrid_group(name='giveaway', description="Giveaway командууд", with_app_command=True, invoke_without_command=True)
    @app_commands.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx):
        embed = discord.Embed(
            title="🎁 Giveaway Командууд",
            description=(
                "`/giveaway create` – Giveaway үүсгэх\n"
                "`/giveaway end` – Giveaway-г хугацаанаас өмнө дуусгах\n"
                "`/giveaway reroll` – Ялагчдыг дахин сонгох\n"
                "`/giveaway list` – Идэвхтэй giveaway-үүд\n"
                "`/giveaway cancel` – Giveaway-г цуцлах\n"
                "`/giveaway entries` – Оролцогчдын тоо"
            ),
            color=INFO_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    @giveaway.command(name='create', description="Giveaway үүсгэх", with_app_command=True)
    @app_commands.describe(
        channel="Giveaway илгээх суваг",
        duration="Үргэлжлэх хугацаа (жишээ: 1h, 30m, 2d, 1w)",
        winners="Ялагчдын тоо",
        prize="Шагналын нэр",
        title="Embed гарчиг (заавал биш, анхдагч: 🎉 GIVEAWAY 🎉)",
        required_role="Оролцоход шаардлагатай роль (заавал биш)",
        color="Embed өнгө (анхдагч: алтан)"
    )
    @app_commands.choices(color=COLOR_CHOICES)
    @app_commands.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def create_giveaway(
        self, ctx,
        channel: discord.TextChannel,
        duration: str,
        winners: int,
        prize: str,
        title: Optional[str] = None,
        required_role: Optional[discord.Role] = None,
        color: Optional[str] = None
    ):
        await ctx.defer(ephemeral=False)

        if winners < 1:
            return await ctx.send(embed=discord.Embed(title="❌ Буруу утга", description="Ялагчдын тоо 1-ээс бага байж болохгүй.", color=ERROR_COLOR))
        if not prize.strip():
            return await ctx.send(embed=discord.Embed(title="❌ Буруу утга", description="Шагнал хоосон байж болохгүй.", color=ERROR_COLOR))

        seconds = self.parse_duration(duration)
        if seconds is None:
            return await ctx.send(embed=discord.Embed(title="❌ Буруу хугацаа", description="Формат: `10s`, `5m`, `2h`, `1d`, `1w`", color=ERROR_COLOR))

        embed_color = COLOR_MAP.get(color, GOLD_COLOR)
        embed_title = title if title else "🎉 **GIVEAWAY** 🎉"

        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
        end_timestamp = int(end_time.timestamp())

        embed = discord.Embed(
            title=embed_title,
            description=(
                f"**Шагнал:** {prize}\n"
                f"**Ялагчдын тоо:** {winners}\n"
                f"**Зохион байгуулагч:** {ctx.author.mention}\n"
                f"**Дуусах:** <t:{end_timestamp}:R>"
            ),
            color=embed_color
        )
        if required_role:
            embed.description += f"\n**Шаардлагатай роль:** {required_role.mention}"

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"{ctx.guild.name} | {ctx.author.display_name}")
        embed.timestamp = end_time

        view = GiveawayEnterView()
        message = await channel.send(embed=embed, view=view)

        await self.bot.db.execute(
            "INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winner_count, end_time, host_id, required_role_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ctx.guild.id, channel.id, message.id, prize, winners, end_timestamp, ctx.author.id,
            required_role.id if required_role else None
        )
        await self.bot.db.commit()

        await ctx.send(f"✅ Giveaway {channel.mention} сувагт үүслээ! Дуусах: {discord.utils.format_dt(end_time, 'R')}")

    @giveaway.command(name='end', description="Giveaway дуусгах", with_app_command=True)
    @app_commands.describe(message_id="Дуусгах giveaway мессежийн ID")
    @app_commands.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def end_giveaway(self, ctx, message_id: int):
        await ctx.defer(ephemeral=False)
        giveaway = await self._get_giveaway_by_message(message_id)
        if not giveaway:
            return await ctx.send(embed=discord.Embed(title="❌ Giveaway олдсонгүй.", color=ERROR_COLOR))
        if giveaway[7]:
            return await ctx.send(embed=discord.Embed(title="❌ Giveaway аль хэдийн дууссан.", color=ERROR_COLOR))

        gid, channel_id, msg_id, prize, winner_count, host_id, req_role_id, ended, end_time, guild_id = giveaway

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send(embed=discord.Embed(title="❌ Суваг олдсонгүй.", color=ERROR_COLOR))
        try:
            message = await channel.fetch_message(msg_id)
        except:
            return await ctx.send(embed=discord.Embed(title="❌ Мессеж олдсонгүй.", color=ERROR_COLOR))

        entries = await self.get_entries(gid, req_role_id, ctx.guild)
        if not entries:
            return await ctx.send(embed=discord.Embed(title="❌ Оролцогч байхгүй.", color=ERROR_COLOR))

        winners = random.sample(entries, min(winner_count, len(entries)))
        await self.finish_giveaway(message, gid, winners, prize, ctx.author)

    @giveaway.command(name='reroll', description="Giveaway дахин сонгох", with_app_command=True)
    @app_commands.describe(message_id="Дахин сонгох giveaway мессежийн ID")
    @app_commands.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def reroll_giveaway(self, ctx, message_id: int):
        await ctx.defer(ephemeral=False)
        giveaway = await self._get_giveaway_by_message(message_id)
        if not giveaway:
            return await ctx.send(embed=discord.Embed(title="❌ Giveaway олдсонгүй.", color=ERROR_COLOR))
        if not giveaway[7]:
            return await ctx.send(embed=discord.Embed(title="❌ Giveaway дуусаагүй байна. Эхлээд дуусгах хэрэгтэй.", color=ERROR_COLOR))

        gid, channel_id, msg_id, prize, winner_count, host_id, req_role_id, ended, end_time, guild_id = giveaway

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send(embed=discord.Embed(title="❌ Суваг олдсонгүй.", color=ERROR_COLOR))
        try:
            await channel.fetch_message(msg_id)
        except:
            return await ctx.send(embed=discord.Embed(title="❌ Мессеж олдсонгүй.", color=ERROR_COLOR))

        entries = await self.get_entries(gid, req_role_id, ctx.guild)
        if not entries:
            return await ctx.send(embed=discord.Embed(title="❌ Дахин сонгох оролцогч байхгүй.", color=ERROR_COLOR))

        new_winners = random.sample(entries, min(winner_count, len(entries)))
        winner_mentions = " ".join(f"<@{uid}>" for uid in new_winners)
        embed = discord.Embed(
            title="🎉 **GIVEAWAY ДАХИН СОНГОГДЛОО** 🎉",
            description=f"**Шагнал:** {prize}\n**Шинэ ялагч(ид):** {winner_mentions}\n**Дахин сонгосон:** {ctx.author.mention}",
            color=GOLD_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)
        await ctx.send(f"✅ {message_id} giveaway-н ялагчид дахин сонгогдлоо.")

    @giveaway.command(name='cancel', description="Giveaway цуцлах", with_app_command=True)
    @app_commands.describe(message_id="Цуцлах giveaway мессежийн ID")
    @app_commands.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def cancel_giveaway(self, ctx, message_id: int):
        await ctx.defer(ephemeral=False)
        giveaway = await self._get_giveaway_by_message(message_id)
        if not giveaway:
            return await ctx.send(embed=discord.Embed(title="❌ Giveaway олдсонгүй.", color=ERROR_COLOR))
        if giveaway[7]:
            return await ctx.send(embed=discord.Embed(title="❌ Giveaway аль хэдийн дууссан эсвэл цуцлагдсан.", color=ERROR_COLOR))

        gid, channel_id, msg_id, prize, winner_count, host_id, req_role_id, ended, end_time, guild_id = giveaway

        channel = self.bot.get_channel(channel_id)
        if channel:
            try:
                message = await channel.fetch_message(msg_id)
                embed = discord.Embed(
                    title="❌ **GIVEAWAY ЦУЦЛАГДЛАА**",
                    description=f"**Шагнал:** {prize}\n**Зохион байгуулагч:** <@{host_id}>\n**Цуцалсан:** {ctx.author.mention}",
                    color=ERROR_COLOR
                )
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                embed.timestamp = discord.utils.utcnow()
                await message.edit(embed=embed, view=None)
            except:
                pass

        await self.bot.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", gid)
        await self.bot.db.commit()
        await ctx.send(f"✅ Giveaway (ID: {message_id}) цуцлагдлаа.")

    @giveaway.command(name='entries', description="Оролцогчдын тоог харах", with_app_command=True)
    @app_commands.describe(message_id="Оролцогчдын тоог харах giveaway мессежийн ID")
    @app_commands.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def entries_giveaway(self, ctx, message_id: int):
        await ctx.defer(ephemeral=True)
        giveaway = await self._get_giveaway_by_message(message_id)
        if not giveaway:
            return await ctx.send(embed=discord.Embed(title="❌ Giveaway олдсонгүй.", color=ERROR_COLOR), ephemeral=True)

        gid = giveaway[0]
        req_role_id = giveaway[6]
        entries = await self.get_entries(gid, req_role_id, ctx.guild)
        await ctx.send(f"📊 **{len(entries)}** оролцогч байна.", ephemeral=True)

    @giveaway.command(name='list', description="Идэвхтэй giveaway-үүдийн жагсаалт", with_app_command=True)
    @app_commands.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def list_giveaways(self, ctx):
        await ctx.defer(ephemeral=False)
        rows = await self.bot.db.fetch(
            "SELECT message_id, prize, end_time, channel_id FROM giveaways WHERE guild_id = ? AND ended = 0",
            ctx.guild.id
        )
        if not rows:
            return await ctx.send(embed=discord.Embed(title="📭 Идэвхтэй giveaway байхгүй", color=WARNING_COLOR))

        embed = discord.Embed(title="🎁 Идэвхтэй Giveaway-үүд", color=GOLD_COLOR)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        for msg_id, prize, end_time, ch_id in rows:
            channel = self.bot.get_channel(ch_id)
            ch_mention = channel.mention if channel else f"<#{ch_id}>"
            embed.add_field(
                name=f"ID: {msg_id}",
                value=f"**Шагнал:** {prize}\n**Дуусах:** <t:{end_time}:R>\n**Суваг:** {ch_mention}",
                inline=False
            )
        await ctx.send(embed=embed)

    @tasks.loop(minutes=1.0)
    async def giveaway_check(self):
        await self.bot.wait_until_ready()
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        expired = await self.bot.db.fetch(
            "SELECT id, channel_id, message_id, prize, winner_count, host_id, required_role_id FROM giveaways WHERE end_time <= ? AND ended = 0",
            now
        )

        for gid, channel_id, msg_id, prize, winner_count, host_id, req_role_id in expired:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue
            try:
                message = await channel.fetch_message(msg_id)
            except:
                await self.bot.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", gid)
                await self.bot.db.commit()
                continue

            guild = channel.guild
            entries = await self.get_entries(gid, req_role_id, guild)
            if entries:
                winners = random.sample(entries, min(winner_count, len(entries)))
                host_user = guild.get_member(host_id) or await self.bot.fetch_user(host_id)
                await self.finish_giveaway(message, gid, winners, prize, host_user)
            else:
                embed = discord.Embed(
                    title="🎉 **GIVEAWAY ДУУСЛАА** 🎉",
                    description=f"**Шагнал:** {prize}\n**Оролцогч байхгүй.**",
                    color=ERROR_COLOR
                )
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                embed.timestamp = discord.utils.utcnow()
                await message.edit(embed=embed, view=None)
                await message.channel.send(embed=embed)
                await self.bot.db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", gid)
                await self.bot.db.commit()

    @giveaway_check.before_loop
    async def before_giveaway_check(self):
        await self.bot.wait_until_ready()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("⛔ Энэ командыг ашиглах эрх танд байхгүй.", delete_after=5)
        else:
            await ctx.send(f"⚠️ Алдаа гарлаа: {error}", delete_after=10)


async def setup(bot):
    await bot.add_cog(Giveaway(bot))