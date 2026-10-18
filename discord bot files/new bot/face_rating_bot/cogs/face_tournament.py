import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button, ChannelSelect
from typing import Optional
import time
import aiohttp
import io
from PIL import Image

# ────────────────── ТЭМЦЭЭНИЙ VIEW (ШИНЭЧЛЭЛ) ──────────────────
class FaceBattleView(View):
    def __init__(self, cog, guild_id, entry1, entry2, timeout_seconds=120):
        super().__init__(timeout=timeout_seconds)
        self.cog = cog
        self.guild_id = guild_id
        self.entry1 = entry1
        self.entry2 = entry2
        self.voters = set()
        self.votes1 = 0
        self.votes2 = 0
        self.started_at = time.time()
        self.message = None
        self._ended = False
        self.stitched_file = None
        self.stitched_url = None

    async def _prepare_images(self):
        """Хоёр зургийг татаж, зэрэгцүүлж нэг зураг болгох"""
        url1 = self.entry1.get("image_url")
        url2 = self.entry2.get("image_url")
        
        if not url1 or not url2:
            return

        try:
            async with aiohttp.ClientSession() as session:
                # 1-р зургийг татах
                async with session.get(url1) as resp1:
                    if resp1.status != 200: return
                    img1_data = await resp1.read()
                
                # 2-р зургийг татах
                async with session.get(url2) as resp2:
                    if resp2.status != 200: return
                    img2_data = await resp2.read()

            img1 = Image.open(io.BytesIO(img1_data)).convert("RGBA")
            img2 = Image.open(io.BytesIO(img2_data)).convert("RGBA")

            # Өндрийг нь ижил болгох (жишээ нь 400px)
            h = 400
            w1 = int(img1.width * (h / img1.height))
            w2 = int(img2.width * (h / img2.height))
            
            img1 = img1.resize((w1, h), Image.Resampling.LANCZOS)
            img2 = img2.resize((w2, h), Image.Resampling.LANCZOS)

            # Хооронд нь зай авах (10px)
            gap = 10
            combined = Image.new("RGBA", (w1 + w2 + gap, h), (0, 0, 0, 0))
            combined.paste(img1, (0, 0))
            combined.paste(img2, (w1 + gap, 0))

            buf = io.BytesIO()
            combined.save(buf, format="PNG")
            buf.seek(0)
            self.stitched_file = discord.File(buf, filename="battle.png")
        except Exception as e:
            print(f"Error stitching images: {e}")

    def embed(self):
        title = f"{self.entry1['username']} VS {self.entry2['username']}"
        e = discord.Embed(title=title, color=0xff4500)
        
        if self.stitched_url:
            e.set_image(url=self.stitched_url)
        else:
            e.set_image(url="attachment://battle.png")

        rem = max(0, int(self.timeout - (time.time() - self.started_at)))
        e.set_footer(text=f"Дуусахад үлдсэн: {rem} секунд")
        return e

    @discord.ui.button(label="⬅️ 0", style=discord.ButtonStyle.primary)
    async def vote1(self, interaction, button):
        if interaction.user.id in self.voters:
            return await interaction.response.send_message("❌ Та аль хэдийн санал өгсөн!", ephemeral=True)
        if interaction.user.id in [self.entry1["user_id"], self.entry2["user_id"]]:
            return await interaction.response.send_message("❌ Өөрийнхөө төлөө санал өгч болохгүй!", ephemeral=True)
        self.voters.add(interaction.user.id); self.votes1 += 1
        button.label = f"⬅️ {self.votes1}"
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="➡️ 0", style=discord.ButtonStyle.primary)
    async def vote2(self, interaction, button):
        if interaction.user.id in self.voters:
            return await interaction.response.send_message("❌ Та аль хэдийн санал өгсөн!", ephemeral=True)
        if interaction.user.id in [self.entry1["user_id"], self.entry2["user_id"]]:
            return await interaction.response.send_message("❌ Өөрийнхөө төлөө санал өгч болохгүй!", ephemeral=True)
        self.voters.add(interaction.user.id); self.votes2 += 1
        button.label = f"➡️ {self.votes2}"
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def _finish(self):
        if self._ended:
            return
        self._ended = True
        for c in self.children: c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass
        await self.cog._end_battle(self)

    async def on_timeout(self):
        await self._finish()

# ────────────────── АДМИН САМБАР ──────────────────
class FaceAdminView(View):
    def __init__(self, cog, entry_options):
        super().__init__(timeout=600)
        self.cog = cog
        self.selected1 = None
        self.selected2 = None
        self.selected_channel = None
        self.selected_duration = 120

        self.select1 = Select(placeholder="1-р зураг сонгох", options=entry_options, row=0)
        self.select2 = Select(placeholder="2-р зураг сонгох", options=entry_options, row=1)
        self.select1.callback = self.cb1
        self.select2.callback = self.cb2
        self.add_item(self.select1); self.add_item(self.select2)

        self.chan_sel = ChannelSelect(placeholder="📢 Зарлах суваг", channel_types=[discord.ChannelType.text], row=2)
        self.chan_sel.callback = self.cb_chan
        self.add_item(self.chan_sel)

        dur_opts = [
            discord.SelectOption(label="1 минут", value="60"),
            discord.SelectOption(label="2 минут (анхдагч)", value="120"),
            discord.SelectOption(label="3 минут", value="180"),
            discord.SelectOption(label="5 минут", value="300"),
            discord.SelectOption(label="10 минут", value="600"),
        ]
        self.dur_sel = Select(placeholder="⏱️ Санал хураалтын хугацаа", options=dur_opts, row=3)
        self.dur_sel.callback = self.cb_dur
        self.add_item(self.dur_sel)

    async def cb1(self, i): self.selected1 = int(self.select1.values[0]); await i.response.defer()
    async def cb2(self, i): self.selected2 = int(self.select2.values[0]); await i.response.defer()
    async def cb_chan(self, i):
        self.selected_channel = self.chan_sel.values[0]
        await i.response.defer(ephemeral=True)
        await i.followup.send(f"📢 {self.selected_channel.mention}", ephemeral=True)
    async def cb_dur(self, i):
        self.selected_duration = int(self.dur_sel.values[0])
        await i.response.defer(ephemeral=True)
        await i.followup.send(f"⏱️ Хугацаа **{self.selected_duration//60} минут** боллоо.", ephemeral=True)

    async def _get_channel(self, interaction):
        """Сонгосон сувгийг жинхэнэ TextChannel объект болгох"""
        if self.selected_channel:
            ch_id = self.selected_channel.id
            ch = interaction.guild.get_channel(ch_id)
            if ch is None:
                try:
                    ch = await interaction.guild.fetch_channel(ch_id)
                except:
                    ch = None
            return ch if ch else interaction.channel
        return interaction.channel

    @discord.ui.button(label="🚀 Эхлүүлэх", style=discord.ButtonStyle.green, row=4)
    async def start_btn(self, interaction, button):
        # Хэрэв хугацаа хадгалагдаагүй бол шууд унших (аюулгүй)
        if self.dur_sel.values:
            self.selected_duration = int(self.dur_sel.values[0])

        if not self.selected1 or not self.selected2:
            return await interaction.response.send_message("❌ Хоёр оролцогч сонгоно уу.", ephemeral=True)
        if self.selected1 == self.selected2:
            return await interaction.response.send_message("❌ Өөр хүн сонгоно уу.", ephemeral=True)
        e1 = await self.cog._get_entry(interaction.guild_id, self.selected1)
        e2 = await self.cog._get_entry(interaction.guild_id, self.selected2)
        if not e1 or not e2:
            return await interaction.response.send_message("❌ Оролцогч олдсонгүй.", ephemeral=True)
        if interaction.guild_id in self.cog.active_battles:
            return await interaction.response.send_message("❌ Нэг тэмцээн аль хэдийн идэвхтэй.", ephemeral=True)

        ch = await self._get_channel(interaction)

        view = FaceBattleView(self.cog, interaction.guild_id, e1, e2, timeout_seconds=self.selected_duration)
        await view._prepare_images()

        files = [view.stitched_file] if view.stitched_file else []
        # Screenshot дээрх шиг ping нэмэх
        content = "@Mogbattle Pings" 
        msg = await ch.send(content=content, embed=view.embed(), view=view, files=files)
        
        if msg.attachments:
            view.stitched_url = msg.attachments[0].url
            
        view.message = msg
        self.cog.active_battles[interaction.guild_id] = view
        await interaction.response.send_message(f"✅ Тэмцээн эхэллээ! ({self.selected_duration//60} минут)", ephemeral=True)

    @discord.ui.button(label="⏹️ Дуусгах", style=discord.ButtonStyle.red, row=4)
    async def end_btn(self, interaction, button):
        v = self.cog.active_battles.pop(interaction.guild_id, None)
        if not v: return await interaction.response.send_message("❌ Идэвхтэй тэмцээн байхгүй.", ephemeral=True)
        v.stop()
        await v._finish()
        await interaction.response.send_message("⏹️ Тэмцээн дуусгагдлаа.", ephemeral=True)

# ────────────────── MAIN COG ──────────────────
class FaceTournamentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_battles = {}

    async def cog_load(self):
        async with self.bot.db.acquire() as conn:
            await conn.execute("""CREATE TABLE IF NOT EXISTS face_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT, user_id TEXT, username TEXT,
                image_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            await conn.commit()

    async def _get_entry(self, gid, eid):
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT id, user_id, image_url, username FROM face_entries WHERE guild_id=? AND id=?", (str(gid), eid)) as cur:
                row = await cur.fetchone()
                if row: return {"id":row[0],"user_id":int(row[1]),"image_url":row[2],"username":row[3]}

    async def _get_all_entries(self, gid):
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT id, username, user_id FROM face_entries WHERE guild_id=? ORDER BY id", (str(gid),)) as cur:
                return await cur.fetchall()

    async def _end_battle(self, view):
        gid = view.guild_id; self.active_battles.pop(gid, None)
        w = None
        if view.votes1 > view.votes2: w = view.entry1
        elif view.votes2 > view.votes1: w = view.entry2
        desc = "⚖️ Тэнцлээ!" if not w else f"🏆 {w['username']} яллаа! ({view.votes1} - {view.votes2})"
        emb = discord.Embed(title="🏁 ТЭМЦЭЭН ДҮН", description=desc, color=0xffd700)
        emb.add_field(name=view.entry1["username"], value=str(view.votes1), inline=True)
        emb.add_field(name=view.entry2["username"], value=str(view.votes2), inline=True)
        if view.message: await view.message.reply(embed=emb)

    # ──── Хэрэглэгчийн командууд ────
    @app_commands.command(name="face_add", description="Зураг(ууд) бүртгүүлэх")
    @app_commands.describe(image1="Эхний зураг (заавал)", image2="Хоёр дахь зураг (заавал биш)")
    async def face_add(self, interaction, image1: discord.Attachment, image2: Optional[discord.Attachment] = None):
        if not (image1.content_type and image1.content_type.startswith("image/")):
            return await interaction.response.send_message("❌ Эхний файл зураг биш!", ephemeral=True)
        if image2 and not (image2.content_type and image2.content_type.startswith("image/")):
            return await interaction.response.send_message("❌ Хоёр дахь файл зураг биш!", ephemeral=True)

        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO face_entries (guild_id, user_id, username, image_url) VALUES (?,?,?,?)",
                (str(interaction.guild_id), str(interaction.user.id), interaction.user.display_name, image1.url)
            )
            if image2:
                await conn.execute(
                    "INSERT INTO face_entries (guild_id, user_id, username, image_url) VALUES (?,?,?,?)",
                    (str(interaction.guild_id), str(interaction.user.id), interaction.user.display_name, image2.url)
                )
            await conn.commit()

        msg = "✅ Эхний зураг бүртгэгдлээ!" if not image2 else "✅ Хоёр зураг бүртгэгдлээ!"
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="face_edit", description="Бүртгэлийн зургаа солих")
    @app_commands.describe(entry_id="ID", image="Шинэ зураг")
    async def face_edit(self, interaction, entry_id: int, image: discord.Attachment):
        entry = await self._get_entry(interaction.guild_id, entry_id)
        if not entry or entry["user_id"] != interaction.user.id:
            return await interaction.response.send_message("❌ Өөрийн бүртгэл биш.", ephemeral=True)
        if not (image.content_type and image.content_type.startswith("image/")):
            return await interaction.response.send_message("❌ Зураг биш!", ephemeral=True)
        async with self.bot.db.acquire() as conn:
            await conn.execute("UPDATE face_entries SET image_url=? WHERE id=? AND guild_id=?",
                               (image.url, entry_id, str(interaction.guild_id)))
            await conn.commit()
        await interaction.response.send_message(f"✅ ID {entry_id} шинэчлэгдлээ.", ephemeral=True)

    @app_commands.command(name="face_list", description="Бүртгэлтэй зургууд")
    async def face_list(self, interaction):
        rows = await self._get_all_entries(interaction.guild_id)
        if not rows: return await interaction.response.send_message("📭 Хоосон.", ephemeral=True)
        e = discord.Embed(title="📋 Бүртгэлтэй зургууд", color=0x9b59b6)
        for eid, name, uid in rows[:25]:
            e.add_field(name=f"ID {eid} – {name}", value=f"UserID: {uid}", inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="facepanel", description="Тэмцээн удирдах самбар (админ)")
    @app_commands.default_permissions(administrator=True)
    async def facepanel(self, interaction):
        rows = await self._get_all_entries(interaction.guild_id)
        if not rows: return await interaction.response.send_message("❌ Зураг байхгүй.", ephemeral=True)
        rows = rows[:25]  # Discord-ийн хязгаар
        opts = [discord.SelectOption(label=f"{n} (ID:{eid})", value=str(eid)) for eid, n, _ in rows]
        await interaction.response.send_message("Админ самбар:", view=FaceAdminView(self, opts), ephemeral=True)

async def setup(bot): await bot.add_cog(FaceTournamentCog(bot))
