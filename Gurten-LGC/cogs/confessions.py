import discord
from discord.ext import commands
from discord import app_commands
import datetime

# ===== COLOR SCHEME =====
EMBED_COLOR   = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR   = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x89b4fa
NEON_PINK     = 0xFF10F0   # нэмэлт неон өнгө

class Confessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== ӨГӨГДЛИЙН САН (SQLite) ====================
    async def init_db(self):
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS confession_config (
            guild_id TEXT PRIMARY KEY,
            confess_channel_id INTEGER,
            output_channel_id INTEGER,
            anonymity INTEGER DEFAULT 1,
            cooldown INTEGER DEFAULT 30,
            next_id INTEGER DEFAULT 1
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS confession_blacklist (
            guild_id TEXT,
            word TEXT,
            PRIMARY KEY (guild_id, word)
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS confession_cooldown (
            user_id TEXT,
            guild_id TEXT,
            last_time INTEGER,
            PRIMARY KEY (user_id, guild_id)
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS confession_messages (
            guild_id TEXT,
            confession_id INTEGER,
            message_id INTEGER,
            user_id TEXT,
            content TEXT,
            PRIMARY KEY (guild_id, confession_id)
        )''')
        await self.bot.db.commit()

    async def get_config(self, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT confess_channel_id, output_channel_id, anonymity, cooldown, next_id FROM confession_config WHERE guild_id = ?",
            str(guild_id)
        )
        if not row:
            return None
        return {
            "confess_channel": row[0],
            "output_channel": row[1],
            "anonymity": bool(row[2]),
            "cooldown": row[3],
            "next_id": row[4]
        }

    async def update_config(self, guild_id, **kwargs):
        # Одоогийн тохиргоо байгаа эсэхийг шалгах
        exists = await self.bot.db.fetchone(
            "SELECT 1 FROM confession_config WHERE guild_id = ?", str(guild_id)
        )
        if exists:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [str(guild_id)]
            await self.bot.db.execute(
                f"UPDATE confession_config SET {set_clause} WHERE guild_id = ?",
                *values
            )
        else:
            cols = ", ".join(kwargs.keys())
            placeholders = ", ".join(["?"] * len(kwargs))
            await self.bot.db.execute(
                f"INSERT INTO confession_config (guild_id, {cols}) VALUES (?, {placeholders})",
                str(guild_id), *kwargs.values()
            )
        await self.bot.db.commit()  # Чухал: commit

    async def increment_id(self, guild_id):
        # next_id-г нэмэгдүүлээд хуучин утгыг буцаах
        await self.bot.db.execute(
            "UPDATE confession_config SET next_id = next_id + 1 WHERE guild_id = ?",
            str(guild_id)
        )
        await self.bot.db.commit()
        row = await self.bot.db.fetchone(
            "SELECT next_id - 1 FROM confession_config WHERE guild_id = ?",
            str(guild_id)
        )
        return row[0] if row else 1

    # ==================== SLASH КОМАНДУУД ====================
    @app_commands.command(name="confess_setup", description="Set up confession channels")
    @app_commands.default_permissions(administrator=True)
    async def confess_setup(self, interaction: discord.Interaction,
                            confess_channel: discord.TextChannel,
                            output_channel: discord.TextChannel,
                            anonymity: bool = True,
                            cooldown_seconds: int = 30):
        await interaction.response.defer(ephemeral=True)
        await self.init_db()
        await self.update_config(interaction.guild_id,
                                 confess_channel_id=confess_channel.id,
                                 output_channel_id=output_channel.id,
                                 anonymity=anonymity,
                                 cooldown=cooldown_seconds)
        embed = discord.Embed(
            title="✅ Confession system configured",
            description=f"**Write channel:** {confess_channel.mention}\n"
                        f"**Output channel:** {output_channel.mention}\n"
                        f"**Anonymous:** {'Yes' if anonymity else 'No'}\n"
                        f"**Cooldown:** {cooldown_seconds}s",
            color=SUCCESS_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Server: {interaction.guild.name}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="confess_edit", description="Edit confession settings")
    @app_commands.default_permissions(administrator=True)
    async def confess_edit(self, interaction: discord.Interaction,
                           anonymity: bool = None,
                           cooldown_seconds: int = None):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_config(interaction.guild_id)
        if not cfg:
            return await interaction.followup.send(
                "❌ Confession system not configured. Use `/confess_setup` first.", ephemeral=True
            )
        updates = {}
        if anonymity is not None:
            updates["anonymity"] = anonymity
        if cooldown_seconds is not None:
            updates["cooldown"] = cooldown_seconds
        if updates:
            await self.update_config(interaction.guild_id, **updates)
            embed = discord.Embed(
                title="✅ Settings updated",
                description=f"**Anonymous:** {anonymity if anonymity is not None else cfg['anonymity']}\n"
                            f"**Cooldown:** {cooldown_seconds if cooldown_seconds is not None else cfg['cooldown']}s",
                color=SUCCESS_COLOR,
                timestamp=datetime.datetime.now()
            )
        else:
            embed = discord.Embed(title="ℹ️ No changes", color=WARNING_COLOR)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="confess_blacklist", description="Add/remove/list blacklisted words")
    @app_commands.default_permissions(administrator=True)
    async def confess_blacklist(self, interaction: discord.Interaction, action: str, word: str = None):
        await interaction.response.defer(ephemeral=True)
        await self.init_db()
        gid = str(interaction.guild_id)

        if action.lower() == "add":
            if not word:
                return await interaction.followup.send("❌ Provide a word.", ephemeral=True)
            await self.bot.db.execute(
                "INSERT OR IGNORE INTO confession_blacklist (guild_id, word) VALUES (?, ?)",
                gid, word.lower()
            )
            await self.bot.db.commit()
            await interaction.followup.send(f"✅ `{word}` added to blacklist.", ephemeral=True)

        elif action.lower() == "remove":
            if not word:
                return await interaction.followup.send("❌ Provide a word.", ephemeral=True)
            await self.bot.db.execute(
                "DELETE FROM confession_blacklist WHERE guild_id = ? AND word = ?",
                gid, word.lower()
            )
            await self.bot.db.commit()
            await interaction.followup.send(f"✅ `{word}` removed from blacklist.", ephemeral=True)

        elif action.lower() == "list":
            rows = await self.bot.db.fetch(
                "SELECT word FROM confession_blacklist WHERE guild_id = ?", gid
            )
            if not rows:
                await interaction.followup.send("📭 No blacklisted words.", ephemeral=True)
            else:
                words = ", ".join([f"`{r[0]}`" for r in rows])
                await interaction.followup.send(f"🚫 Blacklisted words: {words}", ephemeral=True)

        else:
            await interaction.followup.send(
                "❌ Invalid action. Use `add`, `remove`, or `list`.", ephemeral=True
            )

    @app_commands.command(name="confess_delete", description="Delete a confession by ID (admin)")
    @app_commands.default_permissions(administrator=True)
    async def confess_delete(self, interaction: discord.Interaction, confession_id: int):
        await interaction.response.defer(ephemeral=False)
        cfg = await self.get_config(interaction.guild_id)
        if not cfg:
            return await interaction.followup.send(
                "❌ Confession system not configured.", ephemeral=True
            )

        row = await self.bot.db.fetchone(
            "SELECT message_id, user_id, content FROM confession_messages WHERE guild_id = ? AND confession_id = ?",
            str(interaction.guild_id), confession_id
        )
        if not row:
            return await interaction.followup.send(
                f"❌ Confession #{confession_id} not found.", ephemeral=True
            )

        msg_id, user_id, content = row
        channel = interaction.guild.get_channel(cfg["output_channel"])
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            except:
                pass

        await self.bot.db.execute(
            "DELETE FROM confession_messages WHERE guild_id = ? AND confession_id = ?",
            str(interaction.guild_id), confession_id
        )
        await self.bot.db.commit()

        embed = discord.Embed(
            title="🗑️ Confession deleted",
            description=f"Confession #{confession_id} deleted by {interaction.user.mention}\n"
                        f"**Content:** {content[:100]}...",
            color=WARNING_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="confess_stats", description="Show confession system stats")
    async def confess_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        cfg = await self.get_config(interaction.guild_id)
        if not cfg:
            return await interaction.followup.send(
                "❌ Confession system not configured.", ephemeral=True
            )

        active = await self.bot.db.fetchone(
            "SELECT COUNT(*) FROM confession_cooldown WHERE guild_id = ?",
            str(interaction.guild_id)
        )
        total_active = active[0] if active else 0

        total_msgs = await self.bot.db.fetchone(
            "SELECT COUNT(*) FROM confession_messages WHERE guild_id = ?",
            str(interaction.guild_id)
        )
        total_messages = total_msgs[0] if total_msgs else 0

        embed = discord.Embed(
            title="📊 Confession System Stats",
            description=f"**Total confessions:** {cfg['next_id'] - 1}\n"
                        f"**Active cooldowns:** {total_active}\n"
                        f"**Stored messages:** {total_messages}\n"
                        f"**Anonymity:** {'Yes' if cfg['anonymity'] else 'No'}\n"
                        f"**Cooldown:** {cfg['cooldown']}s",
            color=INFO_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Server: {interaction.guild.name}")
        await interaction.followup.send(embed=embed)

    # ==================== EVENT ====================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        cfg = await self.get_config(message.guild.id)
        if not cfg or message.channel.id != cfg["confess_channel"]:
            return

        now = int(datetime.datetime.now().timestamp())

        # Cooldown шалгах
        row = await self.bot.db.fetchone(
            "SELECT last_time FROM confession_cooldown WHERE user_id = ? AND guild_id = ?",
            str(message.author.id), str(message.guild.id)
        )
        if row and (now - row[0]) < cfg["cooldown"]:
            remaining = cfg["cooldown"] - (now - row[0])
            await message.delete()
            await message.channel.send(
                f"{message.author.mention}, please wait {remaining} seconds.",
                delete_after=5
            )
            return

        # Хар үг шалгах
        rows = await self.bot.db.fetch(
            "SELECT word FROM confession_blacklist WHERE guild_id = ?",
            str(message.guild.id)
        )
        blacklist = [r[0] for r in rows]
        for w in blacklist:
            if w in message.content.lower():
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, your message contains a blacklisted word.",
                    delete_after=5
                )
                return

        output_channel = message.guild.get_channel(cfg["output_channel"])
        if not output_channel:
            return

        confess_id = await self.increment_id(message.guild.id)

        author_name = "Anonymous" if cfg["anonymity"] else message.author.display_name

        embed = discord.Embed(
            title=f"📩 Confession #{confess_id}",
            description=message.content,
            color=GOLD_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text=f"Submitted by {author_name}")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        sent_msg = await output_channel.send(embed=embed)

        # Мессежийг бүртгэх
        await self.bot.db.execute(
            "INSERT INTO confession_messages (guild_id, confession_id, message_id, user_id, content) VALUES (?, ?, ?, ?, ?)",
            str(message.guild.id), confess_id, sent_msg.id, str(message.author.id), message.content[:500]
        )
        await self.bot.db.commit()

        # Cooldown бүртгэх (хэрэв байгаа бол шинэчлэх)
        await self.bot.db.execute(
            "INSERT INTO confession_cooldown (user_id, guild_id, last_time) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET last_time = ?",
            str(message.author.id), str(message.guild.id), now, now
        )
        await self.bot.db.commit()

        await message.delete()
        try:
            await message.author.send(f"✅ Your confession (#{confess_id}) has been sent.")
        except:
            pass

    async def cog_load(self):
        await self.init_db()

async def setup(bot):
    await bot.add_cog(Confessions(bot))