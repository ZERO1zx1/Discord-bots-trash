import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import time
import asyncio
from datetime import datetime, timezone

# ===== COLORS =====
EMBED_COLOR      = 0x1e1e2f
ERROR_COLOR      = 0xf38ba8
SUCCESS_COLOR    = 0xa6e3a1
WARNING_COLOR    = 0xf9e2af
GOLD_COLOR       = 0xfab387
PURPLE_COLOR     = 0xcba6f7
INFO_COLOR       = 0x89b4fa
NEON_PINK        = 0xFF10F0   
NEON_GREEN       = 0x39FF14
NEON_YELLOW      = 0xCCFF00

ROB_COOLDOWN     = 3600
HACK_COOLDOWN    = 7200
GIVE_COOLDOWN    = 86400

rob_cooldowns    = {}
hack_cooldowns   = {}
give_cooldowns   = {}

GEM_RING_IDS     = [36, 37, 38, 39, 40, 41, 42]

class BlackjackView(View):
    def __init__(self, ctx, casino_cog, bet):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.casino = casino_cog
        self.original_bet = bet
        self.bet = bet
        self.dealer_cards = [self.draw_card() for _ in range(2)]
        self.hands = [[self.draw_card() for _ in range(2)]]
        self.active_hand_index = 0
        self.game_over = False
        self.all_hands_resolved = False
        self.message = None
        self.update_embed()
        # Товчлуурын анхны төлвийг async task-ээр тохируулна (хурдан идэвхжинэ)
        asyncio.create_task(self._init_buttons())

    async def _init_buttons(self):
        # Эхний товчлуурын төлвийг тогтоох
        await self._update_buttons()
        # Хэрэв мессеж хадгалагдсан бол шинэчлэх (энэ үед message = None байх тул засвар хийхгүй)
        if self.message:
            await self.message.edit(embed=self.embed, view=self)

    def draw_card(self):
        suits = ["♥️", "♦️", "♣️", "♠️"]
        values = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
        suit = random.choice(suits)
        val = random.choice(values)
        display = f"{suit}A" if val == 11 else f"{suit}{val}"
        return {"value": val, "display": display, "suit": suit, "rank": val if val != 11 else 1}

    @staticmethod
    def card_rank(card):
        """Картын хуваах үеийн зэрэглэл: 2-9 тоо, 10/J/Q/K бүгд 10, A 11"""
        val = card["value"]
        if val == 11:
            return 11  # A
        elif val == 10:
            return 10
        else:
            return val

    def hand_value(self, cards):
        total = sum(c["value"] for c in cards)
        aces = sum(1 for c in cards if c["value"] == 11)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def update_embed(self):
        embed = discord.Embed(
            title="🃏 **BLACKJACK**",
            color=GOLD_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url)
        active_hand = self.hands[self.active_hand_index]
        player_val = self.hand_value(active_hand)
        player_display = " | ".join(c["display"] for c in active_hand)

        if self.game_over or self.all_hands_resolved:
            dealer_display = " | ".join(c["display"] for c in self.dealer_cards)
            dealer_val = self.hand_value(self.dealer_cards)
        else:
            dealer_display = f"{self.dealer_cards[0]['display']} | 🃟"
            dealer_val = "?"

        embed.add_field(name="🎴 ТАНЫ КАРТ", value=f"```yaml\n{player_display} = {player_val}```", inline=False)
        embed.add_field(name="🃟 ДИЛЕР", value=f"```yaml\n{dealer_display} = {dealer_val}```", inline=False)

        if len(self.hands) > 1:
            hand_status = []
            for i, hand in enumerate(self.hands):
                if i == self.active_hand_index:
                    hand_status.append(f"👉 Гар {i+1} (идэвхтэй): {self.hand_value(hand)}")
                else:
                    status = "тоглож байна" if not self.all_hands_resolved else f"үр дүн: {self.hand_value(hand)}"
                    hand_status.append(f"✋ Гар {i+1}: {self.hand_value(hand)}")
            embed.add_field(name="🤲 ХУВААСАН ГАРУУД", value="\n".join(hand_status), inline=False)

        embed.description = f"💰 **Бооцоо:** {self.bet:,}₮"
        self.embed = embed

    async def _update_buttons(self):
        """Товчлууруудыг одоогийн төлөвт тохируулна (async)."""
        if self.game_over or self.all_hands_resolved:
            for child in self.children:
                child.disabled = True
            return

        active_hand = self.hands[self.active_hand_index]
        hand_val = self.hand_value(active_hand)

        self.hit_button.disabled = (hand_val > 21)
        self.stand_button.disabled = False

        # Double Down шалгах
        can_double = (len(active_hand) == 2 and 
                      not self.all_hands_resolved and 
                      len(self.hands) == 1)
        if can_double:
            economy = self.ctx.bot.get_cog("Economy")
            if economy:
                bal = await economy.get_balance(self.ctx.author.id, self.ctx.guild.id)
                can_double = bal >= self.original_bet
        self.double_down_button.disabled = not can_double

        # Split шалгах
        can_split = (len(self.hands) == 1 and len(active_hand) == 2 and 
                     self.card_rank(active_hand[0]) == self.card_rank(active_hand[1]))
        if can_split:
            economy = self.ctx.bot.get_cog("Economy")
            if economy:
                bal = await economy.get_balance(self.ctx.author.id, self.ctx.guild.id)
                can_split = bal >= self.original_bet
        self.split_button.disabled = not can_split

    async def double_down(self, interaction):
        economy = self.ctx.bot.get_cog("Economy")
        if not economy: return
        await economy.update_balance(self.ctx.author.id, self.ctx.guild.id, -self.original_bet)
        self.bet = self.original_bet * 2
        active_hand = self.hands[self.active_hand_index]
        active_hand.append(self.draw_card())
        await self.stand(interaction, from_double=True)

    async def split_hand(self, interaction):
        economy = self.ctx.bot.get_cog("Economy")
        if not economy: return
        await economy.update_balance(self.ctx.author.id, self.ctx.guild.id, -self.original_bet)
        self.bet = self.original_bet * 2 

        first_hand = self.hands[0]
        card1, card2 = first_hand[0], first_hand[1]
        self.hands = [[card1], [card2]]
        for hand in self.hands:
            hand.append(self.draw_card())
        self.active_hand_index = 0

        await self._update_buttons()
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    async def finalize_game(self, interaction):
        self.game_over = True
        self.all_hands_resolved = True
        for child in self.children: child.disabled = True

        dealer_val = self.hand_value(self.dealer_cards)
        while dealer_val < 17:
            self.dealer_cards.append(self.draw_card())
            dealer_val = self.hand_value(self.dealer_cards)

        total_win = 0
        bonus_percent = self.ctx.bot.config.get("bonus_percent", 10)
        results_text = []
        for i, hand in enumerate(self.hands):
            player_val = self.hand_value(hand)
            if player_val > 21:
                outcome = f"Гар {i+1}: 💥 BUST ({player_val})"
                win = -self.original_bet
            elif dealer_val > 21:
                outcome = f"Гар {i+1}: 🎉 Дилер BUST ({dealer_val}) - ЯЛАЛТ!"
                win = self.original_bet
            elif player_val > dealer_val:
                outcome = f"Гар {i+1}: 🏆 ЯЛЛАА ({player_val} vs {dealer_val})"
                win = self.original_bet
            elif player_val < dealer_val:
                outcome = f"Гар {i+1}: 😞 ЯЛАГДАЛ ({player_val} vs {dealer_val})"
                win = -self.original_bet
            else:
                outcome = f"Гар {i+1}: 🤝 ТЭНЦСЭН ({player_val} vs {dealer_val})"
                win = 0

            bonus = int(win * bonus_percent / 100) if win > 0 else 0
            win_with_bonus = win + bonus
            total_win += win_with_bonus
            bonus_text = f" (+{bonus:,} бонус)" if bonus else ""
            results_text.append(f"{outcome} → **{win_with_bonus:+,}₮**{bonus_text}")

            if win > 0:
                await self.casino.update_game_stats(self.ctx.author.id, self.ctx.guild.id, True, self.original_bet, win_with_bonus)
                await self.casino.try_give_gem_ring(self.ctx.author.id, self.ctx.guild.id, self.ctx.channel, self.ctx.author.mention)
            elif win < 0:
                await self.casino.update_game_stats(self.ctx.author.id, self.ctx.guild.id, False, self.original_bet, -win)

        economy = self.ctx.bot.get_cog("Economy")
        if economy:
            await economy.update_balance(self.ctx.author.id, self.ctx.guild.id, total_win)

        embed = discord.Embed(
            title="🃏 **BLACKJACK - ҮР ДҮН**",
            color=SUCCESS_COLOR if total_win >= 0 else ERROR_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url)
        dealer_display = " | ".join(c["display"] for c in self.dealer_cards)
        embed.add_field(name="🃟 ДИЛЕР", value=f"```yaml\n{dealer_display} = {dealer_val}```", inline=False)
        embed.add_field(name="📋 ДҮН", value="\n".join(results_text), inline=False)
        embed.description = f"💰 **Нийт хожил/гарз:** {total_win:+,}₮"
        embed.set_footer(text="🃏 Тоглоом дууслаа")
        await interaction.response.edit_message(embed=embed, view=self)

    async def hit(self, interaction):
        active_hand = self.hands[self.active_hand_index]
        active_hand.append(self.draw_card())
        if self.hand_value(active_hand) > 21:
            self._next_hand_or_finish(interaction)
        else:
            await self._update_buttons()
            self.update_embed()
            await interaction.response.edit_message(embed=self.embed, view=self)

    async def stand(self, interaction, from_double=False):
        if not from_double:
            self._next_hand_or_finish(interaction)
        else:
            self._next_hand_or_finish(interaction)

    def _next_hand_or_finish(self, interaction):
        if self.active_hand_index < len(self.hands) - 1:
            self.active_hand_index += 1
            asyncio.create_task(self._after_hand_switch(interaction))
        else:
            asyncio.create_task(self.finalize_game(interaction))

    async def _after_hand_switch(self, interaction):
        await self._update_buttons()
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    # ---------- Товчлуурууд ----------
    @discord.ui.button(label="🃏 Hit", style=discord.ButtonStyle.primary, row=0)
    async def hit_button(self, interaction: discord.Interaction, button: Button):
        if self.game_over or self.all_hands_resolved:
            return await interaction.response.send_message("Тоглоом дууссан.", ephemeral=True)
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Энэ тоглоом таных биш!", ephemeral=True)
        await self.hit(interaction)

    @discord.ui.button(label="🛑 Stand", style=discord.ButtonStyle.danger, row=0)
    async def stand_button(self, interaction: discord.Interaction, button: Button):
        if self.game_over or self.all_hands_resolved:
            return await interaction.response.send_message("Тоглоом дууссан.", ephemeral=True)
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Таных биш!", ephemeral=True)
        await self.stand(interaction)

    @discord.ui.button(label="⏫ Double Down", style=discord.ButtonStyle.success, row=1)
    async def double_down_button(self, interaction: discord.Interaction, button: Button):
        if self.game_over or self.all_hands_resolved:
            return await interaction.response.send_message("Тоглоом дууссан.", ephemeral=True)
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Таных биш!", ephemeral=True)
        if len(self.hands[self.active_hand_index]) != 2:
            return await interaction.response.send_message("Double Down зөвхөн эхний хоёр картанд хийгдэнэ.", ephemeral=True)
        await self.double_down(interaction)

    @discord.ui.button(label="✂️ Split", style=discord.ButtonStyle.secondary, row=1)
    async def split_button(self, interaction: discord.Interaction, button: Button):
        if self.game_over or self.all_hands_resolved:
            return await interaction.response.send_message("Тоглоом дууссан.", ephemeral=True)
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Таных биш!", ephemeral=True)
        if len(self.hands) != 1 or len(self.hands[0]) != 2:
            return await interaction.response.send_message("Split зөвхөн эхний хоёр картанд хийгдэнэ.", ephemeral=True)
        if self.card_rank(self.hands[0][0]) != self.card_rank(self.hands[0][1]):
            return await interaction.response.send_message("Картуудын зэрэглэл ижил биш байна.", ephemeral=True)
        await self.split_hand(interaction)

    @discord.ui.button(label="❓ Тусламж", style=discord.ButtonStyle.gray, disabled=True, row=2)
    async def help_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "🃏 **BLACKJACK ТУХАЙ** 🃏\n\n"
            "🎴 **ЗОРИЛГО:** 21-д ойртох, гэхдээ хэтрүүлэхгүй.\n\n"
            "🔹 **Hit** – Нэмэлт карт авах\n"
            "🔹 **Stand** – Одоо байгаа картаараа тоглох\n"
            "🔹 **Double Down** – Бооцоогоо 2х нэмээд, ганц карт аваад зогсох\n"
            "🔹 **Split** – Хэрэв эхний хоёр карт ижил зэрэглэлтэй бол (жишээ нь, 8-8, 10-10) хоёр тусдаа гар болгон хувааж, тус бүрт нэмэлт карт тараана. Бооцоо давхарлана.\n\n"
            "💡 **Картны үнэ:** A=1/11, 2-10=нэрлэсэн, J/Q/K=10\n\n"
            "⏳ Дилер 17 хүрэх хүртэл карт татна.",
            ephemeral=True
        )

    async def on_timeout(self):
        if not self.game_over and not self.all_hands_resolved:
            self.game_over = True
            for child in self.children: child.disabled = True
            embed = discord.Embed(
                title="⏰ ХУГАЦАА ДУУССАН",
                description="Тоглоом хүчингүй. Бооцоо буцаагдлаа.",
                color=WARNING_COLOR
            )
            economy = self.ctx.bot.get_cog("Economy")
            if economy: await economy.update_balance(self.ctx.author.id, self.ctx.guild.id, self.original_bet)
            if self.message: await self.message.edit(embed=embed, view=self)
            self.stop()

class HighLowView(View):
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
        self.amount = amount
        self.message = None

    async def on_timeout(self):
        for child in self.children: child.disabled = True
        if self.message: await self.message.edit(view=self)

    @discord.ui.button(label="📈 HIGHER", style=discord.ButtonStyle.success)
    async def higher_button(self, interaction, button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Таных биш!", ephemeral=True)
        await self.cog.highlow_game(self.ctx, self.amount, "higher")
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="📉 LOWER", style=discord.ButtonStyle.danger)
    async def lower_button(self, interaction, button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Таных биш!", ephemeral=True)
        await self.cog.highlow_game(self.ctx, self.amount, "lower")
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="❓ Тусламж", style=discord.ButtonStyle.secondary, disabled=True)
    async def help_button(self, interaction, button):
        await interaction.response.send_message(
            "🎲 **HIGH-LOW ТУХАЙ** 🎲\n\n"
            "1️⃣ 1-100 хүртэл санамсаргүй тоо гарна.\n"
            "2️⃣ Та дараагийн тоо өмнөхөөсөө өндөр эсвэл доогуур байхыг таах хэрэгтэй.\n"
            "3️⃣ Зөв тааварлавал бооцооны мөнгө хоёр дахин өснө!\n"
            "4️⃣ Буруу тааварлавал бооцоо алдагдана.\n\n"
            "🍔 Тоглоомын өмнө өлсөж болохгүй! `geat` командаар хоол идээрэй.\n"
            "😡 Ууртай үед тоглох боломжгүй! `grelax` командаар амраарай.",
            ephemeral=True
        )    

class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def init_db(self):
        """SQLite хүснэгт үүсгэх"""
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS game_stats (
                user_id TEXT, guild_id TEXT,
                wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0, total_bet INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        await self.bot.db.commit()

    async def cog_load(self):
        await self.init_db()

    async def update_game_stats(self, user_id, guild_id, won, bet, win_amt):
        """Тоглогчийн статистикийг шинэчлэх (SQLite, commit-тэй)"""
        row = await self.bot.db.fetchone(
            "SELECT 1 FROM game_stats WHERE user_id=? AND guild_id=?",
            str(user_id), str(guild_id)
        )
        if not row:
            await self.bot.db.execute(
                "INSERT INTO game_stats (user_id, guild_id, wins, losses, total_won, total_bet) VALUES (?,?,0,0,0,0)",
                str(user_id), str(guild_id)
            )
            await self.bot.db.commit()
        if won:
            await self.bot.db.execute(
                "UPDATE game_stats SET wins = wins + 1, total_won = total_won + ?, total_bet = total_bet + ? WHERE user_id=? AND guild_id=?",
                win_amt, bet, str(user_id), str(guild_id)
            )
        else:
            await self.bot.db.execute(
                "UPDATE game_stats SET losses = losses + 1, total_bet = total_bet + ? WHERE user_id=? AND guild_id=?",
                bet, str(user_id), str(guild_id)
            )
        await self.bot.db.commit()

    async def try_give_gem_ring(self, user_id, guild_id, channel, mention):
        """Ховор тохиолдолд gem ring өгөх"""
        if random.randint(1, 100) <= random.randint(5, 10):
            shop_cog = self.bot.get_cog("ShopCog")
            if shop_cog:
                ring_id = random.choice(GEM_RING_IDS)
                await shop_cog.add_item(user_id, guild_id, ring_id, 1)
                await channel.send(f"💎 Сонирхолтой! {mention} -д ховор **Gem Ring** бэлэглэлээ!")

    async def get_cooldown(self, cd_dict, user_id, limit):
        last = cd_dict.get(str(user_id), 0)
        now = time.time()
        if now - last < limit:
            return int(limit - (now - last))
        return 0

    async def set_cooldown(self, cd_dict, user_id):
        cd_dict[str(user_id)] = time.time()

    async def resolve_amount(self, ctx, amount_str):
        economy = self.bot.get_cog("Economy")
        if not economy: return None, "Эдийн засгийн систем ажиллахгүй байна!"
        if amount_str.lower() == 'all':
            bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
            if bal <= 0: return None, "Танд мөнгө байхгүй."
            return bal, None
        try:
            amt = int(amount_str)
            if amt <= 0: return None, "Дүн эерэг байх ёстой!"
            return amt, None
        except ValueError: return None, "Дүн нь тоо эсвэл 'all' байх ёстой!"

    async def check_hunger_mood(self, ctx):
        economy = self.bot.get_cog("Economy")
        if economy:
            hunger, mood = await economy.get_hunger_mood(ctx.author.id, ctx.guild.id)
            if hunger >= 80:
                await ctx.send(f"🍔 {ctx.author.mention}, та өлсөж байна! Тоглох тэнхээгүй. Эхлээд `geat` хийгээрэй.")
                return False
            if mood >= 80:
                await ctx.send(f"😡 {ctx.author.mention}, та ууртай байна! Тоглох боломжгүй. `grelax` амраарай.")
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

    # ---- High-Low тоглоомын туслах функц ----
    async def highlow_game(self, ctx, amount, choice):
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send("❌ Эдийн засаг ажиллахгүй байна!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд тоглох боломжгүй.")
        if amount <= 0: return await ctx.send("❌ Дүн эерэг байх ёстой!")
        first = random.randint(1, 100)
        second = random.randint(1, 100)
        win = (choice in ['higher','high'] and second > first) or (choice in ['lower','low'] and second < first)
        bonus_percent = self.bot.config.get("bonus_percent", 10)
        await self.add_hunger_mood(ctx, 5, 3)
        if win:
            total_win = amount + int(amount * bonus_percent / 100)
            await economy.update_balance(ctx.author.id, ctx.guild.id, total_win)
            await self.update_game_stats(ctx.author.id, ctx.guild.id, True, amount, total_win)
            embed = discord.Embed(
                title="🎉 ХОЖЛОО!",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.description = f"**Таны таамаглал:** {choice.upper()}\n\n🎲 Эхний тоо: **{first}** → Дараагийн тоо: **{second}**\n\n✨ **+{total_win:,}** ₮ нэмэгдлээ!"
        else:
            await economy.update_balance(ctx.author.id, ctx.guild.id, -amount)
            await self.update_game_stats(ctx.author.id, ctx.guild.id, False, amount, 0)
            embed = discord.Embed(
                title="😞 ХОЖИГДЛОО",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.description = f"**Таны таамаглал:** {choice.upper()}\n\n🎲 Эхний тоо: **{first}** → Дараагийн тоо: **{second}**\n\n💸 **-{amount:,}** ₮ хасагдлаа."
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="High-Low тоглоом")
        await ctx.send(embed=embed)

    # ==================== КОМАНДУУД ====================
    @commands.command(name='blackjack', aliases=['bj'])
    async def blackjack(self, ctx, amount_str: str):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send("❌ Эдийн засаг ажиллахгүй байна!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байхдаа тоглох боломжгүй.")
        amount, error = await self.resolve_amount(ctx, amount_str)
        if error: return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description=error, color=ERROR_COLOR))
        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount: return await ctx.send(f"❌ Танд {amount:,}₮ хүрэлцэхгүй!")
        await economy.update_balance(ctx.author.id, ctx.guild.id, -amount)
        await self.add_hunger_mood(ctx, 5, 3)
        view = BlackjackView(ctx, self, amount)
        view.message = await ctx.send(embed=view.embed, view=view)

    @commands.command(name='rob')
    async def rob(self, ctx, target: discord.Member):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send("❌ Эдийн засаг ажиллахгүй байна!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Та шоронд байна.")
        if target.id == ctx.author.id or target.bot: return await ctx.send("❌ Буруу хэрэглэгч.")
        guild_id = ctx.guild.id
        if await economy.is_bank_protected(target.id, guild_id):
            return await ctx.send(f"❌ {target.mention} банк хамгаалсан.")
        if await economy.get_balance(target.id, guild_id) <= 0:
            return await ctx.send(f"❌ {target.mention} -д мөнгөгүй.")
        cd = await self.get_cooldown(rob_cooldowns, ctx.author.id, ROB_COOLDOWN)
        if cd:
            m, s = divmod(cd, 60)
            return await ctx.send(f"⏳ Дараагийн дээрэм: {m}м {s}с")
        await self.set_cooldown(rob_cooldowns, ctx.author.id)
        await self.add_hunger_mood(ctx, 10, 5)
        success = random.random() < 0.3
        if success:
            steal = random.randint(1, min(5000, await economy.get_balance(target.id, guild_id)))
            await economy.update_balance(target.id, guild_id, -steal)
            await economy.update_balance(ctx.author.id, guild_id, steal)
            await self.update_game_stats(ctx.author.id, guild_id, True, steal, steal)
            embed = discord.Embed(
                title="🏆 ДЭЭРЭМЖ АМЖИЛТТАЙ!",
                description=f"Та **{target.mention}**-аас **{steal:,}** ₮ дээрэмдэж чадлаа!",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        else:
            fine = random.randint(100, 2000)
            await economy.update_balance(ctx.author.id, guild_id, -fine)
            await economy.set_prison(ctx.author.id, guild_id, hours=2)
            await self.update_game_stats(ctx.author.id, guild_id, False, fine, 0)
            embed = discord.Embed(
                title="🚨 БАРИГДЛАА!",
                description=f"🔒 Дээрэм бүтэлгүйтэж, **{fine:,}** ₮ торгууль төлөв.\n⏰ 2 цаг шоронд.",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="⏱️ Дараагийн дээрэм 1 цагийн дараа")
        await ctx.send(embed=embed)

    @commands.command(name='hack')
    async def hack(self, ctx, target: discord.Member):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send("❌ Эдийн засаг ажиллахгүй!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байна.")
        if target.id == ctx.author.id or target.bot: return await ctx.send("❌ Буруу хэрэглэгч.")
        cd = await self.get_cooldown(hack_cooldowns, ctx.author.id, HACK_COOLDOWN)
        if cd:
            h, m = divmod(cd, 3600)[0], (cd % 3600)//60
            return await ctx.send(f"⏳ Хакер хүртэл {h}ц {m}м")
        target_bank = await economy.get_bank(target.id, ctx.guild.id)
        target_bal = await economy.get_balance(target.id, ctx.guild.id)
        if target_bank + target_bal <= 0:
            return await ctx.send(f"💸 {target.mention} хоосон данс")
        success = random.random() < 0.3
        await self.set_cooldown(hack_cooldowns, ctx.author.id)
        await self.add_hunger_mood(ctx, 10, 5)
        bonus_percent = self.bot.config.get("bonus_percent", 10)
        if success:
            if target_bank > 0:
                max_steal = min(target_bank, int(target_bank * 0.35))
                hack_amt = random.randint(max(1, max_steal // 2), max(1, max_steal))
                await economy.update_bank(target.id, ctx.guild.id, -hack_amt)
            else:
                max_steal = min(target_bal, int(target_bal * 0.35))
                hack_amt = random.randint(max(1, max_steal // 2), max(1, max_steal))
                await economy.update_balance(target.id, ctx.guild.id, -hack_amt)
            bonus = int(hack_amt * bonus_percent / 100)
            hack_amt += bonus
            await economy.update_balance(ctx.author.id, ctx.guild.id, hack_amt)
            await self.update_game_stats(ctx.author.id, ctx.guild.id, True, hack_amt, hack_amt)
            embed = discord.Embed(
                title="💎 ХАКЕР АМЖИЛТТАЙ!",
                description=f"Та **{target.mention}**-н данснаас **{hack_amt:,}** ₮ хулгайлсан!\n✨ Бонус: +{bonus:,}₮",
                color=PURPLE_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        else:
            fine = random.randint(2000, 8000)
            await economy.update_balance(ctx.author.id, ctx.guild.id, -fine)
            await economy.set_prison(ctx.author.id, ctx.guild.id, hours=2)
            await self.update_game_stats(ctx.author.id, ctx.guild.id, False, fine, 0)
            embed = discord.Embed(
                title="🚔 ХАКЕР БАРИГДЛАА!",
                description=f"🔒 Хакер оролдлого илэрч, **{fine:,}** ₮ торгууль төлөв.\n⏰ 2 цаг шоронд.",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="⏱️ Дараагийн хакер 2 цагийн дараа")
        await ctx.send(embed=embed)

    @commands.command(name='cgive', aliases=['cgift'])
    async def cgive(self, ctx, target: discord.Member, amount: int):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send("❌ Эдийн засаг ажиллахгүй!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд бэлэг өгөх боломжгүй.")
        if target.id == ctx.author.id or amount <= 0: return await ctx.send("❌ Алдаа.")
        cd = await self.get_cooldown(give_cooldowns, ctx.author.id, GIVE_COOLDOWN)
        if cd:
            h, m = divmod(cd, 3600)[0], (cd % 3600)//60
            return await ctx.send(f"⏳ {h}ц {m}м хүлээх хэрэгтэй")
        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount: return await ctx.send(f"❌ Мөнгө хүрэлцэхгүй!")
        await self.set_cooldown(give_cooldowns, ctx.author.id)
        await economy.update_balance(ctx.author.id, ctx.guild.id, -amount)
        await economy.update_balance(target.id, ctx.guild.id, amount)
        await self.add_hunger_mood(ctx, 5, 3)
        embed = discord.Embed(
            title="🎁 БЭЛЭГ ИЛГЭЭГДЛЭЭ!",
            description=f"{ctx.author.mention} → {target.mention}\n**{amount:,}** ₮ бэлэглэлээ!",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="⏱️ Дараагийн бэлэг 24 цагийн дараа")
        await ctx.send(embed=embed)

    @commands.command(name='highlow', aliases=['hl'])
    async def highlow(self, ctx, amount_str: str, choice: str = None):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send("❌ Эдийн засаг ажиллахгүй!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд тоглох боломжгүй.")
        if amount_str.lower() == 'all':
            amount = await economy.get_balance(ctx.author.id, ctx.guild.id)
            if amount <= 0: return await ctx.send("❌ Мөнгөгүй.")
        else:
            try: amount = int(amount_str)
            except: return await ctx.send("❌ Дүн тоо эсвэл 'all'")
        if amount <= 0: return await ctx.send("❌ Дүн эерэг байх ёстой!")
        if choice is None:
            view = HighLowView(self, ctx, amount)
            embed = discord.Embed(
                title="🎲 HIGH-LOW",
                description=f"**Таны бооцоо:** 💰 {amount:,}₮\nHigher эсвэл Lower сонгоно уу.",
                color=GOLD_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            view.message = await ctx.send(embed=embed, view=view)
            return
        await self.highlow_game(ctx, amount, choice)

    # ---------- Error handlers ----------
    @rob.error
    async def rob_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Зөв хэлбэр: `{ctx.prefix}rob @хэрэглэгч`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Хэрэглэгч олдсонгүй.")
        else: raise error

    @hack.error
    async def hack_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Зөв хэлбэр: `{ctx.prefix}hack @хэрэглэгч`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Хэрэглэгч олдсонгүй.")
        else: raise error

    @cgive.error
    async def cgive_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Зөв хэлбэр: `{ctx.prefix}cgive @хэрэглэгч <дүн>`")
        else: raise error

async def setup(bot):
    await bot.add_cog(Casino(bot))
