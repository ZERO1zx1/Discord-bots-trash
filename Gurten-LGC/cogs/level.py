import asyncio, io, json, logging, os, time, random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import aiohttp, discord
from discord.ext import commands, tasks
from discord import ui
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

# ---------- Logger ----------
log = logging.getLogger(__name__)

# ---------- Paths (FIXED) ----------
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
DEFAULT_ASSET_FONT = os.path.join(ASSETS_DIR, "levelfont.otf")

# Ensure assets directory exists
os.makedirs(ASSETS_DIR, exist_ok=True)

# ---------- Font helper (kept for legacy) ----------
try:
    from .font_utils import load_font as _load_font, list_fonts as _list_fonts, find_font as _find_font
except ImportError:
    def _list_fonts():
        return []

    def _find_font(name: Optional[str] = None, bold: Optional[bool] = None) -> Optional[str]:
        if not name:
            return None
        return None

    def _load_font(size: int = 40, bold: bool = True, font_name: Optional[str] = None):
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf"
        ] if bold else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf"
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except:
                    pass
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

# ========== NEW: BATTLE XP SYSTEM DEFAULTS ==========
DEFAULT_BATTLE_WIN_XP = 50
DEFAULT_BATTLE_LOSE_XP = 20
DEFAULT_BATTLE_DRAW_XP = 35
DEFAULT_BATTLE_COOLDOWN = 300  # 5 минут

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


def _resolve_font_name(cfg: Optional[Dict[str, Any]] = None) -> Optional[str]:
    if cfg is None:
        cfg = {}
    font_name = cfg.get("font_name")
    if font_name:
        found = _find_font(font_name)
        if found:
            return found
    fonts = _list_fonts()
    if fonts:
        return random.choice(fonts)
    return None


async def _load_background_image(url: Optional[str]):
    if not url:
        return None

    if isinstance(url, str) and url.startswith(("http://", "https://")):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception:
            return None

    if isinstance(url, str):
        candidate_paths = []
        if os.path.isabs(url):
            candidate_paths.append(url)
        else:
            candidate_paths.extend([
                os.path.join(ASSETS_DIR, url),
                os.path.join(os.path.dirname(__file__), url),
                os.path.join(os.getcwd(), url),
            ])
        for path in candidate_paths:
            if os.path.exists(path):
                try:
                    return Image.open(path).convert("RGBA")
                except Exception as e:
                    log.warning(f"Failed to load background image from {path}: {e}")
                    continue
    return None


# ========== FIXED: Asset loading with better error handling ==========
async def _load_overlay(overlay_name: str, width: int, height: int) -> Optional[Image.Image]:
    """Load and resize overlay with comprehensive error handling"""
    candidate_paths = [
        os.path.join(ASSETS_DIR, overlay_name),
        os.path.join(os.path.dirname(__file__), "assets", overlay_name),
        os.path.join(os.getcwd(), "assets", overlay_name),
    ]
    
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                overlay = Image.open(path).convert("RGBA")
                overlay = overlay.resize((width, height), resample=Resampling.LANCZOS)
                log.debug(f"Successfully loaded overlay: {overlay_name} from {path}")
                return overlay
            except Exception as e:
                log.warning(f"Error loading overlay {overlay_name} from {path}: {e}")
                continue
    
    log.warning(f"Overlay not found: {overlay_name}")
    return None


async def render_dlc_card(member, level, xp, needed, rank, background_url=None, font_name: Optional[str] = None):
    try:
        width, height = 900, 360
        base = Image.new("RGBA", (width, height), (20, 25, 35, 255))

        # Load background
        background = await _load_background_image(background_url)
        if background:
            try:
                background = background.resize((width, height), resample=Resampling.LANCZOS)
                base.alpha_composite(background)
            except Exception as e:
                log.warning(f"Failed to composite background: {e}")

        # ========== FIXED: Better overlay loading ==========
        for overlay_name in ["overlay1.png", "curveborder.png"]:
            overlay = await _load_overlay(overlay_name, width, height)
            if overlay:
                try:
                    base.alpha_composite(overlay)
                except Exception as e:
                    log.warning(f"Failed to composite overlay {overlay_name}: {e}")

        draw = ImageDraw.Draw(base)
        
        # Avatar handling
        avatar_url = None
        try:
            avatar_url = getattr(member.display_avatar, "url", None)
            if avatar_url and hasattr(member.display_avatar, "replace"):
                avatar_url = member.display_avatar.replace(size=256).url
        except Exception:
            avatar_url = None

        if not avatar_url and getattr(member, "avatar", None):
            try:
                avatar_url = member.avatar.url
            except Exception:
                avatar_url = None

        if avatar_url:
            avatar = await fetch_avatar(avatar_url, 160)
            if avatar is None:
                avatar = Image.new("RGBA", (160, 160), (88, 101, 242, 255))
        else:
            avatar = Image.new("RGBA", (160, 160), (88, 101, 242, 255))

        avatar = avatar.convert("RGBA").resize((160, 160), resample=Resampling.LANCZOS)
        mask = Image.new("L", (160, 160), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 159, 159), fill=255)
        avatar.putalpha(mask)
        base.alpha_composite(avatar, dest=(50, 100))

        # Font loading with better fallback
        font_choice = font_name or _resolve_font_name()
        font_main = _load_font(46, bold=True, font_name=font_choice)
        font_sub = _load_font(28, bold=False, font_name=font_choice)
        font_small = _load_font(18, bold=False, font_name=font_choice)
        
        if font_main is None:
            if os.path.exists(DEFAULT_ASSET_FONT):
                try:
                    font_main = ImageFont.truetype(DEFAULT_ASSET_FONT, 46)
                    log.debug(f"Loaded font from {DEFAULT_ASSET_FONT}")
                except Exception as e:
                    log.warning(f"Failed to load custom font: {e}")
                    font_main = ImageFont.load_default()
            else:
                log.warning(f"Default font file not found at {DEFAULT_ASSET_FONT}, using fallback")
                font_main = ImageFont.load_default()
        
        if font_sub is None:
            font_sub = font_main or ImageFont.load_default()
        if font_small is None:
            font_small = font_main or ImageFont.load_default()

        # Text rendering (Монголчилсон)
        title = member.display_name[:24]
        draw.text((240, 80), title, font=font_main, fill=(255, 255, 255, 255))
        draw.text((240, 150), f"Түвшин {level}", font=font_sub, fill=(234, 179, 8, 255))
        draw.text((240, 190), f"Байр #{rank}", font=font_sub, fill=(200, 200, 200, 255))

        # XP bar
        bar_x, bar_y, bar_w, bar_h = 240, 250, 580, 32
        draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=14, fill=(60, 67, 82, 255))
        fill_w = int(bar_w * min(1.0, xp / max(1, needed)))
        if fill_w > 0:
            draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=14, fill=(114, 137, 218, 255))
        xp_text = f"{xp:,}/{needed:,} XP"
        tx_w, tx_h = draw.textbbox((0, 0), xp_text, font=font_small)[2:]
        draw.text((bar_x + (bar_w - tx_w) // 2, bar_y + (bar_h - tx_h) // 2), xp_text, font=font_small, fill=(255, 255, 255, 255))

        footer_text = f"{member.name} • Gurten LGC-ээр бүтээгдсэн"
        draw.text((240, 310), footer_text, font=font_small, fill=(170, 170, 170, 255))

        buffer = io.BytesIO()
        base.save(buffer, "PNG")
        buffer.seek(0)
        return buffer
    except Exception as e:
        log.error(f"render_dlc_card error: {e}", exc_info=True)
        return None

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

# ---------- Avatar helper ----------
async def fetch_avatar(url, size=128):
    if not url:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"avatar fetch failed: {resp.status}")
                data = await resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size), resample=Resampling.LANCZOS)
    except Exception:
        return None
    return img

# ========== NEW: BATTLE XP SYSTEM ==========
class BattleXPSystem:
    """Шинэ тулааны XP систем – хэрэглэгчид хоорондоо тулалдаж XP авна"""
    
    def __init__(self):
        self.active_battles: Dict[tuple, Dict[str, Any]] = {}
        self.battle_cooldowns: Dict[int, float] = {}
    
    async def start_battle(self, challenger_id: int, opponent_id: int, db, guild_id: int) -> bool:
        """Хоёр хэрэглэгчийн тулааныг эхлүүлэх"""
        now = time.time()
        key = (challenger_id, opponent_id)
        
        # Тулаан идэвхтэй эсэхийг шалгах
        if key in self.active_battles or (opponent_id, challenger_id) in self.active_battles:
            return False
        
        # Хөргөлтийн хугацаа шалгах
        if challenger_id in self.battle_cooldowns:
            if now - self.battle_cooldowns[challenger_id] < DEFAULT_BATTLE_COOLDOWN:
                return False
        
        self.active_battles[key] = {
            "challenger": challenger_id,
            "opponent": opponent_id,
            "started": now,
            "guild_id": guild_id,
            "status": "хүлээгдэж байна"
        }
        
        return True
    
    async def resolve_battle(self, key: tuple, outcome: str) -> Dict[str, int]:
        """Тулааныг дүгнэж, XP шагнал буцаана
        outcome: 'challenger_win', 'opponent_win', 'draw'
        """
        if key not in self.active_battles:
            return {}
        
        battle = self.active_battles[key]
        challenger_id, opponent_id = key
        
        rewards = {}
        
        if outcome == "challenger_win":
            rewards[challenger_id] = DEFAULT_BATTLE_WIN_XP
            rewards[opponent_id] = DEFAULT_BATTLE_LOSE_XP
        elif outcome == "opponent_win":
            rewards[challenger_id] = DEFAULT_BATTLE_LOSE_XP
            rewards[opponent_id] = DEFAULT_BATTLE_WIN_XP
        else:  # тэнцээ
            rewards[challenger_id] = DEFAULT_BATTLE_DRAW_XP
            rewards[opponent_id] = DEFAULT_BATTLE_DRAW_XP
        
        # Хөргөлт тогтоох
        self.battle_cooldowns[challenger_id] = time.time()
        self.battle_cooldowns[opponent_id] = time.time()
        
        # Тулааныг устгах
        del self.active_battles[key]
        
        return rewards
    
    def get_battle_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Хэрэглэгчийн идэвхтэй тулааны мэдээлэл авах"""
        for key, battle in self.active_battles.items():
            if user_id in key:
                return {**battle, "participants": key}
        return None
    
    def get_cooldown_remaining(self, user_id: int) -> int:
        """Хөргөлтийн үлдэгдэл хугацааг секундээр буцаана"""
        if user_id not in self.battle_cooldowns:
            return 0
        remaining = int(DEFAULT_BATTLE_COOLDOWN - (time.time() - self.battle_cooldowns[user_id]))
        return max(0, remaining)


# ========== NEW: DAILY QUEST/STREAK XP SYSTEM ==========
class DailyQuestXPSystem:
    """Өдөр тутмын даалгавар ба цуврал урамшууллын систем"""
    
    def __init__(self):
        self.user_streaks: Dict[int, Dict[str, Any]] = {}
    
    async def claim_daily_quest(self, user_id: int, db, guild_id: int) -> Optional[Dict[str, Any]]:
        """Өдрийн шагналыг авах ба цувралыг шинэчлэх"""
        today = datetime.now(timezone.utc).date()
        
        if user_id not in self.user_streaks:
            self.user_streaks[user_id] = {
                "last_claim": None,
                "streak": 0,
                "total_quests": 0
            }
        
        user_data = self.user_streaks[user_id]
        
        # Өнөөдөр авсан эсэхийг шалгах
        if user_data["last_claim"] and user_data["last_claim"].date() == today:
            return None
        
        # Цувралыг шинэчлэх
        if user_data["last_claim"]:
            last_date = user_data["last_claim"].date()
            yesterday = today - timedelta(days=1)
            if last_date == yesterday:
                user_data["streak"] += 1
            else:
                user_data["streak"] = 1
        else:
            user_data["streak"] = 1
        
        user_data["last_claim"] = datetime.now(timezone.utc)
        user_data["total_quests"] += 1
        
        # XP шагнал тооцох (суурь 30 + цувралын нэмэгдэл)
        base_xp = 30
        streak_bonus = user_data["streak"] * 5
        total_xp = base_xp + streak_bonus
        
        return {
            "xp": total_xp,
            "streak": user_data["streak"],
            "bonus": streak_bonus
        }
    
    def get_user_streak(self, user_id: int) -> Dict[str, Any]:
        """Хэрэглэгчийн цувралын мэдээлэл авах"""
        if user_id not in self.user_streaks:
            return {"streak": 0, "total_quests": 0, "last_claim": None}
        return self.user_streaks[user_id]


# Системүүдийг эхлүүлэх
battle_xp_system = BattleXPSystem()
daily_quest_system = DailyQuestXPSystem()


# ========== Leveling Cog (шинэ системүүдтэй) ==========
class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.battle_xp = battle_xp_system
        self.daily_quests = daily_quest_system
    
    # Таны одоо байгаа бусад методууд энд байна...
    
    # ========== ШИНЭ: ТУЛААНЫ КОМАНДУУД ==========
    @commands.hybrid_command(name="battle", aliases=["fight", "duel"])
    async def start_battle_cmd(self, ctx, opponent: discord.Member):
        """Хэн нэгнийг тулаанд урих!"""
        if opponent.bot or opponent == ctx.author:
            return await ctx.send("❌ Бот эсвэл өөртэйгөө тулалдах боломжгүй!", ephemeral=True)
        
        # Өрсөлдөгч өөр тулаанд оролцож байгаа эсэх
        if self.battle_xp.get_battle_status(opponent.id):
            return await ctx.send(f"❌ {opponent.display_name} аль хэдийн тулалдаж байна!", ephemeral=True)
        
        # Хөргөлт шалгах
        cooldown = self.battle_xp.get_cooldown_remaining(ctx.author.id)
        if cooldown > 0:
            return await ctx.send(f"⏱️ Дараагийн тулаан хүртэл {cooldown}с хүлээнэ үү", ephemeral=True)
        
        # Тулаан эхлүүлэх
        success = await self.battle_xp.start_battle(ctx.author.id, opponent.id, self.bot.db, ctx.guild.id)
        if not success:
            return await ctx.send("❌ Тулаан эхлүүлэх боломжгүй!", ephemeral=True)
        
        # Үр дүн сонгох товчлууртай харагдац үүсгэх
        view = BattleView(self.battle_xp, ctx.author.id, opponent.id)
        embed = discord.Embed(
            title="⚔️ ТУЛААН ЭХЛҮҮЛЭХ ⚔️",
            description=f"{ctx.author.mention} нь {opponent.mention}-тай тулалдахаар урилаа!",
            color=0xff6b6b
        )
        embed.add_field(name="Ялагчийг сонго:", value="Доорх товчлуураар үр дүнг оруулна уу!", inline=False)
        
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
    
    @commands.hybrid_command(name="dailyquest", aliases=["dq", "quest"])
    async def daily_quest_cmd(self, ctx):
        """Өдрийн XP шагналаа авах"""
        result = await self.daily_quests.claim_daily_quest(ctx.author.id, self.bot.db, ctx.guild.id)
        
        if result is None:
            streak_info = self.daily_quests.get_user_streak(ctx.author.id)
            return await ctx.send(
                f"❌ Та өнөөдөр аль хэдийн авсан байна!\n"
                f"🔥 Одоогийн цуврал: **{streak_info['streak']}** өдөр\n"
                f"Маргааш дахин авна уу!",
                ephemeral=True
            )
        
        embed = discord.Embed(
            title="✅ ӨДРИЙН ШАГНАЛ АМЖИЛТТАЙ!",
            color=SUCCESS_COLOR
        )
        embed.add_field(name="🎁 Авсан XP:", value=f"**{result['xp']} XP**", inline=True)
        embed.add_field(name="🔥 Цуврал:", value=f"**{result['streak']} өдөр**", inline=True)
        embed.add_field(name="⭐ Нэмэгдэл:", value=f"+{result['bonus']} XP", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="mybattle", aliases=["battleinfo"])
    async def battle_info_cmd(self, ctx):
        """Таны идэвхтэй тулааны мэдээлэл"""
        battle = self.battle_xp.get_battle_status(ctx.author.id)
        
        if not battle:
            cooldown = self.battle_xp.get_cooldown_remaining(ctx.author.id)
            if cooldown > 0:
                return await ctx.send(
                    f"⏱️ Танд идэвхтэй тулаан байхгүй.\n"
                    f"Дараагийн тулаан хүртэл {cooldown}с хүлээнэ үү",
                    ephemeral=True
                )
            return await ctx.send("❌ Одоогоор идэвхтэй тулаан байхгүй.", ephemeral=True)
        
        challenger = await self.bot.fetch_user(battle["challenger"])
        opponent = await self.bot.fetch_user(battle["opponent"])
        
        embed = discord.Embed(
            title="⚔️ ИДЭВХТЭЙ ТУЛААН",
            color=0xff6b6b
        )
        embed.add_field(name="👹 Уригч:", value=challenger.mention, inline=True)
        embed.add_field(name="🗡️ Өрсөлдөгч:", value=opponent.mention, inline=True)
        embed.add_field(name="📊 Төлөв:", value=battle["status"], inline=False)
        
        await ctx.send(embed=embed, ephemeral=True)


class BattleView(ui.View):
    """Тулааны үр дүнг сонгох UI"""
    
    def __init__(self, battle_system, challenger_id, opponent_id):
        super().__init__(timeout=300)
        self.battle_system = battle_system
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.message = None
    
    @ui.button(label="Уригч ялна", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def challenger_win(self, interaction: discord.Interaction, button: ui.Button):
        await self._resolve_battle(interaction, "challenger_win")
    
    @ui.button(label="Өрсөлдөгч ялна", style=discord.ButtonStyle.primary, emoji="🗡️")
    async def opponent_win(self, interaction: discord.Interaction, button: ui.Button):
        await self._resolve_battle(interaction, "opponent_win")
    
    @ui.button(label="Тэнцээ", style=discord.ButtonStyle.secondary, emoji="🤝")
    async def draw(self, interaction: discord.Interaction, button: ui.Button):
        await self._resolve_battle(interaction, "draw")
    
    async def _resolve_battle(self, interaction: discord.Interaction, outcome: str):
        key = (self.challenger_id, self.opponent_id)
        rewards = await self.battle_system.resolve_battle(key, outcome)
        
        if not rewards:
            return await interaction.response.send_message("❌ Тулаан олдсонгүй!", ephemeral=True)
        
        embed = discord.Embed(
            title="✅ ТУЛААН ДУУССАН!",
            color=SUCCESS_COLOR
        )
        
        for user_id, xp in rewards.items():
            user = await interaction.client.fetch_user(user_id)
            embed.add_field(name=f"{user.display_name}", value=f"+{xp} XP", inline=True)
        
        embed.add_field(name="Үр дүн:", value=outcome.replace("_", " ").title(), inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(Level(bot))