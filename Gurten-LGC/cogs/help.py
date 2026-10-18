import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from datetime import datetime, timezone

GOLD_COLOR = 0xfab387
PURPLE_COLOR = 0xcba6f7
ERROR_COLOR = 0xf38ba8

CATEGORIES = [
    "💰 Эдийн засаг, Тоглоом, Casino",
    "🎫 Сугалаа & Minefield, PvP",
    "🕵️ Мафи",
    "📊 Түвшин & XP",
    "🏪 Дэлгүүр & 💍 Гэрлэлт",
    "🛒 Зах зээл (Marketplace)",
    "🛠️ Модераци & Staff",
    "🎉 Хөгжилтэй",
    "👑 Админ",
    "🔢 Тооллого",
    "📌 Sticky & Зарлал",
    "🔗 Урилга",
    "🔊 Түр дууны суваг",
    "🤖 AI Chat",
    "🎭 Role удирдлага",
    "🤫 Нууц мэдүүлэг (Confessions)",
    "🎁 Giveaway",
    "👋 Мэндчилгээ (Greetings)",
    "🖼️ Аватар log",
]


class HelpView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.current_index = -1

        options = []
        for cat in CATEGORIES:
            emoji = cat.split()[0]
            options.append(discord.SelectOption(label=cat, emoji=emoji, value=cat))

        self.cat_select = Select(placeholder="📋 Категори сонгох", options=options, row=0)
        self.cat_select.callback = self.select_callback
        self.add_item(self.cat_select)

        self.prev_button = Button(label="◀ Өмнөх", style=discord.ButtonStyle.gray, row=1)
        self.prev_button.callback = self.prev_callback
        self.add_item(self.prev_button)

        self.next_button = Button(label="Дараах ▶", style=discord.ButtonStyle.gray, row=1)
        self.next_button.callback = self.next_callback
        self.add_item(self.next_button)

        self.prev_button.disabled = True
        self.next_button.disabled = True

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected = self.cat_select.values[0]
        if selected in CATEGORIES:
            self.current_index = CATEGORIES.index(selected)
            await self.update_message(interaction)

    async def prev_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.current_index > 0:
            self.current_index -= 1
            await self.update_message(interaction)

    async def next_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.current_index < len(CATEGORIES) - 1:
            self.current_index += 1
            await self.update_message(interaction)

    async def update_message(self, interaction: discord.Interaction):
        if self.current_index < 0:
            return
        embed = self._build_embed(interaction.client)
        self.prev_button.disabled = (self.current_index == 0)
        self.next_button.disabled = (self.current_index == len(CATEGORIES) - 1)

        for opt in self.cat_select.options:
            opt.default = (opt.value == CATEGORIES[self.current_index])

        await interaction.edit_original_response(embed=embed, view=self)

    def _build_embed(self, bot):
        prefix = self._get_prefix(bot)

        index = self.current_index
        category = CATEGORIES[index]
        embed = discord.Embed(
            title=f"{category}",
            description="*Доорх командуудыг ашиглан тоглоом тоглож, мөнгө олох, серверээ удирдах боломжтой.*",
            color=GOLD_COLOR if index % 2 == 0 else PURPLE_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=f"📖 {bot.user.display_name} – Тусламж", icon_url=bot.user.display_avatar.url)
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.set_footer(text=f"Хуудас {index+1}/{len(CATEGORIES)}")

        # ===== 0: Эдийн засаг, Тоглоом, Casino =====
        if index == 0:
            embed.add_field(name="💸 ЭДИЙН ЗАСАГ", value="", inline=False)
            embed.add_field(name="`bal` `daily` `work` `bail`", value="Үлдэгдэл, өдрийн урамшуулал, ажил, шоронгоос гарах", inline=False)
            embed.add_field(name="`transfer` `deposit` `withdraw`", value="Мөнгө шилжүүлэх, банк", inline=False)
            embed.add_field(name="`setjob` `removejob` `listjobs`", value="Ажлын байр нэмэх, устгах, жагсаах", inline=False)
            embed.add_field(name="`lb` `globaltop` `bankprotect`", value="Лидерборд, глобал топ, банк хамгаалалт", inline=False)
            embed.add_field(name="`profilecard` `stats` `eat` `relax`", value="Зурагт профайл, төлөв, хоол идэх, амрах", inline=False)
            embed.add_field(name="🎲 ТОГЛООМ", value="", inline=False)
            embed.add_field(name="`gamble` `flip` `slot` `roulette` `dice`", value="Азын тоглоом", inline=True)
            embed.add_field(name="`gamestats` `gameleaderboard`", value="Тоглоомын статистик, топ", inline=True)
            embed.add_field(name="🎰 Casino", value="", inline=False)
            embed.add_field(name="`blackjack` `highlow`", value="Blackjack, High-Low", inline=True)
            embed.add_field(name="`rob` `hack` `cgive` `crime`", value="Дээрэмдэх, хакердах, бэлэг өгөх", inline=True)
            embed.add_field(name="⚠️ Анхаар!", value="Дээрэмдэх, хакердах амжилтгүй бол торгууль төлөх болно!", inline=False)

        # ===== 1: Сугалаа & Minefield, PvP =====
        elif index == 1:
            embed.add_field(name="🎫 СУГАЛАА", value="", inline=False)
            embed.add_field(name="`lottery` `draw` `lottery_info` `lottery_participants` `lottery_cooldown`", value="Тасалбар авах, сугалах, мэдээлэл", inline=False)
            embed.add_field(name="💣 MINEFIELD", value="", inline=False)
            embed.add_field(name="`minefield` `aliases`, 'mf, mines'", value="Minefield тоглоом, mine тайлах", inline=False)
            embed.add_field(name="Картын зиндаа", value="Royal Flush → Straight Flush → ... → High Card", inline=False)
            embed.add_field(name="⚔️ PvP", value="", inline=False)
            embed.add_field(name="`pvp` `mines`", value="Тулаан, Mines тоглоом", inline=True)

        # ===== 2: Мафи =====
        elif index == 2:
            embed.add_field(name="🕵️ MAFIA", value="", inline=False)
            embed.add_field(name="`mafia create` `join` `start` `end`", value="Тоглоом үүсгэх, нэгдэх, эхлүүлэх, дуусгах", inline=False)
            embed.add_field(name="`mafia status` `players` `alive`", value="Төлөв, тоглогчид, амьд тоглогчид", inline=True)
            embed.add_field(name="`mafiarule`", value="Дүрэм", inline=True)
            embed.add_field(name="🌙 Шөнө (фракцийн чат/DM)", value="`kill` `save` `investigate` `sleep`", inline=False)
            embed.add_field(name="☀️ Өдөр", value="`vote <дугаар>` – хөөх", inline=False)

        # ===== 3: Түвшин & XP =====
        elif index == 3:
            embed.description = "**📊 Түвшин ба XP** – идэвхтэй байж цол аваарай"
            embed.add_field(name="`rank` `/leveling user` `leveling leaderboard`", value="Ранк карт, лидерборд (зураг)", inline=False)
            embed.add_field(name="XP эх үүсвэр", value="💬 Чат 1‑5 | 🎤 Voice 1‑5 | 🖼️ Зураг 3 | 🎵 Дуут 4 | 💼 Ажил 10‑20 | 🎮 Тоглоом 2‑5", inline=False)
            embed.add_field(name="🏅 Цолууд", value="🌱 Newbie → ⭐ Active → 🔥 Expert → 🛡️ Veteran → 💎 Elite → 👑 Legend", inline=False)
            embed.add_field(name="Админ командууд", value="`leveling set` – суваг тохируулах\n`leveling stop` – мэдэгдэл унтраах\n`leveling toggle` – систем асаах/унтраах\n`leveling exception` – онцгой суваг/хэрэглэгч\n`leveling setxp` – XP тохируулах\n`leveling reset` – XP устгах\n`leveling setrole` – түвшинд роль оноох", inline=False)

        # ===== 4: Дэлгүүр & Гэрлэлт =====
        elif index == 4:
            embed.add_field(name="🏪 ДЭЛГҮҮР", value="", inline=False)
            embed.add_field(name="`shop` `buy` `invcard`", value="Дэлгүүр, худалдаж авах, инвентар карт", inline=True)
            embed.add_field(name="`drink` `use` `accessories`", value="Уух, хэрэглэх, аксессуар", inline=True)
            embed.add_field(name="`iteminfo` `cafe` `dine` `trade`", value="Барааны мэдээлэл, кафе, хоол идэх, солилцоо", inline=True)
            embed.add_field(name="`vape` `sogtol`", value="Вайпны жагсаалт, согтолтын түвшин", inline=True)
            embed.add_field(name="📦 НӨӨЦ (Stock)", value="`stock status` `stock set` `stock add` `stock remove` `stock reset`", inline=False)
            embed.add_field(name="⚠️ Мансуурлын торгууль", value="Түвшин 100% хүрвэл 2 цаг шоронд + 5% торгууль", inline=False)
            embed.add_field(name="💍 ГЭРЛЭЛТ", value="", inline=False)
            embed.add_field(name="`/propose` `/divorce` `/gift` `/love` `/autoaccept` `/spouse`", value="Үндсэн үйлдлүүд", inline=False)
            embed.add_field(name="`/familytree` `/adopt` `/accept_adoption` `/decline_adoption` `/disown`", value="Гэр бүлийн мод, хүүхэд өргөмжлөх", inline=False)
            embed.add_field(name="`/marriage_profile` `/marriage_card`", value="Профайл, зурагт карт", inline=False)
            embed.add_field(name="Админ тохиргоо", value="`/polygamy` `/maxspouses` `/toggle_marriage` `/block_marriage` `/unblock_marriage`", inline=False)

        # ===== 5: Зах зээл =====
        elif index == 5:
            embed.add_field(name="🛒 ЗАХ ЗЭЭЛ", value="", inline=False)
            embed.add_field(name="`marketplace sell <ID> <тоо> <үнэ>`", value="Бараа зарах", inline=False)
            embed.add_field(name="`marketplace buy <зарын ID>`", value="Бараа худалдаж авах", inline=False)
            embed.add_field(name="`marketplace listings [хуудас]`", value="Идэвхтэй зарлалууд", inline=False)
            embed.add_field(name="`marketplace cancel <зарын ID>`", value="Өөрийн зарыг цуцлах", inline=False)
            embed.add_field(name="💡 Хэрэглэх заавар", value="Инвентар дахь бараагаа `gmarketplace sell`-ээр зарж, бусад хэрэглэгчид `gmarketplace buy`-ээр худалдаж авна. Зар цуцлахад бараа буцаан инвентарт орно.", inline=False)

        # ===== 6: Модераци & Staff =====
        elif index == 6:
            embed.add_field(name="🛠️ МОДЕРАЦИ", value="", inline=False)
            embed.add_field(name="`kick` `ban` `unban` `banlist`", value="Хөөх, бан, бан цуцлах, бан жагсаалт", inline=True)
            embed.add_field(name="`clear` `timeout` `untimeout`", value="Мессеж устгах, түр хаах, тайлах", inline=True)
            embed.add_field(name="`warn` `warnings` `unwarn` `warnedusers`", value="Анхааруулга өгөх, харах, устгах, жагсаалт", inline=True)
            embed.add_field(name="👥 STAFF СИСТЕМ", value="", inline=False)
            embed.add_field(name="`/staff_set_channel`", value="Лог, зарлал, статистик сувгийг тохируулах", inline=False)
            embed.add_field(name="`/staff_add` `/staff_remove` `/staff_list`", value="Staff нэмэх, хасах, жагсаалт", inline=True)
            embed.add_field(name="`/staff_counts` `/staff_status`", value="Долоо хоногийн KPI оноо, тодорхой гишүүний мэдээлэл", inline=True)

        # ===== 7: Хөгжилтэй =====
        elif index == 7:
            embed.add_field(name="🎉 ХӨГЖИЛТЭЙ", value="", inline=False)
            embed.add_field(name="`avatar` `profile`", value="Аватар харах, профайл", inline=True)
            embed.add_field(name="Үйлдлүүд (GIF)", value="`hug` `kiss` `slap` `pat` `cuddle` `bite` `poke` `wave` `punch` `boop` `bully` `tickle` `handhold` `stare` `highfive` `snuggle`", inline=False)
            embed.add_field(name="Эмоцууд (GIF)", value="`cry` `dance` `laugh` `sleep` `smile` `blush` `pout` `shrug` `think` `angry` `happy` `thumbsup`", inline=False)
            embed.add_field(name="🕵️ AI МӨРДӨГЧ", value="`aimurder` `murder_guess` `aimurder_help`", inline=False)

        # ===== 8: Админ =====
        elif index == 8:
            embed.add_field(name="👑 АДМИН", value="", inline=False)
            embed.add_field(name="`guildinfo` `servericon` `serverbanner` `serversplash`", value="Серверийн мэдээлэл, дүрс, баннер, splash", inline=True)
            embed.add_field(name="`rolelist` `addmoney` `removemoney` `reload`", value="Роль жагсаалт, мөнгө нэмэх/хасах, ког дахин ачаалах", inline=True)
            embed.add_field(name="`lock` `unlock`", value="Суваг түгжих/нээх", inline=True)
            embed.add_field(name="`setjob` `removejob` `listjobs`", value="Ажлын байр нэмэх, устгах, жагсаах", inline=True)

        # ===== 9: Тооллого =====
        elif index == 9:
            embed.add_field(name="🔢 ТООЛЛОГО", value="", inline=False)
            embed.add_field(name="`/count_set` `/count_toggle`", value="Суваг тохируулах, идэвхжүүлэх/унтраах", inline=True)
            embed.add_field(name="`/count_stats_user` `/count_stats_server` `/count_leaderboard`", value="Хэрэглэгчийн/серверийн статистик, топ 10", inline=True)
            embed.add_field(name="`/count_set_failed_role` `/count_set_reliable_role`", value="Алдааны роль, найдвартай тоологч роль", inline=True)
            embed.add_field(name="Дүрэм", value="• Дараагийн тоог бичнэ\n• Нэг хүн дараалан болохгүй\n• Алдаа гарвал 0 болно", inline=False)

        # ===== 10: Sticky & Зарлал =====
        elif index == 10:
            embed.add_field(name="📌 STICKY & ЗАРЛАЛ", value="", inline=False)
            embed.add_field(name="`stick` `unstick`", value="Sticky тохируулах, устгах", inline=True)
            embed.add_field(name="`/announce`", value="Зарлал илгээх (модал, embed)", inline=True)
            embed.add_field(name="Зарлалын онцлог", value="✅ Суваг сонгох | Гарчиг, текст, өнгө | Зураг, footer | Урьдчилан харах | POST товч", inline=False)

        # ===== 11: Урилга =====
        elif index == 11:
            embed.add_field(name="🔗 УРИЛГА", value="", inline=False)
            embed.add_field(name="`/invitelog_set` `/invitelog_toggle` `/invitelog_status` `/fakedelay`", value="Тохиргоо", inline=True)
            embed.add_field(name="`/inviteleaderboard` `/invitestats` `/invitecodes`", value="Урилгын лидерборд, статистик, кодууд", inline=True)
            embed.add_field(name="`/invitedlist` `/inviter` `/statsgraph`", value="Урьсан хүмүүс, хэн урьсан, график", inline=True)
            embed.add_field(name="`/addinvitelabel` `/removeinvitelabel`", value="Урилгын шошго", inline=True)

        # ===== 12: Түр дууны суваг =====
        elif index == 12:
            embed.add_field(name="🔊 ТҮР ДУУНЫ СУВАГ", value="", inline=False)
            embed.add_field(name="`/voicesetup` `/voicesettings`", value="Тохиргоо", inline=True)
            embed.add_field(name="📋 Удирдлагын самбар", value="Түр суваг үүсэхэд гарч ирэх товчлуурууд:", inline=False)
            embed.add_field(name="Товчнууд", value="🔒 Түгжих | 🔓 Тайлах | ✏️ Нэр өөрчлөх | 👥 Хязгаар | 🚫 Хэрэглэгч хөөх", inline=False)
            embed.add_field(name="💡 Ашиглах заавар", value="Create Voice сувгийн тохиргоонд 'Text Channel' идэвхжүүлбэл удирдлагын самбар тухайн сувгийн текст чатад гарна.", inline=False)

        # ===== 13: AI Chat =====
        elif index == 13:
            embed.add_field(name="🤖 AI CHAT", value="", inline=False)
            embed.add_field(name="`/ai_setup` `/ai_toggle` `/ai_status` `/ai_personality`", value="Суваг тохируулах, идэвхжүүлэх/унтраах, төлөв, зан чанар солих", inline=True)
            embed.add_field(name="Зан чанарууд", value="😊 Найрсаг | 😏 Ёжтой | 🧙 Мэргэн | 🐱 Муур", inline=False)
            embed.add_field(name="📌 Ажиллах зарчим", value="Тохируулсан сувагт бичсэн мессеж бүрт AI (Groq) автоматаар хариулна. Сүүлийн хэдэн мессежийг контекст болгон ашиглана.", inline=False)

        # ===== 14: Role удирдлага =====
        elif index == 14:
            embed.add_field(name="🎭 ROLE УДИРДЛАГА", value="", inline=False)
            embed.add_field(name="Үндсэн role", value="`role give @user @role` – роль өгөх\n`role remove @user @role` – роль хасах", inline=False)
            embed.add_field(name="Түр role (TempRole)", value="`temprole give @user @role <хугацаа>` – түр роль өгөх (жишээ: 1h, 30m, 1d)\n`temprole remove @user @role` – хугацаанаас өмнө цуцлах", inline=False)
            embed.add_field(name="💡 Хугацааны формат", value="30s, 5m, 2h, 1d, 1w", inline=False)
            embed.add_field(name="🔁 Автомат", value="Түр role хугацаа дуусахад автоматаар хасагдана.", inline=False)

        # ===== 15: Нууц мэдүүлэг =====
        elif index == 15:
            embed.add_field(name="🤫 CONFESSIONS", value="", inline=False)
            embed.add_field(name="Тохиргоо", value="`/confess_setup` – сувгуудыг тохируулах\n`/confess_edit` – тохиргоо өөрчлөх", inline=False)
            embed.add_field(name="Мэдүүлэг", value="Тохируулсан сувагт мессеж бичихэд автоматаар нэргүй мэдүүлэг болно.", inline=False)
            embed.add_field(name="Админ командууд", value="`/confess_blacklist add/remove/list` – хориотой үгс\n`/confess_delete <ID>` – мэдүүлэг устгах\n`/confess_stats` – статистик", inline=False)
            embed.add_field(name="Хугацаа", value="Хэрэглэгч бүрт тохируулсан cooldown (анхдагч 30с) үйлчилнэ.", inline=False)

        # ===== 16: Giveaway =====
        elif index == 16:
            embed.add_field(name="🎁 GIVEAWAY", value="", inline=False)
            embed.add_field(name="Үүсгэх", value="`giveaway create` – giveaway эхлүүлэх\n`giveaway end <ID>` – дуусгах\n`giveaway reroll <ID>` – ялагчдыг дахин сонгох", inline=False)
            embed.add_field(name="Удирдлага", value="`giveaway cancel <ID>` – цуцлах\n`giveaway list` – идэвхтэй giveaway-үүд\n`giveaway entries <ID>` – оролцогчдын тоо", inline=False)
            embed.add_field(name="Оролцох", value="Giveaway мессеж дээрх 🎉 товчлуураар оролцоно.", inline=False)
            embed.add_field(name="Шагнал", value="Автоматаар тохируулсан хугацаанд дуусч, санамсаргүй ялагч шалгарна.", inline=False)

        # ===== 17: Мэндчилгээ =====
        elif index == 17:
            embed.add_field(name="👋 GREETINGS", value="", inline=False)
            embed.add_field(name="Тохиргоо", value="`/greeting_set welcome/goodbye/boost <суваг> [загварын ID]`\n`/greeting_toggle welcome/goodbye/boost/dm`", inline=False)
            embed.add_field(name="Загвар", value="`/template_create` – шинэ embed загвар үүсгэх\n`/template_edit <ID>` – загвар засварлах\n`/template_delete <ID>` – устгах\n`/template_list` – жагсаалт\n`/template_preview <ID>` – урьдчилан харах", inline=False)
            embed.add_field(name="Хувьсагчид", value="`/placeholders` – бүх хувьсагчдыг харах\nЖишээ: `{user:name}`, `{server:name}`", inline=False)
            embed.add_field(name="Статус", value="`/greeting_status` – одоогийн тохиргоо харах\n`/greeting_reset` – бүх тохиргоо устгах", inline=False)

        # ===== 18: Аватар лог =====
        elif index == 18:
            embed.add_field(name="🖼️ АВАТАР LOG", value="", inline=False)
            embed.add_field(name="Тохиргоо", value="`avatar_log <суваг> [true/false]` – лог суваг тохируулах\n`avatar_log_toggle` – идэвхжүүлэх/унтраах\n`avatar_log_status` – төлөв шалгах", inline=False)
            embed.add_field(name="Мэдэгдэл", value="Хэрэглэгч аватар солиход хуучин/шинэ зургийг embed хэлбэрээр илгээнэ.", inline=False)

        return embed

    @staticmethod
    def _get_prefix(bot):
        prefix = bot.command_prefix
        if callable(prefix):
            try:
                import inspect
                # Хэрэв prefix функц message параметр хүлээдэг бол бид зүгээр л "g" гэж үзнэ
                if 'message' in inspect.signature(prefix).parameters:
                    prefix = 'g'
                else:
                    prefix = prefix(bot, None)
            except:
                prefix = 'g'
        if isinstance(prefix, (list, tuple)):
            prefix = prefix[0] if prefix else 'g'
        elif not isinstance(prefix, str):
            prefix = 'g'
        return prefix


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='help', aliases=['h', 'commands', 'тусламж', 'ghelp'],
                             description="Бүх командын тусламж харах")
    async def help_command(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📖 Gurten | LGC командын тусламж",
            description="Доорх **dropdown цэснээс** хүссэн категорио сонгон, командуудыг харна уу.\n\n"
                        "Товчлуураар хуудас солих боломжтой.",
            color=PURPLE_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Доорх жагсаалтаас категори сонгоно уу | 180 секунд идэвхтэй")
        view = HelpView()
        await ctx.send(embed=embed, view=view)

    # ===== АЛДААНЫ ҮЕД ТУСЛАМЖ САНАЛ БОЛГОХ =====
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Хэрэглэгч буруу команд бичвэл тусламж руу чиглүүлэх"""
        if isinstance(error, commands.CommandNotFound):
            attempted = ctx.message.content.split()[0][len(ctx.prefix):]
            # Жижиг үсэгтэй, хэт богино биш үед л хариу өгнө
            if len(attempted) >= 2 and not attempted.startswith('_'):
                embed = discord.Embed(
                    title="❓ Команд олдсонгүй",
                    description=f"`{attempted}` гэж команд байхгүй байна.\n"
                                f"Бүх командыг харахын тулд `{ctx.prefix}help` гэж бичнэ үү.\n\n"
                                f"💡 **Зөвлөмж:** Та магадгүй `{ctx.prefix}{attempted}` гэх команд байгаа эсэхийг шалгана уу.",
                    color=ERROR_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text=f"Prefix: {ctx.prefix}")
                await ctx.send(embed=embed, delete_after=15)


async def setup(bot):
    await bot.add_cog(Help(bot))