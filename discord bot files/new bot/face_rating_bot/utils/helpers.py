import random
from config import XP_MIN, XP_MAX, get_text

def random_xp():
    return random.randint(XP_MIN, XP_MAX)

def format_currency(amount, lang=None):
    coin_text = get_text("coins", lang)
    return f"💰 {amount:,} {coin_text}"
