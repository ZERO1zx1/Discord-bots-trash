import discord
from discord.ext import commands
from discord.ui import Select, View, Button
import random
import time

EMBED_COLOR = 0x2b2d31
SUCCESS_COLOR = 0x57f287
ERROR_COLOR = 0xed4245
WARNING_COLOR = 0xfee75c
GOLD_COLOR = 0xffd700
PURPLE_COLOR = 0x9b59b6
INFO_COLOR = 0x3498db

SHOP_ITEMS = [
    {"id":1,"name":"Beer","price":30000,"emoji":"🍺","desc":"Cool and foamy beer.","strength":1,"category":"drink"},
    {"id":2,"name":"Wine","price":30000,"emoji":"🍷","desc":"Red wine.","strength":2,"category":"drink"},
    {"id":3,"name":"Vodka","price":25000,"emoji":"🥃","desc":"Clear and strong vodka.","strength":3,"category":"drink"},
    {"id":4,"name":"Whiskey","price":40000,"emoji":"🥃","desc":"Aged in wooden barrels.","strength":3,"category":"drink"},
    {"id":5,"name":"Rum","price":35000,"emoji":"🍹","desc":"Sugarcane rum.","strength":2,"category":"drink"},
    {"id":6,"name":"Tequila","price":38000,"emoji":"🍸","desc":"Made from agave.","strength":3,"category":"drink"},
    {"id":7,"name":"Gin","price":32000,"emoji":"🍸","desc":"Flavored with juniper berries.","strength":2,"category":"drink"},
    {"id":8,"name":"Brandy","price":42000,"emoji":"🥃","desc":"Distilled from wine.","strength":3,"category":"drink"},
    {"id":9,"name":"Sake","price":28000,"emoji":"🍶","desc":"Japanese rice sake.","strength":2,"category":"drink"},
    {"id":10,"name":"Liqueur","price":32000,"emoji":"🍹","desc":"Sweet and fruity liqueur.","strength":1,"category":"drink"},
    {"id":11,"name":"Silver Ring","price":50000,"emoji":"💍","desc":"Shining silver ring.","strength":0,"category":"ring","subcat":"old"},
    {"id":12,"name":"Gold Ring","price":70000,"emoji":"💍","desc":"Elegant gold ring.","strength":0,"category":"ring","subcat":"old"},
    {"id":13,"name":"Pearl Ring","price":100000,"emoji":"💍","desc":"Expensive pearl ring.","strength":0,"category":"ring","subcat":"old"},
    {"id":14,"name":"Gemstone Ring","price":80000,"emoji":"💍","desc":"Ring with onyx stone.","strength":0,"category":"ring","subcat":"old"},
    {"id":15,"name":"Royal Ring","price":60000,"emoji":"👑","desc":"Inherited from royalty.","strength":0,"category":"ring","subcat":"old"},
    {"id":36,"name":"Diamond","price":500000,"emoji":"💎","desc":"Hardest and clearest.","strength":0,"category":"ring","subcat":"gem"},
    {"id":37,"name":"Ruby","price":400000,"emoji":"🔴","desc":"Red colored gemstone.","strength":0,"category":"ring","subcat":"gem"},
    {"id":38,"name":"Sapphire","price":450000,"emoji":"🔵","desc":"Deep blue gemstone.","strength":0,"category":"ring","subcat":"gem"},
    {"id":39,"name":"Emerald","price":420000,"emoji":"🟢","desc":"Green colored gemstone.","strength":0,"category":"ring","subcat":"gem"},
    {"id":40,"name":"Pearl","price":350000,"emoji":"⚪","desc":"Treasure of the sea.","strength":0,"category":"ring","subcat":"gem"},
    {"id":41,"name":"Topaz","price":250000,"emoji":"🟡","desc":"Blue and yellowish colors.","strength":0,"category":"ring","subcat":"gem"},
    {"id":42,"name":"Jade","price":380000,"emoji":"🟢","desc":"Symbol of peace and longevity.","strength":0,"category":"ring","subcat":"gem"},
    {"id":43,"name":"Gold","price":300000,"emoji":"🟡","desc":"Valuable and stainless.","strength":0,"category":"ring","subcat":"metal"},
    {"id":44,"name":"Silver","price":150000,"emoji":"⚪","desc":"Suitable for everyday wear.","strength":0,"category":"ring","subcat":"metal"},
    {"id":45,"name":"Copper","price":80000,"emoji":"🟠","desc":"Good for health.","strength":0,"category":"ring","subcat":"metal"},
    {"id":46,"name":"Platinum","price":550000,"emoji":"⚪","desc":"Very durable and hypoallergenic.","strength":0,"category":"ring","subcat":"metal"},
    {"id":47,"name":"Steel","price":60000,"emoji":"⚪","desc":"Scratch-resistant and doesn't tarnish.","strength":0,"category":"ring","subcat":"metal"},
    {"id":48,"name":"Titanium","price":120000,"emoji":"⚪","desc":"Lightweight and strong.","strength":0,"category":"ring","subcat":"metal"}
]

INTOXICATION_LEVELS = [
    (0, "🧊 Сэргэг", 0x00ffff),
    (1, "😊 Хөнгөн сэргэлт", 0x2ecc71),
    (3, "😌 Дунд зэрэг", 0xf1c40f),
    (6, "🤪 Харуун согтол", 0xe67e22),
    (10, "🥴 Хүчтэй согтол", 0xe74c3c),
    (15, "😵 Барж байхаа мэдэхгүй", 0x8e44ad)
]

class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_inventory (
                user_id TEXT,
                guild_id TEXT,
                item_id INTEGER,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id, item_id)
            )''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_drunk (
                user_id TEXT,
                guild_id TEXT,
                level INTEGER DEFAULT 0,
                last_update INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS shop_custom_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                name TEXT,
                price INTEGER,
                emoji TEXT,
                desc TEXT,
                strength INTEGER DEFAULT 0,
                category TEXT DEFAULT "item",
                subcat TEXT,
                added_by TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            await conn.commit()

        async with self.bot.db.acquire() as conn:
            async with conn.execute("PRAGMA table_info(user_inventory)") as cur:
                cols = [row[1] for row in await cur.fetchall()]
            if "guild_id" not in cols:
                await conn.execute("ALTER TABLE user_inventory ADD COLUMN guild_id TEXT")
                await conn.commit()
            async with conn.execute("PRAGMA table_info(user_drunk)") as cur:
                cols = [row[1] for row in await cur.fetchall()]
            if "guild_id" not in cols:
                await conn.execute("ALTER TABLE user_drunk ADD COLUMN guild_id TEXT")
                await conn.commit()

    async def cog_load(self):
        await self.init_db()

    async def get_shop_items(self, guild_id=None):
        """Бүх барааг авах (default + custom)"""
        items = list(SHOP_ITEMS)
        if guild_id:
            async with self.bot.db.acquire() as conn:
                async with conn.execute(
                    "SELECT id, name, price, emoji, desc, strength, category, subcat FROM shop_custom_items WHERE guild_id=?",
                    (str(guild_id),)
                ) as cur:
                    rows = await cur.fetchall()
            for row in rows:
                items.append({
                    "id": row[0] + 1000,  # Custom items start at 1000
                    "name": row[1],
                    "price": row[2],
                    "emoji": row[3],
                    "desc": row[4],
                    "strength": row[5],
                    "category": row[6],
                    "subcat": row[7],
                    "custom": True
                })
        return items

    async def get_user_inventory(self, uid, guild_id):
        inv = {}
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT item_id, quantity FROM user_inventory WHERE user_id=? AND guild_id=?",
                (str(uid), str(guild_id))
            ) as cur:
                rows = await cur.fetchall()
        for row in rows:
            inv[row[0]] = row[1]
        return inv

    async def add_item(self, uid, guild_id, iid, qty=1):
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO user_inventory (user_id, guild_id, item_id, quantity) VALUES (?,?,?,?) ON CONFLICT(user_id,guild_id,item_id) DO UPDATE SET quantity=quantity+?",
                (str(uid), str(guild_id), iid, qty, qty)
            )
            await conn.commit()

    async def remove_item(self, uid, guild_id, iid, qty=1):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT quantity FROM user_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
                (str(uid), str(guild_id), iid)
            ) as cur:
                row = await cur.fetchone()
            if not row or row[0] < qty:
                return False
            new_qty = row[0] - qty
            if new_qty == 0:
                await conn.execute("DELETE FROM user_inventory WHERE user_id=? AND guild_id=? AND item_id=?", (str(uid), str(guild_id), iid))
            else:
                await conn.execute("UPDATE user_inventory SET quantity=? WHERE user_id=? AND guild_id=? AND item_id=?", (new_qty, str(uid), str(guild_id), iid))
            await conn.commit()
        return True

    async def get_drunk_level(self, uid, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT level, last_update FROM user_drunk WHERE user_id=? AND guild_id=?",
                (str(uid), str(guild_id))
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return 0
        level, last = row
        if last is None:
            return level
        now = int(time.time())
        hours = (now - last) // 3600
        if hours > 0:
            new_level = max(0, level - hours)
            if new_level != level:
                async with self.bot.db.acquire() as conn:
                    await conn.execute(
                        "UPDATE user_drunk SET level=?, last_update=? WHERE user_id=? AND guild_id=?",
                        (new_level, now, str(uid), str(guild_id))
                    )
                    await conn.commit()
                return new_level
        return level

    async def add_drunk(self, uid, guild_id, strength):
        current = await self.get_drunk_level(uid, guild_id)
        new_level = current + strength
        now = int(time.time())
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO user_drunk (user_id, guild_id, level, last_update) VALUES (?,?,?,?) ON CONFLICT(user_id,guild_id) DO UPDATE SET level=?, last_update=?",
                (str(uid), str(guild_id), new_level, now, new_level, now)
            )
            await conn.commit()
        return new_level

    def get_drunk_status(self, level):
        for threshold, name, color in INTOXICATION_LEVELS:
            if level <= threshold:
                return name, color
        return "😵 Хэт хүнд", ERROR_COLOR

    def get_intoxication_bar(self, level):
        max_level = 20
        filled = min(level, max_level)
        empty = max_level - filled
        bar = "█" * filled + "░" * empty
        return f"`{bar}` `{level}/{max_level}`"

    # ----------------------- DROPDOWN SHOP -----------------------
    @commands.command(name='shop', aliases=['store', 'дэлгүүр'])
    async def shop(self, ctx):
        items = await self.get_shop_items(ctx.guild.id)
        options = []
        for item in items:
            label = f"{item['emoji']} {item['name']} - {item['price']:,} мөнгө"
            description = item['desc'][:50]
            if len(label) > 100:
                label = label[:97] + "..."
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(item['id']),
                    description=description[:100],
                    emoji=item['emoji']
                )
            )
        if len(options) > 25:
            options = options[:25]

        select = Select(placeholder="🛒 Бараа сонгох (1 ширхэг автоматаар худалдана)", options=options)

        async def select_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("❌ Энэ цэс танд зориулагдаагүй!", ephemeral=True)
            item_id = int(select.values[0])
            item = next((i for i in items if i["id"] == item_id), None)
            if not item:
                return await interaction.response.send_message("❌ Бараа олдсонгүй.", ephemeral=True)

            economy = self.bot.get_cog("Economy")
            if not economy:
                return await interaction.response.send_message("❌ Системийн алдаа.", ephemeral=True)

            guild_id = ctx.guild.id
            balance = await economy.get_balance(ctx.author.id, guild_id)
            price = item["price"]
            if balance < price:
                embed = discord.Embed(
                    title="❌ Хангалтгүй мөнгө",
                    description=f"**{item['emoji']} {item['name']}** худалдаж авахад **{price:,}** мөнгө шаардлагатай.\nТаны үлдэгдэл: `{balance:,}` мөнгө",
                    color=ERROR_COLOR
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            await economy.update_balance(ctx.author.id, guild_id, -price)
            await self.add_item(ctx.author.id, guild_id, item["id"], 1)

            embed = discord.Embed(
                title="✅ Худалдан авалт амжилттай",
                description=f"{ctx.author.mention} **{item['emoji']} {item['name']}** -г `{price:,}` мөнгөөр худалдаж авлаа!",
                color=SUCCESS_COLOR
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=False)

        select.callback = select_callback
        view = View()
        view.add_item(select)

        embed = discord.Embed(
            title="🏪 Дэлгүүр",
            description=f"Доорх цэснээс бараагаа сонгоход **1 ширхэг** шууд худалдаж авна.\n\n🛍️ Нийт бараа: **{len(items)}**",
            color=GOLD_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="!buy <ID> <тоо> - олон ширхэг авах | !additem - шинэ бараа нэмэх")
        await ctx.send(embed=embed, view=view)

    # ----------------------- BUY COMMAND -----------------------
    @commands.command(name='buy')
    async def buy(self, ctx, item_input: str, quantity: int = 1):
        if quantity <= 0 or quantity > 64:
            embed = discord.Embed(title="❌ Алдаа", description="Тоо хэмжээ 1-64 хооронд байх ёстой!", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        try:
            item_id = int(item_input)
        except ValueError:
            embed = discord.Embed(
                title="❌ Буруу ID",
                description=f"`{item_input}` нь тоо биш байна. Зөв хэлбэр: `buy <ID> <тоо>`",
                color=ERROR_COLOR
            )
            return await ctx.send(embed=embed)

        items = await self.get_shop_items(ctx.guild.id)
        item = next((i for i in items if i["id"] == item_id), None)
        if not item:
            embed = discord.Embed(title="❌ Бараа олдсонгүй", description=f"`{item_id}` ID-тай бараа байхгүй.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ Системийн алдаа", description="Эдийн засгийн систем ажиллахгүй байна!", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        guild_id = ctx.guild.id
        balance = await economy.get_balance(ctx.author.id, guild_id)
        total_price = item["price"] * quantity
        if balance < total_price:
            embed = discord.Embed(
                title="❌ Мөнгө хүрэлцэхгүй",
                description=f"**{item['emoji']} {item['name']}** x{quantity} худалдаж авахад **{total_price:,}** мөнгө шаардлагатай.\nТаны үлдэгдэл: `{balance:,}` мөнгө",
                color=ERROR_COLOR
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)

        await economy.update_balance(ctx.author.id, guild_id, -total_price)
        await self.add_item(ctx.author.id, guild_id, item["id"], quantity)

        embed = discord.Embed(
            title="✅ Худалдан авалт амжилттай",
            description=f"{ctx.author.mention} **{item['emoji']} {item['name']}** x{quantity} -г `{total_price:,}` мөнгөөр худалдаж авлаа!",
            color=SUCCESS_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ----------------------- ADD ITEM (ADMIN) -----------------------
    @commands.command(name='additem')
    @commands.has_permissions(administrator=True)
    async def add_item_cmd(self, ctx, name: str, price: int, emoji: str, strength: int = 0, *, description: str = "Шинэ бараа"):
        """Шинэ бараа нэмэх (Admin only)
        Хэрэглээ: !additem "Item Name" 50000 🎁 0 "Item description"
        """
        if price <= 0:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Үнэ 0-ээс их байх ёстой!", color=ERROR_COLOR))
        if len(name) > 50:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Нэр 50 тэмдэгтээс урт байж болохгүй!", color=ERROR_COLOR))
        if len(description) > 200:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Тайлбар 200 тэмдэгтээс урт байж болохгүй!", color=ERROR_COLOR))

        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO shop_custom_items (guild_id, name, price, emoji, desc, strength, added_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(ctx.guild.id), name, price, emoji, description, strength, str(ctx.author.id))
            )
            await conn.commit()
            async with conn.execute("SELECT last_insert_rowid()") as cur:
                new_id = (await cur.fetchone())[0]

        embed = discord.Embed(
            title="✅ Шинэ бараа нэмэгдлээ",
            description=f"**{emoji} {name}** дэлгүүрт нэмэгдлээ!",
            color=SUCCESS_COLOR
        )
        embed.add_field(name="🆔 ID", value=f"{new_id + 1000}", inline=True)
        embed.add_field(name="💰 Үнэ", value=f"{price:,} мөнгө", inline=True)
        embed.add_field(name="🍺 Хүч", value=str(strength), inline=True)
        embed.add_field(name="📝 Тайлбар", value=description, inline=False)
        embed.set_footer(text=f"Нэмсэн: {ctx.author.name}")
        await ctx.send(embed=embed)

    @commands.command(name='removeitem')
    @commands.has_permissions(administrator=True)
    async def remove_item_cmd(self, ctx, item_id: int):
        """Дэлгүүрээс бараа устгах (Admin only)"""
        real_id = item_id - 1000
        if real_id < 0:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Default барааг устгах боломжгүй!", color=ERROR_COLOR))

        async with self.bot.db.acquire() as conn:
            async with conn.execute(
                "SELECT name, emoji FROM shop_custom_items WHERE id=? AND guild_id=?",
                (real_id, str(ctx.guild.id))
            ) as cur:
                row = await cur.fetchone()
            if not row:
                return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Ийм ID-тай бараа олдсонгүй!", color=ERROR_COLOR))

            await conn.execute("DELETE FROM shop_custom_items WHERE id=? AND guild_id=?", (real_id, str(ctx.guild.id)))
            await conn.commit()

        embed = discord.Embed(
            title="🗑️ Бараа устгагдлаа",
            description=f"**{row[1]} {row[0]}** дэлгүүрээс устгагдлаа.",
            color=WARNING_COLOR
        )
        await ctx.send(embed=embed)

    @commands.command(name='shopitems')
    async def shop_items_list(self, ctx):
        """Дэлгүүрт байгаа бүх барааг харах"""
        items = await self.get_shop_items(ctx.guild.id)

        default_items = [i for i in items if not i.get("custom")]
        custom_items = [i for i in items if i.get("custom")]

        embed = discord.Embed(title="🏪 ДЭЛГҮҮРИЙН БАРААНУУД", color=GOLD_COLOR)

        # Default items
        default_text = ""
        for item in default_items:
            default_text += f"`{item['id']:>3}` {item['emoji']} **{item['name']}** — {item['price']:,}₮\n"
        embed.add_field(name=f"📦 Стандарт бараа ({len(default_items)})", value=default_text[:1024] or "—", inline=False)

        # Custom items
        if custom_items:
            custom_text = ""
            for item in custom_items:
                custom_text += f"`{item['id']:>3}` {item['emoji']} **{item['name']}** — {item['price']:,}₮\n"
            embed.add_field(name=f"✨ Нэмэлт бараа ({len(custom_items)})", value=custom_text[:1024], inline=False)

        embed.set_footer(text="!buy <ID> <тоо> - худалдаж авах | !additem - шинэ бараа нэмэх")
        await ctx.send(embed=embed)

    # ----------------------- INVENTORY -----------------------
    @commands.command(name='inv', aliases=['inventory', 'инвентарь'])
    async def inventory(self, ctx):
        guild_id = ctx.guild.id
        inv = await self.get_user_inventory(ctx.author.id, guild_id)
        if not inv:
            embed = discord.Embed(
                title="🎒 Хоосон инвентарь",
                description="`!shop` командаар бараа худалдаж авна уу.",
                color=WARNING_COLOR
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)

        items = await self.get_shop_items(guild_id)
        items_list = []
        total_value = 0
        for iid, qty in inv.items():
            item = next((i for i in items if i["id"] == iid), None)
            if item:
                items_list.append((item, qty))
                total_value += item["price"] * qty

        per_page = 6
        total_pages = (len(items_list) + per_page - 1) // per_page

        def get_inv_embed(page):
            start = page * per_page
            end = start + per_page
            embed = discord.Embed(
                title=f"🎒 {ctx.author.display_name}-ын инвентарь",
                color=PURPLE_COLOR
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            for item, qty in items_list[start:end]:
                if item['category'] == "drink":
                    embed.add_field(
                        name=f"{item['emoji']} **{item['name']}** (ID: {item['id']}) x{qty}",
                        value=f"💰 Үнэ: {item['price']:,} мөнгө\n🍺 Хүч: {item['strength']}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name=f"{item['emoji']} **{item['name']}** (ID: {item['id']}) x{qty}",
                        value=f"💰 Үнэ: {item['price']:,} мөнгө",
                        inline=False
                    )
            embed.add_field(name="📊 Нийт үнэ", value=f"```yaml\n{total_value:,} мөнгө```", inline=False)
            embed.set_footer(text=f"{page+1}/{total_pages} | !drink <ID> - уух | !sogtol - согтолтын түвшин")
            return embed

        class InvPagination(View):
            def __init__(self, cog, original_ctx, total_pages):
                super().__init__(timeout=60)
                self.cog = cog
                self.ctx = original_ctx
                self.page = 0
                self.total = total_pages
                self.message = None

            async def update(self):
                embed = get_inv_embed(self.page)
                await self.message.edit(embed=embed, view=self)

            @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
            async def prev(self, interaction: discord.Interaction, button: Button):
                if interaction.user != self.ctx.author:
                    return await interaction.response.send_message("Энэ товчлуур танд зориулагдаагүй!", ephemeral=True)
                if self.page > 0:
                    self.page -= 1
                    await self.update()
                await interaction.response.defer()

            @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
            async def nxt(self, interaction: discord.Interaction, button: Button):
                if interaction.user != self.ctx.author:
                    return await interaction.response.send_message("Энэ товчлуур танд зориулагдаагүй!", ephemeral=True)
                if self.page < self.total - 1:
                    self.page += 1
                    await self.update()
                await interaction.response.defer()

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                try:
                    await self.message.edit(view=self)
                except Exception:
                    pass

        if total_pages <= 1:
            embed = get_inv_embed(0)
            await ctx.send(embed=embed)
        else:
            view = InvPagination(self, ctx, total_pages)
            view.message = await ctx.send(embed=get_inv_embed(0), view=view)

    # ----------------------- DRINK -----------------------
    @commands.command(name='drink', aliases=['уух'])
    async def drink(self, ctx, item_id: int):
        items = await self.get_shop_items(ctx.guild.id)
        item = next((i for i in items if i["id"] == item_id), None)
        if not item or item["strength"] == 0:
            embed = discord.Embed(title="❌ Алдаа", description="Энэ бараа уух боломжгүй.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        guild_id = ctx.guild.id
        inv = await self.get_user_inventory(ctx.author.id, guild_id)
        if inv.get(item_id, 0) == 0:
            embed = discord.Embed(
                title="❌ Танд энэ бараа байхгүй",
                description=f"`!buy {item_id}` командаар эхлээд худалдаж авна уу.",
                color=ERROR_COLOR
            )
            return await ctx.send(embed=embed)

        await self.remove_item(ctx.author.id, guild_id, item_id, 1)
        new_level = await self.add_drunk(ctx.author.id, guild_id, item["strength"])
        status_name, status_color = self.get_drunk_status(new_level)
        bar = self.get_intoxication_bar(new_level)

        quotes = [
            f"🍻 {ctx.author.mention} **{item['name']}** -г нэг амттай балгалаа!",
            f"🥂 {ctx.author.mention} аягаа өргөлөө. Сайхан амраарай!",
            f"🍺 {ctx.author.mention} сүүлийн дусал дуслыг уув.",
            f"🎉 {ctx.author.mention} баяр хөөрөөр дүүрэн байна!"
        ]
        embed = discord.Embed(
            title="🍻 Шингэн алт!",
            description=random.choice(quotes),
            color=SUCCESS_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🍾 Үлдэгдэл", value=f"**{inv.get(item_id,0)-1}** ширхэг үлдлээ.", inline=False)
        embed.add_field(name="🧠 Согтолтын түвшин", value=f"{status_name}\n{bar}", inline=False)
        await ctx.send(embed=embed)

    # ----------------------- DRUNK STATUS -----------------------
    @commands.command(name='sogtol', aliases=['согтуу', 'drunk'])
    async def show_drunk(self, ctx):
        guild_id = ctx.guild.id
        level = await self.get_drunk_level(ctx.author.id, guild_id)
        status_name, status_color = self.get_drunk_status(level)
        bar = self.get_intoxication_bar(level)
        embed = discord.Embed(
            title=f"🍺 {ctx.author.display_name}-ын согтол",
            description=f"{status_name}\n{bar}",
            color=status_color
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Согтолтын түвшин цаг тутамд буурдаг")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))