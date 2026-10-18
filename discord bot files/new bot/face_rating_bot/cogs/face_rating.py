import discord
import io
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button, ChannelSelect
from ai import analyze_face
from image import draw_rating_card
import aiohttp

class FaceRatingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with self.bot.db.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT, username TEXT,
                    overall REAL, jawline REAL, eyes REAL,
                    cheekbones REAL, symmetry REAL, skin REAL,
                    summary TEXT, advice TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                await conn.execute("ALTER TABLE ratings ADD COLUMN advice TEXT")
            except Exception:
                pass

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS rating_config (
                    guild_id TEXT PRIMARY KEY,
                    announce_channel INTEGER
                )
            """)
            await conn.commit()

    async def _get_announce_channel(self, guild_id: int) -> discord.TextChannel | None:
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT announce_channel FROM rating_config WHERE guild_id=?",
                (str(guild_id),)
            ) as cur:
                row = await cur.fetchone()
        if row and row[0]:
            return self.bot.get_channel(int(row[0]))
        return None

    async def _set_announce_channel(self, guild_id: int, channel: discord.TextChannel):
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO rating_config (guild_id, announce_channel) VALUES (?,?)",
                (str(guild_id), channel.id)
            )
            await conn.commit()

    @app_commands.command(name="rate", description="Нүүрний зургаа үнэлүүлэх 📸")
    @app_commands.describe(image="Үнэлүүлэх зураг")
    async def rate(self, interaction: discord.Interaction, image: discord.Attachment):
        if not image.content_type or not image.content_type.startswith("image/"):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Алдаа",
                    description="Зөвхөн зураг оруулна уу! (JPEG, PNG, GIF)",
                    color=0xed4245
                ),
                ephemeral=True
            )
        await interaction.response.defer()

        try:
            data = await analyze_face(image.url)
        except Exception as e:
            error_msg = str(e)
            print(f"[FaceRating] Error analyzing face: {error_msg}")
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Үнэлэлт амжилтгүй",
                    description=error_msg[:200],
                    color=0xed4245
                )
            )

        # Хадгалах
        try:
            async with self.bot.db.acquire() as conn:
                await conn.execute(
                    "INSERT INTO ratings (user_id, username, overall, jawline, eyes, cheekbones, symmetry, skin, summary, advice)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(interaction.user.id), interaction.user.name,
                        float(data.get("overall", 0)), float(data.get("jawline", 0)), float(data.get("eyes", 0)),
                        float(data.get("cheekbones", 0)), float(data.get("symmetry", 0)), float(data.get("skin", 0)),
                        data.get("summary", ""), data.get("advice", "")
                    )
                )
                await conn.commit()
        except Exception as e:
            print(f"[FaceRating] Database save error: {e}")

        # Карт үүсгэх
        card_file = None
        try:
            card_buf = draw_rating_card(interaction.user.name, data)
            card_file = discord.File(card_buf, filename="rating.png")
        except Exception as e:
            print(f"[FaceRating] Карт үүсгэхэд алдаа: {e}")

        # Хэрэглэгчийн зургийг татаж файл болгох
        user_image_file = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image.url) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        ext = image.filename.split(".")[-1] if "." in image.filename else "png"
                        user_image_file = discord.File(
                            io.BytesIO(img_data),
                            filename=f"user_image.{ext}"
                        )
        except Exception as e:
            print(f"[FaceRating] Хэрэглэгчийн зураг татахад алдаа: {e}")

        # Embed бэлтгэх
        embed = discord.Embed(title="⭐ Нүүрний үнэлгээ", color=0xffd700)
        embed.add_field(name="Нийт оноо", value=f"**{data['overall']:.1f} / 10**", inline=False)
        embed.add_field(name="Эрүүний хэлбэр", value=f"{data['jawline']:.1f}", inline=True)
        embed.add_field(name="Нүд", value=f"{data['eyes']:.1f}", inline=True)
        embed.add_field(name="Шанааны хэлбэр", value=f"{data['cheekbones']:.1f}", inline=True)
        embed.add_field(name="Тэгш хэм", value=f"{data['symmetry']:.1f}", inline=True)
        embed.add_field(name="Арьс", value=f"{data['skin']:.1f}", inline=True)
        embed.add_field(name="AI дүгнэлт", value=data.get("summary", ""), inline=False)
        if data.get("advice"):
            embed.add_field(name="💡 Хөгжүүлэх зөвлөгөө", value=data["advice"], inline=False)
        embed.set_thumbnail(url=image.url)
        if card_file:
            embed.set_image(url="attachment://rating.png")
        embed.set_footer(text=f"{interaction.user.name} • FaceBot")

        # Илгээх файлуудыг жагсаах
        files = []
        if card_file:
            files.append(card_file)
        if user_image_file:
            files.append(user_image_file)

        # Зарлах сувагт нийтлэх
        try:
            announce_ch = await self._get_announce_channel(interaction.guild_id)
            if announce_ch and announce_ch.permissions_for(interaction.guild.me).send_messages:
                try:
                    await announce_ch.send(embed=embed, files=files if files else None)
                except Exception as e:
                    print(f"[FaceRating] Зарлах сувагт илгээхэд алдаа: {e}")
        except Exception as e:
            print(f"[FaceRating] Announce channel error: {e}")

        # Хэрэглэгчид хариу илгээх
        try:
            await interaction.followup.send(embed=embed, files=files if files else None)
        except Exception as e:
            print(f"[FaceRating] Followup send error: {e}")
            await interaction.followup.send(
                embed=discord.Embed(
                    title="⭐ Үнэлгээ амжилттай",
                    description=f"Нийт оноо: **{data.get('overall', 0):.1f}/10**",
                    color=0xffd700
                )
            )

    @app_commands.command(name="history", description="Өөрийн үнэлгээний түүх 📜")
    async def history(self, interaction: discord.Interaction):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT overall, created_at FROM ratings WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
                (str(interaction.user.id),)
            ) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="📜 Түүх",
                    description="Одоогоор ямар ч үнэлгээ байхгүй.",
                    color=0xfab387
                ),
                ephemeral=True
            )
        embed = discord.Embed(
            title=f"📜 {interaction.user.name}-ын үнэлгээний түүх",
            color=0x3498db
        )
        for i, (score, date) in enumerate(rows, 1):
            embed.add_field(name=f"#{i} – {score:.1f}", value=str(date)[:10], inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="top", description="Хамгийн өндөр үнэлгээтэй хэрэглэгчид 🏆")
    async def top(self, interaction: discord.Interaction):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT username, overall FROM ratings ORDER BY overall DESC LIMIT 10"
            ) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🏆 Топ",
                    description="Одоогоор өгөгдөл байхгүй.",
                    color=0xfab387
                )
            )
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        embed = discord.Embed(
            title="🏆 FaceBot – Хамгийн өндөр үнэлгээ",
            color=0xffd700
        )
        for i, (name, score) in enumerate(rows):
            embed.add_field(
                name=f"{medals.get(i, f'#{i+1}')} {name}",
                value=f"**{score:.1f}**",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="face_stats", description="Өөрийн нүүрний үзүүлэлтийн статистик 📊")
    async def face_stats(self, interaction: discord.Interaction):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT AVG(overall), AVG(jawline), AVG(eyes), AVG(cheekbones), AVG(symmetry), AVG(skin), COUNT(*) FROM ratings WHERE user_id=?",
                (str(interaction.user.id),)
            ) as cur:
                row = await cur.fetchone()
        
        if not row or row[6] == 0:
            return await interaction.response.send_message("📊 Танд одоогоор үнэлгээний түүх байхгүй байна.", ephemeral=True)
        
        avg_overall, avg_jaw, avg_eyes, avg_cheek, avg_sym, avg_skin, count = row
        embed = discord.Embed(title=f"📊 {interaction.user.name}-ын статистик", color=0x3498db)
        embed.description = f"Нийт **{count}** удаа үнэлүүлсэн байна."
        embed.add_field(name="Дундаж оноо", value=f"**{avg_overall:.1f}**", inline=False)
        embed.add_field(name="Эрүү", value=f"{avg_jaw:.1f}", inline=True)
        embed.add_field(name="Нүд", value=f"{avg_eyes:.1f}", inline=True)
        embed.add_field(name="Шанаа", value=f"{avg_cheek:.1f}", inline=True)
        embed.add_field(name="Тэгш хэм", value=f"{avg_sym:.1f}", inline=True)
        embed.add_field(name="Арьс", value=f"{avg_skin:.1f}", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="compare", description="Өөр хэрэглэгчтэй нүүрний үнэлгээгээрээ өрсөлдөх ⚔️")
    @app_commands.describe(user="Өрсөлдөх хэрэглэгч")
    async def compare(self, interaction: discord.Interaction, user: discord.User):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT overall FROM ratings WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
                (str(interaction.user.id),)
            ) as cur:
                row1 = await cur.fetchone()
            async with conn.execute(
                "SELECT overall FROM ratings WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
                (str(user.id),)
            ) as cur:
                row2 = await cur.fetchone()
        
        if not row1:
            return await interaction.response.send_message("❌ Та өөрөө үнэлгээ хийлгээгүй байна.", ephemeral=True)
        if not row2:
            return await interaction.response.send_message(f"❌ {user.name} үнэлгээ хийлгээгүй байна.", ephemeral=True)
        
        score1, score2 = row1[0], row2[0]
        winner = interaction.user if score1 > score2 else (user if score2 > score1 else None)
        
        embed = discord.Embed(title="⚔️ Нүүрний үнэлгээний тулаан", color=0xff4500)
        embed.add_field(name=interaction.user.name, value=f"**{score1:.1f}**", inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name=user.name, value=f"**{score2:.1f}**", inline=True)
        
        if winner:
            embed.description = f"🏆 Ялагч: **{winner.mention}**"
        else:
            embed.description = "⚖️ Тэнцлээ!"
            
        await interaction.response.send_message(embed=embed)

    # ══════════════ АДМИН ПАНЕЛЬ (RATINGPANEL) ══════════════
    @app_commands.command(name="ratingpanel", description="AI Rating админ самбар")
    async def ratingpanel(self, interaction: discord.Interaction):
        is_owner = interaction.user.id == self.bot.config["owner_id"]
        is_co_owner = interaction.user.id in self.bot.config["co_owners"]
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_owner or is_co_owner or is_admin):
            return await interaction.response.send_message(
                "⛔ Танд админ эрх байхгүй.",
                ephemeral=True
            )

        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT id, username, overall, created_at FROM ratings ORDER BY created_at DESC LIMIT 10"
            ) as cur:
                rows = await cur.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Ямар ч үнэлгээ байхгүй.",
                ephemeral=True
            )

        options = []
        for rid, name, score, date in rows:
            options.append(
                discord.SelectOption(
                    label=f"{name} - {score:.1f} ({str(date)[:10]})",
                    value=str(rid)
                )
            )

        view = RatingAdminView(self, options, interaction.guild_id)
        embed = discord.Embed(
            title="⭐ AI Rating Admin Panel",
            description="Сүүлийн 10 үнэлгээг удирдах",
            color=0xfab387
        )
        announce_ch = await self._get_announce_channel(interaction.guild_id)
        embed.add_field(
            name="📢 Зарлах суваг",
            value=announce_ch.mention if announce_ch else "Тохируулаагүй",
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RatingAdminView(View):
    def __init__(self, cog, options, guild_id):
        super().__init__(timeout=180)
        self.cog = cog
        self.guild_id = guild_id
        self.selected_id = None

        self.select = Select(
            placeholder="Устгах үнэлгээг сонгох...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_id = int(self.select.values[0])
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            f"Сонгогдсон ID: {self.selected_id}",
            ephemeral=True
        )

    @discord.ui.button(label="🗑️ Үнэлгээ устгах", style=discord.ButtonStyle.red, row=1)
    async def delete_btn(self, interaction: discord.Interaction, button: Button):
        if not self.selected_id:
            return await interaction.response.send_message(
                "❌ Эхлээд үнэлгээ сонгоно уу.",
                ephemeral=True
            )
        async with self.cog.bot.db.acquire() as conn:
            await conn.execute("DELETE FROM ratings WHERE id=?", (self.selected_id,))
            await conn.commit()
        await interaction.response.send_message(
            f"✅ ID {self.selected_id} устгагдлаа.",
            ephemeral=True
        )
        self.stop()
        await interaction.edit_original_response(view=None)

    @discord.ui.button(label="📢 Суваг тохируулах", style=discord.ButtonStyle.blurple, row=1)
    async def channel_btn(self, interaction: discord.Interaction, button: Button):
        view = ChannelSelectView(self.cog, self.guild_id, self)
        await interaction.response.send_message(
            "Зарлах сувгаа сонгоно уу:",
            view=view,
            ephemeral=True
        )


class ChannelSelectView(View):
    def __init__(self, cog, guild_id, parent_view):
        super().__init__(timeout=60)
        self.cog = cog
        self.guild_id = guild_id
        self.parent_view = parent_view
        self.channel_select = ChannelSelect(
            placeholder="Зарлах суваг сонгох...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )
        self.channel_select.callback = self.channel_callback
        self.add_item(self.channel_select)

    async def channel_callback(self, interaction: discord.Interaction):
        channel = self.channel_select.values[0]
        await self.cog._set_announce_channel(self.guild_id, channel)
        await interaction.response.send_message(
            f"✅ {channel.mention} суваг зарлах суваг боллоо.",
            ephemeral=True
        )
        self.stop()


async def setup(bot):
    await bot.add_cog(FaceRatingCog(bot))