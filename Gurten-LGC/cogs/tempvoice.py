import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle
import asyncio

# ---------- Control Panel Modals ----------
class RenameModal(ui.Modal, title="Сувгийн нэрийг өөрчлөх"):
    name = ui.TextInput(label="Шинэ нэр", placeholder="Шинэ нэрээ бичнэ үү...", max_length=100)
    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Энэ үйлдлийг зөвхөн серверт ашиглана уу.", ephemeral=True)
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.edit(name=self.name.value)
            await interaction.response.send_message(f"✅ Нэр **{self.name.value}** боллоо.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Суваг олдсонгүй.", ephemeral=True)


class LimitModal(ui.Modal, title="Оролтын хязгаар тогтоох"):
    limit = ui.TextInput(label="Хязгаар (0-99)", placeholder="0 - хязгааргүй", default="0")
    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("❌ Энэ үйлдлийг зөвхөн серверт ашиглана уу.", ephemeral=True)
        try:
            limit = int(self.limit.value)
            if 0 <= limit <= 99:
                channel = interaction.guild.get_channel(self.channel_id)
                if channel:
                    await channel.edit(user_limit=limit)
                    msg = f"✅ Хязгаар: {limit} (хязгааргүй)" if limit == 0 else f"✅ Хязгаар: {limit} хэрэглэгч"
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Суваг олдсонгүй.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ 0-99 хооронд тоо оруулна уу.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Буруу формат.", ephemeral=True)


# ---------- Kick User Select View ----------
class KickUserSelect(ui.View):
    def __init__(self, channel: discord.VoiceChannel, owner_id: int):
        super().__init__(timeout=60)
        self.channel = channel
        self.owner_id = owner_id

        members = [m for m in channel.members if not m.bot and m.id != owner_id]
        if not members:
            self.add_item(ui.Button(label="Хэрэглэгч байхгүй", disabled=True, style=ButtonStyle.gray))
            return

        options = [
            discord.SelectOption(label=m.display_name, value=str(m.id), description=f"ID: {m.id}")
            for m in members[:25]
        ]
        select = ui.Select(placeholder="Хөөх хэрэглэгчээ сонгоно уу...", options=options, min_values=1, max_values=1)

        async def kick_callback(interaction: discord.Interaction):
            if interaction.guild is None:
                return await interaction.response.send_message("❌ Энэ үйлдлийг зөвхөн серверт ашиглана уу.", ephemeral=True)
            if interaction.user.id != self.owner_id:
                return await interaction.response.send_message("❌ Та эзэмшигч биш!", ephemeral=True)
            user_id = int(select.values[0])
            member = interaction.guild.get_member(user_id)
            if not member or member not in self.channel.members:
                return await interaction.response.send_message("❌ Хэрэглэгч олдсонгүй.", ephemeral=True)
            try:
                await member.move_to(None)
                await interaction.response.send_message(f"✅ {member.mention} хөөгдлөө.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Хөөх эрх хүрэлцэхгүй.", ephemeral=True)
            self.stop()
            try:
                await interaction.message.delete()
            except discord.HTTPException:
                pass

        select.callback = kick_callback
        self.add_item(select)


# ---------- Main Control Panel View ----------
class ControlView(ui.View):
    def __init__(self, bot, channel_id: int, owner_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.channel_id = channel_id
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("❌ Энэ үйлдлийг зөвхөн серверт ашиглана уу.", ephemeral=True)
            return False
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Та энэ сувгийн эзэн биш!", ephemeral=True)
            return False
        return True

    @ui.button(label="Түгжих", style=ButtonStyle.red, emoji="🔒", row=0)
    async def lock(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Суваг олдсонгүй!", ephemeral=True)
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("🔒 Суваг түгжигдлээ.", ephemeral=True)

    @ui.button(label="Тайлах", style=ButtonStyle.green, emoji="🔓", row=0)
    async def unlock(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Суваг олдсонгүй!", ephemeral=True)
        await channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("🔓 Суваг нээлттэй.", ephemeral=True)

    @ui.button(label="Нэр өөрчлөх", style=ButtonStyle.blurple, emoji="✏️", row=1)
    async def rename(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RenameModal(self.channel_id))

    @ui.button(label="Хязгаар", style=ButtonStyle.gray, emoji="👥", row=1)
    async def set_limit(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LimitModal(self.channel_id))

    @ui.button(label="Хэрэглэгчид", style=ButtonStyle.gray, emoji="🚫", row=2)
    async def manage_users(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Суваг олдсонгүй!", ephemeral=True)
        view = KickUserSelect(channel, self.owner_id)
        await interaction.response.send_message("👥 **Сувгаас хэрэглэгч хөөх:**", view=view, ephemeral=True)

    @ui.button(label="Хөөх", style=ButtonStyle.red, emoji="👢", row=2)
    async def kick_user(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Суваг олдсонгүй!", ephemeral=True)
        view = KickUserSelect(channel, self.owner_id)
        await interaction.response.send_message("👤 **Хөөх хэрэглэгчээ сонгоно уу:**", view=view, ephemeral=True)


# ---------- Main TempVoice Cog (SQLite) ----------
class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.init_db()

    async def init_db(self):
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS guild_config (
            guild_id TEXT PRIMARY KEY,
            create_channel_id INTEGER,
            category_id INTEGER,
            max_channels_per_user INTEGER DEFAULT 3,
            control_channel_id INTEGER
        )''')
        await self.bot.db.commit()
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS temp_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            channel_id INTEGER UNIQUE,
            owner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        await self.bot.db.commit()

    async def send_control_panel(self, member: discord.Member, channel: discord.VoiceChannel):
        embed = discord.Embed(
            title="🎛️ Түр сувгийн удирдлага",
            description=f"**{channel.name}** сувгийг доорх товчлуураар удирдана уу.",
            color=0x5865F2
        )
        embed.add_field(name="Эзэмшигч", value=member.mention)
        embed.set_footer(text="Удирдлагын самбар байнгын идэвхтэй.")
        view = ControlView(self.bot, channel.id, member.id)

        # Get configured control text channel
        row = await self.bot.db.fetchone(
            "SELECT control_channel_id FROM guild_config WHERE guild_id = ?", str(member.guild.id)
        )
        if row and row[0]:
            target = member.guild.get_channel(row[0])
            if target:
                try:
                    await target.send(embed=embed, view=view)
                except discord.Forbidden:
                    pass
            else:
                try:
                    await member.send(embed=embed, view=view)
                except discord.Forbidden:
                    pass
        else:
            try:
                await member.send(embed=embed, view=view)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        # --- Create temporary channel ---
        if after.channel and not before.channel:
            guild_id = member.guild.id
            row = await self.bot.db.fetchone(
                "SELECT create_channel_id, max_channels_per_user, category_id FROM guild_config WHERE guild_id = ?",
                str(guild_id)
            )
            if row and row[0] == after.channel.id:
                create_channel_id, max_channels, category_id = row
                max_channels = max_channels or 3
                category_id = category_id or after.channel.category_id

                # Check user's current channel count
                count_row = await self.bot.db.fetchone(
                    "SELECT COUNT(*) FROM temp_channels WHERE guild_id = ? AND owner_id = ?",
                    str(guild_id), str(member.id)
                )
                count = count_row[0] if count_row else 0
                if count >= max_channels:
                    try:
                        await member.send(f"❌ Хамгийн ихдээ {max_channels} түр суваг үүсгэх боломжтой.")
                    except:
                        pass
                    await member.move_to(None)
                    return

                category = member.guild.get_channel(category_id) if category_id else after.channel.category
                overwrites = {
                    member.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
                    member: discord.PermissionOverwrite(manage_channels=True, mute_members=True, deafen_members=True)
                }
                new_channel = await member.guild.create_voice_channel(
                    name=f"🔊 {member.display_name}",
                    category=category,
                    overwrites=overwrites
                )
                await member.move_to(new_channel)

                await self.bot.db.execute(
                    "INSERT INTO temp_channels (guild_id, channel_id, owner_id) VALUES (?, ?, ?)",
                    str(guild_id), new_channel.id, member.id
                )
                await self.bot.db.commit()
                await self.send_control_panel(member, new_channel)

        # --- Delete empty temporary channel ---
        if before.channel:
            channel = before.channel
            row = await self.bot.db.fetchone("SELECT id FROM temp_channels WHERE channel_id = ?", channel.id)
            if row and len(channel.members) == 0:
                await asyncio.sleep(3)
                if len(channel.members) == 0:
                    try:
                        await channel.delete(reason="Хоосон түр суваг")
                    except:
                        pass
                    await self.bot.db.execute("DELETE FROM temp_channels WHERE channel_id = ?", channel.id)
                    await self.bot.db.commit()

    # ---------- Admin slash commands ----------
    @app_commands.command(name="voicesetup", description="Түр суваг үүсгэх тохиргоо")
    @app_commands.describe(
        create_channel="Хэрэглэгч энэ сувагт ороход түр суваг үүснэ",
        category="Түр сувгуудыг байрлуулах категори (заавал биш)",
        max_channels="Нэг хэрэглэгчийн үүсгэх түр сувгийн дээд хязгаар (анхдагч 3)",
        control_channel="Удирдлагын самбар илгээх текст суваг (заавал биш)"
    )
    @app_commands.default_permissions(administrator=True)
    async def voicesetup(self, interaction: discord.Interaction,
                         create_channel: discord.VoiceChannel,
                         category: discord.CategoryChannel = None,
                         max_channels: int = 3,
                         control_channel: discord.TextChannel = None):
        guild_id = str(interaction.guild_id)
        cat_id = category.id if category else create_channel.category_id
        cc_id = control_channel.id if control_channel else None

        await self.bot.db.execute(
            """INSERT OR REPLACE INTO guild_config (guild_id, create_channel_id, category_id, max_channels_per_user, control_channel_id)
               VALUES (?, ?, ?, ?, ?)""",
            guild_id, create_channel.id, cat_id, max_channels, cc_id
        )
        await self.bot.db.commit()

        embed = discord.Embed(title="✅ Тохиргоо хадгалагдлаа", color=discord.Color.green())
        embed.add_field(name="Create суваг", value=create_channel.mention, inline=False)
        if category:
            embed.add_field(name="Түр сувгийн категори", value=category.name, inline=False)
        embed.add_field(name="Хамгийн их суваг", value=max_channels, inline=False)
        if control_channel:
            embed.add_field(name="Удирдлагын самбарын суваг", value=control_channel.mention, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="voicesettings", description="Одоогийн түр сувгийн тохиргоог харах")
    @app_commands.default_permissions(administrator=True)
    async def voicesettings(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        row = await self.bot.db.fetchone(
            "SELECT create_channel_id, category_id, max_channels_per_user, control_channel_id FROM guild_config WHERE guild_id = ?",
            guild_id
        )
        if not row:
            return await interaction.response.send_message("❌ Тохиргоо хийгдээгүй байна. `/voicesetup` ашиглана уу.", ephemeral=True)

        create_ch = interaction.guild.get_channel(row[0])
        cat = interaction.guild.get_channel(row[1]) if row[1] else None
        ctrl_ch = interaction.guild.get_channel(row[3]) if row[3] else None

        embed = discord.Embed(title="Тохиргоо", color=discord.Color.blue())
        embed.add_field(name="Create суваг", value=create_ch.mention if create_ch else "Устгагдсан", inline=False)
        embed.add_field(name="Категори", value=cat.name if cat else "Create-н категори", inline=False)
        embed.add_field(name="Дээд хязгаар", value=row[2], inline=False)
        embed.add_field(name="Удирдлагын самбарын суваг", value=ctrl_ch.mention if ctrl_ch else "Тохируулаагүй", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TempVoice(bot))