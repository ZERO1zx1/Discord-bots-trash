import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
import aiosqlite
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import os
from config import DB_PATH
from utils.helpers import format_currency

# ---------- Фонт туслах ----------
def get_font(size: int, bold: bool = False):
    try:
        font_paths = []
        if bold:
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ]
        else:
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ]
        for path in font_paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    except:
        pass
    return ImageFont.load_default()

def format_number(num: int) -> str:
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

# ---------- Аватар татах ----------
async def fetch_avatar(session, url: str, size: int = 64):
    try:
        async with session.get(url) as resp:
            data = await resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
    except:
        img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img

# ==================== VIEW ====================
class LeaderboardView(View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.guild_id = ctx.guild.id
        self.current_category = "level"
        self.page = 0
        self.per_page = 10

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Энэ лидерборд таны биш.", ephemeral=True)
            return False
        return True

    @Select(
        placeholder="🏆 Лидербордын төрөл сонгох",
        options=[
            discord.SelectOption(label="🏆 Түвшин", value="level", description="Түвшнээр эрэмбэлэх"),
            discord.SelectOption(label="💬 Мессеж", value="messages", description="Илгээсэн мессежийн тоогоор"),
            discord.SelectOption(label="🎤 Дуут цаг", value="voice_time", description="Дуут сувагт зарцуулсан хугацаа"),
            discord.SelectOption(label="❤️ Реакц", value="reactions", description="Реакц дарах тоогоор"),
            discord.SelectOption(label="💰 Мөнгө", value="money", description="Валютын хэмжээгээр"),
            discord.SelectOption(label="📨 Урилга", value="invites", description="Урилгын тоогоор (хэрэв байгаа бол)"),
            discord.SelectOption(label="🔢 Тоололт", value="counting", description="Counting тоглоомын зөв тоололт"),
            discord.SelectOption(label="🎮 Тоглоом", value="games", description="Тоглоомын ялалт/хожил"),
        ]
    )
    async def category_select(self, interaction, select):
        self.current_category = select.values[0]
        self.page = 0
        embed, file = await self.build_embed()
        await interaction.response.edit_message(embed=embed, attachments=[file] if file else [], view=self)

    @Button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction, button):
        self.page = max(0, self.page - 1)
        embed, file = await self.build_embed()
        await interaction.response.edit_message(embed=embed, attachments=[file] if file else [], view=self)

    @Button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction, button):
        self.page += 1
        embed, file = await self.build_embed()
        await interaction.response.edit_message(embed=embed, attachments=[file] if file else [], view=self)

    @Button(label="📸 Карт", style=discord.ButtonStyle.success)
    async def show_card(self, interaction, button):
        await interaction.response.defer()
        rows, title, label_func = await self.fetch_data(self.page * self.per_page, self.per_page)
        if not rows:
            return await interaction.edit_original_response(
                embed=discord.Embed(description="Энэ төрөлд өгөгдөл байхгүй.", color=0xff0000),
                view=self
            )
        file = await self.generate_card(rows, title, label_func)
        embed = discord.Embed(color=0x2f3136)
        embed.set_image(url="attachment://leaderboard_card.png")
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

    # ---------- Өгөгдөл татах ----------
    async def fetch_data(self, offset, limit):
        cat = self.current_category
        if cat == "level":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            return rows, "🏆 ТҮВШНИЙ ЛИДЕРБОРД", lambda lvl, xp: f"Түв.{lvl} • {format_number(xp)} XP"

        elif cat == "messages":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, message_count FROM users ORDER BY message_count DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            return rows, "💬 МЕССЕЖИЙН ЛИДЕРБОРД", lambda cnt: f"{format_number(cnt)} мессеж"

        elif cat == "voice_time":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, voice_seconds FROM users ORDER BY voice_seconds DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            def voice_label(sec):
                h, m = divmod(sec, 3600)
                return f"{h} цаг {m//60} мин"
            return rows, "🎤 ДУУТ ЦАГИЙН ЛИДЕРБОРД", voice_label

        elif cat == "reactions":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, reaction_count FROM users ORDER BY reaction_count DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            return rows, "❤️ РЕАКЦЫН ЛИДЕРБОРД", lambda cnt: f"{format_number(cnt)} реакц"

        elif cat == "money":
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT user_id, balance + bank AS total FROM users ORDER BY total DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = await cur.fetchall()
            return rows, "💰 ВАЛЮТЫН ЛИДЕРБОРД", lambda bal: f"{format_number(bal)} ₮"

        elif cat == "invites":
            inv = self.cog.bot.get_cog("InviteTracker")
            if inv and hasattr(inv, "get_top_inviters"):
                rows = await inv.get_top_inviters(self.guild_id, limit, offset)
                return rows, "📨 УРИЛГЫН ЛИДЕРБОРД", lambda cnt: f"{format_number(cnt)} урилга"
            return None, None, None

        elif cat == "counting":
            cnt = self.cog.bot.get_cog("Counting")
            if cnt and hasattr(cnt, "get_top_counters"):
                rows = await cnt.get_top_counters(self.guild_id, limit, offset)
                return rows, "🔢 ТООЛОЛТЫН ЛИДЕРБОРД", lambda c: f"{format_number(c)} зөв тоололт"
            return None, None, None

        elif cat == "games":
            g = self.cog.bot.get_cog("Games")
            if g and hasattr(g, "get_top_games"):
                rows = await g.get_top_games(self.guild_id, limit, offset)
                return rows, "🎮 ТОГЛООМЫН ЛИДЕРБОРД", lambda sc: f"{format_number(sc)} ₮ хожил"
            return None, None, None

        return None, None, None

    # ---------- Карт зурах ----------
    async def generate_card(self, rows, title, label_func):
        W, H = 900, 560
        img = Image.new("RGBA", (W, H), "#2f3136")
        draw = ImageDraw.Draw(img)

        font_title = get_font(34, bold=True)
        font_name = get_font(22, bold=True)
        font_small = get_font(18, bold=False)

        draw.text(((W - draw.textlength(title, font=font_title)) // 2, 25), title, fill="#fab387", font=font_title)
        draw.line((40, 75, W - 40, 75), fill="#484b51", width=2)

        row_height = 45
        start_y = 90
        avatar_size = 38

        async with aiohttp.ClientSession() as session:
            for i, row in enumerate(rows):
                y = start_y + i * row_height
                uid = str(row[0])
                value = row[1]
                member = self.ctx.guild.get_member(int(uid))
                if not member:
                    try:
                        member = await self.cog.bot.fetch_user(int(uid))
                    except:
                        continue
                name = member.display_name if member else "Тодорхойгүй"

                avatar_url = member.display_avatar.replace(size=128, format="png").url
                avatar_img = await fetch_avatar(session, avatar_url, avatar_size)
                img.paste(avatar_img, (35, y + 3), avatar_img)

                rank_text = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"#{i+1}")
                draw.text((85, y + 6), rank_text, fill="#ffffff", font=font_name)
                draw.text((120, y + 6), name[:20], fill="#ffffff", font=font_name)

                if isinstance(value, tuple):
                    label = label_func(*value)
                else:
                    label = label_func(value)
                draw.text((450, y + 6), label, fill="#a6a6a6", font=font_small)

        draw.text((W // 2 - 100, H - 30), "Powered by Discord Leveling", fill="#666666", font=get_font(14))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="leaderboard_card.png")

    # ---------- Embed үүсгэх ----------
    async def build_embed(self):
        offset = self.page * self.per_page
        rows, title, label_func = await self.fetch_data(offset, self.per_page)
        embed = discord.Embed(title=title, color=0x7289da)
        if not rows:
            embed.description = "Одоогоор өгөгдөл байхгүй."
            return embed, None

        desc = []
        for i, row in enumerate(rows, start=offset + 1):
            uid = str(row[0])
            value = row[1]
            member = self.ctx.guild.get_member(int(uid))
            if not member:
                try:
                    member = await self.cog.bot.fetch_user(int(uid))
                except:
                    continue
            name = member.display_name if member else "Тодорхойгүй"
            if isinstance(value, tuple):
                label = label_func(*value)
            else:
                label = label_func(value)
            desc.append(f"`#{i}` **{name}** – {label}")

        embed.description = "\n".join(desc[:self.per_page])
        embed.set_footer(text=f"Хуудас {self.page + 1}  •  Нийт {len(rows)} харуулж байна")
        return embed, None


# ==================== COG ====================
class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Олон төрлийн лидерборд харах")
    async def slash_leaderboard(self, interaction: discord.Interaction):
        view = LeaderboardView(self, interaction)
        embed, file = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @commands.hybrid_command(name="lb", aliases=["leaderboard"], description="Лидерборд харах")
    async def prefix_leaderboard(self, ctx):
        view = LeaderboardView(self, ctx)
        embed, file = await view.build_embed()
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
