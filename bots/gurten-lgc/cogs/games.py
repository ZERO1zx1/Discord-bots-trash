import discord
from discord.ext import commands
import random
from datetime import datetime, timezone

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR   = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x89b4fa
PURPLE_COLOR  = 0xcba6f7
EMBED_COLOR   = 0x1e1e2f

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== ӨГӨГДЛИЙН САН (SQLite) ====================
    async def init_tables(self):
        """game_stats хүснэгтийг үүсгэх (байхгүй бол)"""
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS game_stats (
            user_id TEXT,
            guild_id TEXT,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            total_won INTEGER DEFAULT 0,
            total_bet INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )''')
        await self.bot.db.commit()

    async def cog_load(self):
        await self.init_tables()

    async def resolve_amount(self, ctx, amount_str: str):
        economy = self.bot.get_cog("Economy")
        if not economy:
            return None, "Эдийн засгийн систем идэвхгүй."
        if amount_str.lower() == 'all':
            bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
            if bal <= 0:
                return None, "Танд мөнгө байхгүй."
            return bal, None
        try:
            amount = int(amount_str)
            if amount <= 0:
                return None, "Дүн эерэг байх ёстой."
            return amount, None
        except ValueError:
            return None, "Дүн нь тоо эсвэл 'all' байх ёстой."

    async def give_rewards(self, ctx, money_change, xp_amount, won=False, bet=0):
        eco = self.bot.get_cog("Economy")
        level = self.bot.get_cog("Leveling")
        bonus_percent = self.bot.config.get("bonus_percent", 10)
        final_money = money_change
        if won and money_change > 0:
            bonus = int(money_change * bonus_percent / 100)
            final_money += bonus
        if eco and final_money != 0:
            await eco.update_balance(ctx.author.id, ctx.guild.id, final_money)
        if level and xp_amount > 0:
            if hasattr(level, 'add_xp'):
                await level.add_xp(ctx.author.id, ctx.guild.id, xp_amount, member=ctx.author, check_mute=True, channel=ctx.channel)
        await self.update_stats(ctx.author.id, ctx.guild.id, won, bet, final_money if won else 0)

    async def update_stats(self, user_id, guild_id, won, bet, win_amt):
        """Тоглогчийн статистикийг шинэчлэх (SQLite, commit-тэй)"""
        try:
            row = await self.bot.db.fetchone(
                "SELECT 1 FROM game_stats WHERE user_id = ? AND guild_id = ?",
                str(user_id), str(guild_id)
            )
            if not row:
                await self.bot.db.execute(
                    "INSERT INTO game_stats (user_id, guild_id, wins, losses, total_won, total_bet) VALUES (?, ?, 0, 0, 0, 0)",
                    str(user_id), str(guild_id)
                )
                await self.bot.db.commit()

            if won:
                await self.bot.db.execute(
                    "UPDATE game_stats SET wins = wins + 1, total_won = total_won + ?, total_bet = total_bet + ? WHERE user_id = ? AND guild_id = ?",
                    win_amt, bet, str(user_id), str(guild_id)
                )
                await self.bot.db.commit()
            else:
                await self.bot.db.execute(
                    "UPDATE game_stats SET losses = losses + 1, total_bet = total_bet + ? WHERE user_id = ? AND guild_id = ?",
                    bet, str(user_id), str(guild_id)
                )
                await self.bot.db.commit()
        except Exception:
            pass

    # ---------- ӨЛСГӨЛӨН / УУР ШАЛГАЛТ ----------
    async def check_hunger_mood(self, ctx):
        economy = self.bot.get_cog("Economy")
        if economy:
            hunger, mood = await economy.get_hunger_mood(ctx.author.id, ctx.guild.id)
            if hunger >= 80:
                await ctx.send(f"🍔 {ctx.author.mention}, та хэт өлсөж байна! Тоглох тэнхээгүй. Эхлээд `geat` эсвэл `gcafe`-с хоол идээрэй.")
                return False
            if mood >= 80:
                await ctx.send(f"😡 {ctx.author.mention}, та хэт ууртай байна! Тоглох боломжгүй. `grelax` амраарай.")
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

    # ==================== ТОГЛООМ КОМАНДУУД ====================
    @commands.command(name='gamble', aliases=['gm'])
    async def gamble(self, ctx, amount_str: str):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy:
            return await ctx.send("❌ Эдийн засгийн систем ажиллахгүй байна!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байхдаа мөрийтэй тоглоом тоглох боломжгүй.")
        amount, err = await self.resolve_amount(ctx, amount_str)
        if err:
            return await ctx.send(f"❌ {err}")
        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(f"❌ Танд {amount:,} мөнгө байхгүй!")
        win = random.random() < 0.3
        xp = random.randint(2, 6)
        if win:
            await self.give_rewards(ctx, amount, xp, won=True, bet=amount)
            embed = discord.Embed(
                title="🎉 ХОЖЛОО! 🎉",
                description=f"**{amount:,}** мөнгө хожлоо!",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="💰 ХОЖСОН", value=f"```diff\n+ {amount:,} мөнгө```", inline=True)
        else:
            await self.give_rewards(ctx, -amount, xp, won=False, bet=amount)
            embed = discord.Embed(
                title="😢 ХОЖИГДЛОО",
                description=f"**{amount:,}** мөнгө алдлаа.",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="📉 АЛДАГДСАН", value=f"```diff\n- {amount:,} мөнгө```", inline=True)
        embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="30% хожих магадлал | Болгоомжтой тоглоорой!")
        await self.add_hunger_mood(ctx, 5, 3)
        await ctx.send(embed=embed)

    @commands.command(name='coinflip', aliases=['cf', 'flip'])
    async def coinflip(self, ctx, choice: str, amount_str: str):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy:
            return await ctx.send("❌ Эдийн засгийн систем ажиллахгүй байна!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байхдаа тоглох боломжгүй.")
        choice = choice.lower()
        if choice not in ('heads', 'h', 'tails', 't'):
            return await ctx.send("❌ Сонголт: `heads` эсвэл `tails`")
        user_choice = 'heads' if choice in ('heads', 'h') else 'tails'
        amount, err = await self.resolve_amount(ctx, amount_str)
        if err:
            return await ctx.send(f"❌ {err}")
        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(f"❌ Танд {amount:,} мөнгө байхгүй!")
        result = random.choice(['heads', 'tails'])
        win = (user_choice == result)
        xp = random.randint(2, 4)
        if win:
            await self.give_rewards(ctx, amount, xp, won=True, bet=amount)
            embed = discord.Embed(
                title="🪙 ХОЖЛОО!",
                description=f"Зоос: **{result.upper()}**\nТаны сонголт: **{user_choice.upper()}**",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="💰 ХОЖСОН", value=f"```diff\n+ {amount:,} мөнгө```", inline=True)
        else:
            await self.give_rewards(ctx, -amount, xp, won=False, bet=amount)
            embed = discord.Embed(
                title="🪙 ХОЖИГДЛОО",
                description=f"Зоос: **{result.upper()}**\nТаны сонголт: **{user_choice.upper()}**",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="📉 АЛДАГДСАН", value=f"```diff\n- {amount:,} мөнгө```", inline=True)
        embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="50/50 магадлал")
        await self.add_hunger_mood(ctx, 5, 3)
        await ctx.send(embed=embed)

    @commands.command(name='slot', aliases=['sl'])
    async def slot(self, ctx, amount_str: str):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy:
            return await ctx.send("❌ Эдийн засгийн систем ажиллахгүй байна!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байхдаа тоглох боломжгүй.")
        amount, err = await self.resolve_amount(ctx, amount_str)
        if err:
            return await ctx.send(f"❌ {err}")
        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(f"❌ Танд {amount:,} мөнгө байхгүй!")
        symbols = ["🍒", "🍋", "🍊", "🍉", "⭐", "💎"]
        a, b, c = random.choices(symbols, k=3)
        xp = random.randint(2, 4)
        if a == b == c:
            mult = 5 if a == "💎" else 3
            win_amount = amount * mult
            await self.give_rewards(ctx, win_amount, random.randint(3, 5), won=True, bet=amount)
            embed = discord.Embed(
                title="🎰 JACKPOT! 🎰",
                description=f"**{a} | {b} | {c}**\n\n🎉 **ХОЖЛОО!** +{win_amount:,} мөнгө",
                color=GOLD_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        elif a == b or b == c or a == c:
            win_amount = amount // 2
            await self.give_rewards(ctx, win_amount, xp, won=True, bet=amount)
            embed = discord.Embed(
                title="🎰 ХЭСЭГ ХОЖЛОО!",
                description=f"**{a} | {b} | {c}**\n\n✅ **+{win_amount:,} мөнгө**",
                color=PURPLE_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        else:
            await self.give_rewards(ctx, -amount, xp, won=False, bet=amount)
            embed = discord.Embed(
                title="🎰 ХОЖИГДЛОО...",
                description=f"**{a} | {b} | {c}**\n\n💔 **-{amount:,} мөнгө**",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=False)
        await self.add_hunger_mood(ctx, 5, 3)
        await ctx.send(embed=embed)

    @commands.command(name='roulette')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roulette(self, ctx, color: str, amount_str: str):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if amount_str.lower() == 'all':
            if economy:
                bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
                if bal <= 0:
                    return await ctx.send(embed=discord.Embed(title="❌ ХАНГАЛТГҮЙ", description="Танд мөнгө байхгүй.", color=ERROR_COLOR))
                amount = bal
            else:
                return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна!", color=ERROR_COLOR))
        if not economy:
            return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна!", color=ERROR_COLOR))
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байхдаа тоглох боломжгүй.")
        color = color.lower()
        if color in ("улаан", "red"): color = "red"
        elif color in ("хар", "black"): color = "black"
        elif color in ("ногоон", "green"): color = "green"
        else:
            return await ctx.send(embed=discord.Embed(title="❌ БУРУУ СОНГОЛТ", description="Сонголт: `red`, `black`, `green`", color=ERROR_COLOR))
        amount, err = await self.resolve_amount(ctx, amount_str)
        if err:
            return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description=err, color=ERROR_COLOR))
        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(embed=discord.Embed(title="❌ ХАНГАЛТГҮЙ", description=f"Танд **{amount:,}** мөнгө хүрэлцэхгүй.", color=ERROR_COLOR))
        number = random.randint(0, 36)
        if number == 0:
            result_color = "green"
            mult = 1
        else:
            if (1 <= number <= 10) or (19 <= number <= 28):
                result_color = "red" if number % 2 == 1 else "black"
            else:
                result_color = "red" if number % 2 == 0 else "black"
            mult = 0.5
        win = (color == result_color)
        xp = random.randint(2, 6)
        if win:
            win_amount = int(amount * mult)
            await self.give_rewards(ctx, win_amount, xp, won=True, bet=amount)
            embed = discord.Embed(
                title="🎡 ХОЖЛОО!",
                description=f"Тоо: **{number}** ({result_color.upper()})\nТаны сонголт: **{color.upper()}**",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="💰 ХОЖСОН", value=f"```diff\n+ {win_amount:,} мөнгө (x{mult})```", inline=True)
        else:
            await self.give_rewards(ctx, -amount, xp, won=False, bet=amount)
            embed = discord.Embed(
                title="🎡 ХОЖИГДЛОО",
                description=f"Тоо: **{number}** ({result_color.upper()})\nТаны сонголт: **{color.upper()}**",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="📉 АЛДАГДСАН", value=f"```diff\n- {amount:,} мөнгө```", inline=True)
        embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Green 0: 1x | Red/Black: 0.5x")
        await self.add_hunger_mood(ctx, 5, 3)
        await ctx.send(embed=embed)

    @commands.command(name='dice')
    async def dice(self, ctx, guess: int, amount_str: str):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy:
            return await ctx.send("❌ Эдийн засгийн систем ажиллахгүй байна!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байхдаа тоглох боломжгүй.")
        if guess < 1 or guess > 6:
            return await ctx.send("❌ 1-6 хооронд таамаглах!")
        amount, err = await self.resolve_amount(ctx, amount_str)
        if err:
            return await ctx.send(f"❌ {err}")
        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(f"❌ Танд {amount:,} мөнгө байхгүй!")
        roll = random.randint(1, 6)
        xp = random.randint(2, 5)
        if roll == guess:
            win_amount = amount * 6
            await self.give_rewards(ctx, win_amount, xp, won=True, bet=amount)
            embed = discord.Embed(
                title="🎲 ХОЖЛОО!",
                description=f"Шоо: **{roll}**\nТаны тоо: **{guess}**",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="💰 ХОЖСОН", value=f"```diff\n+ {win_amount:,} мөнгө (x6)```", inline=True)
        else:
            await self.give_rewards(ctx, -amount, xp, won=False, bet=amount)
            embed = discord.Embed(
                title="🎲 ХОЖИГДЛОО",
                description=f"Шоо: **{roll}**\nТаны тоо: **{guess}**",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="📉 АЛДАГДСАН", value=f"```diff\n- {amount:,} мөнгө```", inline=True)
        embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await self.add_hunger_mood(ctx, 5, 3)
        await ctx.send(embed=embed)

    @commands.command(name='rps', aliases=['rockpaperscissors'])
    async def rps(self, ctx, choice: str, amount_str: str):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        if not await self.check_hunger_mood(ctx): return
        economy = self.bot.get_cog("Economy")
        if not economy:
            return await ctx.send("❌ Эдийн засгийн систем ажиллахгүй байна!")
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("🚔 Шоронд байхдаа тоглох боломжгүй.")
        choice = choice.lower()
        choices = ['rock', 'paper', 'scissors']
        if choice not in choices:
            return await ctx.send("❌ Сонголт: `rock`, `paper`, `scissors`")
        amount, err = await self.resolve_amount(ctx, amount_str)
        if err:
            return await ctx.send(f"❌ {err}")
        bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
        if bal < amount:
            return await ctx.send(f"❌ Танд {amount:,} мөнгө байхгүй!")
        bot_choice = random.choice(choices)
        win = (choice == bot_choice) or (choice == 'rock' and bot_choice == 'scissors') or (choice == 'paper' and bot_choice == 'rock') or (choice == 'scissors' and bot_choice == 'paper')
        xp = random.randint(2, 5)
        if win:
            win_amount = amount
            await self.give_rewards(ctx, win_amount, xp, won=True, bet=amount)
            embed = discord.Embed(
                title="✂️ ХОЖЛОО!",
                description=f"Таны сонголт: **{choice.upper()}**\nБотын сонголт: **{bot_choice.upper()}**",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="💰 ХОЖСОН", value=f"```diff\n+ {win_amount:,} мөнгө```", inline=True)
        else:
            await self.give_rewards(ctx, -amount, xp, won=False, bet=amount)
            embed = discord.Embed(
                title="✂️ ХОЖИГДЛОО",
                description=f"Таны сонголт: **{choice.upper()}**\nБотын сонголт: **{bot_choice.upper()}**",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="📉 АЛДАГДСАН", value=f"```diff\n- {amount:,} мөнгө```", inline=True)
        embed.add_field(name="✨ XP", value=f"```diff\n+ {xp} XP```", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await self.add_hunger_mood(ctx, 5, 3)
        await ctx.send(embed=embed)

    @commands.command(name='answer', aliases=['8ball'])
    async def answer(self, ctx, *, question: str):
        if not question.endswith("?"):
            return await ctx.send("❌ Таны асуулт төгсгөлд `?` тэмдэгт оруулна уу.")
        responses = [
            "Тийм",
            "Үгүй",
            "Магадлалтай",
            "Хувьсах боломжтой",
            "Тодорхой биш"
        ]
        response = random.choice(responses)
        await ctx.send(f"🎱 {response}")

    # ==================== СТАТИСТИК ====================
    @commands.command(name='gamestats')
    async def gamestats(self, ctx):
        row = await self.bot.db.fetchone(
            "SELECT wins, losses, total_won, total_bet FROM game_stats WHERE user_id = ? AND guild_id = ?",
            str(ctx.author.id), str(ctx.guild.id)
        )
        if not row:
            embed = discord.Embed(
                title="📊 СТАТИСТИК БАЙХГҮЙ",
                description=f"{ctx.author.mention} тоглоом тоглоогүй.",
                color=WARNING_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)
        wins, losses, total_won, total_bet = row
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        net = total_won - total_bet
        embed = discord.Embed(
            title=f"🎮 {ctx.author.display_name} - ТОГЛООМЫН СТАТИСТИК",
            color=GOLD_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="🏆 ЯЛАЛТ", value=str(wins), inline=True)
        embed.add_field(name="💀 ХОЖИГДОЛ", value=str(losses), inline=True)
        embed.add_field(name="📊 ЯЛАЛТЫН ХУВЬ", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="💰 ХОЖСОН", value=f"+{total_won:,}", inline=True)
        embed.add_field(name="🎲 ТАВЬСАН", value=f"-{total_bet:,}", inline=True)
        embed.add_field(name="📈 ЦЭВЭР АШИГ", value=f"{net:+,}", inline=True)
        embed.set_footer(text=f"{ctx.guild.name} | {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name='gameleaderboard', aliases=['gamelb'])
    async def gameleaderboard(self, ctx):
        rows = await self.bot.db.fetch(
            "SELECT user_id, total_won FROM game_stats WHERE guild_id = ? ORDER BY total_won DESC LIMIT 10",
            str(ctx.guild.id)
        )
        if not rows:
            embed = discord.Embed(
                title="🎲 ШИЛДЭГ 10",
                description="Одоогоор тоглоогүй.",
                color=EMBED_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)
        total_won_all = sum(won for _, won in rows)
        embed = discord.Embed(
            title="🎲🏆 ТОГЛООМЫН ШИЛДЭГ 10",
            description=f"Нийт хожил: **{total_won_all:,}** 💰",
            color=GOLD_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        top_won = rows[0][1]
        for i, (uid, won) in enumerate(rows):
            try: user = await self.bot.fetch_user(int(uid)); name = user.display_name[:20]
            except: name = f"ID: {uid}"
            bar_len = 20
            progress = int((won / top_won) * bar_len) if top_won > 0 else 0
            bar = "▰" * progress + "▱" * (bar_len - progress)
            embed.add_field(name=f"{medals[i]} **{name}**", value=f"💰 {won:,} мөнгө\n```{bar}```", inline=False)
        embed.set_footer(text=f"Сервер: {ctx.guild.name}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))