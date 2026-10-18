# config_manager.py
import json
import os

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {
            "owner_id": 1468270807686840543,
            "co_owner_ids": [1457121140597063899, 1118116540676571177],
            "xp_per_message": 15,
            "voice_xp_per_minute": 1,
            "base_xp_needed": 100,
            "bonus_percent": 10,
            "transfer_tax_percent": 10,
            "max_balance": 100000000
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4)
        return default
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)