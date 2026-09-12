import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("PYTHON_BOT_TOKEN")
BATTLE_ROLE_NAME = os.getenv("BATTLE_ROLE_NAME", "BattleFans")
DAILY_BONUS = int(os.getenv("DAILY_BONUS", 1000))
WEEKLY_BONUS = int(os.getenv("WEEKLY_BONUS", 5000))
HOURLY_BONUS = int(os.getenv("HOURLY_BONUS", 100))
WORK_MIN = int(os.getenv("WORK_MIN", 50))
WORK_MAX = int(os.getenv("WORK_MAX", 200))
ROB_SUCCESS_RATE = float(os.getenv("ROB_SUCCESS_RATE", 0.4))
BANK_SAFE = os.getenv("BANK_SAFE", "True").lower() == "true"
DB_PATH = "data/discord.db"

XP_MIN = 10
XP_MAX = 20
LEVEL_MULTIPLIER = 100

# Локализаци
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "mn")
FALLBACK_LANGUAGE = os.getenv("FALLBACK_LANGUAGE", "en")

# Орчуулгын толь (энгийн жишээ)
TRANSLATIONS = {
    "mn": {
        "balance": "Үлдэгдэл",
        "daily": "Өдөр тутмын бонус",
        "weekly": "Долоо хоногийн бонус",
        "hourly": "Цагийн бонус",
        "pay": "Мөнгө шилжүүлэх",
        "work": "Ажил",
        "rob": "Дээрэм",
        "deposit": "Хадгалуулах",
        "withdraw": "Авах",
        "bank": "Банк",
        "leaderboard": "Лидерборд",
        "rank": "Түвшин",
        "xp": "XP оноо",
        "xpleaderboard": "XP лидерборд",
        "coins": "монет",
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
        "xpleaderboard": "XP Leaderboard",
        "coins": "coins",
    }
}

def get_text(key, lang=None):
    if lang is None:
        lang = DEFAULT_LANGUAGE
    if lang not in TRANSLATIONS:
        lang = FALLBACK_LANGUAGE
    return TRANSLATIONS.get(lang, {}).get(key, key)
