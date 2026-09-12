import discord
from discord.ext import commands
import asyncio
import random
import time
from typing import Dict, List, Optional
from datetime import datetime, timezone

# ===== COLOR SCHEME =====
EMBED_COLOR   = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR   = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR    = 0xfab387
PURPLE_COLOR  = 0xcba6f7
INFO_COLOR    = 0x89b4fa
MAFIA_RED     = 0xdd7878

# ===== DVR MANAGER (SQLite) =====
class DVRManager:
    def __init__(self, bot):
        self.bot = bot
        self.dvr_role_name = "DVR Manager"

    async def init_db(self):
        """SQLite DVR хүснэгт үүсгэх"""
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS user_dvr (
                user_id TEXT PRIMARY KEY,
                channel_id INTEGER,
                guild_id INTEGER,
                created_at INTEGER
            )
        ''')

    async def create_dvr_channel(self, member: discord.Member):
        guild = member.guild
        category = discord.utils.get(guild.categories, name="🎬 DVR Rooms")
        if not category:
            try:
                category = await guild.create_category("🎬 DVR Rooms")
            except discord.Forbidden:
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        try:
            channel = await guild.create_text_channel(
                name=f"dvr-{member.name.lower()}",
                category=category,
                overwrites=overwrites
            )
        except discord.Forbidden:
            return

        await self.bot.db.execute(
            "INSERT OR REPLACE INTO user_dvr (user_id, channel_id, guild_id, created_at) VALUES (?, ?, ?, ?)",
            str(member.id), channel.id, guild.id, int(time.time())
        )

        embed = discord.Embed(
            title="🎥 DVR CONTROL СУВАГ",
            description=f"👋 Сайн уу, {member.mention}! Энд ашиглах командуудын жагсаалт.",
            color=INFO_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="🔨 `gdvr kick @user`", value="Хэрэглэгчийг сувгаас kick хийх", inline=False)
        embed.add_field(name="⚠️ `gdvr warn @user <шалтгаан>`", value="Анхааруулга (warn) илгээх", inline=False)
        embed.add_field(name="🔇 `gdvr mute @user`", value="10 минутаар mute хийх", inline=False)
        embed.add_field(name="📋 `gdvr list`", value="Сувагт байгаа хэрэглэгчдийн жагсаалт", inline=False)
        embed.set_footer(text="DVR System | Зөвхөн энэ сувагт ажиллана")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await channel.send(embed=embed)
        return channel

    async def delete_dvr_channel(self, user_id: int, guild: discord.Guild):
        row = await self.bot.db.fetchone(
            "SELECT channel_id FROM user_dvr WHERE user_id = ?", str(user_id)
        )
        if row:
            channel = guild.get_channel(row[0])
            if channel:
                try:
                    await channel.delete()
                except discord.Forbidden:
                    pass
            await self.bot.db.execute("DELETE FROM user_dvr WHERE user_id = ?", str(user_id))

    async def get_dvr_channel(self, user_id: int) -> Optional[discord.TextChannel]:
        row = await self.bot.db.fetchone(
            "SELECT channel_id, guild_id FROM user_dvr WHERE user_id = ?", str(user_id)
        )
        if row:
            guild = self.bot.get_guild(row[1])
            if guild:
                return guild.get_channel(row[0])
        return None


# ===== MAFIA DATA CLASSES =====
class MafiaPlayer:
    def __init__(self, member: discord.Member, number: int):
        self.member = member
        self.number = number
        self.role: Optional[str] = None
        self.alive = True
        self.night_action: Optional[int] = None
        self.night_action_extra: Optional[int] = None
        self.copied_role = False
        self.vote_target: Optional[int] = None


class MafiaGame:
    def __init__(self, channel: discord.TextChannel, host: discord.Member):
        self.channel = channel
        self.host = host
        self.players: List[MafiaPlayer] = []
        self.phase = "waiting"
        self.day_count = 1
        self.night_task: Optional[asyncio.Task] = None
        self.vote_task: Optional[asyncio.Task] = None
        self.event_used = False
        self.interrogation_used = False
        self.joker_win = False
        self.double_kill_night = False
        self.blackout_night = False
        self.role_swap_pending = False
        self.role_swap_pair = None
        self.mafia_channel: Optional[discord.TextChannel] = None
        self.detective_channel: Optional[discord.TextChannel] = None
        self.game_category: Optional[discord.CategoryChannel] = None


# ===== MAIN COG =====
class Mafia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games: Dict[int, MafiaGame] = {}
        self.dvr = DVRManager(bot)
        self.night_timeout = 120
        self.day_vote_timeout = 120
        self.bot.loop.create_task(self._init_dvr_db())

    async def _init_dvr_db(self):
        await self.bot.wait_until_ready()
        await self.dvr.init_db()

    def get_game(self, channel_id: int) -> Optional[MafiaGame]:
        return self.games.get(channel_id)

    # ========== EMBED HELPERS ==========
    async def send_embed(self, channel, title, desc, color=EMBED_COLOR, fields=None, thumbnail=None, footer=None):
        embed = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now(timezone.utc))
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if fields:
            for name, val in fields:
                embed.add_field(name=name, value=val, inline=False)
        if footer:
            embed.set_footer(text=footer)
        await channel.send(embed=embed)

    async def send_dm(self, member, title, desc, color=EMBED_COLOR, thumbnail=None):
        try:
            embed = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now(timezone.utc))
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            await member.send(embed=embed)
        except:
            pass

    def role_name(self, role: str) -> str:
        names = {
            "civilian": "👨‍🌾 Иргэн (Civilian)",
            "mafia": "🔪 Мафи (Mafia)",
            "detective": "👮 Цагдаа (Detective)",
            "doctor": "💊 Эмч (Doctor)",
            "turncoat": "🔄 Урвагч (Turncoat)",
            "don": "👑 Don (Мафийн ахлагч)",
            "godmother": "👸 Godmother (Мафийн эх)",
            "joker": "🃏 Joker"
        }
        return names.get(role, "❓ Тодорхойгүй")

    # ===== DVR GROUP =====
    @commands.group(name='dvr', invoke_without_command=True)
    async def dvr_group(self, ctx):
        if not any(r.name == self.dvr.dvr_role_name for r in ctx.author.roles):
            return await ctx.send(embed=discord.Embed(title="⛔ PERMISSION DENIED", description="Танд энэ командыг ашиглах permission алга.", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)), delete_after=5)
        ch = await self.dvr.get_dvr_channel(ctx.author.id)
        if not ch or ctx.channel.id != ch.id:
            return await ctx.send(embed=discord.Embed(title="⛔ БУРУУ СУВАГ (WRONG CHANNEL)", description="Энэ команд зөвхөн таны DVR сувагт ажиллана.", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)), delete_after=5)
        embed = discord.Embed(title="🎛️ DVR CONTROL COMMANDS", color=PURPLE_COLOR, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="🔨 `gdvr kick @user`", value="Хэрэглэгчийг сувгаас kick хийх", inline=False)
        embed.add_field(name="⚠️ `gdvr warn @user <шалтгаан>`", value="Анхааруулга (warn) илгээх", inline=False)
        embed.add_field(name="🔇 `gdvr mute @user`", value="10 минутаар mute хийх", inline=False)
        embed.add_field(name="📋 `gdvr list`", value="Сувагт байгаа хэрэглэгчдийн жагсаалт", inline=False)
        embed.set_footer(text="DVR System – зөвхөн өөрийн сувагт ашиглана")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    @dvr_group.command(name='kick')
    async def dvr_kick(self, ctx, member: discord.Member):
        if not any(r.name == self.dvr.dvr_role_name for r in ctx.author.roles):
            return await ctx.send(embed=discord.Embed(title="⛔ PERMISSION DENIED", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)))
        ch = await self.dvr.get_dvr_channel(ctx.author.id)
        if not ch or ctx.channel.id != ch.id:
            return await ctx.send(embed=discord.Embed(title="⛔ БУРУУ СУВАГ (WRONG CHANNEL)", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)))
        await ch.set_permissions(member, read_messages=False)
        await ctx.send(embed=discord.Embed(title="✅ KICK ХИЙГДЛЭЭ", description=f"{member.mention} DVR сувгаас kick хийгдлээ.", color=SUCCESS_COLOR, timestamp=datetime.now(timezone.utc)))

    @dvr_group.command(name='warn')
    async def dvr_warn(self, ctx, member: discord.Member, *, reason="Анхааруулга"):
        if not any(r.name == self.dvr.dvr_role_name for r in ctx.author.roles):
            return await ctx.send(embed=discord.Embed(title="⛔ PERMISSION DENIED", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)))
        ch = await self.dvr.get_dvr_channel(ctx.author.id)
        if not ch or ctx.channel.id != ch.id:
            return await ctx.send(embed=discord.Embed(title="⛔ БУРУУ СУВАГ (WRONG CHANNEL)", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)))
        try:
            await member.send(embed=discord.Embed(title="⚠️ DVR АНХААРУУЛГА", description=f"**Шалтгаан:** {reason}\n**Суваг:** {ch.mention}", color=WARNING_COLOR, timestamp=datetime.now(timezone.utc)))
        except:
            pass
        await ctx.send(embed=discord.Embed(title="⚠️ АНХААРУУЛГА ИЛГЭЭВ", description=f"{member.mention} -д анхааруулга илгээлээ.", color=WARNING_COLOR, timestamp=datetime.now(timezone.utc)))

    @dvr_group.command(name='mute')
    async def dvr_mute(self, ctx, member: discord.Member):
        if not any(r.name == self.dvr.dvr_role_name for r in ctx.author.roles):
            return await ctx.send(embed=discord.Embed(title="⛔ PERMISSION DENIED", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)))
        ch = await self.dvr.get_dvr_channel(ctx.author.id)
        if not ch or ctx.channel.id != ch.id:
            return await ctx.send(embed=discord.Embed(title="⛔ БУРУУ СУВАГ (WRONG CHANNEL)", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)))
        await ch.set_permissions(member, send_messages=False)
        await ctx.send(embed=discord.Embed(title="🔇 MUTED", description=f"{member.mention} 10 минутаар mute хийгдлээ.", color=WARNING_COLOR, timestamp=datetime.now(timezone.utc)))
        await asyncio.sleep(600)
        try:
            await ch.set_permissions(member, send_messages=None)
        except discord.Forbidden:
            pass
        await ctx.send(embed=discord.Embed(title="🔊 UNMUTED", description=f"{member.mention} mute-ээс гарлаа.", color=SUCCESS_COLOR, timestamp=datetime.now(timezone.utc)))

    @dvr_group.command(name='list')
    async def dvr_list(self, ctx):
        if not any(r.name == self.dvr.dvr_role_name for r in ctx.author.roles):
            return await ctx.send(embed=discord.Embed(title="⛔ PERMISSION DENIED", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)))
        ch = await self.dvr.get_dvr_channel(ctx.author.id)
        if not ch or ctx.channel.id != ch.id:
            return await ctx.send(embed=discord.Embed(title="⛔ БУРУУ СУВАГ (WRONG CHANNEL)", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc)))
        members = [m.mention for m in ch.members if not m.bot]
        embed = discord.Embed(title="👥 DVR СУВАГТ ХЭРЭГЛЭГЧИД", color=INFO_COLOR, timestamp=datetime.now(timezone.utc))
        if members:
            embed.description = "\n".join(members)
        else:
            embed.description = "Одоогоор хэрэглэгч байхгүй."
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    # ===== MAFIA COMMANDS =====
    @commands.command(name='mafiarule', aliases=['mrule', 'mr'])
    async def mafia_rule(self, ctx):
        embed = discord.Embed(title="🕵️‍♂️ **MAFIA GAME RULES**", color=PURPLE_COLOR, timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
        embed.add_field(name="🎭 **ДҮРҮҮД**", value="`👮 Цагдаа` • `🔪 Мафи` • `💊 Эмч` • `🔄 Урвагч` • `🃏 Joker` • `👑 Don/Godmother (20+)` • `👨‍🌾 Иргэн`", inline=False)
        embed.add_field(name="🌙 **ШӨНӨ (NIGHT PHASE)**", value="🔪 Мафи: `kill <дугаар>`\n💊 Эмч: `save <дугаар>`\n👮 Цагдаа: `investigate <дугаар>`\n🔄 Урвагч: `sleep <үхсэн дугаар>`\n*Бүх үйлдлийг өөрийн фракцийн нууц сувагт илгээнэ*", inline=False)
        embed.add_field(name="☀️ **ӨДӨР (DAY PHASE)**", value="🗳️ Санал өгөх: `vote <дугаар>` (нийтийн сувагт)", inline=False)
        embed.add_field(name="🎲 **ТУСГАЙ ҮЙЛ ЯВДАЛ**", value="`🌑 Blackout` – цагдаа/эмч ажиллахгүй\n`🧨 Double Kill` – мафи 2 хүн ална\n`🔄 Role Swap` – 2 хүний дүр солигдоно\n`🔥 Interrogation Mode` – Hot seat хэлэлцүүлэг", inline=False)
        embed.add_field(name="🏆 **ЯЛАЛТ (WIN CONDITIONS)**", value="• **Иргэд** – бүх мафи, урвагч үхсэн\n• **Мафи** – тоо тэнцвэл ялна\n• 🃏 **Joker** – өөрийгөө vote-оор хөөлгөвөл solo win хийнэ", inline=False)
        embed.set_footer(text="Тоглогчдыг дугаараар (1-20) дуудна. Шөнийн үйлдлээ нууц сувагтаа хийнэ.")
        await ctx.send(embed=embed)

    @commands.group(name='mafia', aliases=['maf'], invoke_without_command=True)
    async def mafia(self, ctx):
        embed = discord.Embed(title="🕵️ **МАФИ ТОГЛООМ**", description="Доорх дэд командуудыг ашиглана уу.", color=PURPLE_COLOR, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="📌 **Үндсэн (Core)**", value="`gmafia create` – шинэ lobby үүсгэх\n`gmafia join` – тоглоомд нэгдэх\n`gmafia start` – эхлүүлэх (12-20 тоглогч)\n`gmafia end` – тоглоомыг дуусгах\n`gmafia status` – төлөв харах", inline=False)
        embed.add_field(name="👥 **Мэдээлэл**", value="`gmafia players` – бүх тоглогчдын жагсаалт\n`gmafia alive` – амьд үлдсэн тоглогчдын жагсаалт", inline=False)
        embed.add_field(name="🎲 **Host команд**", value="`gmafia event` – random event (нэг удаа)\n`gmafia interrogate <дугаар>` – Hot seat хэлэлцүүлэг (нэг удаа)", inline=False)
        embed.add_field(name="ℹ️ **Тусламж**", value="`gmafia rule` – дэлгэрэнгүй дүрэм", inline=False)
        embed.set_footer(text="Тоглоом эхлэхэд бүгд нууц сувагтаа дүрээ (role) авна")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    @mafia.command(name='rule')
    async def mafia_rule_sub(self, ctx):
        """Дүрмийг харуулах"""
        await self.mafia_rule(ctx)

    @mafia.command(name='create')
    async def mafia_create(self, ctx):
        if ctx.channel.id in self.games:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Энэ сувагт аль хэдийн тоглоом явж байна.", ERROR_COLOR)
        self.games[ctx.channel.id] = MafiaGame(ctx.channel, ctx.author)
        await self.send_embed(ctx.channel, "✅ **ТОГЛООМ ҮҮСЛЭЭ**", f"**Эзэмшигч:** {ctx.author.mention}\n`gmafia join` – нэгдэх\n`gmafia start` – эхлүүлэх (12-20 тоглогч)", SUCCESS_COLOR)

    @mafia.command(name='join')
    async def mafia_join(self, ctx):
        game = self.get_game(ctx.channel.id)
        if not game:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом байхгүй. `gmafia create` ашиглана уу.", ERROR_COLOR)
        if game.phase != "waiting":
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом аль хэдийн эхэлсэн байна (Already in progress).", ERROR_COLOR)
        if any(p.member.id == ctx.author.id for p in game.players):
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Та аль хэдийн нэгдсэн байна.", ERROR_COLOR)
        if len(game.players) >= 20:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Дээд хязгаар 20 тоглогч.", ERROR_COLOR)
        num = len(game.players) + 1
        game.players.append(MafiaPlayer(ctx.author, num))
        await self.send_embed(ctx.channel, "✅ **НЭГДЛЭЭ**", f"{ctx.author.mention} → **{num}** дугаартай тоглогч. Нийт: **{len(game.players)}/20**", SUCCESS_COLOR)

    @mafia.command(name='players')
    async def mafia_players(self, ctx):
        game = self.get_game(ctx.channel.id)
        if not game:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом байхгүй.", ERROR_COLOR)
        if not game.players:
            return await self.send_embed(ctx.channel, "📋 **ТОГЛОГЧИД**", "Одоогоор тоглогч байхгүй.", WARNING_COLOR)
        status_emoji = {True: "✅", False: "💀"}
        lines = [f"**{p.number}.** {p.member.mention} {status_emoji[p.alive]}" for p in game.players]
        await self.send_embed(ctx.channel, f"📋 **ТОГЛОГЧИД ({len(game.players)})**", "\n".join(lines), EMBED_COLOR)

    @mafia.command(name='alive')
    async def mafia_alive(self, ctx):
        game = self.get_game(ctx.channel.id)
        if not game:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом байхгүй.", ERROR_COLOR)
        alive = [p for p in game.players if p.alive]
        if not alive:
            return await self.send_embed(ctx.channel, "💀 **АМЬД ТОГЛОГЧ**", "Амьд тоглогч байхгүй байна.", WARNING_COLOR)
        lines = [f"**{p.number}.** {p.member.mention}" for p in alive]
        await self.send_embed(ctx.channel, f"👥 **АМЬД ТОГЛОГЧИД ({len(alive)})**", "\n".join(lines), SUCCESS_COLOR)

    @mafia.command(name='status')
    async def mafia_status(self, ctx):
        game = self.get_game(ctx.channel.id)
        if not game:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом байхгүй.", ERROR_COLOR)
        phase_text = {
            "waiting": "🟢 Waiting lobby",
            "night": "🌙 Шөнө (Night)",
            "day": f"☀️ Өдөр {game.day_count} (Day)",
            "ended": "⛔ Дууссан (Ended)"
        }.get(game.phase, "❓ Тодорхойгүй")
        embed = discord.Embed(title="📊 **ТОГЛООМЫН ТӨЛӨВ**", color=EMBED_COLOR, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="🎮 **Фаза**", value=phase_text, inline=True)
        embed.add_field(name="👥 **Тоглогчид**", value=f"{len(game.players)}", inline=True)
        embed.add_field(name="👑 **Эзэн**", value=game.host.mention, inline=True)
        embed.add_field(name="🎲 **Үйл явдал**", value="Ашиглагдсан" if game.event_used else "Боломжтой", inline=True)
        embed.add_field(name="🔥 **Interrogation**", value="Ашиглагдсан" if game.interrogation_used else "Боломжтой", inline=True)
        await ctx.send(embed=embed)

    @mafia.command(name='event')
    async def mafia_event(self, ctx):
        game = self.get_game(ctx.channel.id)
        if not game or game.phase != "night":
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Энэ командыг зөвхөн шөнийн цагаар, тоглоом эхэлсний дараа ашиглаж болно.", ERROR_COLOR)
        if ctx.author.id != game.host.id:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Зөвхөн Host үйл явдлыг идэвхжүүлж болно.", ERROR_COLOR)
        if game.event_used:
            return await self.send_embed(ctx.channel, "⚠️ **МЭДЭЭ**", "Үйл явдал аль хэдийн ашиглагдсан байна.", WARNING_COLOR)
        await self.trigger_random_event(game)

    async def trigger_random_event(self, game: MafiaGame):
        event = random.choice(["blackout", "double_kill", "role_swap"])
        game.event_used = True
        if event == "blackout":
            game.blackout_night = True
            await self.send_embed(game.channel, "🌑 **BLACKOUT**", "Энэ шөнө цагдаа, эмч ажиллахгүй (Abilities disabled)! Зөвхөн мафи л үйлдэл хийх боломжтой.", WARNING_COLOR, thumbnail="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
        elif event == "double_kill":
            game.double_kill_night = True
            await self.send_embed(game.channel, "🧨 **DOUBLE KILL**", "Мафи энэ шөнө **2 хүн** алах боломжтой (Double Kill)! Хоёр дахь байгаа `kill <дугаар>` командаар илгээнэ үү.\nХэрэв хоёр дахь бай олдохгүй бол санамсаргүй амьд тоглогч алагдана.", WARNING_COLOR, thumbnail="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
            if game.mafia_channel:
                for p in game.players:
                    if p.role in ("mafia", "don", "godmother") and p.alive:
                        await self.send_dm(p.member, "🧨 DOUBLE KILL", "Та энэ шөнө **хоёр хүн** алах боломжтой.", WARNING_COLOR)
        elif event == "role_swap":
            game.role_swap_pending = True
            await self.send_embed(game.channel, "🔄 **ROLE SWAP**", "Host тоглогчдын дугаарыг сонгоно уу: `!mafia swap <дугаар1> <дугаар2>` (30 секунд)", WARNING_COLOR, thumbnail="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
            def check(m):
                return m.author.id == game.host.id and m.channel == game.channel and m.content.startswith('!mafia swap')
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                parts = msg.content.split()
                if len(parts) == 3:
                    try:
                        num1, num2 = int(parts[1]), int(parts[2])
                        p1 = next((p for p in game.players if p.number == num1), None)
                        p2 = next((p for p in game.players if p.number == num2), None)
                        if p1 and p2 and p1.alive and p2.alive:
                            p1.role, p2.role = p2.role, p1.role
                            await self.send_embed(game.channel, "🔄 Дүр солигдлоо (Role Swapped)!", f"**{p1.number}** болон **{p2.number}** дугаартай тоглогчдын дүр солигдлоо.", SUCCESS_COLOR)
                            await self.send_dm(p1.member, "🔄 ДҮР СОЛИГДЛОО", f"Таны шинэ дүр: **{self.role_name(p1.role)}**", INFO_COLOR)
                            await self.send_dm(p2.member, "🔄 ДҮР СОЛИГДЛОО", f"Таны шинэ дүр: **{self.role_name(p2.role)}**", INFO_COLOR)
                        else:
                            await self.send_embed(game.channel, "❌ Алдаа", "Буруу дугаар эсвэл тоглогч үхсэн байна.", ERROR_COLOR)
                    except:
                        await self.send_embed(game.channel, "❌ Алдаа", "Зөв формат: `!mafia swap 3 5`", ERROR_COLOR)
                else:
                    await self.send_embed(game.channel, "❌ Алдаа", "Зөв формат: `!mafia swap 3 5`", ERROR_COLOR)
            except asyncio.TimeoutError:
                await self.send_embed(game.channel, "⏰ Хугацаа дууссан", "Role swap цуцлагдлаа.", WARNING_COLOR)
            game.role_swap_pending = False

    @mafia.command(name='interrogate')
    async def mafia_interrogate(self, ctx, target_num: int):
        game = self.get_game(ctx.channel.id)
        if not game or game.phase != "day":
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Interrogation зөвхөн өдрийн цагаар хийгдэнэ.", ERROR_COLOR)
        if ctx.author.id != game.host.id:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Зөвхөн Host interrogation эхлүүлж болно.", ERROR_COLOR)
        if game.interrogation_used:
            return await self.send_embed(ctx.channel, "⚠️ **МЭДЭЭ**", "Interrogation аль хэдийн ашиглагдсан байна.", WARNING_COLOR)

        target = next((p for p in game.players if p.number == target_num and p.alive), None)
        if not target:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", f"{target_num} дугаартай амьд тоглогч байхгүй.", ERROR_COLOR)

        game.interrogation_used = True
        await self.send_embed(ctx.channel, f"🔥 **INTERROGATION MODE** 🔥", f"**{target.member.mention}** (№{target.number}) hot seat-д суулаа!\nБүгд асуулт асууж болно. Host төгсгөлд үнэн/худал эсэхийг хэлнэ.\nХэлэлцүүлэг 2 минут үргэлжилнэ.", GOLD_COLOR)
        await asyncio.sleep(120)
        truth = random.choice([True, False])
        await self.send_embed(ctx.channel, "🔍 ДҮН", f"Host-ийн дүгнэлт: {target.member.mention} **{'ҮНЭН (TRUTH)' if truth else 'ХУДАЛ (LIE)'}**", INFO_COLOR)

    # ========== ФРАКЦИЙН СУВАГ ҮҮСГЭХ ==========
    async def create_faction_channels(self, game: MafiaGame):
        guild = game.channel.guild
        cat = discord.utils.get(guild.categories, name="🕵️ Mafia Game")
        if not cat:
            try:
                cat = await guild.create_category("🕵️ Mafia Game")
            except discord.Forbidden:
                await self.send_embed(game.channel, "⚠️ **Анхаар**", "Ботод суваг үүсгэх эрх байхгүй тул фракцийн чат ажиллахгүй. DM ашиглана уу.", WARNING_COLOR)
                return
        game.game_category = cat

        mafia_players = [p for p in game.players if p.role in ("mafia", "don", "godmother")]
        if len(mafia_players) >= 2:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
            }
            for p in mafia_players:
                overwrites[p.member] = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
            overwrites[guild.me] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            try:
                channel = await guild.create_text_channel(name="mafia-chat", category=cat, overwrites=overwrites)
                game.mafia_channel = channel
                await channel.send(embed=discord.Embed(title="🔪 МАФИ ЧАТ", description="Энд та нар хэлэлцэж, `kill <дугаар>` командаар хэн алахаа шийднэ.", color=MAFIA_RED, timestamp=datetime.now(timezone.utc)))
            except discord.Forbidden:
                pass

        detective_players = [p for p in game.players if p.role == "detective"]
        if len(detective_players) >= 2:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
            }
            for p in detective_players:
                overwrites[p.member] = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
            overwrites[guild.me] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            try:
                channel = await guild.create_text_channel(name="detective-chat", category=cat, overwrites=overwrites)
                game.detective_channel = channel
                await channel.send(embed=discord.Embed(title="👮 ЦАГДАА ЧАТ", description="Энд та нар мэдээллээ хуваалцаж, `investigate <дугаар>` командаар хэнийг шалгахаа шийднэ.", color=INFO_COLOR, timestamp=datetime.now(timezone.utc)))
            except discord.Forbidden:
                pass

    async def delete_faction_channels(self, game: MafiaGame):
        for ch in [game.mafia_channel, game.detective_channel]:
            if ch:
                try:
                    await ch.delete()
                except:
                    pass
        if game.game_category:
            try:
                channels = game.game_category.channels
                if len(channels) == 0:
                    await game.game_category.delete()
            except:
                pass

    # ========== MAFIA START ==========
    @mafia.command(name='start')
    async def mafia_start(self, ctx):
        game = self.get_game(ctx.channel.id)
        if not game:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом байхгүй.", ERROR_COLOR)
        if game.phase != "waiting":
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом аль хэдийн эхэлсэн байна (Already in progress).", ERROR_COLOR)
        if ctx.author.id != game.host.id:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Зөвхөн тоглоом эзэмшигч эхлүүлж болно.", ERROR_COLOR)
        if len(game.players) < 12:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Хамгийн багадаа 12 тоглогч шаардлагатай.", ERROR_COLOR)

        roles = self.generate_roles(len(game.players))
        for i, p in enumerate(game.players):
            p.role = roles[i]
            p.alive = True
            p.copied_role = False
            p.night_action = None
            p.night_action_extra = None
            p.vote_target = None

        await self.create_faction_channels(game)
        game.phase = "night"
        game.day_count = 1

        for p in game.players:
            embed_desc = f"**{self.role_name(p.role)}**\n\n{self.role_description(p.role, p.number)}"
            await self.send_dm(p.member, "🔮 ТАНЫ ДҮР", embed_desc, PURPLE_COLOR, thumbnail="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")

        # Мафи чат мэдээлэл
        if game.mafia_channel:
            mafia_players = [p for p in game.players if p.role in ("mafia", "don", "godmother")]
            if len(mafia_players) > 1:
                mafia_names = [f"№{p.number} - {p.member.mention}" for p in mafia_players]
                await game.mafia_channel.send(embed=discord.Embed(title="🔪 МАФИ ХАМТРАГЧИД", description="\n".join(mafia_names), color=MAFIA_RED, timestamp=datetime.now(timezone.utc)))
        else:
            mafia_players = [p for p in game.players if p.role in ("mafia", "don", "godmother")]
            if len(mafia_players) == 1:
                await self.send_dm(mafia_players[0].member, "🔪 МАФИ", "Та ганцаараа мафи. Хамтрагч байхгүй.", MAFIA_RED)

        if game.detective_channel:
            detective_players = [p for p in game.players if p.role == "detective"]
            if len(detective_players) > 1:
                det_names = [f"№{p.number} - {p.member.mention}" for p in detective_players]
                await game.detective_channel.send(embed=discord.Embed(title="👮 ЦАГДАА ХАМТРАГЧИД", description="\n".join(det_names), color=INFO_COLOR, timestamp=datetime.now(timezone.utc)))
        else:
            detective_players = [p for p in game.players if p.role == "detective"]
            if len(detective_players) == 1:
                await self.send_dm(detective_players[0].member, "👮 ЦАГДАА", "Та ганцаараа цагдаа.", INFO_COLOR)

        joker = next((p for p in game.players if p.role == "joker"), None)
        if joker:
            await self.send_dm(joker.member, "🃏 JOKER", "Хэрэв та өдөр vote-оор хөөгдвөл ганцаараа ялна.", GOLD_COLOR)

        faction_info = ""
        if game.mafia_channel:
            faction_info += f"🔪 Мафи: {game.mafia_channel.mention}\n"
        if game.detective_channel:
            faction_info += f"👮 Цагдаа: {game.detective_channel.mention}\n"

        start_embed = discord.Embed(
            title="🌙 **ШӨНӨ БОЛЛО**",
            description=f"Нийт **{len(game.players)}** тоглогчтой тоглоом эхэллээ!\n\n"
                        f"**Үйлдлээ хийх сувгууд:**\n"
                        f"{faction_info if faction_info else 'DM-ээр үйлдлээ илгээнэ үү (фракцийн чат байхгүй).'}\n"
                        f"• 🔪 Мафи: `kill <дугаар>`\n"
                        f"• 💊 Эмч: `save <дугаар>`\n"
                        f"• 👮 Цагдаа: `investigate <дугаар>`\n"
                        f"• 🔄 Урвагч: `sleep <үхсэн дугаар>`\n\n"
                        f"⏱️ **Хугацаа: {self.night_timeout} секунд**",
            color=PURPLE_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        start_embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
        start_embed.set_footer(text=f"Host: {game.host.display_name}")
        await ctx.send(embed=start_embed)

        if not game.event_used and random.random() < 0.3:
            await self.trigger_random_event(game)

        game.night_task = self.bot.loop.create_task(self.night_phase_timer(game))

    @mafia.command(name='end')
    async def mafia_end(self, ctx):
        game = self.get_game(ctx.channel.id)
        if not game:
            return
        if ctx.author.id != game.host.id:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Зөвхөн эзэн тоглоомыг зогсоож болно.", ERROR_COLOR)
        await self.end_game(game)

    async def end_game(self, game: MafiaGame, reason: str = "Тоглоом дуусгав"):
        if game.night_task:
            game.night_task.cancel()
        if game.vote_task:
            game.vote_task.cancel()
        await self.delete_faction_channels(game)
        if game.channel.id in self.games:
            del self.games[game.channel.id]
        try:
            await self.send_embed(game.channel, "⏹️ **ТОГЛООМ ЗОГСЛОО**", reason, WARNING_COLOR)
        except:
            pass

    # ===== GAME LOGIC =====
    def generate_roles(self, count: int) -> List[str]:
        roles = []
        mafia_cnt = max(1, round(count / 4))
        for _ in range(mafia_cnt):
            roles.append("mafia")
        remaining = count - mafia_cnt
        if remaining >= 4:
            roles.append("detective")
            roles.append("doctor")
            remaining -= 2
        elif remaining >= 3:
            roles.append("doctor")
            remaining -= 1
        if count >= 6 and remaining >= 1:
            roles.append("turncoat")
            remaining -= 1
        if count >= 12 and remaining >= 1:
            roles.append("joker")
            remaining -= 1
        if count >= 20:
            don_role = random.choice(["don", "godmother"])
            for i, r in enumerate(roles):
                if r == "mafia":
                    roles[i] = don_role
                    break
        for _ in range(remaining):
            roles.append("civilian")
        random.shuffle(roles)
        return roles

    def role_description(self, role: str, num: int) -> str:
        base = f"🔢 **Таны дугаар:** `{num}`\n\n"
        if role == "mafia":
            return base + "**🌙 Шөнийн үйлдэл:** `kill <дугаар>`\n⚠️ Хамтрагчаа (мафи, урвагч) алж болохгүй."
        elif role == "detective":
            return base + "**🌙 Шөнийн үйлдэл:** `investigate <дугаар>`\n🔍 Хариуг би танд DM-ээр илгээнэ."
        elif role == "doctor":
            return base + "**🌙 Шөнийн үйлдэл:** `save <дугаар>`\n💊 Хэрэв мафийн алсан хүн эмчлэгдвэл амьд үлдэнэ."
        elif role == "turncoat":
            return base + "**🌙 Шөнийн үйлдэл:** `sleep <үхсэн дугаар>`\n🔄 Тэдний дүрийг хуулна (Role copy)."
        elif role in ("don", "godmother"):
            return base + "**🌙 Шөнийн үйлдэл:** `kill <дугаар>`\n👑 Та мафийн удирдагч. Өөрийн хамтрагчаа мэднэ."
        elif role == "joker":
            return base + "**☀️ Өдрийн үйлдэл:** `vote <дугаар>`\n🃏 Хэрэв та өөртөө санал өгүүлж, vote-оор хөөгдвөл ганцаараа ялна (Solo win)."
        else:
            return base + "**☀️ Өдрийн үйлдэл:** `vote <дугаар>`\n🗳️ Мафийг олоход тусал."

    async def night_phase_timer(self, game: MafiaGame):
        await asyncio.sleep(self.night_timeout)
        game = self.get_game(game.channel.id)
        if not game or game.phase != "night":
            return
        await self.resolve_night_actions(game)

    async def resolve_night_actions(self, game: MafiaGame):
        mafia_players = [p for p in game.players if p.role in ("mafia", "don", "godmother") and p.alive]
        doctor = next((p for p in game.players if p.role == "doctor" and p.alive), None)
        detective = next((p for p in game.players if p.role == "detective" and p.alive), None)
        turncoat = next((p for p in game.players if p.role == "turncoat" and p.alive), None)

        blackout = game.blackout_night
        game.blackout_night = False

        kill_votes = {}
        for p in mafia_players:
            if p.night_action and isinstance(p.night_action, int):
                kill_votes[p.night_action] = kill_votes.get(p.night_action, 0) + 1

        kill_targets = []
        if kill_votes:
            max_v = max(kill_votes.values())
            candidates = [num for num, cnt in kill_votes.items() if cnt == max_v]
            kill_targets.append(random.choice(candidates))

        if game.double_kill_night:
            extra_kills = []
            for p in mafia_players:
                if p.night_action_extra and isinstance(p.night_action_extra, int):
                    extra_kills.append(p.night_action_extra)
            if extra_kills:
                extra_counts = {}
                for t in extra_kills:
                    extra_counts[t] = extra_counts.get(t, 0) + 1
                max_e = max(extra_counts.values())
                candidates2 = [num for num, cnt in extra_counts.items() if cnt == max_e]
                kill_targets.append(random.choice(candidates2))
            if len(kill_targets) < 2:
                alive_nums = [p.number for p in game.players if p.alive and p.number not in kill_targets]
                if alive_nums:
                    kill_targets.append(random.choice(alive_nums))
            game.double_kill_night = False

        doctor_target = doctor.night_action if doctor and isinstance(doctor.night_action, int) else None
        detective_target = detective.night_action if detective and isinstance(detective.night_action, int) else None
        turncoat_target = turncoat.night_action if turncoat and isinstance(turncoat.night_action, int) else None

        if turncoat and turncoat_target is None:
            dead_nums = [p.number for p in game.players if not p.alive and p.number != turncoat.number]
            if dead_nums:
                turncoat_target = random.choice(dead_nums)
                await self.send_dm(turncoat.member, "🔄 АВТОМАТ ДҮР ХУУЛАЛТ", f"Та **{turncoat_target}** дугаартай тоглогчийн дүрийг автоматаар хууллаа.", WARNING_COLOR)

        if turncoat_target:
            target = next((p for p in game.players if p.number == turncoat_target), None)
            if target and not target.alive and target.role in ("mafia", "detective", "doctor"):
                turncoat.role = target.role
                turncoat.copied_role = True
                await self.send_dm(turncoat.member, "🔄 ДҮР ХУУЛАВ", f"Та одоо **{self.role_name(target.role)}** боллоо!", SUCCESS_COLOR)

        if detective_target and not blackout:
            target = next((p for p in game.players if p.number == detective_target), None)
            if target and target.alive:
                is_mafia = target.role in ("mafia", "don", "godmother") or (target.role == "turncoat" and not target.copied_role)
                result = "**МАФИ (SUS)**" if is_mafia else "**ЦЭВЭР (CLEAN)**"
                await self.send_dm(detective.member, "🔍 МӨРДӨЛТИЙН ҮР ДҮН", f"{detective_target} дугаартай тоглогч → {result}", GOLD_COLOR)

        killed_players = []
        for kt in kill_targets:
            target = next((p for p in game.players if p.number == kt), None)
            if target and target.alive:
                if doctor_target == kt and not blackout:
                    await self.send_embed(game.channel, "💊 **АМЬД ҮЛДЭВ**", f"🔹 **{kt}** дугаартай тоглогч эмчийн авралаар амьд үлдлээ.", SUCCESS_COLOR)
                else:
                    target.alive = False
                    killed_players.append(kt)

        if killed_players:
            await self.send_embed(game.channel, "💀 **АЛАГДЛАА**", f"🔸 **{', '.join(map(str, killed_players))}** дугаартай тоглогч(д) шөнө алагдлаа!\n" + "\n".join([f"📜 Тэр **{self.role_name(next(p for p in game.players if p.number == kp).role)}** байсан." for kp in killed_players]), ERROR_COLOR)

        for p in game.players:
            p.night_action = None
            p.night_action_extra = None

        if await self.check_win(game):
            return

        game.phase = "day"
        game.day_count += 1
        day_embed = discord.Embed(
            title="☀️ **ӨДӨР БОЛЛО**",
            description=f"**{game.day_count}** -р өдөр эхэллээ.\n"
                        f"Амьд тоглогчид vote хийж хөөх тоглогчийн дугаарыг `vote <дугаар>` гэж нийтийн сувагт бичнэ үү.\n\n"
                        f"⏱️ **Хугацаа: {self.day_vote_timeout} секунд**",
            color=GOLD_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        day_embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
        await game.channel.send(embed=day_embed)
        game.vote_task = self.bot.loop.create_task(self.voting_phase_timer(game))

    async def voting_phase_timer(self, game: MafiaGame):
        await asyncio.sleep(self.day_vote_timeout)
        game = self.get_game(game.channel.id)
        if not game or game.phase != "day":
            return

        votes = {}
        for p in game.players:
            if p.alive and p.vote_target:
                votes[p.vote_target] = votes.get(p.vote_target, 0) + 1

        result_embed = discord.Embed(title="🗳️ **САНАЛ ХУРААЛТЫН ДҮН**", color=INFO_COLOR, timestamp=datetime.now(timezone.utc))
        eliminated_num = None
        if not votes:
            result_embed.description = "Хэн ч санал өгөөгүй тул хэн ч хөөгдсөнгүй (No votes cast)."
            result_embed.color = WARNING_COLOR
        else:
            max_v = max(votes.values())
            eliminated = [num for num, cnt in votes.items() if cnt == max_v]
            if len(eliminated) > 1:
                result_embed.description = f"**{', '.join(map(str, eliminated))}** нар адил санал авсан тул хэн ч үхээгүй."
                result_embed.color = WARNING_COLOR
            else:
                eliminated_num = eliminated[0]
                elim_player = next((p for p in game.players if p.number == eliminated_num), None)
                if elim_player:
                    elim_player.alive = False
                    result_embed.description = f"⚖️ **{eliminated_num}** дугаартай тоглогч хөөгдөн үхэв!\n📜 Тэр **{self.role_name(elim_player.role)}** байсан."
                    result_embed.color = ERROR_COLOR

        await game.channel.send(embed=result_embed)

        if eliminated_num is not None:
            joker = next((p for p in game.players if p.role == "joker" and p.number == eliminated_num), None)
            if joker:
                game.joker_win = True
                win_embed = discord.Embed(title="🃏 **JOKER SOLO WIN!** 🃏", description=f"**{joker.member.mention}** өөрийгөө vote-оор хөөлгөж, ганцаараа ялалт байгууллаа!", color=GOLD_COLOR, timestamp=datetime.now(timezone.utc))
                await game.channel.send(embed=win_embed)
                game.phase = "ended"
                await self.delete_faction_channels(game)
                del self.games[game.channel.id]
                return

        for p in game.players:
            p.vote_target = None

        if await self.check_win(game):
            return

        game.phase = "night"
        night_embed = discord.Embed(
            title="🌙 **ШӨНӨ БУУВ**",
            description="Мафи, эмч, цагдаа, урвагч үйлдлээ өөрийн фракцийн сувагт (эсвэл DM) хийгээрэй.\n"
                        f"⏱️ **Хугацаа: {self.night_timeout} секунд**",
            color=PURPLE_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        await game.channel.send(embed=night_embed)
        game.night_task = self.bot.loop.create_task(self.night_phase_timer(game))

    async def check_win(self, game: MafiaGame) -> bool:
        alive = [p for p in game.players if p.alive]
        mafia_side = [p for p in alive if p.role in ("mafia", "don", "godmother") or (p.role == "turncoat" and not p.copied_role)]
        town_side = [p for p in alive if p not in mafia_side and p.role != "joker"]

        if len(mafia_side) == 0:
            win_embed = discord.Embed(title="🎉 **ИРГЭД ЯЛАЛТ БАЙГУУЛЛАА!**", description="Бүх мафи болон урвагч үхсэн. Хот амар тайван боллоо (GG).", color=SUCCESS_COLOR, timestamp=datetime.now(timezone.utc))
            await game.channel.send(embed=win_embed)
            game.phase = "ended"
            await self.delete_faction_channels(game)
            del self.games[game.channel.id]
            return True
        if len(mafia_side) >= len(town_side):
            win_embed = discord.Embed(title="💀 **МАФИ ЯЛАЛТ БАЙГУУЛЛАА!**", description="Мафи бүх иргэдийг дийлсэн. Хот тэдний гарт орлоо.", color=MAFIA_RED, timestamp=datetime.now(timezone.utc))
            await game.channel.send(embed=win_embed)
            game.phase = "ended"
            await self.delete_faction_channels(game)
            del self.games[game.channel.id]
            return True
        return False

    # ========== MESSAGE LISTENER (Vote + Night Actions) ==========
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Өдрийн vote (нийтийн сувагт)
        if message.guild:
            game = self.get_game(message.channel.id)
            if game and game.phase == "day":
                content = message.content.strip().lower()
                if content.startswith("vote "):
                    try:
                        parts = content.split()
                        if len(parts) != 2:
                            return
                        target_num = int(parts[1])
                    except:
                        return
                    voter = next((p for p in game.players if p.member.id == message.author.id), None)
                    if not voter or not voter.alive:
                        await message.delete()
                        return
                    target = next((p for p in game.players if p.number == target_num and p.alive), None)
                    if not target:
                        await message.channel.send(f"{message.author.mention} **{target_num}** дугаартай амьд тоглогч байхгүй.", delete_after=5)
                        await message.delete()
                        return
                    if voter.vote_target is not None:
                        await message.channel.send(f"{message.author.mention} Та аль хэдийн санал өгсөн байна.", delete_after=5)
                        await message.delete()
                        return
                    voter.vote_target = target.number
                    await message.channel.send(f"✅ {message.author.mention} → **{target_num}** дугаарт санал өглөө.", delete_after=5)
                    await message.delete()
                return

            # Фракцийн сувгууд дахь шөнийн командууд
            game = None
            for g in self.games.values():
                if g.phase == "night" and message.channel.id in [c.id for c in (g.mafia_channel, g.detective_channel) if c]:
                    game = g
                    break
            if not game:
                return

            player = next((p for p in game.players if p.member.id == message.author.id), None)
            if not player or not player.alive:
                return

            content = message.content.strip().lower()
            parts = content.split()
            if len(parts) != 2:
                await message.channel.send(f"{message.author.mention} ❌ **Буруу формат!** Жишээ: `kill 3`, `save 5`, `investigate 2`, `sleep 7`")
                return
            action, target_str = parts[0], parts[1]
            try:
                target_num = int(target_str)
            except:
                await message.channel.send(f"{message.author.mention} ❌ **Зөвхөн тоо оруулна уу.**")
                return

            target_player = next((p for p in game.players if p.number == target_num), None)
            if not target_player:
                await message.channel.send(f"{message.author.mention} ❌ **{target_num}** дугаартай тоглогч байхгүй.")
                return

            role = player.role
            channel = message.channel

            if action == "kill":
                if role not in ("mafia", "don", "godmother"):
                    await channel.send(f"{message.author.mention} ❌ **Та мафи биш.**")
                    return
                if target_num == player.number:
                    await channel.send(f"{message.author.mention} ❌ **Өөртөө алах боломжгүй.**")
                    return
                if target_player.role in ("mafia", "don", "godmother", "turncoat"):
                    await channel.send(f"{message.author.mention} ❌ **Хамтрагчаа алж болохгүй.**")
                    return
                if game.double_kill_night and player.night_action is not None:
                    player.night_action_extra = target_num
                    await channel.send(f"✅ {message.author.mention} **{target_num}** -г хоёр дахь байгаагаар алахаар шийдлээ.")
                else:
                    player.night_action = target_num
                    await channel.send(f"✅ {message.author.mention} **{target_num}** -г алахаар шийдлээ.")
            elif action == "save":
                if role != "doctor":
                    await channel.send(f"{message.author.mention} ❌ **Зөвхөн эмч эмчилнэ.**")
                    return
                player.night_action = target_num
                await channel.send(f"✅ {message.author.mention} **{target_num}** -г эмчлэнэ.")
            elif action == "investigate":
                if role != "detective":
                    await channel.send(f"{message.author.mention} ❌ **Зөвхөн цагдаа мөрдөнө.**")
                    return
                player.night_action = target_num
                await channel.send(f"✅ {message.author.mention} **{target_num}** -г мөрдөнө.")
            elif action == "sleep":
                if role != "turncoat":
                    await channel.send(f"{message.author.mention} ❌ **Зөвхөн урвагч унтаж болно.**")
                    return
                if target_player.alive:
                    await channel.send(f"{message.author.mention} ❌ **Зөвхөн үхсэн тоглогчтой унтана.**")
                    return
                player.night_action = target_num
                await channel.send(f"✅ {message.author.mention} **{target_num}** -тэй унтана.")
            else:
                await channel.send(f"{message.author.mention} ❌ **Буруу үйлдэл.** Зөвшөөрөгдсөн: `kill`, `save`, `investigate`, `sleep`")

        # DM-ээр ирсэн командууд (фракцийн суваггүй үед)
        if message.guild is None:
            game = None
            for g in self.games.values():
                for p in g.players:
                    if p.member.id == message.author.id and p.alive and g.phase == "night":
                        game = g
                        player = p
                        break
                if game:
                    break
            if not game:
                return

            content = message.content.strip().lower()
            parts = content.split()
            if len(parts) != 2:
                await message.channel.send("❌ **Буруу формат!** Жишээ: `kill 3`, `save 5`, `investigate 2`, `sleep 7`")
                return
            action, target_str = parts[0], parts[1]
            try:
                target_num = int(target_str)
            except:
                await message.channel.send("❌ **Зөвхөн тоо оруулна уу.**")
                return

            target_player = next((p for p in game.players if p.number == target_num), None)
            if not target_player:
                await message.channel.send(f"❌ **{target_num}** дугаартай тоглогч байхгүй.")
                return

            role = player.role

            if action == "kill":
                if role not in ("mafia", "don", "godmother"):
                    await message.channel.send("❌ **Та мафи биш.**")
                    return
                if target_num == player.number:
                    await message.channel.send("❌ **Өөртөө алах боломжгүй.**")
                    return
                if target_player.role in ("mafia", "don", "godmother", "turncoat"):
                    await message.channel.send("❌ **Хамтрагчаа алж болохгүй.**")
                    return
                if game.double_kill_night and player.night_action is not None:
                    player.night_action_extra = target_num
                    await message.channel.send(f"✅ Та **{target_num}** -г хоёр дахь байгаагаар алахаар шийдлээ.")
                else:
                    player.night_action = target_num
                    await message.channel.send(f"✅ Та **{target_num}** -г алахаар шийдлээ.")
            elif action == "save":
                if role != "doctor":
                    await message.channel.send("❌ **Зөвхөн эмч эмчилнэ.**")
                    return
                player.night_action = target_num
                await message.channel.send(f"✅ Та **{target_num}** -г эмчлэнэ.")
            elif action == "investigate":
                if role != "detective":
                    await message.channel.send("❌ **Зөвхөн цагдаа мөрдөнө.**")
                    return
                player.night_action = target_num
                await message.channel.send(f"✅ Та **{target_num}** -г мөрдөнө.")
            elif action == "sleep":
                if role != "turncoat":
                    await message.channel.send("❌ **Зөвхөн урвагч унтаж болно.**")
                    return
                if target_player.alive:
                    await message.channel.send("❌ **Зөвхөн үхсэн тоглогчтой унтана.**")
                    return
                player.night_action = target_num
                await message.channel.send(f"✅ Та **{target_num}** -тэй унтана.")
            else:
                await message.channel.send("❌ **Буруу үйлдэл.** Зөвшөөрөгдсөн: `kill`, `save`, `investigate`, `sleep`")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_has = any(r.name == self.dvr.dvr_role_name for r in before.roles)
        after_has = any(r.name == self.dvr.dvr_role_name for r in after.roles)
        if not before_has and after_has:
            await self.dvr.create_dvr_channel(after)
        elif before_has and not after_has:
            await self.dvr.delete_dvr_channel(after.id, after.guild)

    def cog_unload(self):
        for game in list(self.games.values()):
            if game.night_task:
                game.night_task.cancel()
            if game.vote_task:
                game.vote_task.cancel()
            self.bot.loop.create_task(self.delete_faction_channels(game))


async def setup(bot):
    await bot.add_cog(Mafia(bot))