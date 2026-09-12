import discord
from discord.ext import commands

class RegistrationChecker(commands.Cog):
    """Командыг гүйцэтгэхийн өмнө бүртгэлийг шалгана."""

    def __init__(self, bot):
        self.bot = bot
        self.skip_commands = ['register', 'reg', 'start', 'help', 'ping', 'invite', 'vote']
        bot.before_invoke(self._check_registration)

    async def _check_registration(self, ctx: commands.Context):
        """Бүртгэл шаардлагатай бол шалгана."""
        if ctx.command.name in self.skip_commands:
            return
        if await self.bot.is_owner(ctx.author):
            return
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return

        economy = self.bot.get_cog("Economy")
        if not economy:
            return

        if await economy.is_registered(ctx.author.id, ctx.guild.id):
            return

        embed = discord.Embed(
            title="🎉 **Gurten Network**-д тавтай морил!",
            description=(
                "Та энэ командыг ашиглахын тулд эхлээд **бүртгүүлэх** шаардлагатай.\n\n"
                "🔹 `g!register` (эсвэл `/register`) командыг ашиглана уу.\n"
                "🔹 Бүртгүүлснээр **10,000₮** эхлэх бонус авах болно.\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "✨ Таны аялал эндээс эхэлнэ.\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            color=0xFFD700
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)
        raise commands.CommandError("Бүртгэлгүй хэрэглэгч")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Slash командад бүртгэл шалгах"""
        if interaction.type != discord.InteractionType.application_command:
            return
        cmd = interaction.command
        if cmd is None or cmd.name in self.skip_commands:
            return

        economy = self.bot.get_cog("Economy")
        if not economy:
            return

        # Админ эсвэл owner-г skip хийх
        if interaction.user.guild_permissions.administrator or interaction.user == interaction.guild.owner:
            return

        if await economy.is_registered(interaction.user.id, interaction.guild_id):
            return

        embed = discord.Embed(
            title="🎉 **Gurten Network**-д тавтай морил!",
            description="Та энэ командыг ашиглахын тулд эхлээд `g!register` командаар бүртгүүлнэ үү!",
            color=0xFFD700
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # ЧУХАЛ: Interaction-ыг шалгаад зөв аргаар хариу илгээх
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def cog_command_error(self, ctx, error):
        """CommandError-уудыг чимээгүй болгох"""
        if isinstance(error, commands.CommandError):
            pass  # Хэрэглэгчид аль хэдийн embed илгээсэн

async def setup(bot):
    await bot.add_cog(RegistrationChecker(bot))
