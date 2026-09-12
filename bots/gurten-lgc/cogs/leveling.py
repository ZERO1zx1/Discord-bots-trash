import asyncio, io, json, logging, os, time, random
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import aiohttp, discord
from discord.ext import commands, tasks
from discord import ui
from PIL import Image, ImageDraw, ImageFont

# ---------- DiscordLevelingCard ----------
try:
    from discordLevelingCard import Settings, RankCard
except ImportError:
    raise ImportError("discordLevelingCard package not found. Install with: pip install discordLevelingCard")

# ---------- Logger ----------
log = logging.getLogger(__name__)

# ---------- Font helper (kept for legacy) ----------
try:
    from .font_utils import load_font as _load_font
except ImportError:
    def _load_font(size=40, bold=True):
        paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ] if bold else [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        for p in paths:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except: pass
        return ImageFont.load_default(size)

# ---------- Color constants ----------
EMBED_COLOR   = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
GOLD_COLOR    = 0xfab387
WARNING_COLOR = 0xf9e2af
ERROR_COLOR   = 0xf38ba8
INFO_COLOR    = 0x89b4fa

# ---------- Defaults ----------
DEFAULT_XP_TIERS = [{"max_words":10,"xp":5},{"max_words":30,"xp":10},{"max_words":999,"xp":20}]
DEFAULT_XP_MEDIA = 15
DEFAULT_XP_REACTION = 1
DEFAULT_XP_VOICE_SILENT = 5
DEFAULT_XP_VOICE_TALKING = 15
DEFAULT_MSG_COOLDOWN = 60
DEFAULT_REACT_COOLDOWN = 10
DEFAULT_PROG_TYPE = "arithmetic"
DEFAULT_PROG_BASE = 100
DEFAULT_PROG_STEP = 150
VOICE_INTERVAL_SECS = 180

# ---------- Safe converters ----------
def _safe_int(value, default=0):
    try: return int(value)
    except: return default

def _safe_float(value, default=0.0):
    try: return float(value)
    except: return default

def _safe_bool(value, default=False):
    if isinstance(value, bool): return value
    if isinstance(value, int): return bool(value)
    if isinstance(value, str): return value.lower() in ('1','true','yes','on')
    return default

# ---------- XP progression math ----------
def xp_for_level(level: int, cfg: Dict[str, Any]) -> int:
    if cfg.get("prog_type") == "geometric":
        mult = float(cfg.get("prog_step", 1.5))
        return max(1, int(cfg.get("prog_base", 100) * (mult ** level)))
    return max(1, cfg.get("prog_base", 100) + level * int(cfg.get("prog_step", 150)))

def xp_for_message(content: str, cfg: Dict[str, Any]) -> int:
    words = len(content.split()) if content else 0
    tiers = cfg.get("xp_tiers", DEFAULT_XP_TIERS)
    if isinstance(tiers, str):
        try: tiers = json.loads(tiers)
        except: tiers = DEFAULT_XP_TIERS
    for tier in sorted(tiers, key=lambda t: int(t["max_words"])):
        if words <= int(tier["max_words"]): return int(tier["xp"])
    return int(tiers[-1]["xp"]) if tiers else 5

# ---------- Avatar helper (unused in DLC, kept for other purposes) ----------
async def fetch_avatar(session, url, size=128):
    try:
        async with session.get(url) as resp: data = await resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size,size))
    except: img = Image.new("RGBA",(size,size),(88,101,242,255))
    mask = Image.new("L",(size,size),0)
    ImageDraw.Draw(mask).ellipse((0,0,size,size),fill=255)
    img.putalpha(mask)
    return img

# ---------- Config load/save ----------
async def get_config(db, guild_id: int) -> Dict[str, Any]:
    async with db.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM leveling_config WHERE guild_id = %s", (str(guild_id),))
            row = await cur.fetchone()
    if not row:
        return {
            "enabled": True, "announce_channel": None, "voice_xp_enabled": True,
            "prog_type": "arithmetic", "prog_base": 100, "prog_step": 150,
            "xp_tiers": DEFAULT_XP_TIERS, "xp_media": 15, "xp_reaction": 1,
            "xp_voice_silent": 5, "xp_voice_talking": 15, "msg_cooldown": 60,
            "react_cooldown": 10, "background_url": None, "xp_drop_enabled": False,
            "xp_drop_channel": None, "xp_drop_min": 100, "xp_drop_max": 500,
            "xp_drop_interval": 3600, "cafe_buff_enabled": True, "invite_xp": 0,
            "marriage_bonus": 0.1,
        }
    cols = ["guild_id","enabled","announce_channel","voice_xp_enabled","prog_type","prog_base","prog_step","xp_tiers","xp_media","xp_reaction","xp_voice_silent","xp_voice_talking","msg_cooldown","react_cooldown","background_url","xp_drop_enabled","xp_drop_channel","xp_drop_min","xp_drop_max","xp_drop_interval","cafe_buff_enabled","invite_xp","marriage_bonus"]
    data = {}
    for i, key in enumerate(cols):
        data[key] = row[i] if i < len(row) else None
    return {
        "enabled": _safe_bool(data.get("enabled"), True),
        "announce_channel": data.get("announce_channel"),
        "voice_xp_enabled": _safe_bool(data.get("voice_xp_enabled"), True),
        "prog_type": data.get("prog_type") or "arithmetic",
        "prog_base": _safe_int(data.get("prog_base"), 100),
        "prog_step": _safe_float(data.get("prog_step"), 150.0),
        "xp_tiers": json.loads(data["xp_tiers"]) if data.get("xp_tiers") and data["xp_tiers"].startswith('[') else DEFAULT_XP_TIERS,
        "xp_media": _safe_int(data.get("xp_media"), 15),
        "xp_reaction": _safe_int(data.get("xp_reaction"), 1),
        "xp_voice_silent": _safe_int(data.get("xp_voice_silent"), 5),
        "xp_voice_talking": _safe_int(data.get("xp_voice_talking"), 15),
        "msg_cooldown": _safe_int(data.get("msg_cooldown"), 60),
        "react_cooldown": _safe_int(data.get("react_cooldown"), 10),
        "background_url": data.get("background_url"),
        "xp_drop_enabled": _safe_bool(data.get("xp_drop_enabled"), False),
        "xp_drop_channel": data.get("xp_drop_channel"),
        "xp_drop_min": _safe_int(data.get("xp_drop_min"), 100),
        "xp_drop_max": _safe_int(data.get("xp_drop_max"), 500),
        "xp_drop_interval": _safe_int(data.get("xp_drop_interval"), 3600),
        "cafe_buff_enabled": _safe_bool(data.get("cafe_buff_enabled"), True),
        "invite_xp": _safe_int(data.get("invite_xp"), 0),
        "marriage_bonus": _safe_float(data.get("marriage_bonus"), 0.1),
    }

async def set_config(db, guild_id: int, cfg: Dict[str, Any]):
    async with db.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO leveling_config
                (guild_id, enabled, announce_channel, voice_xp_enabled,
                 prog_type, prog_base, prog_step, xp_tiers,
                 xp_media, xp_reaction, xp_voice_silent, xp_voice_talking,
                 msg_cooldown, react_cooldown, background_url,
                 xp_drop_enabled, xp_drop_channel, xp_drop_min, xp_drop_max, xp_drop_interval,
                 cafe_buff_enabled, invite_xp, marriage_bonus)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    enabled = VALUES(enabled), announce_channel = VALUES(announce_channel),
                    voice_xp_enabled = VALUES(voice_xp_enabled), prog_type = VALUES(prog_type),
                    prog_base = VALUES(prog_base), prog_step = VALUES(prog_step),
                    xp_tiers = VALUES(xp_tiers), xp_media = VALUES(xp_media),
                    xp_reaction = VALUES(xp_reaction), xp_voice_silent = VALUES(xp_voice_silent),
                    xp_voice_talking = VALUES(xp_voice_talking), msg_cooldown = VALUES(msg_cooldown),
                    react_cooldown = VALUES(react_cooldown), background_url = VALUES(background_url),
                    xp_drop_enabled = VALUES(xp_drop_enabled), xp_drop_channel = VALUES(xp_drop_channel),
                    xp_drop_min = VALUES(xp_drop_min), xp_drop_max = VALUES(xp_drop_max),
                    xp_drop_interval = VALUES(xp_drop_interval), cafe_buff_enabled = VALUES(cafe_buff_enabled),
                    invite_xp = VALUES(invite_xp), marriage_bonus = VALUES(marriage_bonus)
            """, (
                str(guild_id), int(cfg.get("enabled",True)), cfg.get("announce_channel"),
                int(cfg.get("voice_xp_enabled",True)), cfg.get("prog_type","arithmetic"),
                int(cfg.get("prog_base",100)), float(cfg.get("prog_step",150)),
                json.dumps(cfg.get("xp_tiers",DEFAULT_XP_TIERS)),
                int(cfg.get("xp_media",15)), int(cfg.get("xp_reaction",1)),
                int(cfg.get("xp_voice_silent",5)), int(cfg.get("xp_voice_talking",15)),
                int(cfg.get("msg_cooldown",60)), int(cfg.get("react_cooldown",10)),
                cfg.get("background_url"), int(cfg.get("xp_drop_enabled",False)),
                cfg.get("xp_drop_channel"), int(cfg.get("xp_drop_min",100)),
                int(cfg.get("xp_drop_max",500)), int(cfg.get("xp_drop_interval",3600)),
                int(cfg.get("cafe_buff_enabled",True)), int(cfg.get("invite_xp",0)),
                float(cfg.get("marriage_bonus",0.1)),
            ))

# ---------- Rank card renderer (DiscordLevelingCard) ----------
async def render_dlc_card(member, level, current_xp, needed_xp, rank_pos, background_url=None):
    try:
        avatar_url = str(member.display_avatar.replace(size=256, format="png").url)
        bg = background_url if isinstance(background_url, str) and background_url.startswith("http") else "#36393f"
        settings = Settings(background=bg, bar_color="#7289da", text_color="white", background_color="#36393f")
        card = RankCard(
            settings=settings,
            avatar=avatar_url,
            level=level,
            username=member.display_name,
            current_exp=current_xp,
            max_exp=needed_xp,
            rank=rank_pos
        )
        # Handle both async and sync versions
        if hasattr(card, 'card1'):
            if asyncio.iscoroutinefunction(card.card1):
                image_bytes = await card.card1()
            else:
                image_bytes = card.card1()
        else:
            # fallback to older method name
            if asyncio.iscoroutinefunction(card.create):
                image_bytes = await card.create()
            else:
                image_bytes = card.create()
        buf = io.BytesIO(image_bytes)
        buf.seek(0)
        return buf
    except Exception as e:
        log.error(f"Rank card render failed: {e}")
        return None

# ---------- UI Views (same as before) ----------
class XPDropView(ui.View):
    def __init__(self, xp_amount, cog):
        super().__init__(timeout=300)
        self.xp_amount = xp_amount; self.cog = cog; self.claimed = set()
    @ui.button(label="🎉 XP авах", style=discord.ButtonStyle.success)
    async def claim(self, interaction, button):
        if interaction.user.id in self.claimed:
            return await interaction.response.send_message("❌ Та аль хэдийн авсан.", ephemeral=True)
        self.claimed.add(interaction.user.id)
        await self.cog.add_xp(interaction.user.id, interaction.guild.id, self.xp_amount,
                             member=interaction.guild.get_member(interaction.user.id))
        await interaction.response.send_message(f"✅ +{self.xp_amount} XP авлаа!", ephemeral=True)

class LevelRewardManagerView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx; self.selected_level = None
    async def build_embed(self):
        entries = await self.cog.get_level_rewards(self.ctx.guild.id)
        embed = discord.Embed(title="🎁 Түвшний мөнгөн шагнал", color=GOLD_COLOR)
        if not entries: embed.description = "Одоогоор ямар ч шагнал тохируулаагүй байна."
        else:
            lines = []
            for e in entries: lines.append(f"**Level {e['level']}** → {e['money']:,} ₮")
            embed.description = "\n".join(lines)
        embed.set_footer(text="Доорх цэсээр түвшин сонгоод 'Шагнал тохируулах' эсвэл 'Устгах' дарна уу.")
        return embed
    async def refresh_message(self, interaction):
        embed = await self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    @ui.select(placeholder="Түвшин сонгох", row=0, min_values=1, max_values=1)
    async def level_select(self, interaction, select):
        self.selected_level = int(select.values[0])
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Түвшин {self.selected_level} сонгогдлоо.", ephemeral=True)
    @ui.button(label="💰 Шагнал тохируулах", style=discord.ButtonStyle.green, row=1)
    async def set_reward_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Эхлээд түвшин сонгоно уу.", ephemeral=True)
        modal = ui.Modal(title="Шагнал тохируулах")
        money_input = ui.TextInput(label="Мөнгөн дүн (₮)", placeholder="5000", required=True)
        modal.add_item(money_input)
        async def on_submit(inter):
            try:
                money = int(money_input.value)
                if money <= 0: raise ValueError
            except: return await inter.response.send_message("❌ Эерэг бүхэл тоо оруулна уу.", ephemeral=True)
            await self.cog.set_level_reward(self.ctx.guild.id, self.selected_level, money)
            await inter.response.send_message(f"✅ Level {self.selected_level} → {money:,} ₮ тохируулагдлаа.", ephemeral=True)
            await self.refresh_message(inter)
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=1)
    async def remove_reward_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Эхлээд түвшин сонгоно уу.", ephemeral=True)
        await self.cog.delete_level_reward(self.ctx.guild.id, self.selected_level)
        await interaction.response.send_message(f"🗑️ Level {self.selected_level} шагнал устгагдлаа.", ephemeral=True)
        await self.refresh_message(interaction)

class LevelRoleManagerView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx
        self.selected_level = None; self.selected_role = None
    async def build_embed(self):
        entries = await self.cog.get_level_roles(self.ctx.guild.id)
        embed = discord.Embed(title="🛠️ Түвшний ролиудыг тохируулах", color=INFO_COLOR)
        if not entries: embed.description = "Одоогоор ямар ч түвшний роль тохируулаагүй байна."
        else:
            lines = []
            for e in entries:
                role = self.ctx.guild.get_role(e["role_id"])
                role_text = role.mention if role else f"<@&{e['role_id']}>"
                lines.append(f"**Level {e['level']}** → {role_text}")
            embed.description = "\n".join(lines)
        embed.set_footer(text="Доорх цэсээр түвшин/роль сонгоод 'Тохируулах' эсвэл 'Устгах' дарна уу.")
        return embed
    async def refresh_message(self, interaction):
        embed = await self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    @ui.select(placeholder="1️⃣ Түвшин сонгох", row=0, min_values=1, max_values=1)
    async def level_select(self, interaction, select):
        self.selected_level = int(select.values[0])
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Түвшин {self.selected_level} сонгогдлоо.", ephemeral=True)
    @ui.select(cls=ui.RoleSelect, placeholder="2️⃣ Роль сонгох", row=1, min_values=1, max_values=1)
    async def role_select(self, interaction, select):
        self.selected_role = select.values[0]
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Роль {self.selected_role.mention} сонгогдлоо.", ephemeral=True)
    @ui.button(label="✅ Тохируулах", style=discord.ButtonStyle.green, row=2)
    async def set_btn(self, interaction, button):
        if self.selected_level is None or self.selected_role is None:
            return await interaction.response.send_message("❌ Түвшин болон роль сонгоно уу.", ephemeral=True)
        await self.cog.set_level_role(self.ctx.guild.id, self.selected_level, self.selected_role.id)
        await interaction.response.send_message(f"✅ Level {self.selected_level} → {self.selected_role.mention}", ephemeral=True)
        await self.refresh_message(interaction)
    @ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=2)
    async def remove_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Түвшин сонгоно уу.", ephemeral=True)
        await self.cog.delete_level_role(self.ctx.guild.id, self.selected_level)
        await interaction.response.send_message(f"🗑️ Level {self.selected_level} устгагдлаа.", ephemeral=True)
        await self.refresh_message(interaction)
    @ui.button(label="🎁 Шагнал", style=discord.ButtonStyle.blurple, row=3)
    async def reward_btn(self, interaction, button):
        view = LevelRewardManagerView(self.cog, self.ctx)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

class LevelingSetupView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx; self.message = None
    async def interaction_check(self, interaction):
        if interaction.user.id == interaction.guild.owner_id or interaction.user.id in self.cog.bot.config.get("co_owners",[]): return True
        await interaction.response.send_message("⛔ Сервер эзэмшигч эсвэл ботын co-owner эрх шаардлагатай.", ephemeral=True)
        return False
    async def refresh(self):
        cfg = await get_config(self.cog.bot.db, self.ctx.guild.id)
        embed = discord.Embed(title="🔧 Түвшний систем тохиргоо", color=INFO_COLOR)
        ch = self.ctx.guild.get_channel(cfg["announce_channel"]) if cfg["announce_channel"] else None
        embed.add_field(name="📢 Мэдэгдэл суваг", value=ch.mention if ch else "Тохируулаагүй", inline=False)
        embed.add_field(name="Систем идэвхтэй", value="✅" if cfg["enabled"] else "❌", inline=True)
        embed.add_field(name="Дуут XP", value="✅" if cfg["voice_xp_enabled"] else "❌", inline=True)
        embed.add_field(name="Cooldown (msg/react)", value=f"{cfg['msg_cooldown']}с / {cfg['react_cooldown']}с", inline=True)
        embed.add_field(name="Прогресс", value=f"{cfg['prog_type']} (base={cfg['prog_base']}, step={cfg['prog_step']})", inline=True)
        embed.add_field(name="Урилгын XP", value=str(cfg.get("invite_xp",0)), inline=True)
        embed.add_field(name="Гэрлэлтийн урамшуулал", value=f"{cfg.get('marriage_bonus',0.1)*100}%", inline=True)
        await self.message.edit(embed=embed, view=self)
    @ui.button(label="📢 Суваг сонгох", style=discord.ButtonStyle.secondary, row=0)
    async def channel_btn(self, interaction, button):
        opts = []
        for ch in interaction.guild.text_channels[:25]:
            opts.append(discord.SelectOption(label=f"#{ch.name}", value=str(ch.id)))
        if not opts: return await interaction.response.send_message("Сонгох суваг байхгүй.", ephemeral=True)
        class ChannelSelect(ui.Select):
            def __init__(self): super().__init__(placeholder="Мэдэгдэл сувгаа сонго...", options=opts)
            async def callback(self, inter):
                cfg = await get_config(self.view.cog.bot.db, self.view.ctx.guild.id)
                cfg["announce_channel"] = int(self.values[0])
                await set_config(self.view.cog.bot.db, self.view.ctx.guild.id, cfg)
                await inter.response.send_message("✅ Суваг тохируулагдлаа.", ephemeral=True)
                await self.view.refresh()
        view = ui.View(timeout=60); view.add_item(ChannelSelect())
        await interaction.response.send_message("Сувгаа сонгоно уу:", view=view, ephemeral=True)
    @ui.button(label="🔄 Систем унтраах/асаах", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction, button):
        cfg = await get_config(self.cog.bot.db, self.ctx.guild.id)
        cfg["enabled"] = not cfg["enabled"]
        await set_config(self.cog.bot.db, self.ctx.guild.id, cfg)
        await interaction.response.send_message(f"Систем {'ассан' if cfg['enabled'] else 'унтарсан'}.", ephemeral=True)
        await self.refresh()
    @ui.button(label="⏱ Cooldown тохируулах", style=discord.ButtonStyle.secondary, row=1)
    async def cd_btn(self, interaction, button):
        modal = ui.Modal(title="Cooldown (секунд)")
        msg_inp = ui.TextInput(label="Мессеж", placeholder="60", required=True)
        react_inp = ui.TextInput(label="Реакц", placeholder="10", required=True)
        modal.add_item(msg_inp); modal.add_item(react_inp)
        async def on_submit(inter):
            try:
                m = int(msg_inp.value); r = int(react_inp.value)
                if m<=0 or r<=0: raise ValueError
            except: return await inter.response.send_message("❌ Эерэг бүхэл тоо оруулна уу.", ephemeral=True)
            cfg = await get_config(self.cog.bot.db, self.ctx.guild.id)
            cfg["msg_cooldown"] = m; cfg["react_cooldown"] = r
            await set_config(self.cog.bot.db, self.ctx.guild.id, cfg)
            await inter.response.send_message("✅ Cooldown шинэчлэгдлээ.", ephemeral=True)
            await self.refresh()
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🎨 Арын зураг URL", style=discord.ButtonStyle.secondary, row=1)
    async def bg_btn(self, interaction, button):
        modal = ui.Modal(title="Арын зураг")
        url_inp = ui.TextInput(label="Зургийн URL", placeholder="https://...", required=True)
        modal.add_item(url_inp)
        async def on_submit(inter):
            cfg = await get_config(self.cog.bot.db, self.ctx.guild.id)
            cfg["background_url"] = url_inp.value.strip()
            await set_config(self.cog.bot.db, self.ctx.guild.id, cfg)
            await inter.response.send_message("✅ Арын зураг тохируулагдлаа.", ephemeral=True)
            await self.refresh()
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🎖️ Түвшний роль тохиргоо", style=discord.ButtonStyle.success, row=2)
    async def role_manager_btn(self, interaction, button):
        view = LevelRoleManagerView(self.cog, self.ctx)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

# ================== MAIN COG ==================
class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self._msg_cooldown = {}
        self._react_cooldown = {}
        self._voice_join = {}
        self._voice_last_xp = {}
        self.voice_task = None
        self.xp_drop_task = None

    async def cog_load(self):
        await self.init_db()
        self.session = aiohttp.ClientSession()
        self.voice_task = asyncio.create_task(self._voice_xp_loop())
        self.xp_drop_task = self.xp_drop_loop.start()

    async def cog_unload(self):
        if self.voice_task: self.voice_task.cancel()
        if self.xp_drop_task: self.xp_drop_task.cancel()
        if self.session: await self.session.close()

    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""CREATE TABLE IF NOT EXISTS levels (
                    user_id VARCHAR(255), guild_id VARCHAR(255),
                    xp BIGINT DEFAULT 0, level INT DEFAULT 1,
                    message_count INT DEFAULT 0, voice_seconds BIGINT DEFAULT 0,
                    reaction_count INT DEFAULT 0, PRIMARY KEY (user_id, guild_id)) ENGINE=InnoDB""")
                await cur.execute("""CREATE TABLE IF NOT EXISTS leveling_config (
                    guild_id VARCHAR(255) PRIMARY KEY, enabled TINYINT DEFAULT 1,
                    announce_channel BIGINT, voice_xp_enabled TINYINT DEFAULT 1,
                    prog_type VARCHAR(20) DEFAULT 'arithmetic', prog_base INT DEFAULT 100,
                    prog_step FLOAT DEFAULT 150, xp_tiers TEXT, xp_media INT DEFAULT 15,
                    xp_reaction INT DEFAULT 1, xp_voice_silent INT DEFAULT 5,
                    xp_voice_talking INT DEFAULT 15, msg_cooldown INT DEFAULT 60,
                    react_cooldown INT DEFAULT 10, background_url TEXT,
                    xp_drop_enabled TINYINT DEFAULT 0, xp_drop_channel BIGINT,
                    xp_drop_min INT DEFAULT 100, xp_drop_max INT DEFAULT 500,
                    xp_drop_interval INT DEFAULT 3600, cafe_buff_enabled TINYINT DEFAULT 1,
                    invite_xp INT DEFAULT 0, marriage_bonus FLOAT DEFAULT 0.1) ENGINE=InnoDB""")
                await cur.execute("""CREATE TABLE IF NOT EXISTS leveling_exceptions (
                    guild_id VARCHAR(255), type VARCHAR(10), target_id BIGINT,
                    PRIMARY KEY (guild_id, type, target_id)) ENGINE=InnoDB""")
                await cur.execute("""CREATE TABLE IF NOT EXISTS level_roles (
                    guild_id VARCHAR(255), level INT, role_id BIGINT,
                    PRIMARY KEY (guild_id, level)) ENGINE=InnoDB""")
                await cur.execute("""CREATE TABLE IF NOT EXISTS level_rewards (
                    guild_id VARCHAR(255), level INT, money INT DEFAULT 0,
                    PRIMARY KEY (guild_id, level)) ENGINE=InnoDB""")
                # Add missing columns if they don't exist
                for col, dtype in [("message_count","INT DEFAULT 0"),("voice_seconds","BIGINT DEFAULT 0"),("reaction_count","INT DEFAULT 0")]:
                    try: await cur.execute(f"ALTER TABLE levels ADD COLUMN {col} {dtype}")
                    except: pass
                for col, dtype in [("cafe_buff_enabled","TINYINT DEFAULT 1"),("invite_xp","INT DEFAULT 0"),("marriage_bonus","FLOAT DEFAULT 0.1")]:
                    try: await cur.execute(f"ALTER TABLE leveling_config ADD COLUMN {col} {dtype}")
                    except: pass

    def _on_cooldown(self, storage, user_id, seconds, guild_id=0):
        now = time.monotonic()
        key = (guild_id, user_id)
        last = storage.get(key, 0)
        if now - last < seconds: return True
        storage[key] = now
        return False

    async def get_active_buff(self, user_id, guild_id):
        mult = 1.0
        try:
            cafe = self.bot.get_cog("Cafe")
            if cafe:
                cfg = await get_config(self.bot.db, guild_id)
                if cfg.get("cafe_buff_enabled", True) and hasattr(cafe, 'get_buff'):
                    buff = cafe.get_buff(user_id, guild_id)
                    if asyncio.iscoroutine(buff): buff = await buff
                    if buff and buff.get('type') == 'xp_boost': mult *= buff.get('xp_mult', 1.0)
        except: pass
        try:
            marriage = self.bot.get_cog("Marriage")
            if marriage and hasattr(marriage, 'get_married_bonus'):
                bonus = marriage.get_married_bonus(user_id, guild_id)
                if asyncio.iscoroutine(bonus): bonus = await bonus
                if bonus: mult *= (1 + bonus)
        except: pass
        return mult

    async def _add_xp(self, user_id, guild_id, amount, member=None, check_mute=True, channel=None):
        if amount == 0: return
        if member and check_mute:
            try:
                if member.timed_out_until and member.timed_out_until > datetime.now(timezone.utc): return
                if hasattr(member,'voice') and member.voice and (member.voice.mute or member.voice.self_mute): return
            except: pass
        if amount > 0:
            try:
                multiplier = await self.get_active_buff(user_id, guild_id)
                amount = int(amount * multiplier)
            except: pass
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT xp, level FROM levels WHERE user_id=%s AND guild_id=%s",(str(user_id),str(guild_id)))
                row = await cur.fetchone()
                xp, level = row if row else (0,1)
                old_level = level
                new_xp = xp + amount
                cfg = await get_config(self.bot.db, guild_id)
                leveled_up = False
                while new_xp < 0 and level > 1:
                    level -= 1
                    new_xp += xp_for_level(level, cfg)
                if new_xp < 0:
                    new_xp = 0
                while True:
                    needed = xp_for_level(level, cfg)
                    if new_xp >= needed:
                        new_xp -= needed; level += 1; leveled_up = True
                    else: break
                await cur.execute("INSERT INTO levels (user_id,guild_id,xp,level) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE xp=%s, level=%s",
                                  (str(user_id),str(guild_id),new_xp,level,new_xp,level))
        if leveled_up and member:
            await self._announce_level_up(member, old_level, level, new_xp, channel)
            try:
                quests = self.bot.get_cog("Quests")
                if quests and hasattr(quests,'trigger_event'): await quests.trigger_event(member.id, guild_id, "level_up", 1)
            except: pass

    async def _announce_level_up(self, member, old, new, current_xp, source_channel):
        guild = member.guild
        cfg = await get_config(self.bot.db, guild.id)
        # Level reward
        try:
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT money FROM level_rewards WHERE guild_id=%s AND level=%s",(str(guild.id),new))
                    reward_row = await cur.fetchone()
            if reward_row and reward_row[0] > 0:
                economy = self.bot.get_cog("Economy")
                if economy:
                    await economy.update_balance(member.id, guild.id, reward_row[0])
                    embed = discord.Embed(title="🎁 Түвшний шагнал!", description=f"{member.mention} Lv.{new} хүрсэн тул **{reward_row[0]:,}₮** авлаа!", color=GOLD_COLOR)
                    ch = guild.get_channel(cfg.get("announce_channel")) if cfg.get("announce_channel") else source_channel
                    if ch:
                        try: await ch.send(embed=embed)
                        except: pass
        except: pass
        # Level role
        try:
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT role_id FROM level_roles WHERE guild_id=%s AND level=%s",(str(guild.id),new))
                    row = await cur.fetchone()
            if row:
                role = guild.get_role(row[0])
                if role and role not in member.roles: await member.add_roles(role, reason=f"Level {new}")
        except: pass
        channel = guild.get_channel(cfg.get("announce_channel")) if cfg.get("announce_channel") else source_channel
        if not channel: return
        needed = xp_for_level(new, cfg)
        rank_pos = await self.get_rank_position(member.id, guild.id)
        try:
            buf = await render_dlc_card(member, new, current_xp, needed, rank_pos, cfg.get("background_url"))
            if buf:
                file = discord.File(buf, filename="levelup.png")
                try: await channel.send(content=member.mention, file=file)
                except: pass
            else:
                embed = discord.Embed(title="🎉 Түвшин ахисан!", description=f"{member.mention} Lv.{new} хүрлээ!", color=GOLD_COLOR)
                try: await channel.send(embed=embed)
                except: pass
        except Exception as e: log.error(f"Level up announcement: {e}")

    # ========== PUBLIC API ==========
    async def add_xp(self, user_id, guild_id, amount, member=None, check_mute=True, channel=None):
        await self._add_xp(user_id, guild_id, amount, member, check_mute, channel)
    async def remove_xp(self, user_id, guild_id, amount, member=None):
        await self._add_xp(user_id, guild_id, -amount, member, check_mute=False)
    async def transfer_xp(self, from_id, to_id, guild_id, amount):
        if await self.get_total_xp(from_id, guild_id) < amount: return False
        await self._add_xp(from_id, guild_id, -amount); await self._add_xp(to_id, guild_id, amount)
        return True
    async def get_total_xp(self, user_id, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT xp, level FROM levels WHERE user_id=%s AND guild_id=%s",(str(user_id),str(guild_id)))
                row = await cur.fetchone()
        if not row: return 0
        xp, level = row
        cfg = await get_config(self.bot.db, guild_id)
        return sum(xp_for_level(l,cfg) for l in range(level)) + xp
    async def get_level(self, user_id, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT level FROM levels WHERE user_id=%s AND guild_id=%s",(str(user_id),str(guild_id)))
                row = await cur.fetchone()
        return row[0] if row else 1
    async def get_rank_position(self, user_id, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT user_id FROM levels WHERE guild_id=%s ORDER BY level DESC, xp DESC",(str(guild_id),))
                rows = await cur.fetchall()
        for i,(uid,) in enumerate(rows):
            if int(uid) == int(user_id): return i+1
        return len(rows)+1
    async def set_xp(self, user_id, guild_id, xp):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                cfg = await get_config(self.bot.db, guild_id)
                level = 1; remaining = xp
                while True:
                    needed = xp_for_level(level, cfg)
                    if remaining >= needed: remaining -= needed; level += 1
                    else: break
                await cur.execute("INSERT INTO levels (user_id,guild_id,xp,level) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE xp=%s,level=%s",
                                  (str(user_id),str(guild_id),remaining,level,remaining,level))
    async def set_level(self, user_id, guild_id, level):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT INTO levels (user_id,guild_id,xp,level) VALUES (%s,%s,0,%s) ON DUPLICATE KEY UPDATE xp=0,level=%s",
                                  (str(user_id),str(guild_id),level,level))

    async def get_config(self, guild_id):
        return await get_config(self.bot.db, guild_id)
    def xp_for_level(self, level, cfg):
        return xp_for_level(level, cfg)
    def get_rank_info(self, level):
        if level < 10: return "Эхлэгч", "🌱"
        if level < 25: return "Сонирхогч", "⭐"
        if level < 50: return "Мэргэжилтэн", "🌟"
        if level < 100: return "Мастер", "💎"
        return "Домог", "👑"

    async def award_invite_xp(self, inviter_id, guild_id):
        cfg = await get_config(self.bot.db, guild_id)
        xp_reward = cfg.get("invite_xp", 0)
        if xp_reward > 0:
            guild = self.bot.get_guild(guild_id)
            member = guild.get_member(inviter_id) if guild else None
            await self._add_xp(inviter_id, guild_id, xp_reward, member=member)

    async def get_exceptions(self, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT type, target_id FROM leveling_exceptions WHERE guild_id=%s",(str(guild_id),))
                rows = await cur.fetchall()
        return {"channels":[r[1] for r in rows if r[0]=="channel"], "users":[r[1] for r in rows if r[0]=="user"]}
    async def add_exception(self, guild_id, exc_type, target_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT IGNORE INTO leveling_exceptions VALUES (%s,%s,%s)",(str(guild_id),exc_type,target_id))
    async def remove_exception(self, guild_id, exc_type, target_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM leveling_exceptions WHERE guild_id=%s AND type=%s AND target_id=%s",(str(guild_id),exc_type,target_id))

    async def get_level_roles(self, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT level, role_id FROM level_roles WHERE guild_id=%s ORDER BY level",(str(guild_id),))
                return [{"level":r[0],"role_id":r[1]} for r in await cur.fetchall()]
    async def set_level_role(self, guild_id, level, role_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("REPLACE INTO level_roles (guild_id,level,role_id) VALUES (%s,%s,%s)",(str(guild_id),level,role_id))
    async def delete_level_role(self, guild_id, level):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM level_roles WHERE guild_id=%s AND level=%s",(str(guild_id),level))

    async def get_level_rewards(self, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT level, money FROM level_rewards WHERE guild_id=%s ORDER BY level",(str(guild_id),))
                return [{"level":r[0],"money":r[1]} for r in await cur.fetchall()]
    async def set_level_reward(self, guild_id, level, money):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("REPLACE INTO level_rewards (guild_id,level,money) VALUES (%s,%s,%s)",(str(guild_id),level,money))
    async def delete_level_reward(self, guild_id, level):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM level_rewards WHERE guild_id=%s AND level=%s",(str(guild_id),level))

    # ========== EVENT LISTENERS ==========
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        cfg = await get_config(self.bot.db, message.guild.id)
        if not cfg["enabled"]: return
        exc = await self.get_exceptions(message.guild.id)
        if message.channel.id in exc["channels"] or message.author.id in exc["users"]: return
        if self._on_cooldown(self._msg_cooldown, message.author.id, cfg["msg_cooldown"], message.guild.id): return
        xp = xp_for_message(message.content, cfg)
        if message.attachments: xp += cfg["xp_media"]
        await self._add_xp(message.author.id, message.guild.id, xp, member=message.author, channel=message.channel)
        try:
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("INSERT INTO levels (user_id,guild_id,message_count) VALUES (%s,%s,1) ON DUPLICATE KEY UPDATE message_count=message_count+1",
                                      (str(message.author.id),str(message.guild.id)))
        except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id or payload.user_id == self.bot.user.id: return
        cfg = await get_config(self.bot.db, payload.guild_id)
        if not cfg["enabled"]: return
        exc = await self.get_exceptions(payload.guild_id)
        if payload.channel_id in exc["channels"] or payload.user_id in exc["users"]: return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return
        if self._on_cooldown(self._react_cooldown, payload.user_id, cfg["react_cooldown"], payload.guild_id): return
        await self._add_xp(payload.user_id, payload.guild_id, cfg["xp_reaction"], member=member, check_mute=False)
        try:
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("INSERT INTO levels (user_id,guild_id,reaction_count) VALUES (%s,%s,1) ON DUPLICATE KEY UPDATE reaction_count=reaction_count+1",
                                      (str(payload.user_id),str(payload.guild_id)))
        except: pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and not after.channel:
            key = (member.guild.id, member.id)
            self._voice_join.pop(key, None); self._voice_last_xp.pop(key, None)

    async def _voice_xp_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = time.monotonic()
                for guild in self.bot.guilds:
                    cfg = await get_config(self.bot.db, guild.id)
                    if not cfg["enabled"] or not cfg.get("voice_xp_enabled",True): continue
                    exc = await self.get_exceptions(guild.id)
                    for vc in guild.voice_channels:
                        for member in vc.members:
                            if member.bot or member.id in exc["users"] or member.voice.deaf or member.voice.self_deaf: continue
                            key = (guild.id, member.id)
                            if key not in self._voice_join: self._voice_join[key] = now; self._voice_last_xp[key] = now
                            if now - self._voice_last_xp.get(key,0) >= VOICE_INTERVAL_SECS:
                                talking = not (member.voice.mute or member.voice.self_mute)
                                xp = cfg["xp_voice_talking"] if talking else cfg["xp_voice_silent"]
                                self._voice_last_xp[key] = now
                                await self._add_xp(member.id, guild.id, xp, member=member, check_mute=False)
                                try:
                                    async with self.bot.db.acquire() as conn:
                                        async with conn.cursor() as cur:
                                            await cur.execute("INSERT INTO levels (user_id,guild_id,voice_seconds) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE voice_seconds=voice_seconds+%s",
                                                              (str(member.id),str(guild.id),VOICE_INTERVAL_SECS,VOICE_INTERVAL_SECS))
                                except: pass
            except Exception as e: log.error(f"Voice XP loop: {e}")
            await asyncio.sleep(30)

    @tasks.loop(minutes=1)
    async def xp_drop_loop(self):
        for guild in self.bot.guilds:
            try:
                cfg = await get_config(self.bot.db, guild.id)
                if not cfg["xp_drop_enabled"]: continue
                channel = guild.get_channel(cfg["xp_drop_channel"])
                if not channel: continue
                if random.random() < 0.1:
                    xp = random.randint(cfg["xp_drop_min"], cfg["xp_drop_max"])
                    embed = discord.Embed(title="🌟 XP DROP!", description=f"Түргэн! Дараагийн товчийг дарж **{xp} XP** аваарай!", color=GOLD_COLOR)
                    view = XPDropView(xp, self)
                    await channel.send(embed=embed, view=view)
            except Exception as e: log.error(f"XP drop: {e}")

    @xp_drop_loop.before_loop
    async def before_xp_drop_loop(self): await self.bot.wait_until_ready()

    # ========== COMMANDS ==========
    @commands.hybrid_command(name="grank", aliases=["rank","lvl"])
    async def grank(self, ctx, user: discord.Member = None):
        target = user or ctx.author
        await ctx.defer()
        total_xp = await self.get_total_xp(target.id, ctx.guild.id)
        level = await self.get_level(target.id, ctx.guild.id)
        cfg = await get_config(self.bot.db, ctx.guild.id)
        xp_in_level = total_xp - sum(xp_for_level(l,cfg) for l in range(level))
        needed = xp_for_level(level, cfg)
        rank = await self.get_rank_position(target.id, ctx.guild.id)
        try:
            buf = await render_dlc_card(target, level, xp_in_level, needed, rank, cfg.get("background_url"))
            if buf:
                file = discord.File(buf, filename="rank.png")
                embed = discord.Embed(color=0x7289da)
                embed.set_image(url="attachment://rank.png")
                embed.set_footer(text=f"Rank #{rank}  •  Total XP: {total_xp:,}")
                await ctx.send(embed=embed, file=file)
            else:
                embed = discord.Embed(title=f"📊 {target.display_name}", description=f"**Level:** {level}\n**XP:** {xp_in_level}/{needed}\n**Rank:** #{rank}", color=0x7289da)
                embed.set_footer(text=f"Total XP: {total_xp:,}")
                await ctx.send(embed=embed)
        except Exception as e: await ctx.send(f"❌ Rank карт үүсгэхэд алдаа гарлаа: {e}", ephemeral=True)

    # ========== NEW: Server Activity Command ==========
    @commands.hybrid_command(name="serveractivity", aliases=["activity"])
    async def server_activity(self, ctx):
        """Серверийн идэвхтэй байдлыг харах"""
        guild = ctx.guild
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        offline = guild.member_count - online
        voice_count = sum(1 for vc in guild.voice_channels for m in vc.members)

        # Message count from database (all-time active chatters)
        active_chatters = 0
        try:
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM levels WHERE guild_id=%s AND message_count > 0", (str(guild.id),))
                    active_chatters = (await cur.fetchone())[0]
        except: pass

        embed = discord.Embed(title=f"📈 {guild.name} - Server Activity", color=SUCCESS_COLOR)
        embed.add_field(name="👥 Members", value=f"Total: {guild.member_count}\nOnline: {online}\nOffline: {offline}")
        embed.add_field(name="🔊 Voice", value=f"Currently in VC: {voice_count}")
        embed.add_field(name="💬 Text Chatters (all-time)", value=active_chatters)
        embed.set_footer(text="Note: Text chatters count is all-time, not 24h. To get 24h stats, add a last_message_time column.")
        await ctx.send(embed=embed)

    async def _is_allowed(self, user):
        try:
            cfg = self.bot.config
            return user.id == cfg.get("owner_id") or user.id in cfg.get("co_owners",[])
        except: return False

    @commands.command(name="addxp")
    async def addxp_cmd(self, ctx, user: discord.Member, amount: int):
        if not await self._is_allowed(ctx.author): return await ctx.send("⛔ Зөвхөн бот эзэмшигч эсвэл co-owner ашиглах боломжтой.", ephemeral=True)
        if amount <= 0: return await ctx.send("❌ Эерэг тоо оруулна уу.", ephemeral=True)
        await self._add_xp(user.id, ctx.guild.id, amount, member=user, check_mute=False)
        await ctx.send(f"✅ {user.display_name}-д {amount} XP нэмлээ.")

    @commands.command(name="removexp")
    async def removexp_cmd(self, ctx, user: discord.Member, amount: int):
        if not await self._is_allowed(ctx.author): return await ctx.send("⛔ Зөвхөн бот эзэмшигч эсвэл co-owner ашиглах боломжтой.", ephemeral=True)
        if amount <= 0: return await ctx.send("❌ Эерэг тоо оруулна уу.", ephemeral=True)
        await self._add_xp(user.id, ctx.guild.id, -amount, member=user, check_mute=False)
        await ctx.send(f"✅ {user.display_name}-ээс {amount} XP хасагдлаа.")

    @commands.command(name="leveling_setup", aliases=["lsetup"])
    async def leveling_setup(self, ctx):
        if not (ctx.author.guild_permissions.administrator or await self._is_allowed(ctx.author)):
            return await ctx.send("⛔ Админ эрх шаардлагатай.", ephemeral=True)
        cfg = await get_config(self.bot.db, ctx.guild.id)
        embed = discord.Embed(title="🔧 Түвшний систем тохиргоо", color=INFO_COLOR)
        ch = ctx.guild.get_channel(cfg["announce_channel"]) if cfg["announce_channel"] else None
        embed.add_field(name="📢 Мэдэгдэл суваг", value=ch.mention if ch else "Тохируулаагүй", inline=False)
        embed.add_field(name="Систем идэвхтэй", value="✅" if cfg["enabled"] else "❌", inline=True)
        embed.add_field(name="Дуут XP", value="✅" if cfg["voice_xp_enabled"] else "❌", inline=True)
        embed.add_field(name="Cooldown (msg/react)", value=f"{cfg['msg_cooldown']}с / {cfg['react_cooldown']}с", inline=True)
        embed.add_field(name="Прогресс", value=f"{cfg['prog_type']} (base={cfg['prog_base']}, step={cfg['prog_step']})", inline=True)
        embed.add_field(name="Урилгын XP", value=str(cfg.get("invite_xp",0)), inline=True)
        embed.add_field(name="Гэрлэлтийн урамшуулал", value=f"{cfg.get('marriage_bonus',0.1)*100}%", inline=True)
        view = LevelingSetupView(self, ctx)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

async def setup(bot):
    await bot.add_cog(Leveling(bot))