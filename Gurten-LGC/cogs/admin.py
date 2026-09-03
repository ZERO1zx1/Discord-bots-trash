import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

class AdminEconomy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_owner_or_co_owner(self, user_id):
        owner = self.bot.owner_id
        co_owners = getattr(self.bot, 'co_owners', [])
        return user_id == owner or user_id in co_owners

    # ---------- Guild Info ----------
    @commands.hybrid_command(name='guildinfo', aliases=['serverinfo'], description='Серверийн мэдээлэл харах')
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def guildinfo(self, ctx):
        await ctx.defer(ephemeral=False)
        if ctx.guild is None:
            embed = discord.Embed(title="❌ АЛДАА", description="Зөвхөн сервер дотор ашиглах боломжтой.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        guild = ctx.guild
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = total_members - humans
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles) - 1
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count or 0
        verif_levels = {
            discord.VerificationLevel.none: "❌ Хязгаарлалтгүй",
            discord.VerificationLevel.low: "✅ Бага",
            discord.VerificationLevel.medium: "⚠️ Дунд",
            discord.VerificationLevel.high: "🔒 Өндөр",
            discord.VerificationLevel.highest: "🔒🔒 Хамгийн өндөр"
        }
        verif_level = verif_levels.get(guild.verification_level, "Тодорхойгүй")
        embed = discord.Embed(title=f"📌 **{guild.name}**", description="*Серверийн дэлгэрэнгүй мэдээлэл*", 
                              color=GOLD_COLOR if guild.premium_tier > 0 else EMBED_COLOR, timestamp=datetime.now())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        embed.add_field(name="👑 **Эзэмшигч**", value=f"{guild.owner.mention}\n`{guild.owner.name}`", inline=True)
        embed.add_field(name="📅 **Үүсгэсэн**", value=f"`{guild.created_at.strftime('%Y-%m-%d %H:%M:%S')}`", inline=True)
        embed.add_field(name="🆔 **Серверийн ID**", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👥 **Гишүүд**", value=f"👨 Жинхэнэ: `{humans}`\n🤖 Бот: `{bots}`\n📊 Нийт: `{total_members}`", inline=True)
        embed.add_field(name="💬 **Сувгууд**", value=f"📝 Текст: `{text_channels}`\n🎙️ Дууны: `{voice_channels}`\n📁 Категори: `{categories}`", inline=True)
        embed.add_field(name="🎭 **Роль**", value=f"`{roles}` роль", inline=True)
        boost_emoji = "⭐" if boost_level == 1 else "🌟🌟" if boost_level == 2 else "🌟🌟🌟" if boost_level == 3 else "💨"
        embed.add_field(name="🚀 **Boost**", value=f"{boost_emoji} Түвшин: `{boost_level}`\n⚡ Boost: `{boost_count}`", inline=True)
        embed.add_field(name="🔐 **Баталгаажуулалт**", value=verif_level, inline=True)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---------- Server Icon ----------
    @commands.hybrid_command(name='servericon', description='Серверийн дүрс харах')
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def servericon(self, ctx):
        await ctx.defer(ephemeral=False)
        if not ctx.guild or not ctx.guild.icon:
            embed = discord.Embed(title="❌ ДҮРС БАЙХГҮЙ", description="Энэ серверт дүрс тохируулаагүй байна.", color=WARNING_COLOR)
            return await ctx.send(embed=embed)
        embed = discord.Embed(title=f"🖼️ **{ctx.guild.name} -ИЙН ДҮРС**", color=GOLD_COLOR)
        embed.set_image(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---------- Server Banner ----------
    @commands.hybrid_command(name='serverbanner', description='Серверийн баннер харах')
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def serverbanner(self, ctx):
        await ctx.defer(ephemeral=False)
        if not ctx.guild or not ctx.guild.banner:
            embed = discord.Embed(title="❌ БАННЕР БАЙХГҮЙ", description="Энэ серверт баннер тохируулаагүй байна.\nBoost Level 2 шаардлагатай.", color=WARNING_COLOR)
            return await ctx.send(embed=embed)
        embed = discord.Embed(title=f"🎨 **{ctx.guild.name} -ИЙН БАННЕР**", color=GOLD_COLOR)
        embed.set_image(url=ctx.guild.banner.url)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---------- Server Splash ----------
    @commands.hybrid_command(name='serversplash', description='Серверийн урилгын дэлгэц харах')
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def serversplash(self, ctx):
        await ctx.defer(ephemeral=False)
        if not ctx.guild or not ctx.guild.splash:
            embed = discord.Embed(title="❌ SPLASH БАЙХГҮЙ", description="Энэ серверт урилгын дэлгэц тохируулаагүй байна.", color=WARNING_COLOR)
            return await ctx.send(embed=embed)
        embed = discord.Embed(title=f"🖼️ **{ctx.guild.name} -ИЙН SPLASH**", color=GOLD_COLOR)
        embed.set_image(url=ctx.guild.splash.url)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---------- Role List ----------
    @commands.hybrid_command(name='rolelist', description='Role жагсаалт харах')
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def rolelist(self, ctx, member: discord.Member = None):
        await ctx.defer(ephemeral=False)
        if not ctx.guild:
            return
        roles = sorted([r for r in ctx.guild.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
        if not roles:
            embed = discord.Embed(title="🎭 **РОЛЬ БАЙХГҮЙ**", description="Энэ серверт @everyone-ээс өөр роль байхгүй.", color=WARNING_COLOR)
            return await ctx.send(embed=embed)
        embed = discord.Embed(title=f"🎭 **{ctx.guild.name} -ИЙН РОЛЬУУД**", description=f"Нийт **{len(roles)}** роль", color=EMBED_COLOR)
        chunks = [roles[i:i+10] for i in range(0, min(len(roles), 50), 10)]
        for idx, chunk in enumerate(chunks):
            value = ", ".join([r.mention for r in chunk])
            if len(value) > 1024:
                value = f"{len(chunk)} роль (жагсаалт хэт урт)"
            embed.add_field(name=f"📋 Роль бүлэг {idx+1}", value=value, inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---------- Add Money ----------
    @commands.hybrid_command(name='addmoney', aliases=['am'], description='Мөнгө нэмэх')
    async def addmoney(self, ctx, member: discord.Member, amount: int):
        if not self.is_owner_or_co_owner(ctx.author.id):
            embed = discord.Embed(title="⛔ ЭРХ ХҮРЭХГҮЙ", description="Зөвхөн бот эзэмшигч / хамт эзэмшигч", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await ctx.defer(ephemeral=False)
        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        if amount <= 0:
            embed = discord.Embed(title="❌ АЛДАА", description="Дүн эерэг байх ёстой.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await economy.ensure_user(member.id, ctx.guild.id)
        await economy.update_balance(member.id, ctx.guild.id, amount)
        new_bal = await economy.get_balance(member.id, ctx.guild.id)
        embed = discord.Embed(title="✅ МӨНГӨ НЭМЭГДЛЭЭ", description=f"{ctx.author.mention} → {member.mention} **{amount:,}** мөнгө нэмлээ.", color=SUCCESS_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="💰 ШИНЭ ҮЛДЭГДЭЛ", value=f"```yaml\n{new_bal:,} мөнгө```", inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---------- Remove Money ----------
    @commands.hybrid_command(name='removemoney', aliases=['rm'], description='Мөнгө хасах')
    async def removemoney(self, ctx, member: discord.Member, amount: int):
        if not self.is_owner_or_co_owner(ctx.author.id):
            embed = discord.Embed(title="⛔ ЭРХ ХҮРЭХГҮЙ", description="Зөвхөн бот эзэмшигч / хамт эзэмшигч", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await ctx.defer(ephemeral=False)
        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        if amount <= 0:
            embed = discord.Embed(title="❌ АЛДАА", description="Дүн эерэг байх ёстой.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        bal = await economy.get_balance(member.id, ctx.guild.id)
        if bal < amount:
            embed = discord.Embed(title="❌ ХАНГАЛТГҮЙ", description=f"{member.mention} -д **{amount:,}** мөнгө хасахад хангалтгүй.\n💰 Одоогийн үлдэгдэл: **{bal:,}** мөнгө", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await economy.update_balance(member.id, ctx.guild.id, -amount)
        new_bal = await economy.get_balance(member.id, ctx.guild.id)
        embed = discord.Embed(title="⚠️ МӨНГӨ ХАСАГДЛАА", description=f"{ctx.author.mention} → {member.mention} **{amount:,}** мөнгө хаслаа.", color=WARNING_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="💰 ШИНЭ ҮЛДЭГДЭЛ", value=f"```yaml\n{new_bal:,} мөнгө```", inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---------- Error handlers ----------
    @addmoney.error
    @removemoney.error
    async def money_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(title="❌ АЛДАА", description=f"Зөв хэлбэр: `{ctx.prefix}{ctx.command.name} @хэрэглэгч <дүн>`\nЖишээ: `{ctx.prefix}{ctx.command.name} @Bold 1000`", color=ERROR_COLOR)
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(title="❌ АЛДАА", description="Хэрэглэгч эсвэл дүн буруу байна. Зөв хэлбэрээр бичнэ үү.", color=ERROR_COLOR)
            await ctx.send(embed=embed)
        else:
            raise error

async def setup(bot):
    await bot.add_cog(AdminEconomy(bot))