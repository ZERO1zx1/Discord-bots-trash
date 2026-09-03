import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import ButtonStyle
import random
from datetime import datetime, timezone

# ===== COLORS (неон палитр) =====
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR   = 0xf38ba8
GOLD_COLOR    = 0xfab387
WARNING_COLOR = 0xf9e2af
INFO_COLOR    = 0x89b4fa
NEON_PINK     = 0xFF10F0
NEON_GREEN    = 0x39FF14
NEON_YELLOW   = 0xCCFF00

GRID_SIZE = 5
BOMB_COUNT = 3
SAFE_COUNT = GRID_SIZE * GRID_SIZE - BOMB_COUNT

COLUMNS = ['A', 'B', 'C', 'D', 'E']

class MinesGame:
    def __init__(self, user_id, bet):
        self.user_id = user_id
        self.bet = bet
        self.current_win = bet
        self.revealed = set()
        self.finished = False
        all_cells = [(col, row) for col in range(GRID_SIZE) for row in range(1, GRID_SIZE+1)]
        self.bombs = set(random.sample(all_cells, BOMB_COUNT))

    def reveal(self, col, row):
        if (col, row) in self.revealed:
            return "already"
        self.revealed.add((col, row))
        if (col, row) in self.bombs:
            self.finished = True
            return "bomb"
        self.current_win = int(self.current_win * 1.5)
        if len(self.revealed) == SAFE_COUNT:
            self.finished = True
            return "all_safe"
        return "safe"

    @property
    def multiplier(self):
        return self.current_win / self.bet

class MinesView(View):
    def __init__(self, bot, ctx, game):
        super().__init__(timeout=120)
        self.bot = bot
        self.ctx = ctx
        self.game = game
        self.message = None
        self.buttons = {}

        for r in range(1, GRID_SIZE+1):
            for c in range(GRID_SIZE):
                label = f"{COLUMNS[c]}{r}"
                btn = Button(label=label, style=ButtonStyle.gray, row=r-1)
                btn.callback = self.make_callback(c, r, btn)
                self.add_item(btn)
                self.buttons[(c, r)] = btn

        cash_btn = Button(label="💰 Cashout (x{:.2f})".format(game.multiplier),
                          style=ButtonStyle.success, row=5)
        cash_btn.callback = self.cashout_callback
        self.add_item(cash_btn)
        self.cash_btn = cash_btn

    def make_callback(self, col, row, button):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.game.user_id:
                return await interaction.response.send_message("❌ Энэ тоглоом таных биш!", ephemeral=True)
            if self.game.finished:
                return await interaction.response.send_message("❌ Тоглоом дууссан.", ephemeral=True)

            result = self.game.reveal(col, row)
            if result == "already":
                return await interaction.response.send_message("❌ Энэ нүд аль хэдийн онгойсон!", ephemeral=True)

            economy = self.bot.get_cog("Economy")
            cog = self.bot.get_cog("Mines")

            if result == "bomb":
                button.style = ButtonStyle.red
                button.label = "💣"
                button.disabled = True
                for child in self.children:
                    child.disabled = True
                embed = discord.Embed(
                    title="💥 БӨМБӨГ!",
                    description=f"{self.ctx.author.mention} та бөмбөгтэй таарч, **{self.game.bet:,}** мөнгө алдлаа!",
                    color=ERROR_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="🗺️ Талбар", value=self.get_grid_string(), inline=False)
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                embed.set_footer(text=f"{self.ctx.guild.name} • Mines")
                await interaction.response.edit_message(embed=embed, view=self)
                await cog.add_hunger_mood(self.ctx, 10, 5)
                self.stop()
                return

            elif result == "all_safe":
                button.style = ButtonStyle.green
                button.label = "✅"
                button.disabled = True
                total_win = self.game.current_win
                await economy.update_balance(self.game.user_id, self.ctx.guild.id, total_win)
                embed = discord.Embed(
                    title="🏆 JACKPOT! БҮХ НҮД ОНГОЙЛГОСОН!",
                    description=f"{self.ctx.author.mention} та бүх аюулгүй нүдийг онгойлгож, **{total_win:,}** мөнгө хожлоо!",
                    color=NEON_GREEN,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="🗺️ Талбар", value=self.get_grid_string(), inline=False)
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                embed.set_footer(text=f"{self.ctx.guild.name} • Mines")
                for child in self.children:
                    child.disabled = True
                await interaction.response.edit_message(embed=embed, view=self)
                await cog.add_hunger_mood(self.ctx, 10, 5)
                self.stop()
                return

            else:  # Аюулгүй
                button.style = ButtonStyle.green
                button.label = "✅"
                button.disabled = True
                self.cash_btn.label = f"💰 Cashout (x{self.game.multiplier:.2f})"
                embed = discord.Embed(
                    title="✅ АЮУЛГҮЙ НҮД!",
                    description=f"{self.ctx.author.mention} та **{COLUMNS[col]}{row}** нүдийг онгойлголоо.\n"
                                f"Одоогийн хожил: **{self.game.current_win:,}** (x{self.game.multiplier:.2f})",
                    color=SUCCESS_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="🗺️ Талбар", value=self.get_grid_string(), inline=False)
                embed.add_field(name="📊 Статистик",
                                value=f"Онгойсон: {len(self.game.revealed)}/{SAFE_COUNT}\n"
                                      f"Үлдсэн аюулгүй: {SAFE_COUNT - len(self.game.revealed)}",
                                inline=False)
                embed.set_footer(text="Хожил авахын тулд 💰 Cashout товчийг дарна уу")
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                await interaction.response.edit_message(embed=embed, view=self)
                await cog.add_hunger_mood(self.ctx, 5, 3)
        return callback

    async def cashout_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Энэ тоглоом таных биш!", ephemeral=True)
        if self.game.finished:
            return await interaction.response.send_message("❌ Тоглоом дууссан.", ephemeral=True)

        economy = self.bot.get_cog("Economy")
        await economy.update_balance(self.game.user_id, self.ctx.guild.id, self.game.current_win)
        embed = discord.Embed(
            title="💰 CASH OUT!",
            description=f"{self.ctx.author.mention} та **{self.game.current_win:,}** мөнгө хожлоо! "
                        f"(x{self.game.multiplier:.2f})",
            color=NEON_YELLOW,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"{self.ctx.guild.name} • Mines")
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        cog = self.bot.get_cog("Mines")
        await cog.add_hunger_mood(self.ctx, 5, 3)
        self.stop()

    def get_grid_string(self):
        lines = []
        for r in range(1, GRID_SIZE+1):
            row = []
            for c in range(GRID_SIZE):
                cell = (c, r)
                if cell in self.game.revealed:
                    if cell in self.game.bombs:
                        row.append("💣")
                    else:
                        row.append("✅")
                else:
                    row.append(f"**{COLUMNS[c]}{r}**")
            lines.append(" | ".join(row))
        return "\n".join(lines)

    async def on_timeout(self):
        if not self.game.finished:
            economy = self.bot.get_cog("Economy")
            await economy.update_balance(self.game.user_id, self.ctx.guild.id, self.game.bet)
            embed = discord.Embed(
                title="⏰ ХУГАЦАА ДУУССАН",
                description=f"{self.ctx.author.mention}, та 2 минутын дотор тоглоомоо дуусгаагүй тул "
                            f"**{self.game.bet:,}** мөнгийг буцаан авлаа.",
                color=WARNING_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(embed=embed, view=self)

class Mines(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_hunger_mood(self, ctx):
        economy = self.bot.get_cog("Economy")
        if economy:
            hunger, mood = await economy.get_hunger_mood(ctx.author.id, ctx.guild.id)
            if hunger >= 80:
                await ctx.send(f"🍔 {ctx.author.mention}, та хэт өлсөж байна! Тоглох тэнхээгүй. `geat` хийгээрэй.")
                return False
            if mood >= 80:
                await ctx.send(f"😡 {ctx.author.mention}, та хэт ууртай байна! `grelax` амраарай.")
                return False
            return True
        return True

    async def add_hunger_mood(self, ctx, hunger_inc=5, mood_inc=3):
        economy = self.bot.get_cog("Economy")
        if economy:
            hunger, mood = await economy.get_hunger_mood(ctx.author.id, ctx.guild.id)
            new_hunger = min(100, hunger + hunger_inc)
            new_mood = min(100, mood + mood_inc)
            await economy.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=new_hunger, mood=new_mood)

    @commands.command(name='mines', aliases=['mf', 'minefield'])
    async def mines(self, ctx, bet: int = None):
        if ctx.guild is None:
            return await ctx.send("❌ Зөвхөн серверт ашиглана уу.")

        if not await self.check_hunger_mood(ctx):
            return

        economy = self.bot.get_cog("Economy")
        if not economy:
            return await ctx.send("❌ Эдийн засгийн систем ачаалагдаагүй байна!")

        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байхдаа тоглох боломжгүй.")

        if bet is None:
            embed = discord.Embed(
                title="💣 MINES ТОГЛООМ",
                description="`gmines <бооцоо>` – шинэ тоглоом эхлүүлэх\nЖишээ: `gmines 5000`",
                color=INFO_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(
                name="Тоглоомын дүрэм",
                value="5x5 талбарт 3 бөмбөг нуугдсан. Нүд онгойлгох бүрт хожил 1.5x өснө. "
                      "Cashout хийх эсвэл бүх нүдийг нээж JACKPOT хожно.",
                inline=False
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text=f"{ctx.guild.name} • Mines")
            return await ctx.send(embed=embed)

        if bet <= 0:
            return await ctx.send("❌ Бооцоо эерэг тоо байх ёстой!")

        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < bet:
            return await ctx.send(f"❌ Танд {bet:,} мөнгө байхгүй! (Үлдэгдэл: {bal:,})")

        await economy.update_balance(ctx.author.id, ctx.guild.id, -bet)

        game = MinesGame(ctx.author.id, bet)
        view = MinesView(self.bot, ctx, game)

        embed = discord.Embed(
            title="💣 MINES ТОГЛООМ",
            description=f"**Бооцоо:** 💰 {bet:,} мөнгө\n"
                        f"5x5 талбарт 3 бөмбөг нуугдсан.\n"
                        f"Нүд онгойлгох бүрт хожил **1.5x**-ээр өснө!",
            color=NEON_YELLOW,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="🗺️ Талбар", value=view.get_grid_string(), inline=False)
        embed.set_footer(text="Нүдний товчлуур дээр дарж онгойлгоно | Cashout товчоор хожил авах")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        view.message = await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Mines(bot))