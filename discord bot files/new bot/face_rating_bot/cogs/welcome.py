import discord
from discord.ext import commands
from discord import app_commands, ui
from discord.ui import View, ChannelSelect
import datetime
import logging

logger = logging.getLogger(__name__)

EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

# ========== Хувьсагч орлуулагч ==========
def replace_vars(text: str, member: discord.Member) -> str:
    if not text:
        return ""
    guild = member.guild
    return text.replace("{user}", member.mention)               .replace("{username}", member.name)               .replace("{server}", guild.name if guild else "Unknown")               .replace("{count}", str(len(guild.members)) if guild else "?")

# ========== АДМИН ПАНЕЛЬ VIEW ==========
class WelcomeSetupView(View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

        # Суваг сонгох
        self.channel_select = ChannelSelect(
            placeholder="📢 Мэдэгдэл илгээх суваг сонгох...",
            channel_types=[discord.ChannelType.text],
            min_values=1, max_values=1,
            row=0
        )
        self.channel_select.callback = self.channel_callback
        self.add_item(self.channel_select)

    async def channel_callback(self, interaction: discord.Interaction):
        channel = self.channel_select.values[0]
        await self.cog.set_config_key(self.guild_id, "channel_id", channel.id)
        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="🔄 Идэвхжүүлэх / Унтраах", style=discord.ButtonStyle.primary, row=1)
    async def toggle_btn(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        current = cfg.get("enabled", False) if cfg else False
        await self.cog.set_config_key(self.guild_id, "enabled", int(not current))
        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="🟢 Welcome текст тохируулах", style=discord.ButtonStyle.success, row=2)
    async def welcome_text_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TextModal("welcome", self))

    @discord.ui.button(label="🔴 Goodbye текст тохируулах", style=discord.ButtonStyle.red, row=2)
    async def goodbye_text_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TextModal("goodbye", self))

    @discord.ui.button(label="🎨 Embed өнгө сонгох", style=discord.ButtonStyle.secondary, row=3)
    async def color_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ColorModal(self))

    @discord.ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=3)
    async def refresh_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.refresh(interaction)

    async def refresh(self, interaction: discord.Interaction = None):
        cfg = await self.cog.get_config(self.guild_id)
        embed = self.build_embed(cfg, self.cog.bot.get_guild(self.guild_id))
        if interaction:
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            if self.message:
                await self.message.edit(embed=embed, view=self)

    def build_embed(self, cfg, guild):
        if not cfg:
            embed = discord.Embed(title="👋 Welcome / Goodbye тохиргоо",
                                  description="Сонголтуудаар тохируулна уу.",
                                  color=INFO_COLOR)
            embed.add_field(name="📢 Суваг", value="❌ Сонгогдоогүй", inline=False)
            embed.add_field(name="🔘 Төлөв", value="❌ Унтарсан", inline=False)
            return embed

        channel = guild.get_channel(cfg.get("channel_id")) if guild and cfg.get("channel_id") else None
        embed = discord.Embed(title="👋 Welcome / Goodbye тохиргоо",
                              color=cfg.get("color", GOLD_COLOR))
        embed.add_field(name="📢 Суваг", value=channel.mention if channel else "❌ Устгагдсан", inline=False)
        embed.add_field(name="🔘 Төлөв", value="✅ Идэвхтэй" if cfg.get("enabled") else "❌ Унтарсан", inline=True)
        embed.add_field(name="🎨 Өнгө", value=f"#{cfg.get('color', GOLD_COLOR):06x}", inline=True)
        embed.add_field(name="🟢 Welcome текст", value=cfg.get("welcome_text", "Тавтай морил {user}!")[:1024] or "—", inline=False)
        embed.add_field(name="🔴 Goodbye текст", value=cfg.get("goodbye_text", "{user} серверээс гарлаа.")[:1024] or "—", inline=False)
        embed.add_field(name="Хувьсагчид", value="`{user}` `{username}` `{server}` `{count}`", inline=False)
        embed.set_footer(text=f"Сервер: {guild.name if guild else 'Unknown'}")
        return embed

# ========== Текст оруулах MODAL ==========
class TextModal(ui.Modal):
    def __init__(self, msg_type, view):
        super().__init__(title=f"{'Welcome' if msg_type == 'welcome' else 'Goodbye'} текст тохируулах")
        self.view = view
        self.msg_type = msg_type
        self.text = ui.TextInput(
            label="Текст (хувьсагч ашиглах боломжтой)",
            style=discord.TextStyle.paragraph,
            placeholder="{user} тавтай морил! {server} серверт тавтай морил.",
            required=True,
            max_length=1024
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        key = "welcome_text" if self.msg_type == "welcome" else "goodbye_text"
        await self.view.cog.set_config_key(self.view.guild_id, key, self.text.value)
        await interaction.response.send_message(f"✅ {self.msg_type} текст хадгалагдлаа.", ephemeral=True)
        await self.view.refresh(interaction)

# ========== Өнгө сонгох MODAL ==========
class ColorModal(ui.Modal):
    def __init__(self, view):
        super().__init__(title="Embed өнгө сонгох")
        self.view = view
        self.color = ui.TextInput(
            label="HEX өнгө (жишээ: fab387)",
            placeholder="fab387",
            required=True,
            max_length=6
        )
        self.add_item(self.color)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            hex_val = int(self.color.value, 16)
            await self.view.cog.set_config_key(self.view.guild_id, "color", hex_val)
            await interaction.response.send_message(f"✅ Өнгө #{self.color.value} боллоо.", ephemeral=True)
            await self.view.refresh(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Зөв HEX утга оруулна уу (0-9, a-f).", ephemeral=True)


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS welcome_config (
                    guild_id TEXT PRIMARY KEY,
                    channel_id INTEGER,
                    enabled INTEGER DEFAULT 1,
                    welcome_text TEXT DEFAULT '{user} тавтай морил!',
                    goodbye_text TEXT DEFAULT '{user} серверээс гарлаа.',
                    color INTEGER DEFAULT 16766720
                )
            """)
            await conn.commit()

    async def cog_load(self):
        await self.init_db()

    async def get_config(self, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT channel_id, enabled, welcome_text, goodbye_text, color FROM welcome_config WHERE guild_id = ?",
                (str(guild_id),)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        return {
            "channel_id": row[0],
            "enabled": bool(row[1]),
            "welcome_text": row[2],
            "goodbye_text": row[3],
            "color": row[4]
        }

    async def set_config_key(self, guild_id, key, value):
        gid = str(guild_id)
        async with self.bot.db.acquire() as conn:
            # Эхлээд мөр байгаа эсэхийг шалгах
            async with conn.execute("SELECT 1 FROM welcome_config WHERE guild_id = ?", (gid,)) as cur:
                exists = await cur.fetchone()
            if exists:
                await conn.execute(
                    f"UPDATE welcome_config SET {key} = ? WHERE guild_id = ?",
                    (value, gid)
                )
            else:
                # Шинэ мөр үүсгэх, бусад утгыг default-аар
                defaults = {
                    'channel_id': None,
                    'enabled': 1,
                    'welcome_text': '{user} тавтай морил!',
                    'goodbye_text': '{user} серверээс гарлаа.',
                    'color': 16766720
                }
                defaults[key] = value
                await conn.execute(
                    "INSERT INTO welcome_config (guild_id, channel_id, enabled, welcome_text, goodbye_text, color) VALUES (?, ?, ?, ?, ?, ?)",
                    (gid, defaults['channel_id'], defaults['enabled'], defaults['welcome_text'], defaults['goodbye_text'], defaults['color'])
                )
            await conn.commit()

    @app_commands.command(name="welcome_setup", description="Welcome / Goodbye тохиргооны самбар нээх")
    @app_commands.default_permissions(administrator=True)
    async def welcome_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_config(interaction.guild_id)
        view = WelcomeSetupView(self, interaction.guild_id)
        embed = view.build_embed(cfg, interaction.guild)
        msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = msg

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.handle_join_leave(member, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.handle_join_leave(member, "leave")

    async def handle_join_leave(self, member: discord.Member, event_type: str):
        if member.bot:
            return
        guild = member.guild
        cfg = await self.get_config(guild.id)
        if not cfg or not cfg.get("enabled") or not cfg.get("channel_id"):
            return
        channel = guild.get_channel(cfg["channel_id"])
        if not channel:
            return

        color = cfg.get("color", GOLD_COLOR)
        if event_type == "join":
            text = replace_vars(cfg.get("welcome_text", "Тавтай морил {user}!"), member)
            title = "👋 Шинэ гишүүн!"
            embed_color = SUCCESS_COLOR
        else:
            text = replace_vars(cfg.get("goodbye_text", "{user} серверээс гарлаа."), member)
            title = "🚪 Гишүүн гарлаа"
            embed_color = WARNING_COLOR

        embed = discord.Embed(
            title=title,
            description=text,
            color=color if color else embed_color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Сервер: {guild.name}")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"Cannot send welcome/goodbye message in {channel.name} (guild: {guild.name})")
        except Exception as e:
            logger.error(f"Error sending welcome/goodbye: {e}")

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))