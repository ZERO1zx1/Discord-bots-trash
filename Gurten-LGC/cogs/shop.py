import discord
from discord.ext import commands
from discord.ui import Select, View, Button
import random
import time
import io
import os
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFont

# ---------- Фонт ----------
try:
    from cogs.font_utils import load_font as _load_font
except ImportError:
    def _load_font(size=40, bold=True):
        paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ] if bold else [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except:
                    pass
        return ImageFont.load_default(size)

# ===== COLORS (неон палитр) =====
EMBED_COLOR = 0x2b2d31
SUCCESS_COLOR = 0x57f287
ERROR_COLOR = 0xed4245
WARNING_COLOR = 0xfee75c
GOLD_COLOR = 0xffd700
PURPLE_COLOR = 0x9b59b6
INFO_COLOR = 0x3498db
NEON_PINK = 0xFF10F0
NEON_GREEN = 0x39FF14
NEON_YELLOW = 0xCCFF00

# ---------- VAPE БРЕНД, ЗАГВАР, АМТ ----------
VAPE_BRANDS = {
    "MOTI": {
        "emoji": "💨",
        "models": {
            "BANG series": {"price": 35000, "desc": "Хүчтэй амт, удаан хэрэглээ.", "strength": 2},
            "PLAY series": {"price": 30000, "desc": "Тоглоомын дизайн.", "strength": 1},
            "GO Pro series": {"price": 40000, "desc": "Мэргэжлийн түвшний.", "strength": 3},
            "X Mini": {"price": 25000, "desc": "Жижиг, авсаархан.", "strength": 1},
            "Dual mesh series": {"price": 38000, "desc": "Давхар mesh ороомогтой.", "strength": 2},
        }
    },
    "SnowPlus": {
        "emoji": "❄️",
        "models": {
            "SnowPlus Lite": {"price": 28000, "desc": "Хөнгөн, зөөврийн.", "strength": 1},
            "SnowPlus Pro": {"price": 42000, "desc": "Сайжруулсан батерей.", "strength": 3},
            "Alien series": {"price": 45000, "desc": "Хачин дизайн.", "strength": 2},
            "Smart display series": {"price": 48000, "desc": "Дэлгэцтэй ухаалаг.", "strength": 2},
            "Ice flavor line": {"price": 32000, "desc": "Мөсөн амтны шугам.", "strength": 1},
        }
    },
    "WAKA": {
        "emoji": "🌊",
        "models": {
            "WAKA Smash": {"price": 30000, "desc": "Хүчтэй цохилт.", "strength": 2},
            "WAKA SoPro": {"price": 36000, "desc": "Сонирхогчидод.", "strength": 3},
            "WAKA Mini": {"price": 22000, "desc": "Жижиг хэмжээтэй.", "strength": 1},
            "Dual flavor edition": {"price": 40000, "desc": "Хос амттай хувилбар.", "strength": 2},
            "High puff series": {"price": 44000, "desc": "Олон удаагийн хэрэглээ.", "strength": 3},
        }
    },
    "MASKKING": {
        "emoji": "🎭",
        "models": {
            "High Pro": {"price": 42000, "desc": "Дээд зэрэглэлийн.", "strength": 3},
            "Neo series": {"price": 35000, "desc": "Орчин үеийн.", "strength": 2},
            "GT series": {"price": 38000, "desc": "Гранд турэр.", "strength": 2},
            "Cube design": {"price": 33000, "desc": "Куб хэлбэрийн.", "strength": 1},
            "Disposable pod line": {"price": 20000, "desc": "Нэг удаагийн.", "strength": 1},
        }
    }
}

VAPE_FLAVORS = {
    "Strawberry Ice": {"emoji": "🍓", "desc": "Гүзээлзгэний мөсөн амт"},
    "Blueberry Mint": {"emoji": "🫐", "desc": "Нэрс, мэдрээний холимог"},
    "Watermelon Ice": {"emoji": "🍉", "desc": "Тарвасны мөсөн амт"},
    "Grape Ice": {"emoji": "🍇", "desc": "Усан үзмийн мөсөн амт"},
    "Mango Peach": {"emoji": "🥭", "desc": "Манго, тоорын холимог"},
    "Cola Ice": {"emoji": "🥤", "desc": "Кола мөсөн амт"},
    "Energy Drink": {"emoji": "⚡", "desc": "Энержи ундааны амт"},
    "Mixed Berry": {"emoji": "🫐", "desc": "Холимог жимсний амт"},
    "Lush Ice": {"emoji": "🧊", "desc": "Луш мөсөн амт"},
    "Kiwi Passionfruit": {"emoji": "🥝", "desc": "Киви, пассионфрут"},
}

# ---------- БҮХ БАРАА ----------
SHOP_ITEMS = [
    # Drinks
    {"id":1,"name":"Beer","price":30000,"emoji":"🍺","desc":"Сэрүүн шар айраг.","strength":12,"category":"drink","rarity":"common"},
    {"id":2,"name":"Wine","price":30000,"emoji":"🍷","desc":"Улаан дарс.","strength":15,"category":"drink","rarity":"common"},
    {"id":3,"name":"Vodka","price":25000,"emoji":"🥃","desc":"Цэвэр архи.","strength":25,"category":"drink","rarity":"common"},
    {"id":4,"name":"Whiskey","price":40000,"emoji":"🥃","desc":"Модон торхонд хөгшрүүлсэн.","strength":30,"category":"drink","rarity":"rare"},
    {"id":5,"name":"Rum","price":35000,"emoji":"🍹","desc":"Чихрийн нишингийн ром.","strength":22,"category":"drink","rarity":"common"},
    {"id":6,"name":"Tequila","price":38000,"emoji":"🍸","desc":"Агаваас хийсэн.","strength":28,"category":"drink","rarity":"common"},
    {"id":7,"name":"Gin","price":32000,"emoji":"🍸","desc":"Арц жимсээр амтлагдсан.","strength":20,"category":"drink","rarity":"common"},
    {"id":8,"name":"Brandy","price":42000,"emoji":"🥃","desc":"Дарсны спирт.","strength":32,"category":"drink","rarity":"rare"},
    {"id":9,"name":"Sake","price":28000,"emoji":"🍶","desc":"Япон цагаан будааны дарс.","strength":18,"category":"drink","rarity":"common"},
    {"id":10,"name":"Liqueur","price":32000,"emoji":"🍹","desc":"Чихэрлэг жимсний ликёр.","strength":15,"category":"drink","rarity":"common"},
    # Cigarette
    {"id":60,"name":"Тамхи","price":5000,"emoji":"🚬","desc":"Энгийн тамхи.","strength":8,"category":"intoxicant","rarity":"common"},
    # Rings (old)
    {"id":11,"name":"Silver Ring","price":50000,"emoji":"💍","desc":"Гялалзсан мөнгөн бөгж.","strength":0,"category":"ring","subcat":"old","rarity":"common"},
    {"id":12,"name":"Gold Ring","price":70000,"emoji":"💍","desc":"Дэгжин алтан бөгж.","strength":0,"category":"ring","subcat":"old","rarity":"rare"},
    {"id":13,"name":"Pearl Ring","price":100000,"emoji":"💍","desc":"Үнэтэй сувдан бөгж.","strength":0,"category":"ring","subcat":"old","rarity":"epic"},
    {"id":14,"name":"Gemstone Ring","price":80000,"emoji":"💍","desc":"Оникс чулуун бөгж.","strength":0,"category":"ring","subcat":"old","rarity":"rare"},
    {"id":15,"name":"Royal Ring","price":60000,"emoji":"👑","desc":"Хааны удам залгасан бөгж.","strength":0,"category":"ring","subcat":"old","rarity":"epic"},
    # Gems
    {"id":36,"name":"Diamond","price":500000,"emoji":"💎","desc":"Хамгийн хатуу, цэвэр.","strength":0,"category":"ring","subcat":"gem","rarity":"legendary"},
    {"id":37,"name":"Ruby","price":400000,"emoji":"🔴","desc":"Улаан өнгийн чулуу.","strength":0,"category":"ring","subcat":"gem","rarity":"epic"},
    {"id":38,"name":"Sapphire","price":450000,"emoji":"🔵","desc":"Хөх өнгийн чулуу.","strength":0,"category":"ring","subcat":"gem","rarity":"epic"},
    {"id":39,"name":"Emerald","price":420000,"emoji":"🟢","desc":"Ногоон өнгийн чулуу.","strength":0,"category":"ring","subcat":"gem","rarity":"epic"},
    {"id":40,"name":"Pearl","price":350000,"emoji":"⚪","desc":"Далайн эрдэнэ.","strength":0,"category":"ring","subcat":"gem","rarity":"rare"},
    {"id":41,"name":"Topaz","price":250000,"emoji":"🟡","desc":"Цэнхэр, шаргал өнгөтэй.","strength":0,"category":"ring","subcat":"gem","rarity":"rare"},
    {"id":42,"name":"Jade","price":380000,"emoji":"🟢","desc":"Энх тайван, урт насны бэлэгдэл.","strength":0,"category":"ring","subcat":"gem","rarity":"epic"},
    # Metals
    {"id":43,"name":"Gold","price":300000,"emoji":"🟡","desc":"Үнэ цэнэтэй, зэврэлтгүй.","strength":0,"category":"ring","subcat":"metal","rarity":"rare"},
    {"id":44,"name":"Silver","price":150000,"emoji":"⚪","desc":"Өдөр тутамд тохиромжтой.","strength":0,"category":"ring","subcat":"metal","rarity":"common"},
    {"id":45,"name":"Copper","price":80000,"emoji":"🟠","desc":"Эрүүл мэндэд сайн.","strength":0,"category":"ring","subcat":"metal","rarity":"common"},
    {"id":46,"name":"Platinum","price":550000,"emoji":"⚪","desc":"Маш бат бөх, харшилгүй.","strength":0,"category":"ring","subcat":"metal","rarity":"legendary"},
    {"id":47,"name":"Steel","price":60000,"emoji":"⚪","desc":"Зураасанд тэсвэртэй.","strength":0,"category":"ring","subcat":"metal","rarity":"common"},
    {"id":48,"name":"Titanium","price":120000,"emoji":"⚪","desc":"Хөнгөн, хүчтэй.","strength":0,"category":"ring","subcat":"metal","rarity":"rare"},
    # New rings (ID 70-79)
    {"id":70,"name":"Мөнгөн бөгж","price":85000,"emoji":"⚪","desc":"Цэвэр мөнгөөр хийсэн.","strength":0,"category":"ring","subcat":"new","rarity":"common"},
    {"id":71,"name":"Хар бөгж","price":95000,"emoji":"⚫","desc":"Мат хар minimalist.","strength":0,"category":"ring","subcat":"new","rarity":"common"},
    {"id":72,"name":"Chrome Hearts бөгж","price":250000,"emoji":"💠","desc":"Chrome Hearts загвар.","strength":0,"category":"ring","subcat":"new","rarity":"epic"},
    {"id":73,"name":"Gothic бөгж","price":180000,"emoji":"🕷️","desc":"Готик хээтэй.","strength":0,"category":"ring","subcat":"new","rarity":"rare"},
    {"id":74,"name":"Skull бөгж","price":200000,"emoji":"💀","desc":"Гавлын хэлбэртэй.","strength":0,"category":"ring","subcat":"new","rarity":"rare"},
    {"id":75,"name":"Minimal flat бөгж","price":110000,"emoji":"🔲","desc":"Хавтгай, minimalist.","strength":0,"category":"ring","subcat":"new","rarity":"common"},
    {"id":76,"name":"Signet бөгж","price":160000,"emoji":"🖋️","desc":"Удам угсааны хэвлэмэл.","strength":0,"category":"ring","subcat":"new","rarity":"rare"},
    {"id":77,"name":"Давхар хурууны бөгж","price":140000,"emoji":"✌️","desc":"Хоёр хуруунд зүүх.","strength":0,"category":"ring","subcat":"new","rarity":"common"},
    {"id":78,"name":"Чулуун бөгж","price":130000,"emoji":"💠","desc":"Байгалийн чулуутай.","strength":0,"category":"ring","subcat":"new","rarity":"common"},
    {"id":79,"name":"Загалмайтай бөгж","price":120000,"emoji":"✝️","desc":"Загалмайн хэлбэртэй.","strength":0,"category":"ring","subcat":"new","rarity":"common"},
    # Аксессуарууд
    {"id":80,"name":"Cuban мөнгөн гинж","price":200000,"emoji":"💎","desc":"Сонгодог Cuban гинж.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"rare"},
    {"id":81,"name":"Miami Cuban гинж","price":220000,"emoji":"💎","desc":"Илүү бүдүүн Miami Cuban.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"rare"},
    {"id":82,"name":"Rope эрчилсэн гинж","price":180000,"emoji":"⛓️","desc":"Олс мэт эрчилсэн.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"common"},
    {"id":83,"name":"Tennis чулуун гинж","price":350000,"emoji":"💎","desc":"Чулуун суулгацтай.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"epic"},
    {"id":84,"name":"Box дөрвөлжин гинж","price":190000,"emoji":"🔗","desc":"Дөрвөлжин холбоостой.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"common"},
    {"id":85,"name":"Figaro гинж","price":170000,"emoji":"⛓️","desc":"Хосолсон холбоос.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"common"},
    {"id":86,"name":"Snake могой гинж","price":210000,"emoji":"🐍","desc":"Могой хэлбэрийн.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"rare"},
    {"id":87,"name":"Minimal мөнгөн зүүлт","price":120000,"emoji":"✨","desc":"Цэвэр minimalist зүүлт.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"common"},
    {"id":88,"name":"Давхарласан гинж","price":160000,"emoji":"⛓️","desc":"Давхарлан зүүх гинж.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"common"},
    {"id":89,"name":"Нарийн aesthetic зүүлт","price":110000,"emoji":"🌟","desc":"Гоёмсог aesthetic.","strength":0,"category":"accessory","subcat":"necklace_minimal","rarity":"common"},
    {"id":90,"name":"Хар металл гинж","price":150000,"emoji":"🖤","desc":"Хар өнгийн металл.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"common"},
    {"id":91,"name":"Өргөстэй spike гинж","price":170000,"emoji":"🌵","desc":"Өргөстэй spike.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"rare"},
    {"id":92,"name":"Gothic загварын гинж","price":190000,"emoji":"🦇","desc":"Готик хэв маяг.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"rare"},
    {"id":93,"name":"Chrome гинж","price":210000,"emoji":"🔩","desc":"Гялалзсан chrome.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"rare"},
    {"id":94,"name":"Skull pendant","price":230000,"emoji":"💀","desc":"Гавлын хэлбэртэй зүүлт.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"epic"},
    {"id":95,"name":"Загалмайтай pendant","price":140000,"emoji":"✝️","desc":"Загалмай хэлбэрийн.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"common"},
    {"id":96,"name":"Razor blade зүүлт","price":130000,"emoji":"🪒","desc":"Салхивч хэлбэрийн.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"common"},
    {"id":97,"name":"Dog tag зүүлт","price":120000,"emoji":"🏷️","desc":"Цэргийн dog tag.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"common"},
    {"id":98,"name":"Цоож pendant","price":110000,"emoji":"🔒","desc":"Цоож хэлбэртэй.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"common"},
    {"id":99,"name":"Cyberpunk зүүлт","price":250000,"emoji":"🤖","desc":"Ирээдүйн cyberpunk.","strength":0,"category":"accessory","subcat":"necklace_dark","rarity":"epic"},
    {"id":100,"name":"Мөнгөн бугуйвч","price":140000,"emoji":"✨","desc":"Энгийн мөнгөн бугуйвч.","strength":0,"category":"accessory","subcat":"bracelet_minimal","rarity":"common"},
    {"id":101,"name":"Cuban бугуйвч","price":160000,"emoji":"💎","desc":"Cuban загвар.","strength":0,"category":"accessory","subcat":"bracelet_minimal","rarity":"rare"},
    {"id":102,"name":"Соронзон бугуйвч","price":120000,"emoji":"🧲","desc":"Соронзон түгжээтэй.","strength":0,"category":"accessory","subcat":"bracelet_minimal","rarity":"common"},
    {"id":103,"name":"Stainless steel бугуйвч","price":100000,"emoji":"🔩","desc":"Зэвэрдэггүй ган.","strength":0,"category":"accessory","subcat":"bracelet_minimal","rarity":"common"},
    {"id":104,"name":"Давхарласан bracelet set","price":180000,"emoji":"⛓️","desc":"Давхарлан зүүх багц.","strength":0,"category":"accessory","subcat":"bracelet_minimal","rarity":"common"},
    {"id":105,"name":"Хар чулуун бугуйвч","price":110000,"emoji":"🖤","desc":"Хар байгалийн чулуу.","strength":0,"category":"accessory","subcat":"bracelet_minimal","rarity":"common"},
    {"id":106,"name":"Matte black бугуйвч","price":130000,"emoji":"⚫","desc":"Мат хар өнгөтэй.","strength":0,"category":"accessory","subcat":"bracelet_minimal","rarity":"common"},
    {"id":107,"name":"Цагаан чулуун бугуйвч","price":110000,"emoji":"⚪","desc":"Цагаан өнгийн чулуун.","strength":0,"category":"accessory","subcat":"bracelet_minimal","rarity":"common"},
    {"id":108,"name":"Chain бугуйвч","price":150000,"emoji":"⛓️","desc":"Гинж хэлбэрийн.","strength":0,"category":"accessory","subcat":"bracelet_punk","rarity":"common"},
    {"id":109,"name":"Арьсан strap","price":120000,"emoji":"🏍️","desc":"Жинхэнэ арьсан.","strength":0,"category":"accessory","subcat":"bracelet_punk","rarity":"common"},
    {"id":110,"name":"Chrome бугуйвч","price":170000,"emoji":"🔩","desc":"Chrome өнгөт.","strength":0,"category":"accessory","subcat":"bracelet_punk","rarity":"rare"},
    {"id":111,"name":"Spike өргөстэй","price":140000,"emoji":"🌵","desc":"Өргөстэй spike.","strength":0,"category":"accessory","subcat":"bracelet_punk","rarity":"rare"},
    {"id":112,"name":"Cyberpunk бугуйвч","price":200000,"emoji":"🤖","desc":"Ирээдүйн cyberpunk.","strength":0,"category":"accessory","subcat":"bracelet_punk","rarity":"epic"},
    {"id":113,"name":"Tactical бугуйвч","price":180000,"emoji":"🎖️","desc":"Tactical загвар.","strength":0,"category":"accessory","subcat":"bracelet_punk","rarity":"rare"},
    {"id":114,"name":"Techwear wrist accessory","price":160000,"emoji":"⌚","desc":"Techwear бугуйн.","strength":0,"category":"accessory","subcat":"bracelet_punk","rarity":"common"},
    {"id":115,"name":"Gothic cuff","price":190000,"emoji":"🦇","desc":"Готик том cuff.","strength":0,"category":"accessory","subcat":"bracelet_punk","rarity":"rare"},
    {"id":120,"name":"Wallet chain","price":130000,"emoji":"⛓️","desc":"Түрийвчний гинж.","strength":0,"category":"accessory","subcat":"techwear","rarity":"common"},
    {"id":121,"name":"Cargo belt","price":150000,"emoji":"🪖","desc":"Cargo бүс.","strength":0,"category":"accessory","subcat":"techwear","rarity":"common"},
    {"id":122,"name":"Keychain accessory","price":50000,"emoji":"🔑","desc":"Түлхүүрийн гоёл.","strength":0,"category":"accessory","subcat":"techwear","rarity":"common"},
    {"id":123,"name":"Carabiner hook","price":40000,"emoji":"🪝","desc":"Карабин дэгээ.","strength":0,"category":"accessory","subcat":"techwear","rarity":"common"},
    {"id":124,"name":"Tactical бээлий","price":120000,"emoji":"🧤","desc":"Tactical загварын бээлий.","strength":0,"category":"accessory","subcat":"techwear","rarity":"common"},
    {"id":125,"name":"Хуруугүй бээлий","price":90000,"emoji":"🧤","desc":"Хуруугүй загвар.","strength":0,"category":"accessory","subcat":"techwear","rarity":"common"},
    {"id":126,"name":"Crossbody bag","price":250000,"emoji":"🎒","desc":"Цээжний цүнх.","strength":0,"category":"accessory","subcat":"techwear","rarity":"rare"},
    {"id":127,"name":"Chest rig цүнх","price":280000,"emoji":"🎒","desc":"Цээжний тактикийн цүнх.","strength":0,"category":"accessory","subcat":"techwear","rarity":"epic"},
    {"id":128,"name":"Хар шил","price":110000,"emoji":"🕶️","desc":"Сонгодог хар шил.","strength":0,"category":"accessory","subcat":"y2k","rarity":"common"},
    {"id":129,"name":"Rectangle шил","price":130000,"emoji":"👓","desc":"Дөрвөлжин хэлбэрийн шил.","strength":0,"category":"accessory","subcat":"y2k","rarity":"common"},
    {"id":130,"name":"Chrome sunglasses","price":150000,"emoji":"🕶️","desc":"Chrome өнгөт шил.","strength":0,"category":"accessory","subcat":"y2k","rarity":"rare"},
    {"id":131,"name":"Balaclava маск","price":70000,"emoji":"🎭","desc":"Нүүр бүтээх маск.","strength":0,"category":"accessory","subcat":"y2k","rarity":"common"},
    {"id":132,"name":"Beanie малгай","price":60000,"emoji":"🧢","desc":"Ноосон beanie.","strength":0,"category":"accessory","subcat":"y2k","rarity":"common"},
    {"id":133,"name":"Ear cuff","price":80000,"emoji":"🦻","desc":"Чихний ear cuff.","strength":0,"category":"accessory","subcat":"y2k","rarity":"common"},
    {"id":134,"name":"Ээмэг","price":50000,"emoji":"💎","desc":"Гоёмсог ээмэг.","strength":0,"category":"accessory","subcat":"y2k","rarity":"common"},
    {"id":135,"name":"Piercing accessory","price":60000,"emoji":"💉","desc":"Piercing хэв маягийн гоёл.","strength":0,"category":"accessory","subcat":"y2k","rarity":"common"},
]

BASE_VAPE_ITEMS = []
for brand, data in VAPE_BRANDS.items():
    for model, mdata in data["models"].items():
        BASE_VAPE_ITEMS.append({
            "id": 3000 + len(BASE_VAPE_ITEMS),
            "name": f"{brand} {model}",
            "price": mdata["price"],
            "emoji": data["emoji"],
            "desc": mdata["desc"],
            "strength": mdata["strength"],
            "category": "vape_base",
            "brand": brand,
            "model": model,
            "rarity": "common"
        })

ALL_VAPE_COMBOS = {}
for brand, data in VAPE_BRANDS.items():
    for model, mdata in data["models"].items():
        for flavor, fdata in VAPE_FLAVORS.items():
            combo_id = 4000 + len(ALL_VAPE_COMBOS)
            ALL_VAPE_COMBOS[combo_id] = {
                "id": combo_id,
                "name": f"{brand} {model} - {flavor}",
                "price": mdata["price"],
                "emoji": data["emoji"],
                "desc": f"{mdata['desc']} | Амт: {flavor}",
                "strength": mdata["strength"],
                "category": "vape",
                "brand": brand,
                "model": model,
                "flavor": flavor,
                "rarity": "rare" if mdata["strength"] >= 3 else "common"
            }

MAX_INTOXICATION = 100
INTOXICATION_LEVELS = [
    (0, "🧊 Тэргэн", 0x00ffff),
    (15, "😊 Хөнгөн сэрүүлэл", 0x2ecc71),
    (35, "😌 Дунд зэрэг", 0xf1c40f),
    (60, "🤪 Харуун согтол", 0xe67e22),
    (85, "🥴 Хүчтэй согтол", 0xe74c3c),
    (100, "😵 Барж байхаа мэдэхгүй", 0x8e44ad)
]


class FlavorSelectView(View):
    def __init__(self, cog, ctx, base_item):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.base_item = base_item
        self.flavor_select = Select(
            placeholder=f"Амт сонгох ({base_item['name']})",
            options=[discord.SelectOption(label=flavor, emoji=fdata["emoji"], value=flavor)
                     for flavor, fdata in VAPE_FLAVORS.items()]
        )
        self.flavor_select.callback = self.select_flavor
        self.add_item(self.flavor_select)

    async def select_flavor(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("❌ Энэ сонголтыг хийх боломжгүй.", ephemeral=True)
        flavor = self.flavor_select.values[0]
        combo_id = None
        for cid, combo in ALL_VAPE_COMBOS.items():
            if combo["brand"] == self.base_item["brand"] and combo["model"] == self.base_item["model"] and combo["flavor"] == flavor:
                combo_id = cid
                break
        if combo_id is None:
            return await interaction.response.send_message("❌ Алдаа: вайп олдсонгүй.", ephemeral=True)
        economy = self.cog.bot.get_cog("Economy")
        if not economy: return await interaction.response.send_message("❌ Системийн алдаа.", ephemeral=True)
        guild_id = self.ctx.guild.id
        balance = await economy.get_balance(self.ctx.author.id, guild_id)
        price = self.base_item["price"]
        if balance < price:
            embed = discord.Embed(title="❌ Хангалтгүй мөнгө",
                                  description=f"**{ALL_VAPE_COMBOS[combo_id]['emoji']} {ALL_VAPE_COMBOS[combo_id]['name']}** худалдаж авахад **{price:,}** ₮ шаардлагатай.\nТаны үлдэгдэл: `{balance:,}` ₮",
                                  color=ERROR_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        stock_cog = self.cog.bot.get_cog("Stock")
        if stock_cog:
            if not await stock_cog.consume_stock(guild_id, combo_id, 1):
                embed = discord.Embed(title="❌ ДУУССАН", description=f"**{ALL_VAPE_COMBOS[combo_id]['emoji']} {ALL_VAPE_COMBOS[combo_id]['name']}** дууссан.", color=ERROR_COLOR)
                await interaction.response.edit_message(embed=embed, view=None)
                return

        await economy.update_balance(self.ctx.author.id, guild_id, -price)
        await self.cog.add_item(self.ctx.author.id, guild_id, combo_id, 1)
        combo = ALL_VAPE_COMBOS[combo_id]
        embed = discord.Embed(title="✅ Худалдан авалт амжилттай",
                              description=f"{self.ctx.author.mention} **{combo['emoji']} {combo['name']}** -г `{price:,}` ₮-өөр худалдаж авлаа!",
                              color=SUCCESS_COLOR)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)


class TradeView(View):
    def __init__(self, shop_cog, trade_id: int, from_user: discord.Member, to_user: discord.Member, item_id: int, quantity: int):
        super().__init__(timeout=120)
        self.shop = shop_cog
        self.trade_id = trade_id
        self.from_user = from_user
        self.to_user = to_user
        self.item_id = item_id
        self.quantity = quantity
        self.finished = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.to_user.id:
            await interaction.response.send_message("❌ Энэ солилцоо танд зориулагдаагүй!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Зөвшөөрөх", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if self.finished:
            return await interaction.response.send_message("Солилцоо дууссан.", ephemeral=True)
        self.finished = True
        guild_id = interaction.guild_id
        success = await self.shop.transfer_items(
            guild_id, self.from_user.id, self.to_user.id, self.item_id, self.quantity
        )
        if success:
            embed = discord.Embed(
                title="🔄 СОЛИЛЦОО АМЖИЛТТАЙ",
                description=f"{self.from_user.mention} → {self.to_user.mention}\n**{self.quantity}x** `{self.item_id}` ID-тай барааг шилжүүллээ.",
                color=SUCCESS_COLOR
            )
        else:
            embed = discord.Embed(
                title="❌ СОЛИЛЦОО БҮТЭЛГҮЙ",
                description="Бараа хүрэлцэхгүй эсвэл системийн алдаа гарлаа.",
                color=ERROR_COLOR
            )
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Татгалзах", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: Button):
        if self.finished:
            return await interaction.response.send_message("Солилцоо дууссан.", ephemeral=True)
        self.finished = True
        for child in self.children:
            child.disabled = True
        embed = discord.Embed(
            title="❌ СОЛИЛЦОО ТАТГАЛЗСАН",
            description=f"{self.to_user.mention} саналаас татгалзлаа.",
            color=ERROR_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=self)
        if self.trade_id in self.shop.pending_trades:
            del self.shop.pending_trades[self.trade_id]

    async def on_timeout(self):
        if not self.finished:
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(view=self)
            if self.trade_id in self.shop.pending_trades:
                del self.shop.pending_trades[self.trade_id]


class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.max_inventory_slots = 50
        self.pending_vape = {}
        self.pending_trades = {}
        self._trade_counter = 0

    # ==================== SQLite INIT ====================
    async def init_db(self):
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS user_inventory (
                user_id TEXT, guild_id TEXT,
                item_id INTEGER, quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id, item_id)
            )
        ''')
        await self.bot.db.commit()
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS user_drunk (
                user_id TEXT, guild_id TEXT,
                level INTEGER DEFAULT 0, last_update INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        await self.bot.db.commit()
        # Серверийн тусгай барааны хүснэгт
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS shop_items (
                guild_id TEXT,
                id INTEGER,
                name TEXT,
                price INTEGER,
                emoji TEXT DEFAULT '📦',
                description TEXT DEFAULT '',
                PRIMARY KEY (guild_id, id)
            )
        ''')
        await self.bot.db.commit()

    async def cog_load(self):
        await self.init_db()

    # ==================== ИНВЕНТАРЫН МЕТОДУУД ====================
    async def get_user_inventory(self, uid, guild_id):
        rows = await self.bot.db.fetch(
            "SELECT item_id, quantity FROM user_inventory WHERE user_id=? AND guild_id=?",
            str(uid), str(guild_id)
        )
        inv = {}
        for row in rows:
            inv[row[0]] = row[1]
        return inv

    async def get_item(self, item_id):
        # Эхлээд глобал бараанууд
        if item_id in ALL_VAPE_COMBOS:
            return ALL_VAPE_COMBOS[item_id]
        for item in SHOP_ITEMS:
            if item["id"] == item_id:
                return item
        return None

    async def add_item(self, uid, guild_id, iid, qty=1):
        await self.bot.db.execute(
            "INSERT INTO user_inventory (user_id, guild_id, item_id, quantity) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id, guild_id, item_id) DO UPDATE SET quantity = quantity + ?",
            str(uid), str(guild_id), iid, qty, qty
        )
        await self.bot.db.commit()

    async def remove_item(self, uid, guild_id, iid, qty=1):
        row = await self.bot.db.fetchone(
            "SELECT quantity FROM user_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
            str(uid), str(guild_id), iid
        )
        if not row or row[0] < qty:
            return False
        new_qty = row[0] - qty
        if new_qty == 0:
            await self.bot.db.execute(
                "DELETE FROM user_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
                str(uid), str(guild_id), iid
            )
        else:
            await self.bot.db.execute(
                "UPDATE user_inventory SET quantity=? WHERE user_id=? AND guild_id=? AND item_id=?",
                new_qty, str(uid), str(guild_id), iid
            )
        await self.bot.db.commit()
        return True

    # ==================== МАНСУУРАЛ ====================
    async def get_drunk_level(self, uid, guild_id):
        row = await self.bot.db.fetchone(
            "SELECT level, last_update FROM user_drunk WHERE user_id=? AND guild_id=?",
            str(uid), str(guild_id)
        )
        if not row:
            return 0
        level, last = row
        if last is None:
            return level
        now = int(time.time())
        hours = (now - last) // 3600
        if hours > 0:
            new_level = max(0, level - hours * 3)
            if new_level != level:
                await self.bot.db.execute(
                    "UPDATE user_drunk SET level=?, last_update=? WHERE user_id=? AND guild_id=?",
                    new_level, now, str(uid), str(guild_id)
                )
                await self.bot.db.commit()
                return new_level
        return level

    async def add_drunk(self, uid, guild_id, strength):
        current = await self.get_drunk_level(uid, guild_id)
        new_level = min(current + strength, MAX_INTOXICATION)
        now = int(time.time())
        await self.bot.db.execute(
            "INSERT INTO user_drunk (user_id, guild_id, level, last_update) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET level = ?, last_update = ?",
            str(uid), str(guild_id), new_level, now, new_level, now
        )
        await self.bot.db.commit()
        return new_level

    def get_drunk_status(self, level):
        for threshold, name, color in INTOXICATION_LEVELS:
            if level <= threshold:
                return name, color
        return "😵 ХЭТ ХҮНД", ERROR_COLOR

    def get_intoxication_bar(self, level):
        max_level = MAX_INTOXICATION
        filled = min(level, max_level)
        bar_len = 20
        filled_blocks = int((filled / max_level) * bar_len)
        bar = "▰" * filled_blocks + "▱" * (bar_len - filled_blocks)
        return f"`{bar}` `{filled}/{max_level}%`"

    # ==================== TRADE ====================
    def get_trade_id(self):
        self._trade_counter += 1
        return self._trade_counter

    async def transfer_items(self, guild_id, from_id, to_id, item_id, quantity):
        removed = await self.remove_item(from_id, guild_id, item_id, quantity)
        if not removed:
            return False
        await self.add_item(to_id, guild_id, item_id, quantity)
        return True

    async def use_item(self, uid, guild_id, item_id):
        item = await self.get_item(item_id)
        if not item or item.get("strength", 0) == 0:
            return False, "❌ Энэ барааг хэрэглэх боломжгүй."

        removed = await self.remove_item(uid, guild_id, item_id, 1)
        if not removed:
            return False, "❌ Танд энэ бараа байхгүй."

        new_level = await self.add_drunk(uid, guild_id, item["strength"])
        economy = self.bot.get_cog("Economy")
        bonus_msg = ""
        if new_level >= MAX_INTOXICATION and economy:
            await economy.set_prison(uid, guild_id, hours=2)
            fine = int(await economy.get_balance(uid, guild_id) * 0.05)
            await economy.update_balance(uid, guild_id, -fine)
            bonus_msg = f"\n🚔 Мансуурал 100% хүрч 2 цаг шоронд орлоо. {fine:,}₮ торгууль."

        status_name, _ = self.get_drunk_status(new_level)
        return True, f"{item['emoji']} **{item['name']}** хэрэглэгдлээ. Мансуурал: {status_name} ({new_level}%){bonus_msg}"

    # ==================== АДМИН КОМАНДУУД (шинэ) ====================
    @commands.command(name='create-item')
    @commands.has_permissions(administrator=True)
    async def create_item(self, ctx, name: str, price: int, emoji: str = "📦", *, desc: str = "Тайлбаргүй"):
        """Шинэ бараа үүсгэх"""
        row = await self.bot.db.fetchone("SELECT MAX(id) FROM shop_items WHERE guild_id=?", str(ctx.guild.id))
        new_id = (row[0] or 0) + 1
        await self.bot.db.execute(
            "INSERT INTO shop_items (guild_id, id, name, price, emoji, description) VALUES (?,?,?,?,?,?)",
            str(ctx.guild.id), new_id, name, price, emoji, desc
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ {emoji} **{name}** (ID: {new_id}) - {price:,} ₮ үнэтэйгээр нэмэгдлээ.")

    @commands.command(name='edit-item')
    @commands.has_permissions(administrator=True)
    async def edit_item(self, ctx, item_id: int, field: str, *, value: str):
        """Бараа засварлах (field: name, price, emoji, desc)"""
        allowed = {'name', 'price', 'emoji', 'desc'}
        if field not in allowed:
            return await ctx.send(f"❌ Зөвшөөрөгдсөн талбарууд: {', '.join(allowed)}")
        col_map = {'name': 'name', 'price': 'price', 'emoji': 'emoji', 'desc': 'description'}
        col = col_map[field]
        if field == 'price':
            try:
                value = int(value)
            except:
                return await ctx.send("❌ Үнэ нь тоо байх ёстой.")
        await self.bot.db.execute(
            f"UPDATE shop_items SET {col}=? WHERE guild_id=? AND id=?",
            value, str(ctx.guild.id), item_id
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ ID {item_id} барааны `{field}` шинэчлэгдлээ.")

    @commands.command(name='delete-item')
    @commands.has_permissions(administrator=True)
    async def delete_item(self, ctx, item_id: int):
        """Дэлгүүрээс бараа устгах"""
        await self.bot.db.execute(
            "DELETE FROM shop_items WHERE guild_id=? AND id=?",
            str(ctx.guild.id), item_id
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ ID {item_id} бараа устгагдлаа.")

    @commands.command(name='give-item')
    @commands.has_permissions(administrator=True)
    async def give_item(self, ctx, member: discord.Member, item_id: int, quantity: int = 1):
        """Гишүүнд бараа өгөх"""
        # Эхлээд глобал бараа эсвэл серверийн бараа байгаа эсэхийг шалгах
        item = await self.get_item(item_id)
        if not item:
            # Серверийн бараа эсэхийг шалгах
            row = await self.bot.db.fetchone("SELECT 1 FROM shop_items WHERE guild_id=? AND id=?", str(ctx.guild.id), item_id)
            if not row:
                return await ctx.send("❌ Ийм ID-тай бараа олдсонгүй.")
        await self.add_item(member.id, ctx.guild.id, item_id, quantity)
        await ctx.send(f"✅ {member.mention}-д `{item_id}` ID-тай бараа x{quantity} өглөө.")

    @commands.command(name='take-item')
    @commands.has_permissions(administrator=True)
    async def take_item(self, ctx, member: discord.Member, item_id: int, quantity: int = 1):
        """Гишүүнээс бараа хураах"""
        success = await self.remove_item(member.id, ctx.guild.id, item_id, quantity)
        if success:
            await ctx.send(f"✅ {member.mention}-ээс `{item_id}` ID-тай бараа x{quantity} хаслаа.")
        else:
            await ctx.send("❌ Бараа хангалтгүй эсвэл байхгүй.")

    # ==================== ДЭЛГҮҮР (хэвээр) ====================
    @commands.command(name='shop', aliases=['store', 'дэлгүүр'])
    async def shop(self, ctx):
        categories = [
            {"name": "🍺 Ундаа (Drinks)", "value": "drink", "emoji": "🍺"},
            {"name": "💍 Бөгж (Rings)", "value": "ring", "emoji": "💍"},
            {"name": "💨 Вайп (Vape)", "value": "vape", "emoji": "💨"},
            {"name": "💫 Аксессуар (Accessories)", "value": "accessory", "emoji": "💫"},
            {"name": "🚬 Тамхи (Intoxicant)", "value": "intoxicant", "emoji": "🚬"},
        ]
        category_options = [discord.SelectOption(label=cat["name"], value=cat["value"], emoji=cat["emoji"]) for cat in categories]
        category_select = Select(placeholder="📂 Категори сонгох", options=category_options)

        async def category_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("❌ Энэ цэс танд зориулагдаагүй!", ephemeral=True)
            selected_cat = category_select.values[0]
            item_options = []
            if selected_cat == "vape":
                for base in BASE_VAPE_ITEMS:
                    label = f"{base['emoji']} {base['name']} - {base['price']:,}💰"
                    desc = f"{base['desc'][:40]} | ⚡{base['strength']}%"
                    item_options.append(discord.SelectOption(label=label[:100], value=f"vape_{base['id']}", description=desc, emoji=base['emoji']))
            else:
                for item in SHOP_ITEMS:
                    if item["category"] == selected_cat:
                        label = f"{item['emoji']} {item['name']} - {item['price']:,}💰"
                        desc = item["desc"][:50]
                        if item.get("strength", 0) > 0: desc += f" | ⚡{item['strength']}%"
                        item_options.append(discord.SelectOption(label=label[:100], value=str(item["id"]), description=desc, emoji=item['emoji']))
            if not item_options:
                return await interaction.response.edit_message(embed=discord.Embed(description="❌ Энэ категорид бараа байхгүй.", color=ERROR_COLOR), view=None)
            if len(item_options) > 25: item_options = item_options[:25]
            item_select = Select(placeholder="🛒 Бараа сонгох", options=item_options)

            async def item_callback(interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("❌ Энэ цэс танд зориулагдаагүй!", ephemeral=True)
                value = item_select.values[0]
                if value.startswith("vape_"):
                    base_id = int(value[5:])
                    base_item = next((i for i in BASE_VAPE_ITEMS if i["id"] == base_id), None)
                    if not base_item: return await interaction.response.send_message("❌ Вайп олдсонгүй.", ephemeral=True)
                    view = FlavorSelectView(self, ctx, base_item)
                    embed = discord.Embed(title=f"{base_item['emoji']} {base_item['name']} - Амт сонгох", description="Доорх цэснээс амтаа сонгоно уу.", color=GOLD_COLOR)
                    await interaction.response.edit_message(embed=embed, view=view)
                    return
                item_id = int(value)
                item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
                if not item: return await interaction.response.send_message("❌ Бараа олдсонгүй.", ephemeral=True)
                economy = self.bot.get_cog("Economy")
                if not economy: return await interaction.response.send_message("❌ Системийн алдаа.", ephemeral=True)
                guild_id = ctx.guild.id
                balance = await economy.get_balance(ctx.author.id, guild_id)
                price = item["price"]
                if balance < price:
                    embed = discord.Embed(title="❌ Хангалтгүй мөнгө",
                                          description=f"**{item['emoji']} {item['name']}** худалдаж авахад **{price:,}** ₮ шаардлагатай.\nТаны үлдэгдэл: `{balance:,}` ₮",
                                          color=ERROR_COLOR)
                    await interaction.response.edit_message(embed=embed, view=None)
                    return

                stock_cog = self.bot.get_cog("Stock")
                if stock_cog:
                    if not await stock_cog.consume_stock(guild_id, item["id"], 1):
                        embed = discord.Embed(title="❌ ДУУССАН", description=f"**{item['emoji']} {item['name']}** дууссан.", color=ERROR_COLOR)
                        await interaction.response.edit_message(embed=embed, view=None)
                        return

                await economy.update_balance(ctx.author.id, guild_id, -price)
                await self.add_item(ctx.author.id, guild_id, item["id"], 1)
                embed = discord.Embed(title="✅ Худалдан авалт амжилттай",
                                      description=f"{ctx.author.mention} **{item['emoji']} {item['name']}** -г `{price:,}` ₮-өөр худалдаж авлаа!",
                                      color=SUCCESS_COLOR)
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
                await interaction.response.edit_message(embed=embed, view=None)

            item_select.callback = item_callback
            item_view = View()
            item_view.add_item(item_select)
            embed = discord.Embed(title=f"🏪 ДЭЛГҮҮР – {selected_cat.upper()}", description="Бараа сонгох", color=GOLD_COLOR)
            await interaction.response.edit_message(embed=embed, view=item_view)

        category_select.callback = category_callback
        cat_view = View()
        cat_view.add_item(category_select)
        embed = discord.Embed(title="🏪 ДЭЛГҮҮР", description="Эхлээд категори сонгоно уу.", color=GOLD_COLOR)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed, view=cat_view)

    @commands.command(name='buy')
    async def buy_legacy(self, ctx, item_input: str, quantity: int = 1):
        if quantity <= 0 or quantity > 64:
            return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description="Тоо хэмжээ 1-64 хооронд байх ёстой!", color=ERROR_COLOR))
        try: item_id = int(item_input)
        except ValueError: return await ctx.send(embed=discord.Embed(title="❌ БУРУУ ID", description=f"`{item_input}` нь тоо биш.", color=ERROR_COLOR))
        item = ALL_VAPE_COMBOS.get(item_id) or next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
        if not item: return await ctx.send(embed=discord.Embed(title="❌ БАРАА ОЛДСОНГҮЙ", description=f"`{item_id}` ID-тай бараа байхгүй.", color=ERROR_COLOR))
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send(embed=discord.Embed(title="❌ СИСТЕМИЙН АЛДАА", color=ERROR_COLOR))
        guild_id = ctx.guild.id
        balance = await economy.get_balance(ctx.author.id, guild_id)
        total_price = item["price"] * quantity
        if balance < total_price:
            embed = discord.Embed(title="❌ ХАНГАЛТГҮЙ",
                                  description=f"**{item['emoji']} {item['name']}** x{quantity} худалдаж авахад **{total_price:,}** ₮ шаардлагатай.\nТаны үлдэгдэл: `{balance:,}` ₮",
                                  color=ERROR_COLOR)
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)

        stock_cog = self.bot.get_cog("Stock")
        if stock_cog:
            if not await stock_cog.consume_stock(guild_id, item["id"], quantity):
                return await ctx.send(embed=discord.Embed(title="❌ ДУУССАН", description=f"Уучлаарай, **{item['emoji']} {item['name']}** дууссан.", color=ERROR_COLOR))

        await economy.update_balance(ctx.author.id, guild_id, -total_price)
        await self.add_item(ctx.author.id, guild_id, item["id"], quantity)
        embed = discord.Embed(title="✅ ХУДАЛДАН АВАЛТ",
                              description=f"{ctx.author.mention} **{item['emoji']} {item['name']}** x{quantity} -г `{total_price:,}` ₮-өөр худалдаж авлаа!",
                              color=SUCCESS_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='vape', aliases=['vapes', 'вайп'])
    async def vape_list(self, ctx):
        embed = discord.Embed(title="💨 ВАЙПНЫ ЖАГСААЛТ", description="Бүх брэнд, загвар, хүч (% - мансуурал нэмэх хувь)", color=GOLD_COLOR)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        for brand, data in VAPE_BRANDS.items():
            lines = []
            for model, mdata in data["models"].items():
                lines.append(f"{data['emoji']} **{model}** — {mdata['price']:,}₮ | ⚡ {mdata['strength']}%")
            embed.add_field(name=f"{data['emoji']} {brand}", value="\n".join(lines), inline=False)
        embed.set_footer(text="Худалдан авах: gshop → Вайп категори → загвар сонгох → амт сонгох")
        await ctx.send(embed=embed)

    @commands.command(name='iteminfo', aliases=['item', 'бараа'])
    async def item_info(self, ctx, item_id: int):
        item = ALL_VAPE_COMBOS.get(item_id) or next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
        if not item:
            return await ctx.send(embed=discord.Embed(title="❌ Бараа олдсонгүй", description=f"`{item_id}` ID-тай бараа байхгүй.", color=ERROR_COLOR))
        embed = discord.Embed(title=f"{item['emoji']} {item['name']}", color=GOLD_COLOR)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="💰 Үнэ", value=f"`{item['price']:,}` ₮", inline=True)
        embed.add_field(name="📂 Төрөл", value=item.get("category", "unknown"), inline=True)
        if item.get("strength", 0) > 0: embed.add_field(name="⚡ Хүч", value=f"`{item['strength']}%`", inline=True)
        embed.add_field(name="📝 Тайлбар", value=item.get("desc", ""), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='drink', aliases=['уух'])
    async def drink(self, ctx, item_id: int):
        item = next((i for i in SHOP_ITEMS if i["id"] == item_id and i["strength"] > 0), None)
        if not item: return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description="Энэ барааг уух боломжгүй.", color=ERROR_COLOR))
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send("❌ Системийн алдаа.")
        guild_id = ctx.guild.id
        if await economy.is_in_prison(ctx.author.id, guild_id):
            return await ctx.send("🚔 Шоронд байхдаа хэрэглэх боломжгүй.")
        inv = await self.get_user_inventory(ctx.author.id, guild_id)
        if inv.get(item_id, 0) == 0:
            return await ctx.send(embed=discord.Embed(title="❌ ТАНД ЭНЭ БАРАА БАЙХГҮЙ", description=f"`gshop`-с худалдаж авна уу.", color=ERROR_COLOR))
        await self.remove_item(ctx.author.id, guild_id, item_id, 1)
        intox = random.randint(5, 10)
        new_level = await self.add_drunk(ctx.author.id, guild_id, intox)
        bonus_msg = ""
        if random.random() < 0.05:
            bonus_type = random.choice(["money", "xp", "ring"])
            if bonus_type == "money":
                bonus = random.randint(500, 3000)
                await economy.update_balance(ctx.author.id, guild_id, bonus)
                bonus_msg = f"\n🎁 **Азтай!** +{bonus:,}₮"
            elif bonus_type == "xp":
                xp_cog = self.bot.get_cog("Leveling")
                if xp_cog:
                    bonus = random.randint(10, 50)
                    await xp_cog.add_xp(ctx.author.id, guild_id, bonus, member=ctx.author, check_mute=True, channel=ctx.channel)
                    bonus_msg = f"\n🎁 **Азтай!** +{bonus} XP"
            else:
                ring_id = random.choice([36,37,38,39,40,41,42])
                await self.add_item(ctx.author.id, guild_id, ring_id, 1)
                ring = next((i for i in SHOP_ITEMS if i["id"] == ring_id), None)
                if ring: bonus_msg = f"\n🎁 **Азтай!** {ring['emoji']} {ring['name']} бөгж нэмэгдлээ!"
        prison = False
        if new_level >= MAX_INTOXICATION:
            await economy.set_prison(ctx.author.id, guild_id, hours=2)
            fine = int(await economy.get_balance(ctx.author.id, guild_id) * 0.05)
            await economy.update_balance(ctx.author.id, guild_id, -fine)
            prison = True
        status_name, status_color = self.get_drunk_status(new_level)
        bar = self.get_intoxication_bar(new_level)
        embed = discord.Embed(title="🍻 ХАМГИЙН ДООЛОН!", description=f"{ctx.author.mention} **{item['name']}** уулаа. (+{intox}%){bonus_msg}", color=status_color)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="🧠 МАНСУУРАЛ", value=f"{status_name}\n{bar}", inline=False)
        if prison: embed.add_field(name="🚔 ШОРОН", value="Мансуурал 100% хүрсэн тул 2 цаг шоронд. 5% торгууль.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='use', aliases=['хэрэглэх'])
    async def use_item_command(self, ctx, item_id: int):
        item = ALL_VAPE_COMBOS.get(item_id)
        if not item:
            item = next((i for i in SHOP_ITEMS if i["id"] == item_id and i["category"] == "intoxicant"), None)
        if not item or item.get("strength", 0) == 0:
            return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description="Энэ барааг хэрэглэх боломжгүй.", color=ERROR_COLOR))
        economy = self.bot.get_cog("Economy")
        if not economy: return await ctx.send("❌ Системийн алдаа.")
        guild_id = ctx.guild.id
        if await economy.is_in_prison(ctx.author.id, guild_id):
            return await ctx.send("🚔 Шоронд байхдаа хэрэглэх боломжгүй.")
        inv = await self.get_user_inventory(ctx.author.id, guild_id)
        if inv.get(item_id, 0) == 0:
            return await ctx.send(embed=discord.Embed(title="❌ ТАНД ЭНЭ БАРАА БАЙХГҮЙ", color=ERROR_COLOR))
        await self.remove_item(ctx.author.id, guild_id, item_id, 1)
        new_level = await self.add_drunk(ctx.author.id, guild_id, item["strength"])
        bonus_msg = ""
        if random.random() < 0.05:
            bonus_type = random.choice(["money", "xp", "ring"])
            if bonus_type == "money":
                bonus = random.randint(500, 3000)
                await economy.update_balance(ctx.author.id, guild_id, bonus)
                bonus_msg = f"\n🎁 **Азтай!** +{bonus:,}₮"
            elif bonus_type == "xp":
                xp_cog = self.bot.get_cog("Leveling")
                if xp_cog:
                    bonus = random.randint(10, 50)
                    await xp_cog.add_xp(ctx.author.id, guild_id, bonus, member=ctx.author, check_mute=True, channel=ctx.channel)
                    bonus_msg = f"\n🎁 **Азтай!** +{bonus} XP"
            else:
                ring_id = random.choice([36,37,38,39,40,41,42])
                await self.add_item(ctx.author.id, guild_id, ring_id, 1)
                ring = next((i for i in SHOP_ITEMS if i["id"] == ring_id), None)
                if ring: bonus_msg = f"\n🎁 **Азтай!** {ring['emoji']} {ring['name']} бөгж нэмэгдлээ!"
        prison = False
        if new_level >= MAX_INTOXICATION:
            await economy.set_prison(ctx.author.id, guild_id, hours=2)
            fine = int(await economy.get_balance(ctx.author.id, guild_id) * 0.05)
            await economy.update_balance(ctx.author.id, guild_id, -fine)
            prison = True
        status_name, status_color = self.get_drunk_status(new_level)
        bar = self.get_intoxication_bar(new_level)
        embed = discord.Embed(title="💨 ХЭРЭГЛЭЛЭЭ", description=f"{ctx.author.mention} **{item['emoji']} {item['name']}** хэрэглэлээ.{bonus_msg}", color=status_color)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="🧠 МАНСУУРАЛ", value=f"{status_name}\n{bar}", inline=False)
        if prison: embed.add_field(name="🚔 ШОРОН", value="Мансуурал 100% хүрсэн тул 2 цаг шоронд. 5% торгууль.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='accessories', aliases=['acc'])
    async def accessories(self, ctx):
        guild_id = ctx.guild.id
        inv = await self.get_user_inventory(ctx.author.id, guild_id)
        acc_items = []
        for iid, qty in inv.items():
            item = next((i for i in SHOP_ITEMS if i["id"] == iid and i["category"] in ("accessory", "necklace", "bracelet", "ring")), None)
            if item: acc_items.append((item, qty))
        if not acc_items:
            return await ctx.send(embed=discord.Embed(title="💫 accessories БАЙХГҮЙ", description="Танд ямар ч accessories байхгүй байна. `gshop`-с худалдаж авна уу.", color=WARNING_COLOR))
        embed = discord.Embed(title=f"💫 {ctx.author.display_name} - ИЙН accessories", color=GOLD_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        for item, qty in acc_items:
            embed.add_field(name=f"{item['emoji']} {item['name']} (ID: {item['id']}) x{qty}", value=f"💰 Үнэ: {item['price']:,} ₮", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='sogtol', aliases=['согтуу', 'drunk'])
    async def show_drunk(self, ctx):
        guild_id = ctx.guild.id
        level = await self.get_drunk_level(ctx.author.id, guild_id)
        status_name, status_color = self.get_drunk_status(level)
        bar = self.get_intoxication_bar(level)
        embed = discord.Embed(title=f"🧠 {ctx.author.display_name} - ИЙН МАНСУУРАЛ", description=f"{status_name}\n{bar}", color=status_color)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Мансуурал цагт 3%-иар буурдаг")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ShopCog(bot))
