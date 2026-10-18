import discord
from discord.ext import commands
from discord.ui import View, Button
import random
import time
import asyncio

# ══════════════ ӨНГӨ ══════════════
SUCCESS_COLOR = 0x57f287
ERROR_COLOR = 0xed4245
WARNING_COLOR = 0xfee75c
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x3498db

# ══════════════ ТОХИРГОО ══════════════
DEFAULT_COOLDOWNS = {
    "gamble": 30, "coinflip": 30, "slot": 45, "roulette": 45,
    "dice": 30, "rps": 30, "numberguess": 30, "highlow": 45,
    "blackjack": 60, "highcard": 60, "hack": 7200, "cgive": 86400,
    "trivia": 15, "crash": 60,
}
MAX_BET = 1_000_000

def _format_money(amount: int) -> str:
    if amount >= 1_000_000_000: return f"{amount/1_000_000_000:.1f}B₮"
    if amount >= 1_000_000: return f"{amount/1_000_000:.1f}M₮"
    if amount >= 1_000: return f"{amount/1_000:.1f}K₮"
    return f"{amount:,}₮"

TRIVIA_QUESTIONS = [
    {"question": "Монгол улсын нийслэл хотыг юу гэдэг вэ?", "answers": ["Улаанбаатар", "Дархан", "Эрдэнэт", "Чойбалсан"], "correct": 0},
    {"question": "Дэлхий дээрх хамгийн өндөр уул?", "answers": ["Эверест", "К2", "Килиманджаро", "Монблан"], "correct": 0},
    {"question": "1 километрт хэдэн метр байдаг вэ?", "answers": ["1000", "100", "10", "10000"], "correct": 0},
    {"question": "Усны химийн томьёо?", "answers": ["H2O", "CO2", "NaCl", "O2"], "correct": 0},
    {"question": "Хүний биеийн хамгийн том эрхтэн?", "answers": ["Арьс", "Элэг", "Зүрх", "Уушиг"], "correct": 0},
    {"question": "Нарнаас хамгийн ойрхон гариг?", "answers": ["Буд", "Сугар", "Дэлхий", "Ангараг"], "correct": 0},
    {"question": "Монгол улсын төрийн далбаанд хэдэн өнгө байдаг вэ?", "answers": ["3", "2", "4", "5"], "correct": 0},
    {"question": "1 жилд хэдэн сар байдаг вэ?", "answers": ["12", "10", "13", "11"], "correct": 0},
    {"question": "Алтан гадас одонг хэдэн хүн хамт авдаг вэ?", "answers": ["2", "1", "3", "4"], "correct": 0},
    {"question": "Монголын хамгийн урт гол?", "answers": ["Орхон", "Хэрлэн", "Сэлэнгэ", "Туул"], "correct": 0},
    {"question": "Компьютерийн 'CPU' гэж юу гэсэн үг вэ?", "answers": ["Central Processing Unit", "Computer Power Unit", "Central Power Unit", "Core Processing Unit"], "correct": 0},
    {"question": "Дэлхийн хамгийн том далай?", "answers": ["Номхон далай", "Атлантын далай", "Энэтхэгийн далай", "Хойд мөсөн далай"], "correct": 0},
    {"question": "Хүн хэдэн шүдтэй вэ?", "answers": ["32", "28", "30", "36"], "correct": 0},
    {"question": "Монгол улс хэдэн аймагтай вэ?", "answers": ["21", "18", "23", "19"], "correct": 0},
    {"question": "Нэг өдөрт хэдэн цаг байдаг вэ?", "answers": ["24", "12", "48", "36"], "correct": 0},
]

# ── VIEW классууд ──
class GambleView(View):
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog = cog; self.ctx = ctx; self.amount = amount

    @discord.ui.button(label="🎲 Gamble", style=discord.ButtonStyle.green)
    async def gamble_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        # 45% хожих магадлал (өмнө 30% байсан)
        won = random.random() < 0.45
        xp = random.randint(5, 20)
        if won:
            win_amt = self.amount * 2
            embed = discord.Embed(title="🎉 Хожиллоо!", description=f"+{_format_money(win_amt)}", color=SUCCESS_COLOR)
            embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=None)
            await self.cog.give_rewards(self.ctx, win_amt, xp, won=True, bet=self.amount)
        else:
            embed = discord.Embed(title="💀 Хожигдлоо", description=f"-{_format_money(self.amount)}", color=ERROR_COLOR)
            embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=None)
            await self.cog.give_rewards(self.ctx, 0, 0, won=False, bet=self.amount)

class CoinflipView(View):
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog = cog; self.ctx = ctx; self.amount = amount
        self.secret = random.choice(["heads", "tails"])

    @discord.ui.button(label="🪙 Heads", style=discord.ButtonStyle.blurple)
    async def heads(self, i, b): await self.resolve(i, "heads")
    @discord.ui.button(label="🪙 Tails", style=discord.ButtonStyle.blurple)
    async def tails(self, i, b): await self.resolve(i, "tails")

    async def resolve(self, interaction, choice):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        won = choice == self.secret
        xp = random.randint(5, 20)
        win_amt = self.amount * 2 if won else 0
        desc = f"Зөв таалаа! +{_format_money(win_amt)}" if won else f"Буруу таалаа ({self.secret}). -{_format_money(self.amount)}"
        color = SUCCESS_COLOR if won else ERROR_COLOR
        embed = discord.Embed(title="🪙 COINFLIP", description=desc, color=color)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.cog.give_rewards(self.ctx, win_amt, xp, won=won, bet=self.amount)

class SlotsView(View):
    symbols = ["🍒","🍋","🍊","🍇","💎","7️⃣"]
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog = cog; self.ctx = ctx; self.amount = amount

    @discord.ui.button(label="🎰 SPIN", style=discord.ButtonStyle.green)
    async def spin(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        roll = [random.choice(self.symbols) for _ in range(3)]
        if roll[0] == roll[1] == roll[2]:
            # Жекпот: 5x (өмнө 10x байсан)
            win_amt, desc, color, won = self.amount * 5, f"{' '.join(roll)}\nЖЕКПОТ! +{_format_money(self.amount*5)}", SUCCESS_COLOR, True
        elif roll[0] == roll[1] or roll[1] == roll[2] or roll[0] == roll[2]:
            # Давхардал: 1.5x (өмнө 2x байсан)
            win_amt, desc, color, won = int(self.amount * 1.5), f"{' '.join(roll)}\nДавхардал! +{_format_money(int(self.amount*1.5))}", SUCCESS_COLOR, True
        else:
            win_amt, desc, color, won = 0, f"{' '.join(roll)}\nХожигдол -{_format_money(self.amount)}", ERROR_COLOR, False
        xp = random.randint(5, 20)
        embed = discord.Embed(title="🎰 SLOTS", description=desc, color=color)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.cog.give_rewards(self.ctx, win_amt, xp, won=won, bet=self.amount)

class RouletteView(View):
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog = cog; self.ctx = ctx; self.amount = amount

    @discord.ui.button(label="🔴 Улаан", style=discord.ButtonStyle.red)
    async def red(self, i, b): await self.resolve(i, "red")
    @discord.ui.button(label="⚫ Хар", style=discord.ButtonStyle.gray)
    async def black(self, i, b): await self.resolve(i, "black")
    @discord.ui.button(label="🟢 Ногоон (0)", style=discord.ButtonStyle.green)
    async def green(self, i, b): await self.resolve(i, "green")

    async def resolve(self, interaction, choice):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        # Жинхэнэ рулет: улаан/хар 47.37%, ногоон 5.26%
        result = random.choices(["red","black","green"], weights=[47.37,47.37,5.26], k=1)[0]
        if choice == result and choice == "green":
            # Ногоон: 14x (өмнө 14x байсан — зөв)
            win_amt, desc, won = self.amount * 14, f"Ногоон 0! +{_format_money(self.amount*14)}", True
        elif choice == result:
            # Улаан/Хар: 2x (өмнө 2x байсан — зөв)
            win_amt, desc, won = self.amount * 2, f"{result.capitalize()}! +{_format_money(self.amount*2)}", True
        else:
            win_amt, desc, won = 0, f"{result.capitalize()} гарлаа. -{_format_money(self.amount)}", False
        xp = random.randint(5, 20)
        embed = discord.Embed(title="🎡 ROULETTE", description=desc, color=GOLD_COLOR)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.cog.give_rewards(self.ctx, win_amt, xp, won=won, bet=self.amount)

class DiceView(View):
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog = cog; self.ctx = ctx; self.amount = amount
        self.secret = random.randint(1, 6)

    async def resolve(self, interaction, guess):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        won = guess == self.secret
        xp = random.randint(5, 20)
        # 6x хожих (өмнө 6x байсан — зөв)
        win_amt = self.amount * 6 if won else 0
        desc = f"Шоо: {self.secret}\nТаасан! +{_format_money(win_amt)}" if won else f"Шоо: {self.secret}\nТааж чадсангүй. -{_format_money(self.amount)}"
        color = SUCCESS_COLOR if won else ERROR_COLOR
        embed = discord.Embed(title="🎲 DICE", description=desc, color=color)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.cog.give_rewards(self.ctx, win_amt, xp, won=won, bet=self.amount)

    @discord.ui.button(label="1", row=0)
    async def b1(self, i, b):
        await self.resolve(i, 1)

    @discord.ui.button(label="2", row=0)
    async def b2(self, i, b):
        await self.resolve(i, 2)

    @discord.ui.button(label="3", row=0)
    async def b3(self, i, b):
        await self.resolve(i, 3)

    @discord.ui.button(label="4", row=1)
    async def b4(self, i, b):
        await self.resolve(i, 4)

    @discord.ui.button(label="5", row=1)
    async def b5(self, i, b):
        await self.resolve(i, 5)

    @discord.ui.button(label="6", row=1)
    async def b6(self, i, b):
        await self.resolve(i, 6)

class RPSView(View):
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog = cog; self.ctx = ctx; self.amount = amount
        self.bot_choice = random.choice(["rock","paper","scissors"])

    async def resolve(self, interaction, user_choice):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        win_conds = {"rock":"scissors","paper":"rock","scissors":"paper"}
        if user_choice == self.bot_choice:
            result, won, money = "Тэнцлээ! Бооцоо буцаагдлаа.", None, self.amount
        elif win_conds[user_choice] == self.bot_choice:
            result, won, money = f"Та хожлоо! Бот {self.bot_choice} тавьсан. +{_format_money(self.amount*2)}", True, self.amount*2
        else:
            result, won, money = f"Та хожигдлоо! Бот {self.bot_choice} тавьсан. -{_format_money(self.amount)}", False, 0
        xp = random.randint(5, 20)
        embed = discord.Embed(title="🪨📄✂️ RPS", description=result, color=GOLD_COLOR)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.cog.give_rewards(self.ctx, money, xp, won=won is True, bet=self.amount)

    @discord.ui.button(label="🪨 Чулуу", style=discord.ButtonStyle.gray)
    async def rock(self, i, b):
        await self.resolve(i, "rock")

    @discord.ui.button(label="📄 Даавуу", style=discord.ButtonStyle.gray)
    async def paper(self, i, b):
        await self.resolve(i, "paper")

    @discord.ui.button(label="✂️ Хайч", style=discord.ButtonStyle.gray)
    async def scissors(self, i, b):
        await self.resolve(i, "scissors")

class GuessButton(Button):
    def __init__(self, number, parent_view):
        super().__init__(label=str(number), style=discord.ButtonStyle.blurple)
        self.number = number; self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.resolve(interaction, self.number)

class NumberGuessView(View):
    def __init__(self, cog, ctx, amount, secret):
        super().__init__(timeout=15)
        self.cog = cog; self.ctx = ctx; self.amount = amount; self.secret = secret
        for i in range(1, 11): self.add_item(GuessButton(i, self))

    async def resolve(self, interaction, guess):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        won = guess == self.secret
        xp = random.randint(5, 20)
        # 10 тооноос 1-г таах: 3x (өмнө 3x байсан — зөв)
        win_amt = self.amount * 3 if won else 0
        desc = f"Зөв тоо **{self.secret}**! +{_format_money(win_amt)}" if won else f"Буруу тоо. Зөв тоо **{self.secret}** байсан. -{_format_money(self.amount)}"
        color = SUCCESS_COLOR if won else ERROR_COLOR
        embed = discord.Embed(title="🔢 NUMBER GUESS", description=desc, color=color)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.cog.give_rewards(self.ctx, win_amt, xp, won=won, bet=self.amount)

class HighLowView(View):
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog = cog; self.ctx = ctx; self.amount = amount
        self.first = random.randint(2, 13); self.second = random.randint(1, 13)

    @discord.ui.button(label="📈 Өндөр", style=discord.ButtonStyle.green)
    async def high(self, i, b): await self.resolve(i, True)
    @discord.ui.button(label="📉 Доогуур", style=discord.ButtonStyle.red)
    async def low(self, i, b): await self.resolve(i, False)

    async def resolve(self, interaction, guess_high):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        if self.first == self.second:
            desc, color, won, win_amt = f"Тоо тэнцлээ ({self.first} = {self.second}). Бооцоо буцаагдлаа.", WARNING_COLOR, None, self.amount
        else:
            won = (self.second > self.first) if guess_high else (self.second < self.first)
            if won:
                desc, color, win_amt = f"Зөв! {self.first} → {self.second}. +{_format_money(self.amount*2)}", SUCCESS_COLOR, self.amount*2
            else:
                desc, color, win_amt = f"Буруу! {self.first} → {self.second}. -{_format_money(self.amount)}", ERROR_COLOR, 0
        xp = random.randint(5, 20)
        embed = discord.Embed(title="🎲 HIGH-LOW", description=desc, color=color)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.cog.give_rewards(self.ctx, win_amt, xp, won=won is True, bet=self.amount)

class BlackjackView(View):
    suits = ["♥","♦","♣","♠"]; ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=60)
        self.cog = cog; self.ctx = ctx; self.amount = amount
        self.deck = [(r,s) for s in self.suits for r in self.ranks]; random.shuffle(self.deck)
        self.player_hand = [self.draw(), self.draw()]
        self.dealer_hand = [self.draw(), self.draw()]
        self.game_over = False; self.update_embed()

    def draw(self): return self.deck.pop()
    def hand_value(self, hand):
        v, a = 0, 0
        for r,_ in hand:
            if r.isdigit(): v += int(r)
            elif r in "JQK": v += 10
            else: a += 1; v += 11
        while v > 21 and a: v -= 10; a -= 1
        return v
    def format_hand(self, h): return " ".join(f"{r}{s}" for r,s in h)
    def update_embed(self):
        e = discord.Embed(title="🃏 BLACKJACK", color=GOLD_COLOR)
        e.add_field(name="🎴 ТАНЫ КАРТ", value=self.format_hand(self.player_hand), inline=False)
        e.add_field(name="🃟 ДИЛЕР", value=self.format_hand(self.dealer_hand[:1]) + " ??", inline=False)
        e.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        e.set_thumbnail(url=self.ctx.author.display_avatar.url)
        self.embed = e

    @discord.ui.button(label="🎯 Цохих (Hit)", style=discord.ButtonStyle.green)
    async def hit(self, i, b):
        if i.user.id != self.ctx.author.id: return await i.response.send_message("Энэ таных биш!", ephemeral=True)
        if self.game_over: return await i.response.defer()
        self.player_hand.append(self.draw())
        if self.hand_value(self.player_hand) > 21: await self.finish(i, "burst"); return
        self.update_embed(); await i.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="🛑 Зогсох (Stand)", style=discord.ButtonStyle.red)
    async def stand(self, i, b):
        if i.user.id != self.ctx.author.id: return await i.response.send_message("Энэ таных биш!", ephemeral=True)
        if self.game_over: return await i.response.defer()
        while self.hand_value(self.dealer_hand) < 17: self.dealer_hand.append(self.draw())
        await self.finish(i, "stand")

    async def finish(self, interaction, reason):
        self.game_over = True
        for c in self.children: c.disabled = True
        pv, dv = self.hand_value(self.player_hand), self.hand_value(self.dealer_hand)
        if reason == "burst": desc, color, won, win_amt = f"ТА ТОССОН! ({pv})\n-{_format_money(self.amount)}", ERROR_COLOR, False, 0
        elif dv > 21 or pv > dv: desc, color, won, win_amt = f"ДИЛЕР ТОССОН!\n{pv} vs {dv}\n+{_format_money(self.amount*2)}", SUCCESS_COLOR, True, self.amount*2
        elif pv == dv: desc, color, won, win_amt = f"ТЭНЦЛЭЭ!\n{pv} vs {dv}\nБооцоо буцаагдлаа.", WARNING_COLOR, None, self.amount
        else: desc, color, won, win_amt = f"ХОЖИГДЛОО!\n{pv} vs {dv}\n-{_format_money(self.amount)}", ERROR_COLOR, False, 0
        xp = random.randint(10, 30)
        embed = discord.Embed(title="🃏 BLACKJACK", description=desc, color=color)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)
        await self.cog.give_rewards(self.ctx, win_amt, xp, won=won is True, bet=self.amount)

class HighCardView(View):
    suits = ["♥","♦","♣","♠"]; ranks = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=60)
        self.cog = cog; self.ctx = ctx; self.amount = amount

    @discord.ui.button(label="🃏 Картаа илрүүл", style=discord.ButtonStyle.green)
    async def reveal(self, interaction, button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Энэ таных биш!", ephemeral=True)
        self.stop()
        pc = random.choice(self.suits)+random.choice(self.ranks)
        dc = random.choice(self.suits)+random.choice(self.ranks)
        pv, dv = self.ranks.index(pc[1:]), self.ranks.index(dc[1:])
        if pv > dv: desc, color, won, win_amt = f"Таны карт: {pc}\nДилер: {dc}\n+{_format_money(self.amount*2)}", SUCCESS_COLOR, True, self.amount*2
        elif pv == dv: desc, color, won, win_amt = f"Таны карт: {pc}\nДилер: {dc}\nТэнцлээ. Бооцоо буцаагдлаа.", WARNING_COLOR, None, self.amount
        else: desc, color, won, win_amt = f"Таны карт: {pc}\nДилер: {dc}\n-{_format_money(self.amount)}", ERROR_COLOR, False, 0
        xp = random.randint(5, 15)
        embed = discord.Embed(title="🃏 HIGH CARD", description=desc, color=color)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.cog.give_rewards(self.ctx, win_amt, xp, won=won is True, bet=self.amount)

class CrashView(View):
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=120)
        self.cog = cog; self.ctx = ctx; self.amount = amount
        self.multiplier = 1.0; self.crashed = False; self.stopped = asyncio.Event()

    @discord.ui.button(label="💰 Мөнгөө авах", style=discord.ButtonStyle.green)
    async def cashout(self, i, b):
        if i.user.id != self.ctx.author.id: return await i.response.send_message("Энэ таных биш!", ephemeral=True)
        if self.crashed: return await i.response.send_message("Аль хэдийн уначихсан!", ephemeral=True)
        self.stopped.set()
        win = int(self.amount * self.multiplier)
        e = discord.Embed(title="💥 CRASH", description=f"Та {self.multiplier:.2f}x дээр авлаа! +{_format_money(win)}", color=SUCCESS_COLOR)
        e.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await i.response.edit_message(embed=e, view=None)
        await self.cog.give_rewards(self.ctx, win, random.randint(10,30), won=True, bet=self.amount)

    async def start(self):
        embed = discord.Embed(title="💥 CRASH", description=f"Үржүүлэгч: **1.00x**\nБооцоо: {_format_money(self.amount)}", color=GOLD_COLOR)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        self.message = await self.ctx.send(embed=embed, view=self)
        # Crash point: 1.0 - 3.0x (өмнө 1.2-5.0 байсан)
        crash_point = random.uniform(1.0, 3.0)
        step = 0.05  # Илүү удаан (өмнө 0.1 байсан)
        try:
            while self.multiplier < crash_point:
                await asyncio.sleep(0.5)
                self.multiplier += step
                embed.description = f"Үржүүлэгч: **{self.multiplier:.2f}x**\nБооцоо: {_format_money(self.amount)}"
                await self.message.edit(embed=embed)
                if self.stopped.is_set(): return
            self.crashed = True
            embed.description = f"💥 **УНАЛАА!** ({crash_point:.2f}x)\n-{_format_money(self.amount)}"
            embed.color = ERROR_COLOR
            await self.message.edit(embed=embed, view=None)
            await self.cog.give_rewards(self.ctx, 0, 0, won=False, bet=self.amount)
        except discord.NotFound: pass

# ── GAMES COG ──
class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    async def cog_load(self):
        await self.init_db()

    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS game_stats ("
                "user_id TEXT, guild_id TEXT, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, "
                "total_won INTEGER DEFAULT 0, total_bet INTEGER DEFAULT 0, "
                "PRIMARY KEY (user_id, guild_id))"
            )
            await conn.commit()

    async def get_economy_cooldown(self, guild_id, command):
        return DEFAULT_COOLDOWNS.get(command, 30)

    async def is_on_cooldown(self, user_id, guild_id, command):
        key = f"{guild_id}:{user_id}:{command}"
        now = time.time(); last = self.cooldowns.get(key, 0)
        cd = await self.get_economy_cooldown(guild_id, command)
        return max(0, int(cd - (now - last))) if now - last < cd else 0

    def set_cooldown(self, user_id, guild_id, command):
        self.cooldowns[f"{guild_id}:{user_id}:{command}"] = time.time()

    async def check_common_restrictions(self, ctx, amount=None):
        if not ctx.guild: await ctx.send("❌ Зөвхөн серверт ашиглана уу."); return False
        eco = self.bot.get_cog("Economy")
        if not eco: await ctx.send("❌ Эдийн засгийн систем ачаалагдаагүй."); return False
        if amount is not None:
            if amount <= 0: await ctx.send(embed=discord.Embed(title="❌ Буруу дүн", description="Эерэг тоо оруулна уу.", color=ERROR_COLOR)); return False
            if amount > MAX_BET: await ctx.send(embed=discord.Embed(title="❌ Хэт их дүн", description=f"Нэг тоглоомд хамгийн ихдээ {_format_money(MAX_BET)} тавих боломжтой.", color=ERROR_COLOR)); return False
            bal = await eco.get_balance(ctx.author.id, ctx.guild.id)
            if bal < amount: await ctx.send(embed=discord.Embed(title="❌ Мөнгө хүрэлцэхгүй", description=f"Танд {amount:,}₮ байхгүй (үлдэгдэл: {bal:,}₮).", color=ERROR_COLOR)); return False
        return True

    async def give_rewards(self, ctx, money, xp, won=False, bet=0):
        eco = self.bot.get_cog("Economy"); lvl = self.bot.get_cog("Leveling")
        # Бонус: хожсон үед 5% (өмнө 10% байсан)
        bonus = int(money * self.bot.config.get("bonus_percent", 5)/100) if won and money>0 else 0
        final = money + bonus
        if eco and final != 0: await eco.update_balance(ctx.author.id, ctx.guild.id, final)
        if lvl and xp > 0 and hasattr(lvl,'add_xp'):
            await lvl.add_xp(ctx.author.id, ctx.guild.id, xp, member=ctx.author, check_mute=True, channel=ctx.channel)
        await self.update_stats(ctx.author.id, ctx.guild.id, won, bet, final if won else 0)

    async def update_stats(self, user_id, guild_id, won, bet, win_amt):
        try:
            async with self.bot.db.acquire() as conn:
                await conn.execute(
                    "INSERT INTO game_stats (user_id,guild_id,wins,losses,total_won,total_bet) VALUES (?,?,0,0,0,0) "
                    "ON CONFLICT(user_id,guild_id) DO UPDATE SET wins = wins",
                    (str(user_id), str(guild_id))
                )
                if won:
                    await conn.execute("UPDATE game_stats SET wins=wins+1, total_won=total_won+?, total_bet=total_bet+? WHERE user_id=? AND guild_id=?", (win_amt, bet, str(user_id), str(guild_id)))
                else:
                    await conn.execute("UPDATE game_stats SET losses=losses+1, total_bet=total_bet+? WHERE user_id=? AND guild_id=?", (bet, str(user_id), str(guild_id)))
                await conn.commit()
        except Exception: pass

    async def start_game(self, ctx, cmd, amount, view_cls, title, desc, **kw):
        if not await self.check_common_restrictions(ctx, amount): return
        rem = await self.is_on_cooldown(ctx.author.id, ctx.guild.id, cmd)
        if rem: m, s = divmod(rem, 60); return await ctx.send(embed=discord.Embed(title="⏳ КҮҮКИ", description=f"**{m}м {s}с** хүлээх хэрэгтэй.", color=WARNING_COLOR))
        eco = self.bot.get_cog("Economy")
        await eco.update_balance(ctx.author.id, ctx.guild.id, -amount)
        self.set_cooldown(ctx.author.id, ctx.guild.id, cmd)
        view = view_cls(self, ctx, amount, **kw)
        embed = discord.Embed(title=title, description=desc, color=GOLD_COLOR)
        embed.set_footer(text=f"Бооцоо: {_format_money(amount)}")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name='gamble', aliases=['gm'])
    async def gamble(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "gamble", amount, GambleView, "🎲 GAMBLE", f"45% хожих магадлалтай. Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='coinflip', aliases=['cf','flip'])
    async def coinflip(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "coinflip", amount, CoinflipView, "🪙 COINFLIP", f"Heads эсвэл Tails сонго! Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='slot', aliases=['sl'])
    async def slot(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "slot", amount, SlotsView, "🎰 SLOTS", f"SPIN дарж эргэлдүүл! Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='roulette', aliases=['rg'])
    async def roulette(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "roulette", amount, RouletteView, "🎡 ROULETTE", f"Улаан, Хар эсвэл Ногоон сонго! Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='dice')
    async def dice(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "dice", amount, DiceView, "🎲 DICE", f"1-6 тоо тааж 6x хожих! Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='rps', aliases=['rockpaperscissors'])
    async def rps(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "rps", amount, RPSView, "🪨📄✂️ RPS", f"Чулуу, Даавуу, Хайч! Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='numberguess', aliases=['numguess'])
    async def numberguess(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        if not await self.check_common_restrictions(ctx, amount): return
        rem = await self.is_on_cooldown(ctx.author.id, ctx.guild.id, "numberguess")
        if rem: m, s = divmod(rem, 60); return await ctx.send(embed=discord.Embed(title="⏳ КҮҮКИ", description=f"**{m}м {s}с** хүлээх хэрэгтэй.", color=WARNING_COLOR))
        eco = self.bot.get_cog("Economy"); await eco.update_balance(ctx.author.id, ctx.guild.id, -amount)
        self.set_cooldown(ctx.author.id, ctx.guild.id, "numberguess")
        secret = random.randint(1, 10)
        view = NumberGuessView(self, ctx, amount, secret)
        embed = discord.Embed(title="🔢 NUMBER GUESS", description=f"1-10 хооронд тоо таа! (3x)\nБооцоо: **{_format_money(amount)}**", color=GOLD_COLOR)
        embed.set_footer(text="15 секундын дотор сонго"); embed.set_thumbnail(url=ctx.author.display_avatar.url)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name='highlow', aliases=['hl'])
    async def highlow(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "highlow", amount, HighLowView, "🎲 HIGH-LOW", f"Дараагийн тоо өндөр эсвэл доогуур? Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='blackjack', aliases=['bj'])
    async def blackjack(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "blackjack", amount, BlackjackView, "🃏 BLACKJACK", f"Блэкжек тоглоом! Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='highcard', aliases=['war'])
    async def highcard(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "highcard", amount, HighCardView, "🃏 HIGH CARD", f"Картаа илрүүлж дилертэй өрсөлд! Бооцоо: **{_format_money(amount)}**")

    @commands.command(name='crash')
    async def crash(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        if not await self.check_common_restrictions(ctx, amount): return
        rem = await self.is_on_cooldown(ctx.author.id, ctx.guild.id, "crash")
        if rem: m, s = divmod(rem, 60); return await ctx.send(embed=discord.Embed(title="⏳ КҮҮКИ", description=f"**{m}м {s}с** хүлээх хэрэгтэй.", color=WARNING_COLOR))
        eco = self.bot.get_cog("Economy"); await eco.update_balance(ctx.author.id, ctx.guild.id, -amount)
        self.set_cooldown(ctx.author.id, ctx.guild.id, "crash")
        view = CrashView(self, ctx, amount); await view.start()

    @commands.command(name='trivia')
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def trivia(self, ctx):
        if not ctx.guild: return await ctx.send("❌ Серверт ашиглана уу.")
        q = random.choice(TRIVIA_QUESTIONS)
        answers = '\n'.join(f"{i+1}. {a}" for i,a in enumerate(q['answers']))
        embed = discord.Embed(title="🧠 TRIVIA", description=f"**{q['question']}**\n\n{answers}", color=INFO_COLOR)
        embed.set_footer(text="Хариултын дугаарыг (1-4) бичнэ үү. 15 секунд байна."); embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        def check(m): return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and 1 <= int(m.content) <= len(q['answers'])
        try:
            msg = await self.bot.wait_for('message', timeout=15.0, check=check)
            idx = int(msg.content)-1
        except: return await ctx.send("⏰ Хугацаа дууссан!")
        xp = random.randint(5,15)
        if idx == q['correct']:
            # Trivia хожсон үед 1000-5000₮ (өмнө XP л байсан)
            reward = random.randint(1000, 5000)
            await ctx.send(f"✅ Зөв! {ctx.author.mention} +{reward:,}₮ +{xp} XP")
            eco = self.bot.get_cog("Economy")
            if eco: await eco.update_balance(ctx.author.id, ctx.guild.id, reward)
            lvl = self.bot.get_cog("Leveling")
            if lvl and hasattr(lvl,'add_xp'): await lvl.add_xp(ctx.author.id, ctx.guild.id, xp, member=ctx.author, check_mute=True, channel=ctx.channel)
        else: await ctx.send(f"❌ Буруу. Зөв хариулт: **{q['answers'][q['correct']]}**")

    @commands.command(name='gamestats')
    async def gamestats(self, ctx):
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT wins,losses,total_won,total_bet FROM game_stats WHERE user_id=? AND guild_id=?", (str(ctx.author.id), str(ctx.guild.id))) as cur:
                row = await cur.fetchone()
        if not row: return await ctx.send(embed=discord.Embed(title="📊 Статистик байхгүй", description=f"{ctx.author.mention} тоглоом тоглоогүй.", color=WARNING_COLOR))
        wins, losses, won, bet = row; total = wins+losses; rate = (wins/total*100) if total>0 else 0
        embed = discord.Embed(title=f"🎮 {ctx.author.display_name} - Тоглоомын статистик", color=GOLD_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🏆 Ялалт", value=wins, inline=True)
        embed.add_field(name="💀 Хожигдол", value=losses, inline=True)
        embed.add_field(name="📊 Хожих %", value=f"{rate:.1f}%", inline=True)
        embed.add_field(name="💰 Хожсон", value=f"+{won:,}₮", inline=True)
        embed.add_field(name="🎲 Тавьсан", value=f"-{bet:,}₮", inline=True)
        embed.add_field(name="📈 Цэвэр", value=f"{won-bet:+,}₮", inline=True)
        await ctx.send(embed=embed)

    async def get_top_games(self, guild_id, limit=10, offset=0):
        async with self.bot.db.acquire() as conn:
            async with conn.execute("SELECT user_id, total_won FROM game_stats WHERE guild_id=? ORDER BY total_won DESC LIMIT ? OFFSET ?", (str(guild_id), limit, offset)) as cur:
                rows = await cur.fetchall()
        return [(int(r[0]), r[1]) for r in rows]

    async def _parse_amount(self, ctx, amount_str):
        eco = self.bot.get_cog("Economy")
        if not eco: await ctx.send("❌ Эдийн засаг ачаалагдаагүй."); return False
        if amount_str.lower() == 'all':
            amount = await eco.get_balance(ctx.author.id, ctx.guild.id)
            if amount <= 0: await ctx.send(embed=discord.Embed(title="❌ Мөнгөгүй", description="Танд мөнгө байхгүй.", color=ERROR_COLOR)); return False
        else:
            try: amount = int(amount_str)
            except ValueError: await ctx.send(embed=discord.Embed(title="❌ Буруу формат", description="Тоо эсвэл 'all' гэж оруулна уу.", color=ERROR_COLOR)); return False
        return amount

async def setup(bot):
    await bot.add_cog(Games(bot))