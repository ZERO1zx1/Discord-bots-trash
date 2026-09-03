# Gurten | LGC Discord Bot

Монголын серверүүдэд зориулсан олон төрлийн функцтэй, хүчирхэг Discord бот. Эдийн засаг, тоглоом, түвшин, гэрлэлт, модераци, хөгжилтэй командууд зэрэг 30 гаруй ког агуулсан бөгөөд MySQL өгөгдлийн сангаар мэдээллээ хадгалдаг.

---

## 🚀 Онцлох функцууд

### 💰 Эдийн засаг
- `gbal`, `gmoney` – үлдэгдэл харах
- `gdaily`, `gwork` – мөнгө олох
- `gtransfer`, `gdeposit`, `gwithdraw` – гүйлгээ
- `gprofile`, `gprofilecard` – дэлгэрэнгүй профайл (embed/зураг)
- `glb`, `gglobaltop` – лидерборд

### 🎲 Тоглоом & Казино
- `ggamble`, `gflip`, `gslot`, `groulette`, `gdice` – азын тоглоомууд
- `gblackjack`, `ghigh-low` – казино тоглоом
- `gpvp`, `gmines` – PvP тулаан

### 🕵️ Мафи & Pickup
- `gmafia` – бүрэн хэмжээний мафи тоглоом
- `gpickup` – pickup line илгээх, дуут суваг үүсгэх

### 📊 Түвшин & XP
- `gleveling rank` – гоёмсог ранг карт (зураг)
- `gleveling leaderboard` – лидерборд
- Дуут суваг, чат, реакц зэргээс XP авах
- Автомат цол, роль олгох

### 🏪 Дэлгүүр & 💍 Гэрлэлт
- `gshop`, `gbuy`, `ginv` – дэлгүүр, бараа худалдаж авах
- `gpropose`, `gdivorce`, `gmarriage_profile` – гэрлэлтийн систем

### 🛠️ Модераци
- `gkick`, `gban`, `gclear`, `gwarn`, `gtimeout`

### 🎉 Хөгжилтэй
- 20+ үйлдэл/эмоц команд (`ghug`, `gkiss`, `gslap`, `gcry`, `gdance` гэх мэт) – GIF дэмжлэгтэй

### 🤖 AI Chat
- OpenAI эсвэл Google Gemini API-тай холбогдож, тусгай сувагт автомат хариулах

### 🔊 Түр дууны суваг
- `gvoicesetup` – түр суваг үүсгэх, удирдлагын самбар

### 📈 Урилгын хяналт
- `ginvitelog_set`, `ginvites` – урилгын статистик, лог

### 📢 Зарлал, Sticky, Тооллого гэх мэт олон төрлийн хэрэгцээт командууд

---

## 📋 Шаардлага

- Python 3.10+
- MySQL (8.0+)
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- (Сонголт) OpenAI API Key эсвэл Google Gemini API Key (AI Chat-д)
- (Сонголт) Serper API Key (хэрэв вэб хайлт ашиглах бол)

## 📦 Сангууд

Шаардлагатай бүх санг `requirements.txt`-д оруулсан:

```
discord.py>=2.3.0
aiomysql>=0.2.0
python-dotenv>=1.0.0
aiohttp>=3.8.0
Pillow>=9.0.0
matplotlib>=3.5.0
google-generativeai>=0.3.0  # Gemini AI-д (хэрэв ашиглах бол)
openai>=1.0.0               # OpenAI-д (хэрэв ашиглах бол)
```

Суулгах:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Тохиргоо

### 1. `.env` файл үүсгэх

Төслийн үндсэн хавтас дотор `.env` нэртэй файл үүсгэж, дараах хувьсагчдыг оруулна:

```env
DISCORD_TOKEN=таны_бот_токен

# MySQL тохиргоо
MYSQLHOST=localhost
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=нууц_үг
MYSQLDATABASE=railway   # эсвэл өөрийн сангийн нэр

# Сонголт: AI Chat
OPENAI_API_KEY=sk-...    # эсвэл GEMINI_API_KEY=...

# Сонголт: Serper вэб хайлт
SERPER_API_KEY=...
```

### 2. `config.json` (заавал биш)

Зарим ерөнхий тохиргоог `config.json` файлаар тохируулж болно:

```json
{
  "owner_id": 123456789012345678,
  "co_owner_ids": [],
  "max_balance": 100000000,
  "transfer_tax_percent": 10
}
```

### 3. MySQL сан үүсгэх

Бот автоматаар хүснэгтүүдийг үүсгэх боловч эхлээд MySQL дээр `railway` (эсвэл өөрийн `MYSQLDATABASE`-д заасан) нэртэй хоосон сан үүсгэх шаардлагатай.

---

## 🚀 Ботыг ажиллуулах

1. **Клоныг татах эсвэл хуулах**
   ```bash
   git clone https://github.com/yourusername/gurten-lgc-bot.git
   cd gurten-lgc-bot
   ```

2. **Виртуал орчин үүсгэх (сайн дураараа)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Сангуудыг суулгах**
   ```bash
   pip install -r requirements.txt
   ```

4. **`.env` тохиргоогоо хийх**

5. **Ботыг эхлүүлэх**
   ```bash
   python main.py
   ```

6. **Discord серверт урих**
   - [Discord Developer Portal](https://discord.com/developers/applications) → OAuth2 → URL Generator
   - `bot` болон `applications.commands` scope-уудыг сонго.
   - Шаардлагатай эрхүүд: `Manage Server`, `Manage Roles`, `Manage Channels`, `Send Messages`, `Read Messages`, `Connect`, `Speak` гэх мэт.
   - Үүсгэсэн холбоосоор сервертээ урина.

---

## ☁️ Railway дээр байршуулах

1. [Railway](https://railway.app) бүртгэл үүсгэж, шинэ төсөл эхлүүл.
2. GitHub репозиторио холбо.
3. **MySQL** сервис нэмэх (Railway дээр "MySQL" сонго).
4. Ботны сервисдээ дараах орчны хувьсагчдыг тохируулах:
   - `DISCORD_TOKEN`
   - `MYSQLHOST` → `${{ MYSQLHOST }}` (Railway автоматаар MySQL-ийн дотоод хаягийг өгнө)
   - `MYSQLPORT` → `${{ MYSQLPORT }}`
   - `MYSQLUSER` → `${{ MYSQLUSER }}`
   - `MYSQLPASSWORD` → `${{ MYSQLPASSWORD }}`
   - `MYSQLDATABASE` → `${{ MYSQLDATABASE }}`
   - Бусад API түлхүүрүүд.
5. Деплой хийх.

Бот амжилттай ачаалагдсаны дараа `ghelp` командаар бүх командыг харна.

---

## 🤝 Хувь нэмэр оруулах

Сайжруулалт, засвар, шинэ функц нэмэхэд нээлттэй. Pull request илгээхээсээ өмнө issue нээж хэлэлцэнэ үү.

---

## 📜 Лиценз

Энэ төсөл MIT лицензийн дагуу түгээгдэнэ. Дэлгэрэнгүйг `LICENSE` файлаас харна уу.

---

Хэрэв асуулт, санал байвал Discord сувгаар холбогдоорой. Амжилттай ашиглаарай! 🎉
