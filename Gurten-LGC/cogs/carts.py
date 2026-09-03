import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import asyncio
import io
import os
import aiohttp
import time
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------- Фонт ----------
try:
    from cogs.font_utils import load_font as _load_font
except ImportError:
    def _load_font(size=40, bold=True):
        paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ] if bold else [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except:
                    pass
        return ImageFont.load_default(size)

# ---------- Өнгө (минималист палитр) ----------
BG_DARK = (30, 33, 37, 255)           # Арын дэвсгэр (Discord dark)
BG_CARD = (44, 47, 51, 255)           # Картны дэвсгэр
BORDER = (66, 70, 77, 255)            # Хүрээ
ACCENT = (88, 101, 242, 255)          # Discord blurple (цэнхэр)
ACCENT_GREEN = (46, 204, 113, 255)    # Амжилттай үйлдлийн ногоон
TEXT_PRIMARY = (255, 255, 255, 255)   # Үндсэн текст
TEXT_SECONDARY = (160, 163, 168, 255) # Туслах текст
BAR_BG = (50, 53, 59, 255)            # Прогресс барын арын өнгө
BAR_FILL = ACCENT                     # Прогресс барын дүүргэлт


# ---------- ЭМОЖИ ИЛРҮҮЛЭГЧ ----------
def is_emoji(char):
    cp = ord(char)
    return any(start <= cp <= end for start, end in [
        (0x1F600, 0x1F64F), (0x1F300, 0x1F5FF), (0x1F680, 0x1F6FF),
        (0x1F1E0, 0x1F1FF), (0x2600, 0x26FF), (0x2700, 0x27BF),
        (0x1F900, 0x1F9FF), (0x1FA00, 0x1FA6F), (0x1FA70, 0x1FAFF),
        (0x200D, 0x200D), (0xFE0F, 0xFE0F),
    ])


class InventoryView(View):
    def __init__(self, cog, member, all_items, page=0):
        super().__init__(timeout=180)
        self.cog = cog
        self.member = member
        self.all_items = all_items
        self.page = page
        self.per_page = 6
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("❌ Энэ товч зөвхөн инвентарын эзэнд зориулагдсан!", ephemeral=True)
            return False
        return True

    async def update_message(self, interaction: discord.Interaction):
        embed, file = await self.cog.build_inventory_embed(self.member, self.all_items, self.page)
        self.prev_button.disabled = (self.page == 0)
        total_pages = max(1, -(-len(self.all_items) // self.per_page))
        self.next_button.disabled = (self.page >= total_pages - 1)
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="🔍 Хэрэглэх", style=discord.ButtonStyle.green, row=0)
    async def use_button(self, interaction: discord.Interaction, button: Button):
        start = self.page * self.per_page
        end = start + self.per_page
        page_items = self.all_items[start:end]
        if not page_items:
            return await interaction.response.send_message("❌ Энэ хуудсанд зүйл байхгүй!", ephemeral=True)

        options = []
        for idx, item in enumerate(page_items):
            label = f"{item['emoji']} {item['name'][:25]} x{item['quantity']}"
            options.append(discord.SelectOption(label=label, value=str(idx)))

        select = Select(placeholder="Хэрэглэх зүйлээ сонгоно уу...", options=options)

        async def select_callback(select_interaction: discord.Interaction):
            idx = int(select.values[0])
            selected = page_items[idx]
            shop = self.cog.bot.get_cog("ShopCog")
            if not shop:
                return await select_interaction.response.send_message("❌ Shop систем олдсонгүй!", ephemeral=True)
            item_id = selected['id']
            if 6000 <= item_id < 7000:
                cafe = self.cog.bot.get_cog("Cafe")
                if not cafe:
                    return await select_interaction.response.send_message("❌ Кафе систем олдсонгүй!", ephemeral=True)
                food_index = item_id - 6000
                if food_index < 0 or food_index >= len(cafe.menu):
                    return await select_interaction.response.send_message("❌ Буруу хоолны ID!", ephemeral=True)
                inv = await shop.get_user_inventory(self.member.id, interaction.guild.id)
                if inv.get(item_id, 0) == 0:
                    return await select_interaction.response.send_message("❌ Танд энэ хоол байхгүй!", ephemeral=True)
                await shop.remove_item(self.member.id, interaction.guild.id, item_id, 1)
                food = cafe.menu[food_index]
                key = f"{self.member.id}_{interaction.guild.id}"
                end_time = time.time() + food['duration']
                cafe.active_buffs[key] = {
                    "type": food['buff'],
                    "end_time": end_time,
                    "xp_mult": food.get('xp_mult', 1),
                    "money_mult": food.get('money_mult', 1),
                }
                await select_interaction.response.send_message(
                    f"🍽️ **{food['emoji']} {food['name']}** идлээ! {food['buff']} ({food['duration']}с)",
                    ephemeral=True
                )
                await self.update_message(interaction)
                return
            if hasattr(shop, 'use_item'):
                success, msg = await shop.use_item(self.member.id, interaction.guild.id, item_id)
                if success:
                    await select_interaction.response.send_message(f"✅ {msg}", ephemeral=True)
                    await self.update_message(interaction)
                else:
                    await select_interaction.response.send_message(f"❌ {msg}", ephemeral=True)
            else:
                await select_interaction.response.send_message("❌ Хэрэглэх систем олдсонгүй!", ephemeral=True)

        select.callback = select_callback
        view = View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Хэрэглэх зүйлээ сонгоно уу:", view=view, ephemeral=True)

    @discord.ui.button(label="◀ Өмнөх", style=discord.ButtonStyle.gray, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Дараах ▶", style=discord.ButtonStyle.gray, row=1)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        total_pages = max(1, -(-len(self.all_items) // self.per_page))
        if self.page < total_pages - 1:
            self.page += 1
            await self.update_message(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except:
                pass


class Cards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _fetch_emoji_image_sync(self, emoji_char, size=28):
        code_points = '-'.join(f'{ord(c):x}' for c in emoji_char)
        url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{code_points}.png"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img = img.resize((size, size), Image.LANCZOS)
            return img
        except:
            return None

    def _draw_text_with_emoji_sync(self, canvas, draw, x, y, text, font, fill_color, emoji_size=28):
        tokens = []
        i = 0
        while i < len(text):
            ch = text[i]
            if is_emoji(ch):
                j = i + 1
                while j < len(text) and (
                    text[j] in ('\u200d', '\ufe0f', '\u20e3') or
                    ('\U0001f3fb' <= text[j] <= '\U0001f3ff')
                ):
                    j += 1
                emoji_seq = text[i:j]
                tokens.append(('emoji', emoji_seq))
                i = j
            else:
                tokens.append(('text', ch))
                i += 1
        cur_x = x
        for typ, val in tokens:
            if typ == 'text':
                draw.text((cur_x, y), val, font=font, fill=fill_color)
                bbox = draw.textbbox((cur_x, y), val, font=font)
                cur_x += bbox[2] - bbox[0]
            else:
                emoji_img = self._fetch_emoji_image_sync(val, size=emoji_size)
                if emoji_img:
                    canvas.paste(emoji_img, (cur_x, y - 4), emoji_img)
                    cur_x += emoji_size + 2
                else:
                    draw.text((cur_x, y), val, font=font, fill=fill_color)
                    bbox = draw.textbbox((cur_x, y), val, font=font)
                    cur_x += bbox[2] - bbox[0]
        return cur_x

    async def _download_avatar(self, sess, url, size):
        try:
            async with sess.get(url) as resp:
                data = await resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
        except:
            img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img

    async def _download_avatar_small(self, sess, url, size=60):
        return await self._download_avatar(sess, url, size)

    async def _gather_user_data(self, member, guild):
        eco = self.bot.get_cog("Economy")
        lvl = self.bot.get_cog("Leveling")
        if not eco or not lvl:
            return None
        guild_id = guild.id
        cash = await eco.get_balance(member.id, guild_id)
        bank = await eco.get_bank(member.id, guild_id)
        total = cash + bank
        hunger, mood = await eco.get_hunger_mood(member.id, guild_id)
        disc_level = await eco.get_discord_level(member.id, guild_id)

        # SQLite-д тохирсон fetchone ашиглах
        row = await self.bot.db.fetchone(
            "SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?",
            str(member.id), str(guild_id)
        )
        if row:
            xp, level = row[0], row[1]
        else:
            xp, level = 0, 1

        next_xp = 100 * level
        if hasattr(lvl, 'xp_for_level'):
            cfg = await lvl.get_config(guild_id)
            next_xp = lvl.xp_for_level(level, cfg)
        title, badge = lvl.get_rank_info(level) if hasattr(lvl, 'get_rank_info') else ("Энгийн", "⭐")

        # Rank тодорхойлох
        rows = await self.bot.db.fetch(
            "SELECT user_id FROM levels WHERE guild_id = ? ORDER BY level DESC, xp DESC",
            str(guild_id)
        )
        rank = next((i for i, (uid,) in enumerate(rows, 1) if str(uid) == str(member.id)), len(rows)+1)

        _, job = eco.get_job_for_level(disc_level)
        job_emoji = job['emoji']
        job_name = job['name']

        # Согтолт
        drunk_row = await self.bot.db.fetchone(
            "SELECT level FROM user_drunk WHERE user_id = ? AND guild_id = ?",
            str(member.id), str(guild_id)
        )
        drunk_level = min(100, drunk_row[0]) if drunk_row else 0

        async with aiohttp.ClientSession() as sess:
            url = member.display_avatar.replace(size=256, format="png").url
            ava = await self._download_avatar(sess, url, 150)
        return {
            "xp": xp, "level": level, "next_xp": next_xp, "rank": rank,
            "title": title, "badge": badge, "cash": cash, "bank": bank,
            "total": total, "job_emoji": job_emoji, "job_name": job_name,
            "hunger": hunger, "mood": mood, "drunk": drunk_level,
            "disc_level": disc_level, "ava": ava
        }

    # ==================== ПРОФАЙЛ КАРТ (МИНИМАЛИСТ) ====================
    def _render_profile_card(self, member, level, xp, next_xp, rank, title, badge,
                             cash, bank, total, job_emoji, job_name,
                             hunger, mood, drunk, avatar_img, disc_level):
        W, H = 900, 320
        RADIUS = 20
        PAD = 30
        AVA = 140

        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Үндсэн карт
        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG_CARD)
        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, outline=BORDER, width=2)

        # Аватар (дугуй хүрээ)
        ava_x, ava_y = PAD, (H - AVA) // 2
        ring_size = AVA + 8
        ring = Image.new("RGBA", (ring_size, ring_size), (0,0,0,0))
        ImageDraw.Draw(ring).ellipse((0,0,ring_size-1,ring_size-1), outline=ACCENT, width=3)
        img.paste(ring, (ava_x-4, ava_y-4), ring)
        img.paste(avatar_img, (ava_x, ava_y), avatar_img)

        # Фонтууд
        font_name = _load_font(40, True)
        font_sub = _load_font(26, False)
        font_small = _load_font(20, False)
        font_title = _load_font(24, True)

        tx = ava_x + AVA + 30
        ty = 25

        # Хэрэглэгчийн нэр
        draw.text((tx, ty), member.display_name[:20], font=font_name, fill=TEXT_PRIMARY)
        draw.text((tx, ty + 45), f"@{member.name}", font=font_small, fill=TEXT_SECONDARY)

        # Зэрэг, медаль
        self._draw_text_with_emoji_sync(img, draw, tx, ty + 75, f"{badge} {title}", font_sub, ACCENT)
        draw.text((tx, ty + 110), f"Lv. {level}  •  #{rank}", font=font_small, fill=TEXT_PRIMARY)

        # XP бар
        bar_x = tx
        bar_y = ty + 145
        bar_w = 260
        bar_h = 18
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_BG)
        progress = xp / next_xp if next_xp else 0
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_FILL)
        draw.text((bar_x + 10, bar_y - 25), f"{xp:,} / {next_xp:,} XP", font=font_small, fill=TEXT_SECONDARY)
        pct = f"{int(progress * 100)}%"
        pct_w = draw.textbbox((0, 0), pct, font=font_small)[2]
        draw.text((bar_x + bar_w - pct_w - 10, bar_y - 25), pct, font=font_small, fill=ACCENT_GREEN)

        # Эдийн засаг (баруун талд)
        eco_x = W - 340
        eco_y = 30
        self._draw_text_with_emoji_sync(img, draw, eco_x, eco_y, "💰 Эдийн засаг", font_title, ACCENT)
        self._draw_text_with_emoji_sync(img, draw, eco_x, eco_y + 40, f"💵 Бэлэн: {cash:,} ₮", font_small, TEXT_PRIMARY)
        self._draw_text_with_emoji_sync(img, draw, eco_x, eco_y + 65, f"🏦 Банк: {bank:,} ₮", font_small, TEXT_PRIMARY)
        self._draw_text_with_emoji_sync(img, draw, eco_x, eco_y + 90, f"💎 Нийт: {total:,} ₮", font_small, ACCENT_GREEN)

        # Статус
        stat_x = eco_x
        stat_y = eco_y + 130
        self._draw_text_with_emoji_sync(img, draw, stat_x, stat_y, "📊 Статус", font_title, ACCENT)
        self._draw_text_with_emoji_sync(img, draw, stat_x, stat_y + 40, f"🍖 Өлсгөлөн: {hunger}%", font_small, TEXT_PRIMARY)
        self._draw_text_with_emoji_sync(img, draw, stat_x, stat_y + 65, f"😡 Уур: {mood}%", font_small, TEXT_PRIMARY)
        self._draw_text_with_emoji_sync(img, draw, stat_x, stat_y + 90, f"🍺 Согтолт: {drunk}%", font_small, TEXT_PRIMARY)
        self._draw_text_with_emoji_sync(img, draw, stat_x, stat_y + 115, f"💼 {job_emoji} {job_name[:20]}", font_small, TEXT_SECONDARY)

        # Доод хэсэг
        self._draw_text_with_emoji_sync(img, draw, PAD, H - 35, f"⭐ Discord Lv. {disc_level}", font_small, TEXT_SECONDARY)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf

    # ==================== ИНВЕНТАР КАРТ (МИНИМАЛИСТ) ====================
    def _render_inventory_card_page(self, member, avatar_img, page_items, used_slots, total_slots, buffs, page=0, total_pages=1):
        W, H = 820, 400
        RADIUS = 20
        PAD = 25
        AVA = 60

        img = Image.new("RGBA", (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)

        # Арын дэвсгэр
        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG_CARD)
        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, outline=BORDER, width=2)

        font_title = _load_font(34, True)
        font_sub = _load_font(22, False)
        font_small = _load_font(18, False)

        ava_x, ava_y = PAD, 20
        img.paste(avatar_img, (ava_x, ava_y), avatar_img)

        name = member.display_name[:20]
        draw.text((ava_x + AVA + 15, ava_y + 5), f"{name}'s Inventory", font=font_title, fill=ACCENT)
        draw.text((ava_x + AVA + 15, ava_y + 45), f"Багтаамж: {used_slots} / {total_slots}", font=font_sub, fill=TEXT_SECONDARY)

        # Багтаамжийн бар
        bar_x = ava_x + AVA + 15
        bar_y = ava_y + 80
        bar_w = 350
        bar_h = 12
        progress = used_slots / total_slots if total_slots else 0
        fill_w = int(bar_w * progress)
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_BG)
        if fill_w > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_FILL)

        # Зураас
        line_y = bar_y + bar_h + 20
        draw.line([(PAD, line_y), (W - PAD, line_y)], fill=BORDER, width=1)

        y = line_y + 20
        for item in page_items:
            rarity = item.get("rarity", "common")
            if rarity in ("legendary", "mythic"):
                name_color = ACCENT_GREEN
            elif rarity in ("epic", "rare"):
                name_color = ACCENT
            else:
                name_color = TEXT_PRIMARY
            emoji_str = item.get("emoji", "📦")
            name = item["name"][:30]
            qty = item["quantity"]
            self._draw_text_with_emoji_sync(img, draw, PAD + 10, y, f"{emoji_str} {name}  x{qty}", font_small, name_color)
            y += 30

        if not page_items:
            draw.text((PAD, y), "Инвентарь хоосон байна.", font=font_small, fill=TEXT_SECONDARY)

        buff_y = H - 60
        draw.line([(PAD, buff_y - 10), (W - PAD, buff_y - 10)], fill=BORDER, width=1)
        draw.text((PAD, buff_y), "✨ Идэвхтэй баффууд", font=font_sub, fill=ACCENT_GREEN)
        if buffs:
            buff_text = "  |  ".join(b['name'] for b in buffs[:3])
            draw.text((PAD, buff_y + 25), buff_text[:80], font=font_small, fill=TEXT_PRIMARY)
        else:
            draw.text((PAD, buff_y + 25), "Одоогоор баффгүй", font=font_small, fill=TEXT_SECONDARY)

        draw.text((W - PAD - 80, H - 25), f"{page + 1}/{total_pages}", font=font_small, fill=TEXT_SECONDARY)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf

    async def build_inventory_embed(self, member, all_items, page=0):
        shop = self.bot.get_cog("ShopCog")
        max_slots = getattr(shop, "max_inventory_slots", 50) if shop else 50
        used_slots = len(all_items)
        buffs = []
        cafe_cog = self.bot.get_cog("Cafe")
        if cafe_cog:
            user_buff = cafe_cog.get_buff(member.id, member.guild.id)
            if user_buff:
                btype = user_buff.get("type", "???")
                remaining = user_buff.get("remaining", 0)
                if remaining:
                    mins, secs = divmod(remaining, 60)
                    btype = f"{btype} ({mins}м {secs}с)"
                buffs.append({"name": btype})
        per_page = 6
        total_pages = max(1, -(-len(all_items) // per_page))
        start = page * per_page
        end = start + per_page
        page_items = all_items[start:end]
        async with aiohttp.ClientSession() as sess:
            url = member.display_avatar.replace(size=128, format="png").url
            avatar_img = await self._download_avatar_small(sess, url, 60)
        buf = await asyncio.to_thread(
            self._render_inventory_card_page,
            member, avatar_img, page_items, used_slots, max_slots, buffs, page, total_pages
        )
        embed = discord.Embed(color=0x5865F2)  # Discord blurple
        embed.set_image(url="attachment://inventory.png")
        embed.set_footer(text=f"{member.guild.name} • {member.display_name}")
        return embed, discord.File(buf, filename="inventory.png")

    @commands.command(name="profile", aliases=["pcard"])
    @app_commands.describe(member="Хэрэглэгч (хоосон бол өөрийнх)")
    async def profilecard(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        await ctx.defer()
        data = await self._gather_user_data(target, ctx.guild)
        if not data:
            return await ctx.send("❌ Шаардлагатай когууд ачаалагдаагүй байна.")
        buf = await asyncio.to_thread(
            self._render_profile_card,
            target, data["level"], data["xp"], data["next_xp"], data["rank"],
            data["title"], data["badge"], data["cash"], data["bank"], data["total"],
            data["job_emoji"], data["job_name"], data["hunger"], data["mood"],
            data["drunk"], data["ava"], data["disc_level"]
        )
        embed = discord.Embed(color=0x5865F2)
        embed.set_image(url="attachment://profilecard.png")
        embed.set_footer(text=f"{ctx.guild.name} • {target.display_name}")
        await ctx.send(embed=embed, file=discord.File(buf, filename="profilecard.png"))

    @commands.command(name="inventory", aliases=["inv", "icard"])
    @app_commands.describe(member="Хэрэглэгч (хоосон бол өөрийнх)")
    async def inventory_card(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        await ctx.defer()
        shop = self.bot.get_cog("ShopCog")
        if not shop:
            return await ctx.send("❌ Shop систем ачаалагдаагүй байна.")
        inv = await shop.get_user_inventory(target.id, ctx.guild.id)
        all_items = []
        for item_id, qty in inv.items():
            item_data = await shop.get_item(item_id)
            if item_data:
                all_items.append({
                    "id": item_id,
                    "name": item_data.get("name", f"Item {item_id}"),
                    "emoji": item_data.get("emoji", "📦"),
                    "quantity": qty,
                    "rarity": item_data.get("rarity", "common"),
                    "category": item_data.get("category", "other"),
                })
        embed, file = await self.build_inventory_embed(target, all_items, 0)
        view = InventoryView(self, target, all_items, 0)
        msg = await ctx.send(embed=embed, file=file, view=view)
        view.message = msg

async def setup(bot):
    await bot.add_cog(Cards(bot))