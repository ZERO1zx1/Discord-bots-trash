import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("PYTHON_BOT_TOKEN")
DAILY_BONUS = int(os.getenv("DAILY_BONUS", 1000))
WEEKLY_BONUS = int(os.getenv("WEEKLY_BONUS", 5000))
HOURLY_BONUS = int(os.getenv("HOURLY_BONUS", 100))
WORK_MIN = int(os.getenv("WORK_MIN", 50))
WORK_MAX = int(os.getenv("WORK_MAX", 200))
ROB_SUCCESS_RATE = float(os.getenv("ROB_SUCCESS_RATE", 0.4))
BANK_SAFE = os.getenv("BANK_SAFE", "True").lower() == "true"

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "data.db")

XP_MIN = 10
XP_MAX = 20
LEVEL_MULTIPLIER = 100

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "mn")
FALLBACK_LANGUAGE = os.getenv("FALLBACK_LANGUAGE", "en")

TRANSLATIONS = {
    "mn": {
        "balance": "Үлдэгдэл",
        "daily": "Өдөр бүрийн урамшуулал",
        "weekly": "Долоо хоног тутмын урамшуулал",
        "hourly": "Цаг тутмын урамшуулал",
        "pay": "Мөнгө шилжүүлэх",
        "work": "Ажиллах",
        "rob": "Дээрэмдэх",
        "deposit": "Хадгалуулах",
        "withdraw": "Мөнгө татах",
        "bank": "Банк",
        "leaderboard": "Лидерборд",
        "rank": "Түвшин",
        "xp": "XP оноо",
        "shop": "Дэлгүүр",
        "buy": "Худалдаж авах",
        "inventory": "Бараа материал",
        "price": "Үнэ",
        "coins": "₮",
    },
    "en": {
        "balance": "Balance",
        "daily": "Daily Bonus",
        "weekly": "Weekly Bonus",
        "hourly": "Hourly Bonus",
        "pay": "Pay",
        "work": "Work",
        "rob": "Rob",
        "deposit": "Deposit",
        "withdraw": "Withdraw",
        "bank": "Bank",
        "leaderboard": "Leaderboard",
        "rank": "Rank",
        "xp": "XP",
        "shop": "Shop",
        "buy": "Buy",
        "inventory": "Inventory",
        "price": "Price",
        "coins": "coins",
    }
}

def get_text(key, lang=None):
    if lang is None:
        lang = DEFAULT_LANGUAGE
    if lang not in TRANSLATIONS:
        lang = FALLBACK_LANGUAGE
    return TRANSLATIONS.get(lang, {}).get(key, key)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PREFIX = os.getenv("PREFIX", ".")
owner_id = int(os.getenv("OWNER_ID", "1269304623135457281"))
co_owner_ids = [int(x.strip()) for x in os.getenv("CO_OWNER_IDS", "").split(",") if x.strip()]
