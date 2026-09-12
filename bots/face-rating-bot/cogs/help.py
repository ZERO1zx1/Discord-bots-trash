import discord
from discord.ext import commands
from discord.ui import Select, View
from config import PREFIX

class HelpSelect(Select):
    def __init__(self, mapping: dict):
        options = []
        for cog_name, cmds in mapping.items():
            if not cmds:
                continue
            emoji = self._cog_emoji(cog_name)
            options.append(
                discord.SelectOption(
                    label=f"{emoji} {cog_name}",
                    value=cog_name,
                    description=f"{len(cmds)} команд"
                )
            )
        super().__init__(
            placeholder="📋 Ангилал сонгоно уу...",
            options=options[:25],
            min_values=1, max_values=1
        )
        self.mapping = mapping

    @staticmethod
    def _cog_emoji(cog_name: str) -> str:
        return {
            "Economy": "💰", "Games": "🎮", "Leveling": "📈",
            "Shop": "🛒", "Moderation": "🛡️", "FaceTournament": "🎭",
            "FaceRatingCog": "⭐",
            "Leaderboard": "📊", "Admin": "🔧", "Help": "❓",
            "InviteTracker": "🔗", "Welcome": "👋",
        }.get(cog_name, "📦")

    async def callback(self, interaction: discord.Interaction):
        cog_name = self.values[0]
        embed = self.view.build_embed(cog_name)
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(View):
    def __init__(self, ctx, mapping: dict):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.mapping = mapping
        self.add_item(HelpSelect(mapping))

    def build_embed(self, cog_name: str):
        cmds = self.mapping.get(cog_name, [])
        p = self.ctx.prefix or PREFIX

        embed = discord.Embed(
            title=f"{HelpSelect._cog_emoji(cog_name)} {cog_name} командууд",
            description=f"`{p}help <команд>` гэж бичиж дэлгэрэнгүй мэдээлэл авах",
            color=0x89b4fa
        )

        for cmd in sorted(cmds, key=lambda c: c.name):
            desc = cmd.description or "Тайлбаргүй"
            aliases = ", ".join(cmd.aliases) if cmd.aliases else "—"
            # Slash командын нэрийг харуулах
            slash_name = cmd.name
            embed.add_field(
                name=f"`{p}{cmd.name}` | `/{slash_name}`",
                value=f"{desc}\n🔄 Алиас: `{aliases}`",
                inline=False
            )

        embed.set_footer(
            text=f"{self.ctx.author.display_name} хүсэлт гаргасан • Looksmax.mn",
            icon_url=self.ctx.author.display_avatar.url
        )
        return embed


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _get_command_map(self) -> dict:
        """Бүх ког, командыг ангиллаар цуглуулах"""
        mapping = {}
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue
            cog_name = cmd.cog_name or "Бусад"
            mapping.setdefault(cog_name, []).append(cmd)
        return mapping

    @commands.hybrid_command(
        name="help",
        aliases=["тусламж", "commands"],
        description="Тусламжийн цэс"
    )
    async def help_cmd(self, ctx, *, query: str = None):
        mapping = self._get_command_map()
        p = ctx.prefix or PREFIX

        if query:
            # Тухайн командын дэлгэрэнгүй
            cmd = self.bot.get_command(query.lower())
            if not cmd:
                # Ангиллын нэр байж магадгүй
                for cog_name in mapping:
                    if cog_name.lower() == query.lower():
                        view = HelpView(ctx, mapping)
                        embed = view.build_embed(cog_name)
                        return await ctx.send(embed=embed, view=view)
                embed = discord.Embed(
                    title="❌ Олдсонгүй",
                    description=f"`{query}` гэсэн команд эсвэл ангилал байхгүй.",
                    color=0xed4245
                )
                return await ctx.send(embed=embed)

            # Командын дэлгэрэнгүй мэдээлэл
            embed = discord.Embed(
                title=f"❓ Командын мэдээлэл",
                color=0x57f287
            )
            embed.add_field(
                name="📄 Тайлбар",
                value=cmd.description or "Тайлбаргүй",
                inline=False
            )
            embed.add_field(
                name="🔄 Алиас",
                value=", ".join(cmd.aliases) if cmd.aliases else "—",
                inline=False
            )
            usage = f"{p}{cmd.name} {cmd.signature}" if cmd.signature else f"{p}{cmd.name}"
            embed.add_field(
                name="⚙️ Хэрэглэх (prefix)",
                value=f"`{usage}`",
                inline=False
            )
            embed.add_field(
                name="💬 Хэрэглэх (slash)",
                value=f"`/{cmd.name}`",
                inline=False
            )
            embed.set_footer(
                text=f"{ctx.author.display_name} • Looksmax.mn",
                icon_url=ctx.author.display_avatar.url
            )
            await ctx.send(embed=embed)
        else:
            # Бүх ангилал харуулах
            view = HelpView(ctx, mapping)
            first_cog = next(iter(mapping.keys()), None)
            embed = view.build_embed(first_cog) if first_cog else discord.Embed(
                title="📖 Тусламж", description="Команд олдсонгүй.", color=0x89b4fa
            )
            embed.set_footer(
                text=f"{ctx.author.display_name} • Looksmax.mn",
                icon_url=ctx.author.display_avatar.url
            )
            await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))