import discord
from discord.ext import commands
import random
import os

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # GIF хавтаснуудын үндсэн зам
        self.gifs_base = os.path.join(os.path.dirname(__file__), "gifs")

    def _get_random_gif(self, action: str):
        """Тухайн үйлдлийн хавтсаас санамсаргүй .gif файл буцаана"""
        folder = os.path.join(self.gifs_base, action)
        if not os.path.isdir(folder):
            return None
        
        files = [f for f in os.listdir(folder) if f.endswith(".gif")]
        if not files:
            return None
            
        filepath = os.path.join(folder, random.choice(files))
        return discord.File(filepath, filename=f"{action}.gif")

    async def _send_action(self, ctx, action: str, texts: list, title: str, color, target: discord.Member = None):
        """Текст болон (боломжтой бол) гифтэй embed илгээх"""
        gif = self._get_random_gif(action)
        embed = discord.Embed(
            title=title,
            description=random.choice(texts),
            color=color
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        if gif:
            embed.set_image(url=f"attachment://{action}.gif")
            await ctx.send(embed=embed, file=gif)
        else:
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='ping')
    async def ping(self, ctx):
        """Bot-н хоцрогдол (latency) шалгах"""
        embed = discord.Embed(
            title="🏓 Pong!", 
            description=f"**Ping:** `{round(self.bot.latency * 1000)}ms`", 
            color=discord.Color.brand_green()
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='avatar', aliases=['av'])
    async def avatar(self, ctx, member: discord.Member = None):
        """Хэрэглэгчийн аватар зургийг харах"""
        target = member or ctx.author
        embed = discord.Embed(
            title=f"🖼️ {target.display_name} -н Аватар",
            color=discord.Color.blurple()
        )
        embed.set_image(url=target.display_avatar.url)
        await ctx.send(embed=embed)
    
    # ----------------------------------------------------------
    #  ACTION COMMANDS (GIF support)
    # ----------------------------------------------------------
    @commands.command(name='hug')
    async def hug(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [
                f"{ctx.author.mention} хэнийг ч юм тэврэхийг хүсэв... sadge.", 
                f"{ctx.author.mention} дэрээ чанга тэврээд санаа алдав."
            ]
            return await self._send_action(ctx, "hug", msgs, "🫂 ГАНЦААРДАЛ", discord.Color.orange())
        
        if target == ctx.author:
            msgs = [
                f"{ctx.author.mention} өөрийгөө тэвэрлээ. Self-love is important!", 
                f"{ctx.author.mention} өөртөө урам өгөн мөрөө цохив."
            ]
            return await self._send_action(ctx, "hug", msgs, "🫂 ӨӨРТӨӨ ХАЙРТАЙ", discord.Color.green())
            
        texts = [
            f"{ctx.author.mention} {target.mention}-г маш чанга тэвэрлээ! 🥰", 
            f"{ctx.author.mention} гүйж очоод {target.mention}-г тэврэн авав.", 
            f"{ctx.author.mention} {target.mention}-д дулаахан тэврэлт илгээлээ."
        ]
        await self._send_action(ctx, "hug", texts, "🫂 **ТЭВРЭЛТ**", discord.Color.green(), target)

    @commands.command(name='kiss')
    async def kiss(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} дэлгэцээ үнсэв бололтой..."]
            return await self._send_action(ctx, "kiss", msgs, "💋 ...", discord.Color.purple())
            
        if target == ctx.author:
            embed = discord.Embed(title="💋 ӨӨРТӨӨ...", description=f"{ctx.author.mention} толинд өөрийгөө үнсэхийг оролдов. 😅", color=discord.Color.purple())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-н хацар дээр нь үнсэв! 😳💖", 
            f"{ctx.author.mention} {target.mention}-н духан дээр зөөлөн үнсэв.", 
            f"{ctx.author.mention} гэнэт {target.mention}-г үнсэж орхилоо."
        ]
        await self._send_action(ctx, "kiss", texts, "💋 **ҮНСЭЛТ**", discord.Color.magenta(), target)

    @commands.command(name='slap')
    async def slap(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} хий дэмий л агаар алгадав."]
            return await self._send_action(ctx, "slap", msgs, "👋 АЛДАА", discord.Color.orange())
            
        if target == ctx.author:
            embed = discord.Embed(title="👋 WAKE UP", description=f"{ctx.author.mention} өөрийгөө алгадан сэргээв.", color=discord.Color.red())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-г чанга гэгч нь алгадлаа! 😖", 
            f"{ctx.author.mention} {target.mention}-нд 'Сэрээч!' гээд алгадав.", 
            f"{ctx.author.mention} {target.mention}-г даварч байна гээд алгадлаа."
        ]
        await self._send_action(ctx, "slap", texts, "👋 **АЛГАДАЛТ**", discord.Color.red(), target)

    @commands.command(name='pat')
    async def pat(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} хий хоосон зүйл илбэж байна..."]
            return await self._send_action(ctx, "pat", msgs, "🫳 ...", discord.Color.blue())
            
        if target == ctx.author:
            embed = discord.Embed(title="🫳 GOOD BOY/GIRL", description=f"{ctx.author.mention} өөрийнхөө толгойг илэв. Хааяа өөрийгөө магтах хэрэгтэй шүү.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-н толгойг зөөлөн илэв. 🌟", 
            f"{ctx.author.mention} {target.mention}-н үсийг арзайлгав.", 
            f"{ctx.author.mention} {target.mention}-д 'Сайн байлаа' гээд толгойд нь хүрэв."
        ]
        await self._send_action(ctx, "pat", texts, "🫳 **PAT PAT**", discord.Color.gold(), target)

    @commands.command(name='cuddle')
    async def cuddle(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} хөнжилдөө шургаад ганцаараа үлдэв..."]
            return await self._send_action(ctx, "cuddle", msgs, "🤗 ЭРХЛЭХ ХҮНГҮЙ", discord.Color.orange())
            
        if target == ctx.author:
            embed = discord.Embed(title="🤗 COMFY", description=f"{ctx.author.mention} хөнжлөөрөө өөрийгөө ороож авав.", color=discord.Color.brand_green())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-тай тэврэлдэн эрхэлж байна. 🛋️", 
            f"{ctx.author.mention} болон {target.mention} нар дулаахан тэврэлдэв.", 
            f"{ctx.author.mention} {target.mention}-д наалдаад хэвтлээ."
        ]
        await self._send_action(ctx, "cuddle", texts, "🤗 **ЭРХЛЭЛТ**", discord.Color.teal(), target)

    @commands.command(name='bite')
    async def bite(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} шүдээ хавирав..."]
            return await self._send_action(ctx, "bite", msgs, "🦷 GRRR", discord.Color.orange())
            
        if target == ctx.author:
            embed = discord.Embed(title="🦷 OUCH", description=f"{ctx.author.mention} өөрийгөө хазаж үзээд 'Аяа!' гэв.", color=discord.Color.red())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-г зөөлөн хазаж авав! 🐺", 
            f"{ctx.author.mention} {target.mention}-н гар руу дайрч хазав!", 
            f"{ctx.author.mention} тоглоомоор {target.mention}-г хазлаа."
        ]
        await self._send_action(ctx, "bite", texts, "🦷 **ХАЗАЛТ**", discord.Color.orange(), target)

    @commands.command(name='poke')
    async def poke(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} дэлгэцээ хатгаж байна."]
            return await self._send_action(ctx, "poke", msgs, "👉 ХАТГАХ", discord.Color.blue())
            
        if target == ctx.author:
            embed = discord.Embed(title="👉 УЙДАЛТ", description=f"{ctx.author.mention} өөрийгөө хатгаж тоглож байна.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-г хуруугаараа хатгав! 'Анхаарлаа хандуулаач!'", 
            f"{ctx.author.mention} {target.mention}-н мөрөн дээр тогшив.", 
            f"{ctx.author.mention} {target.mention}-г зогсолтгүй хатгаж байна."
        ]
        await self._send_action(ctx, "poke", texts, "👉 **POKE**", discord.Color.green(), target)

    @commands.command(name='wave')
    async def wave(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} хэнд ч юм гараа даллав..."]
            return await self._send_action(ctx, "wave", msgs, "👋 HELLO?", discord.Color.blue())
            
        texts = [
            f"{ctx.author.mention} {target.mention} руу гараа даллаж байна! 👋", 
            f"{ctx.author.mention} холоос {target.mention}-г хараад баяртайгаар даллав.", 
            f"{ctx.author.mention} {target.mention}-тай мэндчиллээ."
        ]
        await self._send_action(ctx, "wave", texts, "👋 **МЭНДЧИЛГЭЭ**", discord.Color.brand_green(), target)

    @commands.command(name='punch')
    async def punch(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} хий дэмий л нударга зангидав."]
            return await self._send_action(ctx, "punch", msgs, "👊 SHADOW BOXING", discord.Color.orange())
            
        if target == ctx.author:
            embed = discord.Embed(title="👊 OOF", description=f"{ctx.author.mention} өөрийгөө дэлсээд авав.", color=discord.Color.red())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-г нударгаар дэлсээд авав! 💢", 
            f"{ctx.author.mention} {target.mention} руу хүчтэй цохилт илгээв.", 
            f"{ctx.author.mention} {target.mention}-н мөр рүү тоглоомоор цохив."
        ]
        await self._send_action(ctx, "punch", texts, "👊 **ЦОХИЛТ**", discord.Color.red(), target)

    @commands.command(name='boop')
    async def boop(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="👆 BOOP", description=f"{ctx.author.mention} агаар boop хийв...", color=discord.Color.blue())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-н хамар дээр 'Boop!' хийлээ. 🐶", 
            f"{ctx.author.mention} гэнэт {target.mention}-г boop хийж цочоов."
        ]
        await self._send_action(ctx, "boop", texts, "👆 **BOOP**", discord.Color.brand_green(), target)

    @commands.command(name='bully')
    async def bully(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="😈 ЭНХ ТАЙВАН", description=f"{ctx.author.mention} хэнийг ч дээрэлхэхгүй байхаар шийдлээ. Good vibes only!", color=discord.Color.brand_green())
            return await ctx.send(embed=embed)
            
        if target == ctx.author:
            embed = discord.Embed(title="😈 BRUH", description=f"{ctx.author.mention} өөртөө хэтэрхий хатуу хандаж байна.", color=discord.Color.orange())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-г 'Ур чадвар чинь дутаж байна!' гэж bully хийв. 😠", 
            f"{ctx.author.mention} {target.mention}-г дээрэлхээд, дараа нь тоглосон юм аа гэв."
        ]
        await self._send_action(ctx, "bully", texts, "😈 **BULLY**", discord.Color.red(), target)

    @commands.command(name='handhold')
    async def handhold(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="🤝 ...", description=f"{ctx.author.mention} гараа халаасандаа хийв.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
            
        if target == ctx.author:
            embed = discord.Embed(title="🤝 ПААХ", description=f"{ctx.author.mention} өөрийнхөө хоёр гарыг атгалцав.", color=discord.Color.brand_green())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-н гараас хөтөллөө! 👫", 
            f"{ctx.author.mention} болон {target.mention} нар хөтлөлцөн алхаж байна."
        ]
        await self._send_action(ctx, "handhold", texts, "🤝 **ХӨТЛӨЛЦӨХ**", discord.Color.teal(), target)

    @commands.command(name='stare')
    async def stare(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="👀 ГӨЛРӨХ", description=f"{ctx.author.mention} хана руу ширтэн гөлөрчээ.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-г нүд цавчилгүй ширтэж байна. 🔍", 
            f"{ctx.author.mention} {target.mention} руу сэжиглэнгүй харав. 'Sus...'", 
            f"{ctx.author.mention} {target.mention}-н нүд рүү гүн гүнзгий ширтлээ."
        ]
        await self._send_action(ctx, "stare", texts, "👀 **ШИРТЭХ**", discord.Color.purple(), target)

    @commands.command(name='highfive')
    async def highfive(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="🙌 АЛГА ТАШИХ", description=f"{ctx.author.mention} өөртөө баяр хүргэн алга ташив.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
            
        if target == ctx.author:
            embed = discord.Embed(title="🙌 SELF-FIVE", description=f"{ctx.author.mention} өөртөө high-five өгөв!", color=discord.Color.brand_green())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} болон {target.mention} нар high-five цохилцов! 🖐️", 
            f"{ctx.author.mention} {target.mention} руу гараа сунган high-five өглөө."
        ]
        await self._send_action(ctx, "highfive", texts, "🙌 **HIGH-FIVE**", discord.Color.brand_green(), target)

    @commands.command(name='snuggle')
    async def snuggle(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="🛋️ COMFY", description=f"{ctx.author.mention} хөнжилдөө шургаад тухтай нь аргагүй хэвтлээ.", color=discord.Color.orange())
            return await ctx.send(embed=embed)
            
        if target == ctx.author:
            embed = discord.Embed(title="🛋️ БҮМБҮҮШ", description=f"{ctx.author.mention} хөнжлөөрөө өөрийгөө хуглаж ороов.", color=discord.Color.brand_green())
            return await ctx.send(embed=embed)
            
        texts = [
            f"{ctx.author.mention} {target.mention}-тай наалдаж эрхэллээ! 🛌", 
            f"{ctx.author.mention} {target.mention}-н мөрөнд наалдаад амарч байна."
        ]
        await self._send_action(ctx, "snuggle", texts, "🛋️ **СУУРЬШИХ**", discord.Color.teal(), target)

    # ----------------------------------------------------------
    #  EMOTE COMMANDS (GIF support)
    # ----------------------------------------------------------
    @commands.command(name='cry')
    async def cry(self, ctx):
        texts = [
            f"{ctx.author.mention} асгартал уйлж байна... 😢", 
            f"{ctx.author.mention} нулимсаа арчиж, санаа алдав.", 
            f"{ctx.author.mention}-д хэн нэгний тэврэлт хэрэгтэй бололтой."
        ]
        await self._send_action(ctx, "cry", texts, "😢 **SADGE**", discord.Color.blue())

    @commands.command(name='dance')
    async def dance(self, ctx):
        texts = [
            f"{ctx.author.mention} хэмнэлд автан бүжиглэж эхэллээ! 🕺", 
            f"{ctx.author.mention} vibe check passed, галзуу бүжиглэж байна.", 
            f"{ctx.author.mention} шалыг эзэгнэж байна даа."
        ]
        await self._send_action(ctx, "dance", texts, "💃 **VIBING**", discord.Color.gold())

    @commands.command(name='laugh')
    async def laugh(self, ctx):
        texts = [
            f"{ctx.author.mention} элгээ хөштөл инээж байна! 🤣", 
            f"{ctx.author.mention} инээсээр байгаад нулимс нь гарчээ.", 
            f"{ctx.author.mention} LMAO."
        ]
        await self._send_action(ctx, "laugh", texts, "😂 **LMAO**", discord.Color.brand_green())

    @commands.command(name='sleep')
    async def sleep(self, ctx):
        texts = [
            f"{ctx.author.mention} afk болж, гүн нойронд автлаа. 💤", 
            f"{ctx.author.mention} хурхирч эхлэв. Одоо бүү саад бол!", 
            f"{ctx.author.mention} амрахаар хэвтлээ, Good night."
        ]
        await self._send_action(ctx, "sleep", texts, "😴 **AFK / УНТАХ**", discord.Color.dark_blue())

    @commands.command(name='think')
    async def think(self, ctx):
        texts = [
            f"{ctx.author.mention} нэгийг гүнзгий бодож байна... 🤔", 
            f"{ctx.author.mention} тархиа 100% ажиллуулж эхэллээ.", 
            f"{ctx.author.mention} 'Хммм...'"
        ]
        await self._send_action(ctx, "think", texts, "🤔 **БОДОЛТ**", discord.Color.purple())

    @commands.command(name='angry')
    async def angry(self, ctx):
        texts = [
            f"{ctx.author.mention} үнэхээр ууртай байна. Бултсан нь дээр байх шүү! 😤", 
            f"{ctx.author.mention} шүдээ зуун уурлаж байна.", 
            f"{ctx.author.mention} keyboard-оо эвдэх нь ээ."
        ]
        await self._send_action(ctx, "angry", texts, "😠 **УУР ХИЛЭН**", discord.Color.dark_red())

    @commands.command(name='happy')
    async def happy(self, ctx):
        texts = [
            f"{ctx.author.mention} маш их баяртай байна! 🥳", 
            f"{ctx.author.mention} нүүр дүүрэн инээмсэглэл тодрууллаа.", 
            f"{ctx.author.mention} hype болоод үсэрч байна!"
        ]
        await self._send_action(ctx, "happy", texts, "😊 **HYPE**", discord.Color.brand_green())

async def setup(bot):
    await bot.add_cog(Fun(bot))