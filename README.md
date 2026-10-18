# MDKU-Zvil — Discord Bot Collection

Хэрэглэгчийн туршлагад суурилсан Discord ботуудын цуглуулга. Эдгээр нь зүгээр л "тест хийх" зорилготой бичигдсэн кодууд юм.

## Бүтэц

```
discord bot test/
├── Gurten-LGC/                    # Үндсэн бот (Python / discord.py)
│   ├── main.py                    # Bot entry point
│   ├── database.py                # SQLite database manager
│   ├── config_manager.py          # JSON config loader
│   ├── config.json                # Тохиргоо (owner_id, xp, etc.)
│   ├── requirements.txt           # Python хамаарлууд
│   └── cogs/                      # 30+Cog модулиуд
│       ├── economy.py             # Эдийн засаг (balance, daily, transfer)
│       ├── shop.py                # Дэлгүүр
│       ├── stock.py               # Хувьцааны зах зээл
│       ├── trade.py               # Худалдаа
│       ├── casino.py              # Казино
│       ├── mines.py               # Нүүрсний тоглоом
│       ├── pvp.py                 # PvP тулаан
│       ├── mafia.py               # Мафи тоглоом
│       ├── lottery.py             # Сугалаа
│       ├── marriage.py            # Гэрлэлт
│       ├── confessions.py         # Нууц илчлэлт
│       ├── register.py            # Бүртгэл
│       ├── leveling.py            # Түвшин систем
│       ├── admin.py               # Админ командууд
│       ├── moderation.py          # Модераци
│       ├── tempvoice.py           # Түр хоосон дууны сувгууд
│       ├── giveaway.py            # Гарцалт
│       ├── quests.py              # Даалгавар
│       ├── cafe.py                # Кафе
│       ├── carts.py               # Сагс
│       ├── confessions.py         # Нууц илчлэлт
│       ├── counting.py            # Тооллого
│       ├── fun.py                 # Зугаа цэнгэл
│       ├── games.py               # Тоглоомууд
│       ├── greetings.py           -- Мэндчилгээ
│       ├── help.py                # Тусламж
│       ├── invite_tracker.py      # Урилга мөрдөх
│       ├── levels.py              # Лидерборд
│       ├── roles.py               -- Роль удирдах
│       ├── sticky.py              -- Баримт бичиг
│       └── avatar_check.py        -- АвATAR шалгах
│
├── my-discord-bot-combined/       # Хосолсон Python + JS бот
│   ├── python/
│   │   ├── bot.py                 # Python bot entry
│   │   ├── config.py              # Тохиргоо
│   │   ├── database.py            # SQLite database
│   │   ├── cogs/
│   │   │   ├── economy.py         # Эдийн засаг
│   │   │   ├── gambling.py        # Мөрий
│   │   │   ├── leveling.py        # Түвшин
│   │   │   ├── games.py           # Тоглоом
│   │   │   ├── admin.py           # Админ
│   │   │   └── leaderboard.py     # Лидерборд
│   │   └── utils/
│   │       ├── helpers.py         # Туслах функцууд
│   │       └── cooldown.py        # Cooldown management
│   └── javascript/
│       ├── index.js               # JS bot entry
│       ├── package.json           # Node dependencies
│       └── src/
│           ├── commands/          # Slash командууд
│           ├── events/            # Event handler-ууд
│           └── handlers/          # Command loader
│
├── discord bot files/             # Хуучин хувилбарууд
│   ├── Gurten-LGC-/              # Хуучин Gurten-LGC
│   └── new bot/
│       ├── face_rating_bot/       # Нүүр үнэлэх бот (AI)
│       └── create_project.py      # Төсөл үүсгэгч
│
├── discord_bot_V1/                # Анхны хувилбар (хоосон)
├── summer_course_2026/            # Зуны сургалтын материалууд
├── main.py                        # Гол launcher (Gurten-LGC ачаалуулагч)
├── create_project.py              # my-discord-bot-combined төсөл үүсгэгч
└── pyproject.toml                 # Python төслийн тохиргоо
```

## Gurten-LGC — Үндсэн Бот

**30+ cog** агуулсан бүрэн funkцитай Discord бот.

### Онцлогууд

| Функц | Тайлбар |
|-------|---------|
| Эдийн засаг | Баланс, өдөр тутмын урамшуулал, шилжүүлэг |
| Дэлгүүр | Зүйлс худалдан авах, худалдах |
| Хувьцаа | Хувьцааны зах зээл |
| Казино | Зоос хаях, слот, рулет |
| PvP | Хэрэглэгч хоорондын тулаан |
| Мафи | Бүлэг тоглоом |
| Сугалаа | Лотерийн тоглоом |
| Гэрлэлт | Хэрэглэгч хоорондын харилцаа |
| Нууц илчлэлт | Аноним мессеж |
| Бүртгэл | Шинэ гишүүдийн бүртгэл |
| Түвшин | XP систем, лидерборд |
| Түр дууны суваг | Автомат дууны сувгууд |
| Гарцалт | Giveaway систем |
| Даалгавар | Quest систем |
| Модераци | Админ командууд |

### Ашиглах

```bash
# Хамаарлууд суулгах
pip install -r Gurten-LGC/requirements.txt

# .env файл үүсгэх
echo "DISCORD_TOKEN=YOUR_TOKEN" > Gurten-LGC/.env

# Бот ажиллуулах
python main.py
```

### Хамаарлууд

- `discord.py>=2.3.0`
- `aiosqlite>=0.19.0`
- `python-dotenv>=1.0.0`
- `aiohttp>=3.9.0`
- `cryptography`
- `matplotlib`
- `Pillow`

## my-discord-bot-combined — Хосолсон Бот

Python болон JavaScript хоёр хэлээр бичигдсэн хосолсон бот.

### Python тал

- Economy, Gambling, Leveling, Games, Admin, Leaderboard
- SQLite database ашиглана
- Slash командууд

### JavaScript тал

- Discord.js v14 ашиглана
- Slash командууд: balance, clear
- Event driven architecture

### Ашиглах

```bash
# Python бот
cd my-discord-bot-combined/python
pip install -r requirements.txt
python bot.py

# JS бот
cd my-discord-bot-combined/javascript
npm install
npm start
```

## face_rating_bot — Нүүр үнэлэх бот

AI ашиглан хэрэглэгчийн нүүрийг үнэлдэг бот.

## Тохиргоо

Бүх ботууд `.env` файл ашиглан нууц мэдээллийг хадгална:

```env
DISCORD_TOKEN=your_token_here
MYSQLHOST=127.0.0.1
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=your_password
MYSQLDATABASE=database_name
```

## Анхааруулга

- `.env` файлуудыг хэзээ ч commit бүү хий
- `config.json` дотор owner_id байгаа тул хувийн мэдээлэл болгох хэрэгтэй
- Бүх код зөвхөн сургалт, тест зорилготой

## Лиценз

Энэхүү төсөл нь зөвхөн хувийн хэрэглээнд зориулагдсан.
