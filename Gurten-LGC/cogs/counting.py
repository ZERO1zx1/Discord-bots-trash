import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, Any, Union
import ast
import operator
import math

# ===== Аюулгүй математик илэрхийлэл бодох =====
ALLOWED_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd,
}

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

def evaluate_expression(expr: str) -> Union[int, float, None]:
    """Аюулгүйгээр математик илэрхийлэл бодож, бүхэл тоо эсвэл бутархай буцаана. Буруу бол None."""
    try:
        tree = ast.parse(expr.strip(), mode='eval')
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            return None
        if isinstance(node, ast.Name):  # хувьсагчийг хорих
            return None

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](left, right)
        raise ValueError("Дэмжигдэхгүй үйлдэл")

    try:
        result = _eval(tree.body)
        if isinstance(result, (int, float)):
            return result
        return None
    except (ValueError, ZeroDivisionError):
        return None


class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== ӨГӨГДЛИЙН САН (SQLite) ====================
    async def init_tables(self):
        # Хүснэгтүүдийг үүсгэх
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS counting_config (
            guild_id TEXT PRIMARY KEY,
            channel_id INTEGER,
            enabled INTEGER DEFAULT 1,
            delete_messages INTEGER DEFAULT 0,
            math_mode INTEGER DEFAULT 0,
            failed_role_id INTEGER,
            reliable_role_id INTEGER,
            save_role_id INTEGER,
            high_score INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS counting_progress (
            guild_id TEXT PRIMARY KEY,
            current_count INTEGER DEFAULT 0,
            last_user_id INTEGER,
            streak INTEGER DEFAULT 0
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS counting_stats (
            guild_id TEXT,
            user_id TEXT,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            strikes INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )''')
        await self.bot.db.commit()

        # Хуучин хүснэгтэд багана нэмэх (алдаа гарвал үл тоох)
        for col, dtype in [("math_mode", "INTEGER DEFAULT 0"), 
                           ("save_role_id", "INTEGER"), 
                           ("best_streak", "INTEGER DEFAULT 0")]:
            try:
                await self.bot.db.execute(f"ALTER TABLE counting_config ADD COLUMN {col} {dtype}")
                await self.bot.db.commit()
            except:
                pass
        try:
            await self.bot.db.execute("ALTER TABLE counting_progress ADD COLUMN streak INTEGER DEFAULT 0")
            await self.bot.db.commit()
        except:
            pass
        try:
            await self.bot.db.execute("ALTER TABLE counting_stats ADD COLUMN best_streak INTEGER DEFAULT 0")
            await self.bot.db.commit()
        except:
            pass

    async def cog_load(self):
        await self.init_tables()

    # ==================== ТУСЛАХ ФУНКЦУУД ====================
    async def get_config(self, guild_id: int) -> Dict[str, Any]:
        row = await self.bot.db.fetchone(
            "SELECT channel_id, enabled, delete_messages, math_mode, failed_role_id, "
            "reliable_role_id, save_role_id, high_score, best_streak FROM counting_config WHERE guild_id = ?",
            str(guild_id)
        )
        if not row:
            return None
        keys = ["channel_id", "enabled", "delete_messages", "math_mode",
                "failed_role_id", "reliable_role_id", "save_role_id", "high_score", "best_streak"]
        config = dict(zip(keys, row))
        config["enabled"] = bool(config["enabled"])
        config["delete_messages"] = bool(config["delete_messages"])
        config["math_mode"] = bool(config["math_mode"])
        config["high_score"] = config["high_score"] or 0
        config["best_streak"] = config["best_streak"] or 0
        return config

    async def get_progress(self, guild_id: int) -> Dict[str, Any]:
        row = await self.bot.db.fetchone(
            "SELECT current_count, last_user_id, streak FROM counting_progress WHERE guild_id = ?",
            str(guild_id)
        )
        if not row:
            return {"current": 0, "last_user": None, "streak": 0}
        return {"current": row[0], "last_user": row[1], "streak": row[2]}

    async def update_progress(self, guild_id: int, current: int, last_user: Optional[int], streak: int):
        await self.bot.db.execute(
            "INSERT INTO counting_progress (guild_id, current_count, last_user_id, streak) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET current_count = ?, last_user_id = ?, streak = ?",
            str(guild_id), current, last_user, streak,
            current, last_user, streak
        )
        await self.bot.db.commit()

    async def reset_count(self, guild_id: int):
        await self.update_progress(guild_id, 0, None, 0)

    async def update_high_score(self, guild_id: int, new_score: int):
        await self.bot.db.execute(
            "UPDATE counting_config SET high_score = ? WHERE guild_id = ?",
            new_score, str(guild_id)
        )
        await self.bot.db.commit()

    async def update_best_streak(self, guild_id: int, new_streak: int):
        await self.bot.db.execute(
            "UPDATE counting_config SET best_streak = ? WHERE guild_id = ?",
            new_streak, str(guild_id)
        )
        await self.bot.db.commit()

    async def add_stats(self, guild_id: int, user_id: int, correct: bool, streak: int = 0):
        col = "correct" if correct else "wrong"
        await self.bot.db.execute(
            f"INSERT OR IGNORE INTO counting_stats (guild_id, user_id, {col}) VALUES (?, ?, 0)",
            str(guild_id), str(user_id)
        )
        await self.bot.db.commit()
        await self.bot.db.execute(
            f"UPDATE counting_stats SET {col} = {col} + 1 WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        await self.bot.db.commit()
        if correct:
            await self.bot.db.execute(
                "UPDATE counting_stats SET best_streak = MAX(best_streak, ?) WHERE guild_id = ? AND user_id = ?",
                streak, str(guild_id), str(user_id)
            )
            await self.bot.db.commit()

    async def add_save_stat(self, guild_id: int, user_id: int):
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO counting_stats (guild_id, user_id, saves) VALUES (?, ?, 0)",
            str(guild_id), str(user_id)
        )
        await self.bot.db.commit()
        await self.bot.db.execute(
            "UPDATE counting_stats SET saves = saves + 1 WHERE guild_id = ? AND user_id = ?",
            str(guild_id), str(user_id)
        )
        await self.bot.db.commit()

    # ==================== ТООЛЛОГО СОНСОГЧ ====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        cfg = await self.get_config(message.guild.id)
        if not cfg or not cfg["enabled"] or message.channel.id != cfg["channel_id"]:
            return

        content = message.content.strip()
        num = None

        # 1. Шууд тоо
        try:
            num = int(content)
        except ValueError:
            # 2. math mode үед илэрхийлэл
            if cfg["math_mode"]:
                num = evaluate_expression(content)
                if num is not None and not isinstance(num, int):
                    num = None
            if num is None:
                return

        if not isinstance(num, int):
            return

        prog = await self.get_progress(message.guild.id)
        expected = prog["current"] + 1

        if num != expected or (prog["last_user"] == message.author.id and prog["current"] != 0):
            await self.add_stats(message.guild.id, message.author.id, False)
            await self.reset_count(message.guild.id)

            embed = discord.Embed(
                title="❌ БУРУУ ТОО!",
                description=f"{message.author.mention} буруу тоо бичлээ.\n**{expected}** байх ёстой байсан.\nТоолол **0** болж шинэчлэгдлээ.",
                color=0xf38ba8
            )
            embed.set_footer(text="Дараагийн тоо: 1")
            embed.timestamp = discord.utils.utcnow()
            await message.channel.send(embed=embed)

            if cfg["delete_messages"]:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass

            if cfg["failed_role_id"]:
                role = message.guild.get_role(cfg["failed_role_id"])
                if role:
                    try:
                        await message.author.add_roles(role, reason="Тооллогын алдаа")
                    except discord.Forbidden:
                        pass
            return

        # Зөв тоо
        new_streak = prog["streak"]
        if prog["last_user"] == message.author.id:
            new_streak += 1
        else:
            new_streak = 1

        await self.update_progress(message.guild.id, expected, message.author.id, new_streak)
        await self.add_stats(message.guild.id, message.author.id, True, new_streak)

        try:
            await message.add_reaction("✅")
        except discord.Forbidden:
            pass

        if expected > cfg["high_score"]:
            await self.update_high_score(message.guild.id, expected)
            embed = discord.Embed(
                title="🏆 ШИНЭ ДЭЭД АМЖИЛТ!",
                description=f"{message.author.mention} **{expected}**-д хүрч, шинэ амжилт тогтоолоо!",
                color=0xfab387
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()
            await message.channel.send(embed=embed)

        if new_streak > cfg["best_streak"]:
            await self.update_best_streak(message.guild.id, new_streak)
            embed = discord.Embed(
                title="🔥 ХАМГИЙН УРТ ЦУВРАЛ!",
                description=f"{message.author.mention} **{new_streak}** дараалсан зөв тоогоор шинэ рекорд тогтоолоо!",
                color=0xffa500
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()
            await message.channel.send(embed=embed)

        # 50 дараалсан зөв бол reliable_role өгөх
        if new_streak == 50 and cfg["reliable_role_id"]:
            role = message.guild.get_role(cfg["reliable_role_id"])
            if role and role not in message.author.roles:
                try:
                    await message.author.add_roles(role, reason="50 дараалсан зөв тоололт")
                    await message.channel.send(f"🌟 {message.author.mention} та найдвартай тоологч боллоо!", delete_after=5)
                except discord.Forbidden:
                    pass

    # ==================== SLASH КОМАНДУУД ====================
    @app_commands.command(name="count_set", description="Тоолох сувгийг тохируулах")
    @app_commands.default_permissions(administrator=True)
    async def count_set(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.execute(
            "INSERT INTO counting_config (guild_id, channel_id, enabled) VALUES (?, ?, 1) "
            "ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?, enabled = 1",
            str(interaction.guild.id), channel.id, channel.id
        )
        await self.bot.db.commit()
        embed = discord.Embed(description=f"✅ Тоолох суваг {channel.mention} боллоо.", color=0xa6e3a1)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_toggle", description="Тооллогыг бүрэн идэвхжүүлэх / унтраах")
    @app_commands.default_permissions(administrator=True)
    async def count_toggle(self, interaction: discord.Interaction):
        cfg = await self.get_config(interaction.guild.id)
        if not cfg:
            embed = discord.Embed(description="❌ Эхлээд `count_set` командаар сувгаа тохируулна уу.", color=0xf38ba8)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        new_state = 0 if cfg["enabled"] else 1
        await self.bot.db.execute(
            "UPDATE counting_config SET enabled = ? WHERE guild_id = ?",
            new_state, str(interaction.guild.id)
        )
        await self.bot.db.commit()
        status = "Идэвхжлээ ✅" if new_state else "Унтарлаа 🔇"
        embed = discord.Embed(description=f"🔘 Тооллого {status}", color=0xa6e3a1 if new_state else 0xf9e2af)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_math_toggle", description="Математик илэрхийлэл зөвшөөрөх / болиулах")
    @app_commands.default_permissions(administrator=True)
    async def count_math_toggle(self, interaction: discord.Interaction):
        cfg = await self.get_config(interaction.guild.id)
        if not cfg:
            embed = discord.Embed(description="❌ Эхлээд `count_set` командаар сувгаа тохируулна уу.", color=0xf38ba8)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        new_state = 0 if cfg["math_mode"] else 1
        await self.bot.db.execute(
            "UPDATE counting_config SET math_mode = ? WHERE guild_id = ?",
            new_state, str(interaction.guild.id)
        )
        await self.bot.db.commit()
        status = "Идэвхжлээ 🔢" if new_state else "Унтарлаа ❌"
        embed = discord.Embed(description=f"🧮 Математик илэрхийлэл {status}", color=0xa6e3a1 if new_state else 0xf9e2af)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_force", description="Тооллыг хүссэн утгаар тогтоох (админ)")
    @app_commands.default_permissions(administrator=True)
    async def count_force(self, interaction: discord.Interaction, number: int):
        if number < 0:
            embed = discord.Embed(description="❌ Тоо 0-ээс бага байж болохгүй.", color=0xf38ba8)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await self.update_progress(interaction.guild.id, number, None, 0)
        embed = discord.Embed(description=f"🔢 Тоолол **{number}** болж тогтоогдлоо.", color=0xa6e3a1)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_stats_user", description="Хэрэглэгчийн тооллогын статистик")
    async def count_stats_user(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        row = await self.bot.db.fetchone(
            "SELECT correct, wrong, saves, strikes, best_streak FROM counting_stats "
            "WHERE guild_id = ? AND user_id = ?",
            str(interaction.guild.id), str(target.id)
        )

        if not row:
            embed = discord.Embed(
                title="📊 Тооллогын статистик",
                description=f"{target.mention} одоогоор тооллогод оролцоогүй байна.",
                color=0x89b4fa
            )
        else:
            correct, wrong, saves, strikes, best_streak = row
            total = correct + wrong
            accuracy = (correct / total * 100) if total > 0 else 0
            embed = discord.Embed(title=f"📊 {target.display_name} - ТООЛЛОГЫН СТАТИСТИК", color=0x89b4fa)
            embed.add_field(name="✅ Зөв", value=f"```{correct}```", inline=True)
            embed.add_field(name="❌ Буруу", value=f"```{wrong}```", inline=True)
            embed.add_field(name="🎯 Нарийвчлал", value=f"```{accuracy:.1f}%```", inline=True)
            embed.add_field(name="🛟 Авралт", value=f"```{saves}```", inline=True)
            embed.add_field(name="⚠️ Анхааруулга", value=f"```{strikes}```", inline=True)
            embed.add_field(name="🔥 Хамгийн урт цуврал", value=f"```{best_streak}```", inline=True)
            embed.set_thumbnail(url=target.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_stats_server", description="Серверийн тооллогын статистик")
    async def count_stats_server(self, interaction: discord.Interaction):
        cfg = await self.get_config(interaction.guild.id)
        if not cfg:
            embed = discord.Embed(description="❌ Тохиргоо хийгдээгүй.", color=0xf38ba8)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        prog = await self.get_progress(interaction.guild.id)

        embed = discord.Embed(title="📈 СЕРВЕРИЙН ТООЛЛОГО", color=0x89b4fa)
        embed.add_field(name="🔢 Одоогийн тоо", value=f"```{prog['current']}```", inline=True)
        embed.add_field(name="🏆 Дээд амжилт", value=f"```{cfg['high_score']}```", inline=True)
        embed.add_field(name="🔥 Хамгийн урт цуврал", value=f"```{cfg['best_streak']}```", inline=True)
        embed.add_field(name="👤 Одоогийн цуврал", value=f"```{prog['streak']}```", inline=True)
        embed.add_field(name="📢 Суваг", value=f"<#{cfg['channel_id']}>", inline=True)
        embed.add_field(name="🔘 Төлөв", value="Идэвхтэй" if cfg["enabled"] else "Унтарсан", inline=True)
        embed.add_field(name="🧮 Math Mode", value="Идэвхтэй" if cfg["math_mode"] else "Унтарсан", inline=True)
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_leaderboard", description="Тооллогын шилдэг 10")
    async def count_leaderboard(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch(
            "SELECT user_id, correct, wrong, best_streak FROM counting_stats "
            "WHERE guild_id = ? ORDER BY correct DESC LIMIT 10",
            str(interaction.guild.id)
        )

        if not rows:
            embed = discord.Embed(description="📭 Одоогоор оролцогч алга.", color=0x89b4fa)
            return await interaction.response.send_message(embed=embed)

        embed = discord.Embed(title="🏆 ТООЛЛОГЫН ШИЛДЭГ 10", color=0xfab387)
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i, (uid, correct, wrong, best_streak) in enumerate(rows):
            user = interaction.guild.get_member(int(uid))
            name = user.display_name if user else f"ID:{uid}"
            embed.add_field(
                name=f"{medals[i]} {name}",
                value=f"✅ {correct}  ❌ {wrong}  🔥 {best_streak}",
                inline=False
            )
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_save", description="Тооллыг аврах (алдаа гарахаас хамгаалах)")
    async def count_save(self, interaction: discord.Interaction):
        cfg = await self.get_config(interaction.guild.id)
        if not cfg or not cfg["enabled"]:
            embed = discord.Embed(description="❌ Тооллого идэвхгүй байна.", color=0xf38ba8)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        allowed = False
        if cfg["save_role_id"]:
            role = interaction.guild.get_role(cfg["save_role_id"])
            if role and role in interaction.user.roles:
                allowed = True
        if cfg["reliable_role_id"]:
            role = interaction.guild.get_role(cfg["reliable_role_id"])
            if role and role in interaction.user.roles:
                allowed = True
        if not allowed:
            embed = discord.Embed(description="❌ Танд аврах эрх байхгүй.", color=0xf38ba8)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        prog = await self.get_progress(interaction.guild.id)
        if prog["current"] == 0:
            embed = discord.Embed(description="❌ Одоогоор тоолол хоосон байна.", color=0xf38ba8)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await self.add_save_stat(interaction.guild.id, interaction.user.id)
        embed = discord.Embed(
            description=f"✅ {interaction.user.mention} тооллыг аварлаа! "
                        f"Одоогийн тоо **{prog['current']}** хэвээр байна.",
            color=0xa6e3a1
        )
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_reset_config", description="Бүх тооллогын тохиргоог устгах (админ)")
    @app_commands.default_permissions(administrator=True)
    async def count_reset_config(self, interaction: discord.Interaction):
        await self.bot.db.execute("DELETE FROM counting_config WHERE guild_id = ?", str(interaction.guild.id))
        await self.bot.db.commit()
        await self.bot.db.execute("DELETE FROM counting_progress WHERE guild_id = ?", str(interaction.guild.id))
        await self.bot.db.commit()
        embed = discord.Embed(description="🧹 Бүх тооллогын тохиргоо болон явц устгагдлаа.", color=0xfab387)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    # ==================== РОЛЬ ТОХИРГОО ====================
    @app_commands.command(name="count_set_failed_role", description="Алдаа гаргасан хэрэглэгчид олгох роль")
    @app_commands.default_permissions(administrator=True)
    async def set_failed_role(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.execute(
            "UPDATE counting_config SET failed_role_id = ? WHERE guild_id = ?",
            role.id, str(interaction.guild.id)
        )
        await self.bot.db.commit()
        embed = discord.Embed(description=f"⚠️ Алдааны роль {role.mention} боллоо.", color=0xf9e2af)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_set_reliable_role", description="Найдвартай тоологч роль")
    @app_commands.default_permissions(administrator=True)
    async def set_reliable_role(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.execute(
            "UPDATE counting_config SET reliable_role_id = ? WHERE guild_id = ?",
            role.id, str(interaction.guild.id)
        )
        await self.bot.db.commit()
        embed = discord.Embed(description=f"✅ Найдвартай роль {role.mention} боллоо.", color=0xa6e3a1)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_set_save_role", description="Аврах эрхтэй роль")
    @app_commands.default_permissions(administrator=True)
    async def set_save_role(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.execute(
            "UPDATE counting_config SET save_role_id = ? WHERE guild_id = ?",
            role.id, str(interaction.guild.id)
        )
        await self.bot.db.commit()
        embed = discord.Embed(description=f"🛟 Аврах роль {role.mention} боллоо.", color=0xa6e3a1)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Counting(bot))