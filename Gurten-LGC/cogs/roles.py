import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone
import re

# ===== COLOR SCHEME (неон палитр) =====
EMBED_COLOR   = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR   = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x89b4fa
NEON_PINK     = 0xFF10F0
NEON_GREEN    = 0x39FF14


def parse_duration(duration_str: str) -> int:
    match = re.match(r"(\d+)([smhdw])", duration_str.lower())
    if not match:
        raise ValueError("Invalid duration format. Use e.g. 30s, 5m, 2h, 1d, 1w")
    value = int(match.group(1))
    unit = match.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    return value * multipliers[unit]


class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        try:
            self.temprole_loop.cancel()
        except Exception:
            pass

    # ==================== SQLite INIT ====================
    async def init_db(self):
        """Хүснэгт үүсгэх (SQLite)"""
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS temproles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                guild_id TEXT,
                role_id INTEGER,
                end_time INTEGER
            )
        ''')
        await self.bot.db.commit()

    async def cog_load(self):
        await self.init_db()
        self.temprole_loop.start()

    def can_manage_role(self, guild, role):
        bot_member = guild.me
        return (bot_member.guild_permissions.manage_roles and
                role.position < bot_member.top_role.position)

    # ==================== ROLE GROUP ====================
    @commands.hybrid_group(name='role', description="Permanent role management. Subcommands: give, remove",
                           with_app_command=True, invoke_without_command=True)
    async def role_group(self, ctx):
        embed = discord.Embed(
            title="🎭 Role Management",
            description="`!role give @user @role` – give role\n`!role remove @user @role` – remove role",
            color=INFO_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"{ctx.guild.name} • Роль удирдлага")
        await ctx.send(embed=embed)

    @role_group.command(name='give', description="Give a permanent role to a user", with_app_command=True)
    @app_commands.describe(user="User", role="Role")
    @commands.has_permissions(manage_roles=True)
    async def role_give(self, ctx, user: discord.Member, role: discord.Role):
        await ctx.defer(ephemeral=False)
        if not self.can_manage_role(ctx.guild, role):
            embed = discord.Embed(
                title="❌ Cannot manage role",
                description="The bot cannot manage this role (role too high or missing permissions).",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)
        if role in user.roles:
            embed = discord.Embed(
                title="⚠️ Already has role",
                description=f"{user.mention} already has {role.mention}.",
                color=WARNING_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            return await ctx.send(embed=embed)
        await user.add_roles(role, reason=f"Given by {ctx.author}")
        embed = discord.Embed(
            title="✅ Role given",
            description=f"Given {role.mention} to {user.mention}.",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"{ctx.guild.name} • {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @role_group.command(name='remove', description="Remove a permanent role from a user", with_app_command=True)
    @app_commands.describe(user="User", role="Role")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, user: discord.Member, role: discord.Role):
        await ctx.defer(ephemeral=False)
        if not self.can_manage_role(ctx.guild, role):
            embed = discord.Embed(
                title="❌ Cannot manage role",
                description="The bot cannot manage this role (role too high or missing permissions).",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)
        if role not in user.roles:
            embed = discord.Embed(
                title="⚠️ User doesn't have role",
                description=f"{user.mention} does not have {role.mention}.",
                color=WARNING_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            return await ctx.send(embed=embed)
        await user.remove_roles(role, reason=f"Removed by {ctx.author}")
        embed = discord.Embed(
            title="✅ Role removed",
            description=f"Removed {role.mention} from {user.mention}.",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"{ctx.guild.name} • {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ==================== TEMPROLE GROUP ====================
    @commands.hybrid_group(name='temprole', description="Temporary role management. Subcommands: give, remove",
                           with_app_command=True, invoke_without_command=True)
    async def temprole_group(self, ctx):
        embed = discord.Embed(
            title="⏱️ Temporary Role Management",
            description="`!temprole give @user @role 1h` – give a temporary role\n`!temprole remove @user @role` – remove early",
            color=INFO_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"{ctx.guild.name} • Түр роль удирдлага")
        await ctx.send(embed=embed)

    @temprole_group.command(name='give', description="Give a temporary role for a specific duration",
                            with_app_command=True)
    @app_commands.describe(user="User", role="Role", duration="Duration (30s, 5m, 2h, 1d, 1w)")
    @commands.has_permissions(manage_roles=True)
    async def temprole_give(self, ctx, user: discord.Member, role: discord.Role, duration: str):
        await ctx.defer(ephemeral=False)
        if not self.can_manage_role(ctx.guild, role):
            embed = discord.Embed(
                title="❌ Cannot manage role",
                description="The bot cannot manage this role (role too high or missing permissions).",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)

        try:
            seconds = parse_duration(duration)
        except ValueError as e:
            embed = discord.Embed(
                title="❌ Invalid duration",
                description=str(e),
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            )
            return await ctx.send(embed=embed)

        if seconds <= 0:
            embed = discord.Embed(
                title="❌ Invalid duration",
                description="Duration must be positive.",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            )
            return await ctx.send(embed=embed)

        end_time = int((datetime.now(timezone.utc) + timedelta(seconds=seconds)).timestamp())

        existing = await self.bot.db.fetchone(
            "SELECT id FROM temproles WHERE user_id = ? AND guild_id = ? AND role_id = ?",
            str(user.id), str(ctx.guild.id), role.id
        )
        if existing:
            await self.bot.db.execute(
                "UPDATE temproles SET end_time = ? WHERE user_id = ? AND guild_id = ? AND role_id = ?",
                end_time, str(user.id), str(ctx.guild.id), role.id
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO temproles (user_id, guild_id, role_id, end_time) VALUES (?, ?, ?, ?)",
                str(user.id), str(ctx.guild.id), role.id, end_time
            )
        await self.bot.db.commit()

        if role not in user.roles:
            try:
                await user.add_roles(role, reason=f"Temporary role ({duration}) given by {ctx.author}")
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Missing permissions",
                    description="Bot lacks 'Manage Roles' or the role is above the bot's highest role.",
                    color=ERROR_COLOR,
                    timestamp=discord.utils.utcnow()
                )
                return await ctx.send(embed=embed)
            except discord.HTTPException as e:
                embed = discord.Embed(
                    title="❌ Failed to add role",
                    description=str(e),
                    color=ERROR_COLOR,
                    timestamp=discord.utils.utcnow()
                )
                return await ctx.send(embed=embed)

        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        parts = []
        if days: parts.append(f"{days} day(s)")
        if hours: parts.append(f"{hours} hour(s)")
        if minutes: parts.append(f"{minutes} minute(s)")
        if secs: parts.append(f"{secs} second(s)")
        time_str = " ".join(parts) if parts else "0 seconds"

        embed = discord.Embed(
            title="⏱️ Temporary role given",
            description=f"Given {role.mention} to {user.mention} for **{time_str}**.",
            color=NEON_GREEN,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"{ctx.guild.name} • {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @temprole_group.command(name='remove', description="Remove a temporary role early", with_app_command=True)
    @app_commands.describe(user="User", role="Role")
    @commands.has_permissions(manage_roles=True)
    async def temprole_remove(self, ctx, user: discord.Member, role: discord.Role):
        await ctx.defer(ephemeral=False)
        entry = await self.bot.db.fetchone(
            "SELECT id FROM temproles WHERE user_id = ? AND guild_id = ? AND role_id = ?",
            str(user.id), str(ctx.guild.id), role.id
        )
        if not entry:
            embed = discord.Embed(
                title="⚠️ Not a temporary role",
                description=f"{user.mention} does not have {role.mention} as a temporary role.",
                color=WARNING_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            return await ctx.send(embed=embed)

        await self.bot.db.execute(
            "DELETE FROM temproles WHERE user_id = ? AND guild_id = ? AND role_id = ?",
            str(user.id), str(ctx.guild.id), role.id
        )
        await self.bot.db.commit()

        if role in user.roles:
            try:
                await user.remove_roles(role, reason=f"Temporary role removed early by {ctx.author}")
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Missing permissions",
                    description="Bot lacks 'Manage Roles' permission.",
                    color=ERROR_COLOR,
                    timestamp=discord.utils.utcnow()
                )
                return await ctx.send(embed=embed)
            except discord.HTTPException as e:
                embed = discord.Embed(
                    title="❌ Failed to remove role",
                    description=str(e),
                    color=ERROR_COLOR,
                    timestamp=discord.utils.utcnow()
                )
                return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="✅ Temporary role removed",
            description=f"Removed {role.mention} from {user.mention} early.",
            color=SUCCESS_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"{ctx.guild.name} • {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ==================== TEMPROLE LOOP ====================
    @tasks.loop(minutes=1.0)
    async def temprole_loop(self):
        await self.bot.wait_until_ready()
        now = int(datetime.now(timezone.utc).timestamp())
        expired = await self.bot.db.fetch(
            "SELECT id, user_id, guild_id, role_id FROM temproles WHERE end_time <= ?", now
        )

        for eid, uid, gid, rid in expired:
            guild = self.bot.get_guild(int(gid))
            if guild:
                user = guild.get_member(int(uid))
                role = guild.get_role(rid)
                if user and role and role in user.roles:
                    try:
                        await user.remove_roles(role, reason="Temporary role expired")
                    except (discord.Forbidden, discord.HTTPException):
                        pass
            await self.bot.db.execute("DELETE FROM temproles WHERE id = ?", eid)
            await self.bot.db.commit()


async def setup(bot):
    await bot.add_cog(RoleManagement(bot))