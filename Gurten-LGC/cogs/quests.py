import discord
from discord.ext import commands
import random
import time

# ══════════════ ӨНГӨ ══════════════
SUCCESS_COLOR = 0x57f287
ERROR_COLOR   = 0xed4245
WARNING_COLOR = 0xfee75c
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x3498db

# ══════════════ ДААЛГАВРЫН ЗАГВАР (Монгол хэл, ойлгомжтой) ══════════════
QUEST_TEMPLATES = [
    # Аватар
    {"desc": "{target} удаа аватар солих", "type": "avatar_change", "min_target": 1, "max_target": 10, "reward_min": 500, "reward_max": 3000},
    # Кафе
    {"desc": "Кафегаас {target} удаа хоол идэх", "type": "cafe_eat", "min_target": 1, "max_target": 10, "reward_min": 300, "reward_max": 2000},
    # Инвентар
    {"desc": "Инвентараас {target} удаа зүйл хэрэглэх", "type": "inventory_use", "min_target": 1, "max_target": 10, "reward_min": 300, "reward_max": 2000},
    # Казино
    {"desc": "Казино тоглоомд {target} удаа оролцох", "type": "casino_play", "min_target": 1, "max_target": 15, "reward_min": 500, "reward_max": 5000},
    # Confession
    {"desc": "{target} удаа нууц захиа бичих", "type": "confession_write", "min_target": 1, "max_target": 10, "reward_min": 400, "reward_max": 3000},
    # Тоололт
    {"desc": "Тоололд {target} удаа оролцох", "type": "counting_participate", "min_target": 1, "max_target": 20, "reward_min": 300, "reward_max": 3000},
    # Ажил
    {"desc": "{target} удаа ажил хийх", "type": "economy_work", "min_target": 1, "max_target": 20, "reward_min": 500, "reward_max": 5000},
    # Хөгжилтэй
    {"desc": "Хөгжилтэй командуудыг {target} удаа ашиглах", "type": "fun_command", "min_target": 3, "max_target": 30, "reward_min": 300, "reward_max": 3000},
    # Тоглоом
    {"desc": "{target} удаа тоглоом тоглох", "type": "game_play", "min_target": 1, "max_target": 15, "reward_min": 400, "reward_max": 4000},
    # Giveaway
    {"desc": "Giveaway-д {target} удаа оролцох", "type": "giveaway_enter", "min_target": 1, "max_target": 10, "reward_min": 400, "reward_max": 3000},
    {"desc": "Giveaway-д {target} удаа ялах", "type": "giveaway_win", "min_target": 1, "max_target": 5, "reward_min": 3000, "reward_max": 20000},
    # Урилга
    {"desc": "{target} хүн урих", "type": "invite_create", "min_target": 1, "max_target": 20, "reward_min": 1000, "reward_max": 10000},
    # Түвшин
    {"desc": "{target} түвшин ахих", "type": "level_up", "min_target": 1, "max_target": 20, "reward_min": 1000, "reward_max": 10000},
    # Гэрлэлт
    {"desc": "Хүнтэй гэрлэх", "type": "marriage_propose", "min_target": 1, "max_target": 3, "reward_min": 5000, "reward_max": 20000},
    # Mines
    {"desc": "Mines тоглоомыг {target} удаа тоглох", "type": "mines_play", "min_target": 1, "max_target": 10, "reward_min": 500, "reward_max": 5000},
    # Модератор
    {"desc": "{target} удаа модератор үйлдэл хийх", "type": "mod_action", "min_target": 1, "max_target": 15, "reward_min": 800, "reward_max": 8000},
    # PvP
    {"desc": "PvP тулаанд {target} удаа оролцох", "type": "pvp_play", "min_target": 1, "max_target": 10, "reward_min": 600, "reward_max": 6000},
    # Роль
    {"desc": "{target} удаа роль өгөх/хасах", "type": "role_give", "min_target": 1, "max_target": 10, "reward_min": 500, "reward_max": 4000},
    # Дэлгүүр
    {"desc": "Дэлгүүрээс {target} удаа худалдан авалт хийх", "type": "shop_purchase", "min_target": 1, "max_target": 10, "reward_min": 400, "reward_max": 4000},
    # Дуут суваг
    {"desc": "Дуут сувагт {target} минут байх", "type": "tempvoice_time", "min_target": 5, "max_target": 120, "reward_min": 500, "reward_max": 10000},
    # Наймаа
    {"desc": "{target} удаа наймаа хийх", "type": "trade_complete", "min_target": 1, "max_target": 15, "reward_min": 500, "reward_max": 5000},
]

class Quests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('''CREATE TABLE IF NOT EXISTS user_quests (
                    user_id VARCHAR(255), guild_id VARCHAR(255),
                    quest_id VARCHAR(50), template_id INT, target INT,
                    progress INT DEFAULT 0, reward_type VARCHAR(20),
                    reward_amount INT, claimed TINYINT(1) DEFAULT 0,
                    created_at BIGINT, PRIMARY KEY (user_id, guild_id, quest_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
                await cur.execute('''CREATE TABLE IF NOT EXISTS quest_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255), guild_id VARCHAR(255),
                    quest_id VARCHAR(50), template_id INT, completed_at BIGINT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    async def cog_load(self):
        await self.init_db()

    async def get_user_quests(self, user_id, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT quest_id, template_id, target, progress, reward_type, reward_amount, claimed FROM user_quests WHERE user_id=%s AND guild_id=%s ORDER BY created_at DESC",
                    (str(user_id), str(guild_id))
                )
                rows = await cur.fetchall()
        return [{"quest_id": r[0], "template_id": r[1], "target": r[2], "progress": r[3],
                 "reward_type": r[4], "reward_amount": r[5], "claimed": bool(r[6])} for r in rows]

    async def add_quest(self, user_id, guild_id, template, quest_id, target, reward_type, reward_amount):
        now = int(time.time())
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO user_quests (user_id, guild_id, quest_id, template_id, target, reward_type, reward_amount, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(user_id), str(guild_id), quest_id, list(QUEST_TEMPLATES).index(template), target, reward_type, reward_amount, now)
                )

    async def remove_quest(self, user_id, guild_id, quest_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM user_quests WHERE user_id=%s AND guild_id=%s AND quest_id=%s",
                                  (str(user_id), str(guild_id), quest_id))

    async def complete_quest(self, user_id, guild_id, quest_id):
        now = int(time.time())
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE user_quests SET claimed=1 WHERE user_id=%s AND guild_id=%s AND quest_id=%s",
                                  (str(user_id), str(guild_id), quest_id))
                await cur.execute("SELECT template_id FROM user_quests WHERE user_id=%s AND guild_id=%s AND quest_id=%s",
                                  (str(user_id), str(guild_id), quest_id))
                row = await cur.fetchone()
                if row:
                    await cur.execute("INSERT INTO quest_history (user_id, guild_id, quest_id, template_id, completed_at) VALUES (%s,%s,%s,%s,%s)",
                                      (str(user_id), str(guild_id), quest_id, row[0], now))

    async def update_progress(self, user_id, guild_id, quest_id, progress):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE user_quests SET progress=%s WHERE user_id=%s AND guild_id=%s AND quest_id=%s",
                                  (progress, str(user_id), str(guild_id), quest_id))

    def generate_quest(self):
        template = random.choice(QUEST_TEMPLATES)
        target = random.randint(template["min_target"], template["max_target"])
        reward_type = random.choice(["money", "xp", "random_item"])
        if reward_type == "money":
            reward_amount = random.randint(template["reward_min"], template["reward_max"])
        elif reward_type == "xp":
            reward_amount = random.randint(50, 500)
        else:
            reward_amount = random.randint(1, 3)
        desc = template["desc"].replace("{target}", str(target))
        return template, target, reward_type, reward_amount, desc

    async def give_reward(self, ctx, quest):
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        if quest["reward_type"] == "money":
            economy = self.bot.get_cog("Economy")
            if economy:
                await economy.update_balance(user_id, guild_id, quest["reward_amount"])
                embed = discord.Embed(description=f"💰 +{quest['reward_amount']}₮", color=SUCCESS_COLOR)
                await ctx.send(embed=embed)
        elif quest["reward_type"] == "xp":
            leveling = self.bot.get_cog("Leveling")
            if leveling:
                await leveling.add_xp(user_id, guild_id, quest["reward_amount"], member=ctx.author, check_mute=True, channel=ctx.channel)
                embed = discord.Embed(description=f"✨ +{quest['reward_amount']} XP", color=SUCCESS_COLOR)
                await ctx.send(embed=embed)
        elif quest["reward_type"] == "random_item":
            shop = self.bot.get_cog("ShopCog") or self.bot.get_cog("Shop")
            if shop:
                item_id = random.choice([36,37,38,39,40,41,42,1,2,3])
                await shop.add_item(user_id, guild_id, item_id, quest["reward_amount"])
                item = await shop.get_item(item_id)
                embed = discord.Embed(description=f"🎁 {item['emoji']} {item['name']} x{quest['reward_amount']}", color=SUCCESS_COLOR)
                await ctx.send(embed=embed)

    # ══════════════ ПРОГРЕСС ШИНЭЧЛЭХ (Бусад когуудаас дуудагдана) ══════════════
    async def trigger_event(self, user_id, guild_id, event_type, value=1):
        quests = await self.get_user_quests(user_id, guild_id)
        for q in quests:
            if q["claimed"]:
                continue
            template = QUEST_TEMPLATES[q["template_id"]]
            if template["type"] == event_type:
                new_progress = q["progress"] + value
                await self.update_progress(user_id, guild_id, q["quest_id"], new_progress)

    def _progress_bar(self, current, total, length=10):
        filled = int(length * current / total) if total > 0 else 0
        return "🟩" * filled + "⬛" * (length - filled)

    # ══════════════ КОМАНДУУД ══════════════
    @commands.group(name='quest', invoke_without_command=True)
    async def quest_group(self, ctx):
        """Даалгаврын тусламж"""
        embed = discord.Embed(
            title="📜 ДААЛГАВРЫН СИСТЕМ",
            description="Даалгавруудыг гүйцэтгэж, мөнгө, XP эсвэл эд зүйлсээр шагнуул!",
            color=GOLD_COLOR
        )
        embed.add_field(name="`gquest new`", value="➕ Шинэ даалгавар авах (хамгийн ихдээ 5)", inline=False)
        embed.add_field(name="`gquest status`", value="📊 Одоогийн идэвхтэй даалгаврууд", inline=False)
        embed.add_field(name="`gquest claim <id>`", value="✅ Даалгавраа биелүүлж, шагнал авах", inline=False)
        embed.add_field(name="`gquest refresh <id>`", value="🔄 Даалгаврыг сольж, шинэчлэх", inline=False)
        embed.add_field(name="`gquest history`", value="📜 Сүүлд биелүүлсэн даалгаврын түүх", inline=False)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Амжилт гаргаж, шагналаа цуглуул!")
        await ctx.send(embed=embed)

    @quest_group.command(name='status')
    async def quest_status(self, ctx):
        quests = await self.get_user_quests(ctx.author.id, ctx.guild.id)
        active = [q for q in quests if not q["claimed"]]
        if not active:
            embed = discord.Embed(
                title="📜 ДААЛГАВАР",
                description="Танд идэвхтэй даалгавар байхгүй. `gquest new` ашиглана уу.",
                color=INFO_COLOR
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title=f"📜 {ctx.author.display_name} – ИДЭВХТЭЙ ДААЛГАВАРУУД",
            color=GOLD_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        for q in active:
            template = QUEST_TEMPLATES[q["template_id"]]
            desc = template["desc"].replace("{target}", str(q["target"]))
            progress = q["progress"]
            prog_bar = self._progress_bar(progress, q["target"])

            if q["reward_type"] == "money":
                reward_str = f"💰 {q['reward_amount']:,}₮"
            elif q["reward_type"] == "xp":
                reward_str = f"✨ {q['reward_amount']} XP"
            else:
                reward_str = f"🎁 Санамсаргүй эд зүйл x{q['reward_amount']}"

            embed.add_field(
                name=f"🔖 `{q['quest_id']}`  |  {reward_str}",
                value=f"{desc}\n{prog_bar} ({progress}/{q['target']})",
                inline=False
            )

        embed.set_footer(text="Биелсэн даалгавраа `gquest claim <id>` гэж авна")
        await ctx.send(embed=embed)

    @quest_group.command(name='new')
    async def quest_new(self, ctx):
        current = await self.get_user_quests(ctx.author.id, ctx.guild.id)
        active = [q for q in current if not q["claimed"]]
        if len(active) >= 5:
            embed = discord.Embed(
                description="❌ Танд аль хэдийн **5** идэвхтэй даалгавар байна.\n`gquest claim` эсвэл `gquest refresh` ашиглана уу.",
                color=ERROR_COLOR
            )
            return await ctx.send(embed=embed)

        template, target, reward_type, reward_amount, desc = self.generate_quest()
        quest_id = f"q{int(time.time()*1000) % 1000000}"
        await self.add_quest(ctx.author.id, ctx.guild.id, template, quest_id, target, reward_type, reward_amount)

        if reward_type == "money":
            reward_text = f"💰 {reward_amount:,}₮"
        elif reward_type == "xp":
            reward_text = f"✨ {reward_amount} XP"
        else:
            reward_text = f"🎁 Санамсаргүй эд зүйл x{reward_amount}"

        embed = discord.Embed(
            title="✅ ШИНЭ ДААЛГАВАР",
            description=f"**{desc}**\n\n🎯 Шагнал: **{reward_text}**",
            color=SUCCESS_COLOR
        )
        embed.set_footer(text=f"Даалгаврын ID: {quest_id}")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @quest_group.command(name='claim')
    async def quest_claim(self, ctx, quest_id: str):
        quests = await self.get_user_quests(ctx.author.id, ctx.guild.id)
        target_quest = next((q for q in quests if q["quest_id"] == quest_id and not q["claimed"]), None)
        if not target_quest:
            embed = discord.Embed(
                description="❌ Ийм ID-тай даалгавар олдсонгүй эсвэл аль хэдийн авсан байна.",
                color=ERROR_COLOR
            )
            return await ctx.send(embed=embed)

        if target_quest["progress"] < target_quest["target"]:
            embed = discord.Embed(
                description=f"❌ Даалгавар хангалтгүй байна ({target_quest['progress']}/{target_quest['target']}).",
                color=ERROR_COLOR
            )
            return await ctx.send(embed=embed)

        await self.give_reward(ctx, target_quest)
        await self.complete_quest(ctx.author.id, ctx.guild.id, quest_id)
        embed = discord.Embed(
            description="✅ Даалгавар амжилттай биеллээ! Шагналаа авлаа.",
            color=SUCCESS_COLOR
        )
        await ctx.send(embed=embed)

    @quest_group.command(name='refresh')
    async def quest_refresh(self, ctx, quest_id: str):
        quests = await self.get_user_quests(ctx.author.id, ctx.guild.id)
        target_quest = next((q for q in quests if q["quest_id"] == quest_id and not q["claimed"]), None)
        if not target_quest:
            embed = discord.Embed(
                description="❌ Ийм ID-тай идэвхтэй даалгавар олдсонгүй.",
                color=ERROR_COLOR
            )
            return await ctx.send(embed=embed)

        await self.remove_quest(ctx.author.id, ctx.guild.id, quest_id)
        embed = discord.Embed(
            description="🗑️ Даалгаврыг цуцаллаа. `gquest new` гэж шинээр авах боломжтой.",
            color=WARNING_COLOR
        )
        await ctx.send(embed=embed)

    @quest_group.command(name='history')
    async def quest_history(self, ctx):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT quest_id, template_id, completed_at FROM quest_history WHERE user_id=%s AND guild_id=%s ORDER BY completed_at DESC LIMIT 10",
                    (str(ctx.author.id), str(ctx.guild.id))
                )
                rows = await cur.fetchall()
        if not rows:
            embed = discord.Embed(
                description="📭 Одоогоор гүйцэтгэсэн даалгаврын түүх байхгүй.",
                color=INFO_COLOR
            )
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title=f"📜 {ctx.author.display_name} – ДААЛГАВРЫН ТҮҮХ",
            color=INFO_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        for qid, tid, ts in rows:
            template = QUEST_TEMPLATES[tid] if tid < len(QUEST_TEMPLATES) else None
            desc = template["desc"].replace("{target}", "?") if template else "Тодорхойгүй"
            time_str = f"<t:{ts}:R>"
            embed.add_field(name=f"🔖 `{qid}`", value=f"{desc}\n✅ {time_str}", inline=False)
        embed.set_footer(text="Сүүлийн 10 биелүүлсэн даалгавар")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Quests(bot))