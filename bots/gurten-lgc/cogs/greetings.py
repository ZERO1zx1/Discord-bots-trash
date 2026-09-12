import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import json
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass, field
import random

# ===== COLORS =====
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR   = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x89b4fa
PURPLE_COLOR  = 0xcba6f7

# ===== CONFIG DATACLASS =====
@dataclass
class GuildConfig:
    guild_id: int
    welcome_channel: Optional[int] = None
    goodbye_channel: Optional[int] = None
    boost_channel: Optional[int] = None
    welcome_template_id: Optional[int] = None
    goodbye_template_id: Optional[int] = None
    boost_template_id: Optional[int] = None
    welcome_enabled: bool = True
    goodbye_enabled: bool = True
    boost_enabled: bool = True
    dm_on_welcome: bool = False
    log_channel: Optional[int] = None

    @property
    def is_welcome_active(self) -> bool:
        return self.welcome_channel is not None and self.welcome_enabled

    @property
    def is_goodbye_active(self) -> bool:
        return self.goodbye_channel is not None and self.goodbye_enabled

    @property
    def is_boost_active(self) -> bool:
        return self.boost_channel is not None and self.boost_enabled

# ===== DEFAULT TEMPLATES =====
DEFAULT_TEMPLATES = {
    "welcome": {
        "title": "🌟 Сайн байна уу, {user:name}!",
        "description": (
            "**{server:name}** серверт тавтай морил! 🎉\n"
            "Та манай **{server:members}** дахь гишүүн боллоо.\n\n"
            "📜 <#123456789> дүрмийг уншина уу.\n"
            "💬 Ерөнхий чатад өөрийгөө танилцуулаарай!"
        ),
        "color": 0xFFB6C1,
        "thumbnail": "{user:avatar}",
        "image": "",
        "author_name": "",
        "author_icon": "",
        "footer_text": "Тавтай морил! • {date}",
        "footer_icon": "{server:icon}",
        "buttons": [
            {"label": "📜 Дүрэм", "url": "https://discord.com/channels/...", "style": 5},
            {"label": "🌐 Вебсайт", "url": "https://example.com", "style": 5}
        ]
    },
    "goodbye": {
        "title": "👋 Баяртай, {user:name}!",
        "description": (
            "{user:mention} манай серверийг орхисонд харамсалтай байна. 😢\n"
            "Одоо серверт **{server:members}** гишүүн үлдлээ.\n\n"
            "Бид таныг үргэлж санаж байх болно. 💕"
        ),
        "color": 0x95A5A6,
        "thumbnail": "{user:avatar}",
        "image": "",
        "author_name": "",
        "author_icon": "",
        "footer_text": "Баяртай! • {date}",
        "footer_icon": "{server:icon}",
        "buttons": []
    },
    "boost": {
        "title": "💎 Шинэ Server Boost!",
        "description": (
            "{user:mention} сая серверийг **Boost** хийлээ! 🚀\n"
            "Маш их баярлалаа! ✨\n\n"
            "Одоо сервер **{server:boost_level}** түвшинд хүрлээ!\n"
            "Нийт boost: **{server:boost_count}** 🎁"
        ),
        "color": 0xF47FFF,
        "thumbnail": "{user:avatar}",
        "image": "",
        "author_name": "",
        "author_icon": "",
        "footer_text": "Шинэ Boost • {date}",
        "footer_icon": "{server:icon}",
        "buttons": []
    }
}

RANDOM_GREETINGS = [
    "Сайн байна уу! Тавтай морил!",
    "Таныг харсандаа баяртай байна!",
    "Манай серверт нэгдсэнд баярлалаа!",
    "Шинэ гишүүн маань ирлээ!",
    "Серверт тавтай морилно уу!",
]

PLACEHOLDERS = {
    "{user:mention}": "Хэрэглэгчийг дурдах (@Boldoo)",
    "{user:name}": "Discord нэр",
    "{user:display_name}": "Сервер дээрх нэр",
    "{user:id}": "ID дугаар",
    "{user:avatar}": "Профайл зургийн URL",
    "{user:created_at}": "Бүртгэл үүсгэсэн огноо",
    "{user:joined_at}": "Серверт нэгдсэн огноо",
    "{server:name}": "Серверийн нэр",
    "{server:id}": "Серверийн ID",
    "{server:members}": "Нийт гишүүдийн тоо",
    "{server:icon}": "Серверийн зургийн URL",
    "{server:owner}": "Эзэмшигчийн нэр",
    "{server:boost_count}": "Нийт boost тоо",
    "{server:boost_level}": "Boost түвшин",
    "{date}": "Одоогийн огноо",
    "{time}": "Одоогийн цаг",
    "{newline}": "Шинэ мөр",
    "{random:greeting}": "Санамсаргүй мэндчилгээ",
}

# ===== UI COMPONENTS =====
class GreetingButtonModal(Modal):
    def __init__(self, callback_func):
        super().__init__(title="🔘 Товчлуур нэмэх")
        self.callback = callback_func
        self.label_input = TextInput(label="Товчны текст", placeholder="Жишээ: 📜 Дүрэм унших", required=True, max_length=80)
        self.add_item(self.label_input)
        self.url_input = TextInput(label="Товчны URL", placeholder="https://...", required=True, max_length=500)
        self.add_item(self.url_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback(interaction, self.label_input.value, self.url_input.value)

class TemplateCreateModal(Modal, title="📝 Embed Загвар бүтээх"):
    def __init__(self, existing: Dict = None, cog=None):
        super().__init__()
        self.cog = cog
        self.existing = existing or {}
        self.template_name = TextInput(
            label="🏷️ Загварын нэр",
            placeholder="Жишээ: Миний Welcome загвар",
            required=True,
            max_length=100,
            default=self.existing.get("name", "")
        )
        self.title_input = TextInput(
            label="📌 Embed гарчиг",
            placeholder="Хувьсагч ашиглаж болно...",
            required=False,
            max_length=256,
            default=self.existing.get("title", "")
        )
        self.description_input = TextInput(
            label="📝 Embed тайлбар",
            style=discord.TextStyle.long,
            placeholder="Хувьсагч ашиглаж болно: {user}, {server:name}...",
            required=True,
            max_length=2000,
            default=self.existing.get("description", "")
        )
        color_default = hex(self.existing["color"]) if "color" in self.existing else ""
        self.color_input = TextInput(
            label="🎨 Өнгө (Hex)",
            placeholder="#57f287",
            required=False,
            max_length=7,
            default=color_default
        )
        self.thumbnail_input = TextInput(
            label="🖼️ Thumbnail URL",
            placeholder="Хувьсагч эсвэл URL...",
            required=False,
            max_length=500,
            default=self.existing.get("thumbnail", "")
        )
        self.add_item(self.template_name)
        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.color_input)
        self.add_item(self.thumbnail_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color = int(self.color_input.value.strip('#'), 16) if self.color_input.value else 0x57f287
        except ValueError:
            return await interaction.response.send_message("❌ Буруу Hex өнгө!", ephemeral=True)

        base = self.existing.copy() if self.existing else {}
        base.update({
            "name": self.template_name.value,
            "title": self.title_input.value,
            "description": self.description_input.value,
            "color": color,
            "thumbnail": self.thumbnail_input.value,
            "image": base.get("image", ""),
            "author_name": base.get("author_name", ""),
            "author_icon": base.get("author_icon", ""),
            "footer_text": base.get("footer_text", ""),
            "footer_icon": base.get("footer_icon", ""),
            "buttons": base.get("buttons", [])
        })
        self.result = base
        await interaction.response.send_message(
            "✅ Загвар бүтээгдлээ! Одоо товчлуур нэмэх үү?",
            view=ButtonAddView(self.result, interaction, self.cog),
            ephemeral=True
        )

class ButtonAddView(View):
    def __init__(self, template: Dict, original_interaction: discord.Interaction, cog):
        super().__init__(timeout=300)
        self.template = template
        self.original_interaction = original_interaction
        self.cog = cog

    @discord.ui.button(label="🔘 Товчлуур нэмэх", style=discord.ButtonStyle.primary)
    async def add_button(self, interaction: discord.Interaction, button: Button):
        modal = GreetingButtonModal(self.add_button_callback)
        await interaction.response.send_modal(modal)

    async def add_button_callback(self, interaction, label, url):
        self.template["buttons"].append({"label": label, "url": url, "style": 5})
        await interaction.response.send_message(f"✅ '{label}' товчлуур нэмэгдлээ!", ephemeral=True, view=self)

    @discord.ui.button(label="💾 Хадгалах", style=discord.ButtonStyle.success)
    async def save_template(self, interaction: discord.Interaction, button: Button):
        await self.cog.save_template(interaction.guild.id, interaction.user.id, self.template)
        await interaction.response.send_message("✅ Загвар амжилттай хадгалагдлаа!", ephemeral=True)
        self.stop()

class TemplateCreateView(View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="📝 Шинэ загвар бүтээх", style=discord.ButtonStyle.primary)
    async def create_new(self, interaction: discord.Interaction, button: Button):
        modal = TemplateCreateModal(cog=self.cog)
        await interaction.response.send_modal(modal)

# ===== MAIN COG =====
class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_cache: Dict[int, GuildConfig] = {}

    async def cog_load(self):
        await self.init_db()

    async def init_db(self):
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS greeting_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s','now'))
            )
        ''')
        await self.bot.db.commit()
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS greeting_config (
                guild_id TEXT PRIMARY KEY,
                welcome_channel INTEGER,
                goodbye_channel INTEGER,
                boost_channel INTEGER,
                welcome_template_id INTEGER,
                goodbye_template_id INTEGER,
                boost_template_id INTEGER,
                welcome_enabled INTEGER DEFAULT 1,
                goodbye_enabled INTEGER DEFAULT 1,
                boost_enabled INTEGER DEFAULT 1,
                dm_on_welcome INTEGER DEFAULT 0,
                log_channel INTEGER
            )
        ''')
        await self.bot.db.commit()

    async def get_config(self, guild_id: int) -> Optional[GuildConfig]:
        if guild_id in self.config_cache:
            return self.config_cache[guild_id]
        row = await self.bot.db.fetchone(
            "SELECT * FROM greeting_config WHERE guild_id = ?", str(guild_id)
        )
        if not row:
            return None
        config = GuildConfig(
            guild_id=guild_id,
            welcome_channel=row[1],
            goodbye_channel=row[2],
            boost_channel=row[3],
            welcome_template_id=row[4],
            goodbye_template_id=row[5],
            boost_template_id=row[6],
            welcome_enabled=bool(row[7]),
            goodbye_enabled=bool(row[8]),
            boost_enabled=bool(row[9]),
            dm_on_welcome=bool(row[10]) if len(row) > 10 else False,
            log_channel=row[11] if len(row) > 11 else None,
        )
        self.config_cache[guild_id] = config
        return config

    def invalidate_cache(self, guild_id: int):
        self.config_cache.pop(guild_id, None)

    def resolve_placeholders(self, text: str, member: discord.Member) -> str:
        if not text:
            return text
        now = datetime.now()
        guild = member.guild
        replacements = {
            "{user:mention}": member.mention,
            "{user:name}": member.name,
            "{user:display_name}": member.display_name,
            "{user:id}": str(member.id),
            "{user:avatar}": str(member.display_avatar.url),
            "{user:created_at}": member.created_at.strftime("%Y-%m-%d %H:%M"),
            "{user:joined_at}": member.joined_at.strftime("%Y-%m-%d %H:%M") if member.joined_at else "N/A",
            "{server:name}": guild.name,
            "{server:id}": str(guild.id),
            "{server:members}": str(guild.member_count),
            "{server:icon}": str(guild.icon.url) if guild.icon else "",
            "{server:owner}": str(guild.owner),
            "{server:boost_count}": str(guild.premium_subscription_count or 0),
            "{server:boost_level}": str(guild.premium_tier),
            "{date}": now.strftime("%Y-%m-%d"),
            "{time}": now.strftime("%H:%M:%S"),
            "{newline}": "\n",
            "{random:greeting}": random.choice(RANDOM_GREETINGS) if RANDOM_GREETINGS else "",
        }
        replacements["{user}"] = member.mention
        replacements["{server}"] = guild.name
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def build_embed(self, template: Dict, member: discord.Member) -> discord.Embed:
        embed = discord.Embed(
            title=self.resolve_placeholders(template.get("title", ""), member) or None,
            description=self.resolve_placeholders(template.get("description", ""), member),
            color=template.get("color", 0x2b2d31),
            timestamp=discord.utils.utcnow()
        )
        if template.get("author_name"):
            embed.set_author(
                name=self.resolve_placeholders(template["author_name"], member),
                icon_url=self.resolve_placeholders(template.get("author_icon", ""), member) or None
            )
        thumb = self.resolve_placeholders(template.get("thumbnail", ""), member)
        if thumb:
            embed.set_thumbnail(url=thumb)
        img = self.resolve_placeholders(template.get("image", ""), member)
        if img:
            embed.set_image(url=img)
        if template.get("footer_text"):
            embed.set_footer(
                text=self.resolve_placeholders(template["footer_text"], member),
                icon_url=self.resolve_placeholders(template.get("footer_icon", ""), member) or None
            )
        return embed

    def build_buttons(self, template: Dict) -> Optional[View]:
        buttons = template.get("buttons", [])
        if not buttons:
            return None
        view = View(timeout=None)
        for btn_data in buttons:
            btn = Button(
                label=btn_data.get("label", "Товч"),
                url=btn_data.get("url", "https://discord.com"),
                style=discord.ButtonStyle(btn_data.get("style", 5))
            )
            view.add_item(btn)
        return view

    async def save_template(self, guild_id: int, creator_id: int, template: Dict):
        await self.bot.db.execute(
            "INSERT INTO greeting_templates (guild_id, creator_id, name, data) VALUES (?, ?, ?, ?)",
            str(guild_id), str(creator_id), template["name"], json.dumps(template)
        )
        await self.bot.db.commit()

    async def get_template(self, template_id: int) -> Optional[Dict]:
        row = await self.bot.db.fetchone(
            "SELECT data FROM greeting_templates WHERE id = ?", template_id
        )
        return json.loads(row[0]) if row else None

    async def get_all_templates(self, guild_id: int, user_id: Optional[int] = None) -> List[Dict]:
        query = "SELECT id, name, data, creator_id FROM greeting_templates WHERE guild_id = ?"
        params = [str(guild_id)]
        if user_id:
            query += " AND creator_id = ?"
            params.append(str(user_id))
        rows = await self.bot.db.fetch(query, *params)
        return [{"id": r[0], "name": r[1], "data": json.loads(r[2]), "creator_id": r[3]} for r in rows]

    async def send_greeting(self, channel_id: int, template_id: Optional[int], member: discord.Member, 
                            default_template: Dict, send_dm: bool = False, log_channel_id: Optional[int] = None):
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        template = await self.get_template(template_id) if template_id else default_template
        embed = self.build_embed(template, member)
        view = self.build_buttons(template)
        try:
            await channel.send(embed=embed, view=view)
        except Exception as e:
            await self.log_error(member.guild, f"Мэндчилгээ илгээхэд алдаа гарлаа: {e}", log_channel_id)

        if send_dm:
            try:
                await member.send(embed=embed, view=view)
            except Exception:
                pass

    async def log_error(self, guild: discord.Guild, message: str, log_channel_id: Optional[int] = None):
        if not log_channel_id:
            return
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            try:
                await log_channel.send(embed=discord.Embed(description=message, color=ERROR_COLOR))
            except:
                pass

    # ================= SLASH COMMANDS =================
    @app_commands.command(name="greeting_set", description="Welcome/Goodbye/Boost сувгийг тохируулах")
    @app_commands.describe(
        event="Үйл явдал",
        channel="Мэдэгдэл очих суваг",
        template_id="Загварын ID (заавал биш)",
        dm="Welcome үед DM илгээх эсэх (зөвхөн welcome)"
    )
    @app_commands.choices(event=[
        app_commands.Choice(name="Welcome", value="welcome"),
        app_commands.Choice(name="Goodbye", value="goodbye"),
        app_commands.Choice(name="Boost", value="boost")
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def greeting_set(self, interaction: discord.Interaction, event: str, channel: discord.TextChannel,
                           template_id: Optional[int] = None, dm: Optional[bool] = None):
        col_channel = f"{event}_channel"
        col_template = f"{event}_template_id"
        await self.bot.db.execute(
            f"INSERT INTO greeting_config (guild_id, {col_channel}, {col_template}) VALUES (?, ?, ?) "
            f"ON CONFLICT(guild_id) DO UPDATE SET {col_channel} = excluded.{col_channel}, {col_template} = excluded.{col_template}",
            str(interaction.guild.id), channel.id, template_id
        )
        await self.bot.db.commit()
        if dm is not None and event == "welcome":
            await self.bot.db.execute(
                "UPDATE greeting_config SET dm_on_welcome = ? WHERE guild_id = ?",
                int(dm), str(interaction.guild.id)
            )
            await self.bot.db.commit()
        self.invalidate_cache(interaction.guild.id)
        embed = discord.Embed(
            title="✅ Амжилттай тохируулагдлаа",
            description=f"**Үйл явдал:** {event.capitalize()}\n**Суваг:** {channel.mention}\n**Загвар ID:** {template_id or 'Анхдагч'}"
                        + (f"\n**DM мэндчилгээ:** {'Идэвхтэй' if dm else 'Идэвхгүй'}" if dm is not None else ""),
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="greeting_toggle", description="Мэдэгдлийг идэвхжүүлэх/унтраах")
    @app_commands.describe(event="Үйл явдал")
    @app_commands.choices(event=[
        app_commands.Choice(name="Welcome", value="welcome"),
        app_commands.Choice(name="Goodbye", value="goodbye"),
        app_commands.Choice(name="Boost", value="boost"),
        app_commands.Choice(name="DM Welcome", value="dm")
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def greeting_toggle(self, interaction: discord.Interaction, event: str):
        config = await self.get_config(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("❌ Тохиргоо байхгүй. `/greeting_set` ашиглана уу.", ephemeral=True)

        if event == "dm":
            new_state = not config.dm_on_welcome
            await self.bot.db.execute(
                "UPDATE greeting_config SET dm_on_welcome = ? WHERE guild_id = ?",
                int(new_state), str(interaction.guild.id)
            )
            await self.bot.db.commit()
            self.invalidate_cache(interaction.guild.id)
            desc = "DM welcome **{}**".format("✅ Идэвхжлээ" if new_state else "❌ Унтарлаа")
        else:
            col = f"{event}_enabled"
            current = getattr(config, col)
            new_state = not current
            await self.bot.db.execute(
                f"UPDATE greeting_config SET {col} = ? WHERE guild_id = ?",
                int(new_state), str(interaction.guild.id)
            )
            await self.bot.db.commit()
            self.invalidate_cache(interaction.guild.id)
            desc = f"{event.capitalize()} мэдэгдэл **{'✅ Идэвхжлээ' if new_state else '❌ Унтарлаа'}**"

        embed = discord.Embed(title="🔄 Төлөв өөрчлөгдлөө", description=desc, color=SUCCESS_COLOR if new_state else WARNING_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="template_create", description="Шинэ embed загвар үүсгэх")
    @app_commands.default_permissions(manage_guild=True)
    async def template_create(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📝 Шинэ Embed Загвар бүтээх",
            description="Доорх товчийг дарж загвар үүсгэх modal-ийг нээнэ үү.\n\n"
                        "**Бэлэн хувьсагчдын жагсаалтыг `/placeholders` командаар харна уу.**",
            color=GOLD_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        view = TemplateCreateView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="template_edit", description="Загварыг засварлах")
    @app_commands.describe(template_id="Загварын ID")
    @app_commands.default_permissions(manage_guild=True)
    async def template_edit(self, interaction: discord.Interaction, template_id: int):
        template = await self.get_template(template_id)
        if not template:
            return await interaction.response.send_message("❌ Загвар олдсонгүй.", ephemeral=True)
        modal = TemplateCreateModal(template, cog=self)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="template_delete", description="Загвар устгах")
    @app_commands.describe(template_id="Загварын ID")
    @app_commands.default_permissions(manage_guild=True)
    async def template_delete(self, interaction: discord.Interaction, template_id: int):
        await self.bot.db.execute("DELETE FROM greeting_templates WHERE id = ?", template_id)
        await self.bot.db.commit()
        await interaction.response.send_message(f"✅ Загвар {template_id} устгагдлаа.", ephemeral=True)

    @app_commands.command(name="template_list", description="Бүх загваруудыг харах")
    @app_commands.default_permissions(manage_guild=True)
    async def template_list(self, interaction: discord.Interaction):
        templates = await self.get_all_templates(interaction.guild.id, interaction.user.id)
        if not templates:
            return await interaction.response.send_message("❌ Танд ямар ч загвар байхгүй байна.", ephemeral=True)
        embed = discord.Embed(title="📋 Таны загварууд", color=INFO_COLOR)
        for t in templates[:15]:
            embed.add_field(
                name=f"ID: {t['id']} — {t['name']}",
                value=f"```{t['data'].get('description', '')[:80]}...```",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="template_preview", description="Загварыг урьдчилан харах")
    @app_commands.describe(template_id="Загварын ID", member="Гишүүний нэр дээр харуулах")
    @app_commands.default_permissions(manage_guild=True)
    async def template_preview(self, interaction: discord.Interaction, template_id: int, member: Optional[discord.Member] = None):
        template = await self.get_template(template_id)
        if not template:
            return await interaction.response.send_message("❌ Загвар олдсонгүй.", ephemeral=True)
        target = member or interaction.user
        embed = self.build_embed(template, target)
        view = self.build_buttons(template)
        await interaction.response.send_message(
            f"👁️ Загвар ID {template_id}-н урьдчилсан харагдац:",
            embed=embed,
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="placeholders", description="Бүх хувьсагчдыг харах")
    async def placeholders(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Хувьсагчдын жагсаалт",
            description="Welcome/Goodbye/Boost загвартаа дараах хувьсагчдыг ашиглана уу.",
            color=GOLD_COLOR
        )
        for placeholder, desc in PLACEHOLDERS.items():
            embed.add_field(name=placeholder, value=desc, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="greeting_status", description="Одоогийн тохиргоог харах")
    @app_commands.default_permissions(manage_guild=True)
    async def greeting_status(self, interaction: discord.Interaction):
        config = await self.get_config(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("❌ Одоогоор тохиргоо хийгдээгүй.", ephemeral=True)
        embed = discord.Embed(title="📊 Одоогийн тохиргоо", color=INFO_COLOR)
        embed.add_field(name="Welcome", value=f"Суваг: {'<#'+str(config.welcome_channel)+'>' if config.welcome_channel else 'Тохируулаагүй'}\n"
                                               f"Идэвхтэй: {'✅' if config.welcome_enabled else '❌'}\n"
                                               f"Загвар ID: {config.welcome_template_id or 'Анхдагч'}\n"
                                               f"DM: {'✅' if config.dm_on_welcome else '❌'}", inline=False)
        embed.add_field(name="Goodbye", value=f"Суваг: {'<#'+str(config.goodbye_channel)+'>' if config.goodbye_channel else 'Тохируулаагүй'}\n"
                                               f"Идэвхтэй: {'✅' if config.goodbye_enabled else '❌'}\n"
                                               f"Загвар ID: {config.goodbye_template_id or 'Анхдагч'}", inline=False)
        embed.add_field(name="Boost", value=f"Суваг: {'<#'+str(config.boost_channel)+'>' if config.boost_channel else 'Тохируулаагүй'}\n"
                                             f"Идэвхтэй: {'✅' if config.boost_enabled else '❌'}\n"
                                             f"Загвар ID: {config.boost_template_id or 'Анхдагч'}", inline=False)
        if config.log_channel:
            embed.add_field(name="Лог суваг", value=f"<#{config.log_channel}>", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="greeting_reset", description="Бүх тохиргоог устгах (болгоомжтой!)")
    @app_commands.default_permissions(administrator=True)
    async def greeting_reset(self, interaction: discord.Interaction):
        await self.bot.db.execute("DELETE FROM greeting_config WHERE guild_id = ?", str(interaction.guild.id))
        await self.bot.db.commit()
        self.invalidate_cache(interaction.guild.id)
        await interaction.response.send_message("🧹 Бүх мэндчилгээний тохиргоо устгагдлаа.", ephemeral=True)

    @app_commands.command(name="set_log_channel", description="Алдааны лог сувгийг тохируулах")
    @app_commands.describe(channel="Лог суваг")
    @app_commands.default_permissions(manage_guild=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.execute(
            "INSERT INTO greeting_config (guild_id, log_channel) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET log_channel = excluded.log_channel",
            str(interaction.guild.id), channel.id
        )
        await self.bot.db.commit()
        self.invalidate_cache(interaction.guild.id)
        await interaction.response.send_message(f"✅ Лог суваг: {channel.mention}", ephemeral=True)

    # ================= EVENT LISTENERS =================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = await self.get_config(member.guild.id)
        if config and config.is_welcome_active:
            await self.send_greeting(
                config.welcome_channel, config.welcome_template_id, member,
                DEFAULT_TEMPLATES["welcome"],
                send_dm=config.dm_on_welcome,
                log_channel_id=config.log_channel
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        config = await self.get_config(member.guild.id)
        if config and config.is_goodbye_active:
            await self.send_greeting(
                config.goodbye_channel, config.goodbye_template_id, member,
                DEFAULT_TEMPLATES["goodbye"],
                log_channel_id=config.log_channel
            )

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.premium_since is None and after.premium_since is not None:
            config = await self.get_config(after.guild.id)
            if config and config.is_boost_active:
                await self.send_greeting(
                    config.boost_channel, config.boost_template_id, after,
                    DEFAULT_TEMPLATES["boost"],
                    log_channel_id=config.log_channel
                )

async def setup(bot):
    await bot.add_cog(Greetings(bot))