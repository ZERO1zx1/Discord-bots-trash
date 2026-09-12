import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa
PURPLE_COLOR = 0xcba6f7

COLOR_MAP = {
    "red": ERROR_COLOR,
    "green": SUCCESS_COLOR,
    "blue": INFO_COLOR,
    "yellow": WARNING_COLOR,
    "purple": PURPLE_COLOR,
    "gold": GOLD_COLOR,
    "random": None
}

class AnnounceModal(Modal):
    """Зарлалын мэдээллийг оруулах модал (суваг нь аль хэдийн сонгогдсон)"""
    def __init__(self, bot, channel: discord.TextChannel):
        super().__init__(title="📢 Зарлал илгээх")
        self.bot = bot
        self.channel = channel

        self.title_input = TextInput(
            label="📌 Гарчиг",
            placeholder="Зарлалын гарчиг...",
            required=False,
            max_length=256
        )
        self.add_item(self.title_input)

        self.description_input = TextInput(
            label="📝 Текст",
            placeholder="Зарлалын үндсэн агуулга...",
            style=discord.TextStyle.long,
            required=True,
            max_length=2000
        )
        self.add_item(self.description_input)

        self.color_input = TextInput(
            label="🎨 Өнгө (red/green/blue/yellow/purple/gold/random)",
            placeholder="blue",
            required=False,
            max_length=20
        )
        self.add_item(self.color_input)

        self.image_input = TextInput(
            label="🖼️ Том зурагны URL",
            placeholder="https://example.com/big_image.png",
            required=False,
            max_length=500
        )
        self.add_item(self.image_input)

        # Зөвхөн 5 талбар үлдээхийн тулд жижиг зураг (thumbnail) хасагдсан.
        # Хэрэв танд thumbnail хэрэгтэй бол өөр нэг талбарыг хасаж, энд нэмж болно.

        self.footer_input = TextInput(
            label="📎 Footer текст",
            placeholder="Жишээ: Багийн мэдэгдэл",
            required=False,
            max_length=200
        )
        self.add_item(self.footer_input)

    async def on_submit(self, interaction: discord.Interaction):
        channel = self.channel
        perms = channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.embed_links:
            return await interaction.response.send_message(
                f"❌ Бот {channel.mention} сувагт илгээх эрхгүй.",
                ephemeral=True
            )

        title = self.title_input.value or None
        description = self.description_input.value
        color_str = self.color_input.value.lower() if self.color_input.value else "blue"
        image_url = self.image_input.value if self.image_input.value else None
        footer_text = self.footer_input.value if self.footer_input.value else None

        if color_str == "random":
            color = discord.Color.random()
        else:
            color_val = COLOR_MAP.get(color_str, INFO_COLOR)
            color = discord.Color(color_val) if isinstance(color_val, int) else discord.Color.blue()

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        if footer_text:
            embed.set_footer(text=footer_text)
        if image_url and image_url.startswith(("http://", "https://")):
            embed.set_image(url=image_url)

        await interaction.response.send_message(
            "📌 **Зарлалын урьдчилсан харагдац**\nДоорх `POST` товчийг дарж илгээнэ үү.",
            embed=embed,
            view=PostView(interaction.user, channel, embed),
            ephemeral=True
        )

class PostView(View):
    def __init__(self, author, channel, embed):
        super().__init__(timeout=120)
        self.author = author
        self.channel = channel
        self.embed = embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Энэ зарлал таны бүтээсэн биш.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="📢 POST", style=discord.ButtonStyle.success)
    async def post_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        try:
            await self.channel.send(embed=self.embed)
            await interaction.followup.send(
                f"✅ Зарлал {self.channel.mention} сувагт илгээгдлээ.",
                ephemeral=True
            )
            self.stop()
        except Exception as e:
            await interaction.followup.send(f"❌ Алдаа: {e}", ephemeral=True)

class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="📢 Зарлал илгээх (модал, урьдчилсан харагдац, POST)")
    @app_commands.describe(channel="Зарлал илгээх суваг")
    @app_commands.default_permissions(manage_messages=True)
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel):
        perms = channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.embed_links:
            return await interaction.response.send_message(
                f"❌ Бот {channel.mention} сувагт `Send Messages` эсвэл `Embed Links` эрхгүй.",
                ephemeral=True
            )
        modal = AnnounceModal(self.bot, channel)
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(Announcement(bot))