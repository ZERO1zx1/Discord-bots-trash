import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import time
import asyncio
import random

# ===== COLORS (неон палитр) =====
EMBED_COLOR   = 0x1e1e2f
ERROR_COLOR   = 0xf38ba8
SUCCESS_COLOR = 0xa6e3a1
WARNING_COLOR = 0xf9e2af
GOLD_COLOR    = 0xfab387
PURPLE_COLOR  = 0xcba6f7
INFO_COLOR    = 0x89b4fa
NEON_PINK     = 0xFF10F0
NEON_GREEN    = 0x39FF14
NEON_YELLOW   = 0xCCFF00

PVP_COOLDOWN = 120  # 2 минут

# ==================== PVP VIEW ====================
class PVPView(View):
    def __init__(self, bot, channel, player1, player2, bet_amount):
        super().__init__(timeout=None)  # хугацааг гараар удирдана
        self.bot = bot
        self.channel = channel
        self.player1 = player1
        self.player2 = player2
        self.bet_amount = bet_amount
        self.player1_score = 0
        self.player2_score = 0
        self.current_round = 1
        self.player1_choice = None
        self.player2_choice = None
        self.round_results = []
        self.player1_ready = False
        self.player2_ready = False
        self.round_active = False
        self.message = None
        self.game_active = True
        self._round_timer = None

    async def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

    async def send_round_embed(self):
        embed = discord.Embed(
            title=f"⚔️ **PVP ТУЛААН - РАУНД {self.current_round}/3**",
            description=f"**{self.player1.display_name}** vs **{self.player2.display_name}**",
            color=GOLD_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
        embed.add_field(
            name="📊 **ОДООГИЙН ХАРЬЦАА**",
            value=f"```yaml\n{self.player1.display_name}: {self.player1_score}\n{self.player2.display_name}: {self.player2_score}```",
            inline=False
        )
        embed.add_field(name="💰 **БООЦОО**", value=f"```fix\n{self.bet_amount:,} мөнгө```", inline=False)

        if self.round_results:
            results_text = ""
            for i, result in enumerate(self.round_results[-2:], max(1, len(self.round_results)-1)):
                results_text += f"**Раунд {i}:** {result[:80]}...\n"
            embed.add_field(name="📜 **СҮҮЛЧИЙН РАУНДУУД**", value=results_text, inline=False)

        status = ""
        status += f"✅ {self.player1.display_name} сонголтоо хийсэн\n" if self.player1_ready else f"⏳ {self.player1.display_name} хүлээж байна...\n"
        status += f"✅ {self.player2.display_name} сонголтоо хийсэн" if self.player2_ready else f"⏳ {self.player2.display_name} хүлээж байна..."
        embed.add_field(name="📌 **ТӨЛӨВ**", value=f"```ini\n{status}```", inline=False)
        embed.set_footer(text="Доорх товчлуураас сонголтоо хийгээрэй! (30 секунд)")
        return embed

    def cancel_timer(self):
        if self._round_timer:
            self._round_timer.cancel()
            self._round_timer = None

    async def start_round_timer(self):
        self.cancel_timer()
        async def timeout():
            await asyncio.sleep(30)
            if self.game_active and self.round_active and not (self.player1_ready and self.player2_ready):
                await self.timeout_round()
        self._round_timer = asyncio.create_task(timeout())

    async def timeout_round(self):
        if not self.round_active:
            return
        self.round_active = False
        self.cancel_timer()
        await self.disable_all_buttons()
        guild_id = self.channel.guild.id
        economy = self.bot.get_cog("Economy")

        # Ялагдагчийг тодорхойлох
        if not self.player1_ready and not self.player2_ready:
            # хоёул хариулаагүй -> тэнцээ, мөнгө буцах
            embed = discord.Embed(
                title="⏰ **ХУГАЦАА ДУУССАН!**",
                description=f"{self.player1.mention} болон {self.player2.mention} аль аль нь хариулаагүй!\nТоглоом хүчингүй болж, мөнгө буцаагдлаа.",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"{self.channel.guild.name}")
            if economy:
                await economy.update_balance(self.player1.id, guild_id, self.bet_amount)
                await economy.update_balance(self.player2.id, guild_id, self.bet_amount)
            self.game_active = False
        elif not self.player1_ready:
            # 1-р тоглогч цагаа хэтрүүлсэн -> 2-р тоглогч раунд хожив
            self.player2_score += 1
            embed = discord.Embed(
                title="⏰ **ХУГАЦАА ДУУССАН!**",
                description=f"{self.player1.mention} хариулаагүй тул **{self.player2.mention}** энэ раундыг хожлоо!",
                color=WARNING_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"{self.channel.guild.name}")
        else:
            # 2-р тоглогч цагаа хэтрүүлсэн
            self.player1_score += 1
            embed = discord.Embed(
                title="⏰ **ХУГАЦАА ДУУССАН!**",
                description=f"{self.player2.mention} хариулаагүй тул **{self.player1.mention}** энэ раундыг хожлоо!",
                color=WARNING_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"{self.channel.guild.name}")

        await self.channel.send(embed=embed)
        # Дараагийн раунд эсвэл тоглоомын төгсгөл
        if self.game_active:
            if self.current_round >= 3:
                await self.end_game()
            else:
                self.current_round += 1
                await self.start_next_round()
        else:
            await self.end_game()

    async def _give_xp(self, user_id, guild_id, amount):
        leveling = self.bot.get_cog("Leveling")
        if leveling:
            try:
                await leveling.add_xp(user_id, guild_id, amount, check_mute=False)
            except:
                pass

    async def process_round(self):
        if not self.game_active:
            return
        p1 = self.player1_choice
        p2 = self.player2_choice

        if p1 == p2:
            result_text = f"⚖️ **ТЭНЦЭЭ!** {self.player1.display_name} ({self.get_choice_mongol(p1)}) vs {self.player2.display_name} ({self.get_choice_mongol(p2)})"
            color = EMBED_COLOR
        elif p1 == "attack" and p2 == "defend":
            result_text = f"⚔️ **ДОВТОЛГОО АМЖИЛТТАЙ!** {self.player1.display_name} → {self.player2.display_name}\n`{self.player1.display_name}` +1 оноо!"
            self.player1_score += 1
            color = SUCCESS_COLOR
        elif p1 == "defend" and p2 == "attack":
            result_text = f"⚔️ **ДОВТОЛГОО АМЖИЛТТАЙ!** {self.player2.display_name} → {self.player1.display_name}\n`{self.player2.display_name}` +1 оноо!"
            self.player2_score += 1
            color = SUCCESS_COLOR
        elif p1 == "stealth" and p2 == "defend":
            result_text = f"🗡️ **НУУЦ ДОВТОЛГОО!** {self.player1.display_name} нууцаар довтолж, хамгаалалтыг нэвтрүүллээ!\n`{self.player1.display_name}` +1 оноо!"
            self.player1_score += 1
            color = PURPLE_COLOR
        elif p1 == "defend" and p2 == "stealth":
            result_text = f"🗡️ **НУУЦ ДОВТОЛГОО!** {self.player2.display_name} нууцаар довтолж, хамгаалалтыг нэвтрүүллээ!\n`{self.player2.display_name}` +1 оноо!"
            self.player2_score += 1
            color = PURPLE_COLOR
        elif (p1 == "stealth" and p2 == "attack") or (p1 == "attack" and p2 == "stealth"):
            result_text = f"⚔️ **СЭРҮҮЛЭГ ДОВТОЛГООНУУД!** Хоёул довтолсон тул тэнцээ!"
            color = WARNING_COLOR
        else:
            result_text = "⚠️ Алдаа гарлаа"
            color = ERROR_COLOR

        self.round_results.append(result_text)

        result_embed = discord.Embed(
            title=f"⚔️ **РАУНД {self.current_round} ДУУСЛАА!**",
            description=f"```yaml\n{result_text}```",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        result_embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
        result_embed.add_field(
            name="📊 **ОДООГИЙН ХАРЬЦАА**",
            value=f"```css\n{self.player1.display_name}: {self.player1_score}  |  {self.player2.display_name}: {self.player2_score}```",
            inline=False
        )
        result_embed.set_footer(text=f"{self.channel.guild.name}")
        await self.channel.send(embed=result_embed)

        self.current_round += 1
        if self.current_round > 3:
            await self.end_game()
        else:
            await self.start_next_round()

    def get_choice_mongol(self, choice):
        choices = {"attack": "⚔️ Довтолгоо", "defend": "🛡️ Хамгаалалт", "stealth": "🗡️ Нууц довтолгоо"}
        return choices.get(choice, "❓ Тодорхойгүй")

    async def check_round_complete(self):
        if self.player1_ready and self.player2_ready and self.round_active and self.game_active:
            self.round_active = False
            self.cancel_timer()
            for item in self.children:
                item.disabled = True
            if self.message:
                try:
                    await self.message.edit(view=self)
                except:
                    pass
            await self.process_round()

    async def start_next_round(self):
        self.player1_choice = None
        self.player2_choice = None
        self.player1_ready = False
        self.player2_ready = False
        for item in self.children:
            item.disabled = False
        embed = await self.send_round_embed()
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except:
                pass
        self.round_active = True
        await self.start_round_timer()

    async def end_game(self):
        self.game_active = False
        self.round_active = False
        self.cancel_timer()
        await self.disable_all_buttons()
        economy = self.bot.get_cog("Economy")
        games_cog = self.bot.get_cog("Games")
        guild_id = self.channel.guild.id

        if self.player1_score > self.player2_score:
            winner, loser, winner_score, loser_score = self.player1, self.player2, self.player1_score, self.player2_score
        elif self.player2_score > self.player1_score:
            winner, loser, winner_score, loser_score = self.player2, self.player1, self.player2_score, self.player1_score
        else:
            embed = discord.Embed(
                title="⚖️ **ТЭНЦЭЭ!**",
                description=f"{self.player1.mention} vs {self.player2.mention}\n{self.player1_score} : {self.player2_score}",
                color=EMBED_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"{self.channel.guild.name}")
            if economy:
                await economy.update_balance(self.player1.id, guild_id, self.bet_amount)
                await economy.update_balance(self.player2.id, guild_id, self.bet_amount)
            await self.channel.send(embed=embed)
            return

        total_win = self.bet_amount * 2
        bonus_percent = 10
        bonus = int(total_win * bonus_percent / 100)
        total_win += bonus

        embed = discord.Embed(
            title="🏆 **ЯЛАЛТ!** 🏆",
            description=f"**{winner.mention}** ялалт байгууллаа! 🎉",
            color=NEON_YELLOW,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=winner.display_avatar.url)
        embed.add_field(
            name="📊 **ЭЦСИЙН ХАРЬЦАА**",
            value=f"```css\n{winner.display_name}: {winner_score}  |  {loser.display_name}: {loser_score}```",
            inline=False
        )
        embed.add_field(
            name="💰 **ШАГНАЛ**",
            value=f"```diff\n+ {total_win:,} мөнгө ({bonus_percent}% бонус)```",
            inline=False
        )
        embed.set_footer(text=f"{self.channel.guild.name}")
        if economy:
            await economy.update_balance(winner.id, guild_id, total_win)
        await self._give_xp(winner.id, guild_id, 15)
        await self._give_xp(loser.id, guild_id, 5)

        if games_cog:
            try:
                await games_cog.update_stats(winner.id, guild_id, True, self.bet_amount, total_win)
                await games_cog.update_stats(loser.id, guild_id, False, self.bet_amount, 0)
            except:
                pass

        await self.channel.send(embed=embed)

    @discord.ui.button(label="⚔️ ДОВТОЛГОО", style=discord.ButtonStyle.danger, row=0, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: Button):
        await self._handle_choice(interaction, "attack")

    @discord.ui.button(label="🛡️ ХАМГААЛАЛТ", style=discord.ButtonStyle.success, row=0, emoji="🛡️")
    async def defend_button(self, interaction: discord.Interaction, button: Button):
        await self._handle_choice(interaction, "defend")

    @discord.ui.button(label="🗡️ НУУЦ ДОВТОЛГОО", style=discord.ButtonStyle.secondary, row=0, emoji="🗡️")
    async def stealth_button(self, interaction: discord.Interaction, button: Button):
        await self._handle_choice(interaction, "stealth")

    async def _handle_choice(self, interaction: discord.Interaction, choice: str):
        if not self.game_active or not self.round_active:
            return await interaction.response.send_message("❌ Тоглоом дууссан эсвэл раунд идэвхтэй биш.", ephemeral=True)
        if interaction.user.id not in [self.player1.id, self.player2.id]:
            return await interaction.response.send_message("❌ Энэ тоглоом таных биш!", ephemeral=True)

        if interaction.user.id == self.player1.id and not self.player1_ready:
            self.player1_choice = choice
            self.player1_ready = True
            await interaction.response.send_message(f"✅ Та **{self.get_choice_mongol(choice)}** сонголоо!", ephemeral=True)
        elif interaction.user.id == self.player2.id and not self.player2_ready:
            self.player2_choice = choice
            self.player2_ready = True
            await interaction.response.send_message(f"✅ Та **{self.get_choice_mongol(choice)}** сонголоо!", ephemeral=True)
        else:
            return await interaction.response.send_message("❌ Та сонголтоо аль хэдийн хийсэн.", ephemeral=True)

        if self.message:
            try:
                await self.message.edit(embed=await self.send_round_embed())
            except:
                pass
        await self.check_round_complete()


# ==================== PVP COG ====================
class PVP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.init_cooldown_table()

    async def init_cooldown_table(self):
        """SQLite pvp_cooldowns хүснэгт үүсгэх"""
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS pvp_cooldowns (
                guild_id TEXT,
                user_id TEXT,
                last_used INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')

    async def check_cooldown(self, guild_id, user_id):
        row = await self.bot.db.fetchone(
            "SELECT last_used FROM pvp_cooldowns WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        if not row:
            return 0
        last = row[0]
        now = int(time.time())
        if now - last < PVP_COOLDOWN:
            return int(PVP_COOLDOWN - (now - last))
        return 0

    async def set_cooldown(self, guild_id, user_id):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO pvp_cooldowns (guild_id, user_id, last_used) VALUES (?, ?, ?)",
            str(guild_id), str(user_id), int(time.time())
        )

    async def resolve_amount(self, ctx, amount_str, economy_cog):
        if amount_str.lower() == 'all':
            bal = await economy_cog.get_balance(ctx.author.id, ctx.guild.id)
            if bal <= 0:
                return None, "Танд мөнгө байхгүй байна!"
            return bal, None
        try:
            amt = int(amount_str)
            if amt <= 0:
                return None, "Дүн эерэг байх ёстой!"
            return amt, None
        except ValueError:
            return None, "Дүн нь тоо эсвэл 'all' байх ёстой!"

    # ==================== PVP / DUEL ====================
    @commands.command(name='pvp', aliases=['duel', 'тулаан', 'fight'], with_app_command=True,
                             description="Хэрэглэгчтэй тулаан хийх")
    @app_commands.describe(
        opponent="Тулалдах хэрэглэгч",
        amount="Бооцооны дүн (тоо эсвэл 'all')"
    )
    async def pvp(self, ctx, opponent: discord.Member, amount: str = None):
        if amount is None:
            embed = discord.Embed(
                title="❌ АЛДАА!",
                description="Зөв хэлбэр: `!pvp @хэрэглэгч <бооцооны дүн/all>`",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="📌 ЖИШЭЭ", value="`!pvp @Bold 100`\n`!pvp @Bold all`", inline=False)
            embed.add_field(
                name="📜 ДҮРЭМ",
                value="⚔️ Довтолгоо → Хамгаалалтыг эвдэнэ\n🛡️ Хамгаалалт → Довтолгоог хаана\n🗡️ Нууц довтолгоо → Хамгаалалтыг нэвтрүүлэх",
                inline=False
            )
            embed.set_footer(text="Тоглогч бүр 2 минут тутамд 1 удаа тоглох боломжтой")
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)

        economy = self.bot.get_cog("Economy")
        if not economy:
            return await ctx.send(embed=discord.Embed(
                title="❌ АЛДАА",
                description="Эдийн засгийн систем ажиллахгүй байна!",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            ))

        if opponent.id == ctx.author.id or opponent.bot:
            return await ctx.send(embed=discord.Embed(
                title="❌ АЛДАА",
                description="Буруу хэрэглэгч.",
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            ))

        cd1 = await self.check_cooldown(ctx.guild.id, ctx.author.id)
        cd2 = await self.check_cooldown(ctx.guild.id, opponent.id)
        if cd1:
            m, s = divmod(cd1, 60)
            return await ctx.send(f"⏳ {ctx.author.mention} дараагийн тулаан хүртэл **{m} мин {s} сек** хүлээх хэрэгтэй!")
        if cd2:
            m, s = divmod(cd2, 60)
            return await ctx.send(f"⏳ {opponent.mention} дараагийн тулаан хүртэл **{m} мин {s} сек** хүлээх хэрэгтэй!")

        amt, err = await self.resolve_amount(ctx, amount, economy)
        if err:
            return await ctx.send(embed=discord.Embed(
                title="❌ АЛДАА",
                description=err,
                color=ERROR_COLOR,
                timestamp=discord.utils.utcnow()
            ))

        await economy.ensure_user(ctx.author.id, ctx.guild.id)
        await economy.ensure_user(opponent.id, ctx.guild.id)

        bal1 = await economy.get_balance(ctx.author.id, ctx.guild.id)
        bal2 = await economy.get_balance(opponent.id, ctx.guild.id)

        if bal1 < amt:
            return await ctx.send(f"❌ {ctx.author.mention} танд **{amt:,}** мөнгө байхгүй! (Үлдэгдэл: {bal1:,}₮)")
        if bal2 < amt:
            return await ctx.send(f"❌ {opponent.mention} танд **{amt:,}** мөнгө байхгүй! (Үлдэгдэл: {bal2:,}₮)")

        class DuelAcceptView(View):
            def __init__(self, cog, challenger, opponent, amount, channel):
                super().__init__(timeout=30)
                self.cog = cog
                self.challenger = challenger
                self.opponent = opponent
                self.amount = amount
                self.channel = channel
                self.accepted = False
                self.message = None

            async def disable_all_buttons(self):
                for item in self.children:
                    item.disabled = True
                if self.message:
                    try:
                        await self.message.edit(view=self)
                    except:
                        pass

            @discord.ui.button(label="✅ ЗӨВШӨӨРӨХ", style=discord.ButtonStyle.success)
            async def accept_button(self, interaction: discord.Interaction, button: Button):
                if interaction.user != self.opponent:
                    return await interaction.response.send_message("❌ Энэ урилга танд зориулагдаагүй!", ephemeral=True)
                self.accepted = True
                await self.disable_all_buttons()
                await self.start_duel(interaction)

            @discord.ui.button(label="❌ ТАТГАЛЗАХ", style=discord.ButtonStyle.danger)
            async def decline_button(self, interaction: discord.Interaction, button: Button):
                if interaction.user != self.opponent:
                    return await interaction.response.send_message("❌ Энэ урилга танд зориулагдаагүй!", ephemeral=True)
                embed = discord.Embed(
                    title="❌ ТАТГАЛЗСАН",
                    description=f"{self.opponent.mention} тулааны урилгаас татгалзлаа.",
                    color=ERROR_COLOR,
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text=f"{self.channel.guild.name}")
                await interaction.response.edit_message(embed=embed, view=None)
                self.stop()

            async def start_duel(self, interaction):
                await self.cog.set_cooldown(interaction.guild_id, self.challenger.id)
                await self.cog.set_cooldown(interaction.guild_id, self.opponent.id)

                economy_cog = self.cog.bot.get_cog("Economy")
                if economy_cog:
                    await economy_cog.update_balance(self.challenger.id, interaction.guild_id, -self.amount)
                    await economy_cog.update_balance(self.opponent.id, interaction.guild_id, -self.amount)

                embed = discord.Embed(
                    title="⚔️ ТУЛААН ЭХЭЛЛЭЭ! ⚔️",
                    description=f"{self.challenger.mention} vs {self.opponent.mention}\nБооцоо: **{self.amount:,}** мөнгө\n3 раундын тулаан эхэллээ!",
                    color=GOLD_COLOR,
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text=f"{self.channel.guild.name}")
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
                await self.channel.send(embed=embed)

                view = PVPView(self.cog.bot, self.channel, self.challenger, self.opponent, self.amount)
                round_embed = await view.send_round_embed()
                view.message = await self.channel.send(embed=round_embed, view=view)
                view.round_active = True
                await view.start_round_timer()

            async def on_timeout(self):
                if not self.accepted:
                    embed = discord.Embed(
                        title="⏰ ХУГАЦАА ДУУССАН",
                        description=f"{self.opponent.mention} тулааны урилгыг хүлээж аваагүй тул хүчингүй боллоо.",
                        color=WARNING_COLOR,
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_footer(text=f"{self.channel.guild.name}")
                    if self.message:
                        try:
                            await self.message.edit(embed=embed, view=None)
                        except:
                            pass

        embed = discord.Embed(
            title="⚔️ ТУЛААНЫ УРИЛГА ⚔️",
            description=f"{ctx.author.mention} {opponent.mention} -г **{amt:,} мөнгө** бооцоотой **3 раунд** тулаанд урила!",
            color=PURPLE_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(
            name="📜 ДҮРЭМ",
            value="⚔️ Довтолгоо → Хамгаалалтыг эвдэнэ\n🛡️ Хамгаалалт → Довтолгоог хаана\n🗡️ Нууц довтолгоо → Хамгаалалтыг нэвтрүүлнэ",
            inline=False
        )
        embed.set_footer(text="30 секундын дотор зөвшөөрөх эсвэл татгалзах товчийг дарна уу!")

        view = DuelAcceptView(self, ctx.author, opponent, amt, ctx.channel)
        msg = await ctx.send(content=opponent.mention, embed=embed, view=view)
        view.message = msg


async def setup(bot):
    await bot.add_cog(PVP(bot))