import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import time
import logging

logger = logging.getLogger(__name__)

class RegisterView(View):
    """Бүртгэлийн товчлуур (хэнд ч адилхан ажиллана)"""
    def __init__(self, cog, ctx):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.button(label="✅ Бүртгүүлэх", style=discord.ButtonStyle.success, emoji="📝")
    async def register_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Энэ товчлуур танд зориулагдаагүй.", ephemeral=True)

        economy = self.cog.bot.get_cog("Economy")
        if not economy:
            return await interaction.response.send_message("❌ Эдийн засгийн систем ачаалагдаагүй байна.", ephemeral=True)

        # Бүртгэлтэй эсэхийг шалгах
        row = await self.cog.bot.db.fetchone(
            "SELECT 1 FROM economy WHERE user_id = ? AND guild_id = ?",
            str(interaction.user.id), str(interaction.guild_id)
        )
        if row:
            return await interaction.response.send_message("✅ Та аль хэдийн бүртгэлтэй байна!", ephemeral=True)

        # Шинэ хэрэглэгч бүртгэх
        await self.cog.bot.db.execute(
            "INSERT INTO economy (user_id, guild_id, balance, bank_balance, last_daily, last_work, "
            "bank_protect_until, prison_until, hunger, mood) "
            "VALUES (?, ?, 10000, 0, NULL, NULL, 0, 0, 0, 0)",
            str(interaction.user.id), str(interaction.guild_id)
        )
        await self.cog.bot.db.commit()

        embed = discord.Embed(
            title="✅ Амжилттай бүртгэгдлээ!",
            description=(
                "🎉 **Gurten Economy**-д тавтай морил.\n\n"
                "💰 Таны дансанд **10,000₮** бонус нэмэгдлээ.\n\n"
                "Одоо та дараах командуудыг ашиглах боломжтой:\n"
                "• `gdaily` – өдрийн бонус\n"
                "• `gwork` – ажил хийх\n"
                "• `gshop` – дэлгүүр үзэх\n"
                "• `gprofile` – профайлаа харах\n\n"
                "🚀 Амжилт хүсье!"
            ),
            color=0x5865F2
        )
        embed.set_thumbnail(url=self.cog.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()


class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Cog ачаалагдах үед slash командыг бүртгэх"""
        # Өмнө нь бүртгэгдсэн байж болзошгүй тул давхар бүртгэлээс сэргийлэх
        self.bot.tree.remove_command("register", guild=None)
        self.bot.tree.add_command(self.register_slash)
        # Зөвхөн хөгжүүлэлтийн үед sync хийх (production дээр global sync удаан)
        try:
            await self.bot.tree.sync()
        except Exception as e:
            logger.error(f"Slash register sync error: {e}")

    @app_commands.command(name="register", description="Gurten эдийн засагт бүртгүүлэх")
    async def register_slash(self, interaction: discord.Interaction):
        """Slash командын бүртгэл"""
        # Fake context үүсгэхгүйгээр шууд бүртгэлийн логикийг ашиглах
        await self._handle_register(interaction.user, interaction.guild, interaction)

    @commands.command(name='register', aliases=['reg', 'start'])
    async def register_prefix(self, ctx):
        """Prefix командын бүртгэл"""
        await self._handle_register(ctx.author, ctx.guild, ctx)

    async def _handle_register(self, user, guild, destination):
        """Бүртгэлийн үндсэн логик (prefix болон slash-д адил)"""
        economy = self.bot.get_cog("Economy")
        if not economy:
            if isinstance(destination, commands.Context):
                return await destination.send("❌ Эдийн засгийн систем ачаалагдаагүй байна.")
            else:
                return await destination.response.send_message("❌ Эдийн засгийн систем ачаалагдаагүй байна.", ephemeral=True)

        # Аль хэдийн бүртгэлтэй эсэх
        row = await self.bot.db.fetchone(
            "SELECT 1 FROM economy WHERE user_id = ? AND guild_id = ?",
            str(user.id), str(guild.id)
        )
        if row:
            msg = "✅ Та аль хэдийн бүртгэлтэй байна!"
            if isinstance(destination, commands.Context):
                return await destination.send(msg, delete_after=10)
            else:
                return await destination.response.send_message(msg, ephemeral=True)

        # Админ / Owner эсэхийг шалгах
        is_admin = (
            user.guild_permissions.administrator or
            user == guild.owner or
            await self.bot.is_owner(user)
        )

        if is_admin:
            embed = discord.Embed(
                title="🔐 **Gurten LGC Бот – Админ/owner бүртгэл**",
                description=(
                    "Та энэ серверийн эзэн эсвэл администратор тул дараах бүх системийг удирдах эрхтэй.\n"
                    "Бүртгүүлснээр танд 10,000₮ бонус олгох бөгөөд доорх командуудыг ашиглах боломжтой.\n\n"
                    "**✨ Таны нээлттэй админ командууд:**\n"
                    "🛡️ **Сервер тохиргоо:** `voicesetup`, `count_set`, `invitelog_set`, `greeting_set`, `confess_setup`\n"
                    "👥 **Хэрэглэгч удирдлага:** `warn`, `ban`, `kick`, `timeout`, `role give/remove`\n"
                    "💰 **Эдийн засаг & Level:** `stock set/add/reset`, `leveling set/toggle/setxp`\n"
                    "🎭 **Тоглоом, зугаа:** `mafia create/start`, `pvp`, `dice`, `gamble`, `drink`\n"
                    "📊 **Статистик:** `regcount`, `reglist`, `staff_counts`, `gamestats`\n\n"
                    "💖 **Gurten LGC Bot-ыг дэмжинэ үү!** Дуртай бол найзуудаа урьж, сервертээ идэвхжүүлээрэй.\n\n"
                    "Бүртгүүлэхийн тулд доорх товчийг дарна уу."
                ),
                color=0x3498db  # Цэнхэр
            )
            embed.set_footer(text="Админ эрхтэй хэрэглэгчид зориулсан мэдээлэл")
        else:
            embed = discord.Embed(
                title="🎉 **Gurten Network**-д тавтай морил!",
                description=(
                    "Та одоогоор бүртгэлгүй байна.\n\n"
                    "Gurten-ийн эдийн засаг, түвшин, дэлгүүр, гэрлэлт болон бусад бүх системийг ашиглахын тулд "
                    "эхлээд бүртгүүлэх шаардлагатай.\n\n"
                    "### 🎁 Бүртгүүлсний урамшуулал\n"
                    "> 💰 10,000₮ эхлэх бонус\n"
                    "> 📈 Level & XP системд нэгдэх\n"
                    "> 🛒 Дэлгүүр болон inventory ашиглах\n"
                    "> 💍 Marriage систем ашиглах\n"
                    "> 🎲 Казино болон тоглоомуудад оролцох\n\n"
                    "Доорх **✅ Бүртгүүлэх** товчийг дарж бүртгэлээ үүсгээрэй.\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "✨ Таны аялал эндээс эхэлнэ.\n"
                    "━━━━━━━━━━━━━━━━━━"
                ),
                color=0xFFD700  # Алтан шар
            )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        view = RegisterView(self, destination if isinstance(destination, commands.Context) else None)

        # Context эсвэл Interaction-д тохируулан илгээх
        if isinstance(destination, commands.Context):
            # Prefix командын хувьд RegisterView-д context-ийг дамжуулах
            view.ctx = destination
            await destination.send(embed=embed, view=view)
        else:
            # Slash командын хувьд interaction-ийг ашиглах
            # RegisterView-д context байхгүй тул тусгайлан тохируулах
            await destination.response.send_message(embed=embed, view=view, ephemeral=False)

async def setup(bot):
    await bot.add_cog(Register(bot))
