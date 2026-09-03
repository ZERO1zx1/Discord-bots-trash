import discord
from discord.ext import commands
from discord import app_commands
import time

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

class ConfirmView(discord.ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Тийм ✅", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Үгүй ❌", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


class Marketplace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.init_db()

    async def init_db(self):
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS marketplace_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            seller_id TEXT,
            item_id INTEGER,
            quantity INTEGER,
            price_per_item INTEGER,
            created_at INTEGER
        )''')
        await self.bot.db.commit()

    # ---------- Database helper methods ----------
    async def get_listing(self, listing_id: int):
        return await self.bot.db.fetchone(
            "SELECT id, guild_id, seller_id, item_id, quantity, price_per_item, created_at "
            "FROM marketplace_listings WHERE id = ?",
            listing_id
        )

    async def delete_listing(self, listing_id: int):
        await self.bot.db.execute("DELETE FROM marketplace_listings WHERE id = ?", listing_id)
        await self.bot.db.commit()

    async def get_all_listings(self, guild_id: int, page=0, per_page=5):
        offset = page * per_page
        return await self.bot.db.fetch(
            "SELECT id, seller_id, item_id, quantity, price_per_item, created_at "
            "FROM marketplace_listings WHERE guild_id = ? "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            str(guild_id), per_page, offset
        )

    async def create_listing(self, guild_id: int, seller_id: int, item_id: int, quantity: int, price_per_item: int):
        now = int(time.time())
        cur = await self.bot.db.execute(
            "INSERT INTO marketplace_listings (guild_id, seller_id, item_id, quantity, price_per_item, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            str(guild_id), str(seller_id), item_id, quantity, price_per_item, now
        )
        await self.bot.db.commit()
        return cur.lastrowid

    async def get_shop_cog(self):
        return self.bot.get_cog("ShopCog")

    # ========== COMMANDS ==========
    @commands.hybrid_group(name='marketplace', aliases=['mp', 'зах'], invoke_without_command=True)
    async def marketplace_group(self, ctx):
        embed = discord.Embed(
            title="🛒 ЗАХ ЗЭЭЛИЙН ТУСЛАМЖ",
            description=(
                "`marketplace sell <item_id> <тоо> <үнэ>` - Зарах\n"
                "`marketplace buy <id>` - Худалдаж авах\n"
                "`marketplace listings` - Жагсаалт\n"
                "`marketplace cancel <id>` - Цуцлах"
            ),
            color=GOLD_COLOR
        )
        await ctx.send(embed=embed)

    @marketplace_group.command(name='sell', description="Бараа зарах")
    @app_commands.describe(item_id="Барааны ID", quantity="Тоо хэмжээ", price="Нэг ширхэгийн үнэ")
    async def marketplace_sell(self, ctx: commands.Context, item_id: int, quantity: int, price: int):
        author = ctx.author
        guild = ctx.guild
        shop = await self.get_shop_cog()
        if not shop:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Shop ажиллахгүй байна.", color=ERROR_COLOR))

        if quantity <= 0 or price <= 0:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Тоо, үнэ эерэг байх ёстой.", color=ERROR_COLOR))

        item = await shop.get_item(item_id)
        if not item:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description=f"`{item_id}` ID-тай бараа байхгүй.", color=ERROR_COLOR))

        inv = await shop.get_user_inventory(author.id, guild.id)
        if inv.get(item_id, 0) < quantity:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Хангалттай бараа байхгүй.", color=ERROR_COLOR))

        embed = discord.Embed(
            title="📢 ЗАРЛАЛ БАТАЛГААЖУУЛАХ",
            description=f"{item['emoji']} **{item['name']}** x{quantity} → {price:,}₮/ш\nНийт үнэ: {price*quantity:,}₮\n\nЗарлалыг үүсгэх үү?",
            color=WARNING_COLOR
        )
        view = ConfirmView()
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not True:
            return await ctx.send("❌ Зар үүсгэхээ цуцаллаа.", ephemeral=True)

        if not await shop.remove_item(author.id, guild.id, item_id, quantity):
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Барааг хасаж чадсангүй.", color=ERROR_COLOR))

        listing_id = await self.create_listing(guild.id, author.id, item_id, quantity, price)
        success_embed = discord.Embed(
            title="✅ ЗАР ҮҮСГЭЛЭЭ",
            description=f"{item['emoji']} **{item['name']}** x{quantity} → {price:,}₮/ш\n🆔 ID: `{listing_id}`",
            color=SUCCESS_COLOR
        )
        await ctx.send(embed=success_embed)

    @marketplace_group.command(name='buy', description="Зарласан барааг худалдаж авах")
    @app_commands.describe(listing_id="Зарлалын ID")
    async def marketplace_buy(self, ctx: commands.Context, listing_id: int):
        author = ctx.author
        guild = ctx.guild
        shop = await self.get_shop_cog()
        economy = self.bot.get_cog("Economy")
        if not shop or not economy:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Систем ажиллахгүй байна.", color=ERROR_COLOR))

        listing = await self.get_listing(listing_id)
        if not listing:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Зарлал олдсонгүй.", color=ERROR_COLOR))

        _, guild_id_str, seller_id, item_id, quantity, price_per_item, _ = listing
        if int(guild_id_str) != guild.id:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Энэ зарлал энэ серверт хамаарахгүй.", color=ERROR_COLOR))
        if str(seller_id) == str(author.id):
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Өөрийн зарыг худалдаж болохгүй.", color=ERROR_COLOR))

        total_price = price_per_item * quantity
        balance = await economy.get_balance(author.id, guild.id)
        if balance < total_price:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description=f"Мөнгө хүрэлцэхгүй. Хэрэгтэй: {total_price:,}₮, Таны үлдэгдэл: {balance:,}₮", color=ERROR_COLOR))

        item = await shop.get_item(item_id)
        item_name = f"{item['emoji']} **{item['name']}**" if item else f"ID:{item_id}"
        embed = discord.Embed(
            title="🛒 ХУДАЛДАН АВАХ БАТАЛГАА",
            description=f"Та {item_name} x{quantity} -г **{total_price:,}** мөнгөөр худалдаж авах гэж байна.\nЗөвшөөрөх үү?",
            color=WARNING_COLOR
        )
        view = ConfirmView()
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not True:
            return await ctx.send("❌ Худалдан авалт цуцлагдлаа.", ephemeral=True)

        # Гүйлгээ хийх
        await economy.update_balance(author.id, guild.id, -total_price)
        await economy.update_balance(int(seller_id), guild.id, total_price)
        await shop.add_item(author.id, guild.id, item_id, quantity)
        await self.delete_listing(listing_id)

        success_embed = discord.Embed(
            title="✅ ХУДАЛДАН АВАЛТ АМЖИЛТТАЙ",
            description=f"{author.mention} {item_name} x{quantity} -г {total_price:,}₮-өөр худалдаж авав.",
            color=SUCCESS_COLOR
        )
        await ctx.send(embed=success_embed)

        seller = guild.get_member(int(seller_id))
        if seller:
            try:
                await seller.send(f"✅ Таны {item_name} x{quantity} зарагдлаа! +{total_price:,}₮")
            except:
                pass

    @marketplace_group.command(name='listings', description="Идэвхтэй зарлалууд")
    @app_commands.describe(page="Хуудас (анхдагч 1)")
    async def marketplace_listings(self, ctx: commands.Context, page: int = 1):
        guild = ctx.guild
        if page < 1:
            page = 1
        per_page = 5
        rows = await self.get_all_listings(guild.id, page=page-1, per_page=per_page)
        if not rows:
            return await ctx.send(embed=discord.Embed(title="📃 ЗАРЛАЛУУД", description="Одоохондоо зарлал байхгүй.", color=INFO_COLOR))

        shop = await self.get_shop_cog()
        embed = discord.Embed(title="🛒 ИДЭВХТЭЙ ЗАРЛАЛУУД", color=GOLD_COLOR)
        for lid, seller_id, item_id, qty, price, _ in rows:
            item = await shop.get_item(item_id) if shop else None
            item_str = f"{item['emoji']} **{item['name']}**" if item else f"ID:{item_id}"
            seller = guild.get_member(int(seller_id))
            seller_name = seller.display_name if seller else f"<@{seller_id}>"
            embed.add_field(
                name=f"📌 ID: {lid} | {seller_name}",
                value=f"{item_str} x{qty} → {price:,}₮/ш (Нийт: {price*qty:,}₮)",
                inline=False
            )
        embed.set_footer(text=f"Хуудас {page} | Худалдаж авах: /marketplace buy")
        await ctx.send(embed=embed)

    @marketplace_group.command(name='cancel', description="Өөрийн зарыг цуцлах")
    @app_commands.describe(listing_id="Зарлалын ID")
    async def marketplace_cancel(self, ctx: commands.Context, listing_id: int):
        author = ctx.author
        guild = ctx.guild
        shop = await self.get_shop_cog()
        if not shop:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Shop ажиллахгүй байна.", color=ERROR_COLOR))

        listing = await self.get_listing(listing_id)
        if not listing:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Зарлал олдсонгүй.", color=ERROR_COLOR))

        _, _, seller_id, item_id, quantity, price_per_item, _ = listing
        if str(seller_id) != str(author.id):
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Та зөвхөн өөрийн зарыг цуцлах боломжтой.", color=ERROR_COLOR))

        item = await shop.get_item(item_id)
        item_name = f"{item['emoji']} **{item['name']}**" if item else f"ID:{item_id}"
        embed = discord.Embed(
            title="❌ ЗАР ЦУЦЛАХ БАТАЛГАА",
            description=f"{item_name} x{quantity} -г цуцлахад бараа таны инвентарт буцаж орох болно.\nЦуцлах уу?",
            color=WARNING_COLOR
        )
        view = ConfirmView()
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not True:
            return await ctx.send("❌ Зар цуцлах үйлдлийг цуцаллаа.", ephemeral=True)

        await shop.add_item(author.id, guild.id, item_id, quantity)
        await self.delete_listing(listing_id)
        await ctx.send(embed=discord.Embed(
            title="✅ ЗАР ЦУЦЛАГДЛАА",
            description=f"{item_name} x{quantity} буцаан инвентарт орлоо.",
            color=SUCCESS_COLOR
        ))


async def setup(bot):
    await bot.add_cog(Marketplace(bot))