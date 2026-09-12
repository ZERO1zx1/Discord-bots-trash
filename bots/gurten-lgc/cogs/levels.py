import asyncio
import io
import json
import logging
import os
import time
import random
from datetime import datetime, timezone
from typing import Optional, Union
import urllib.request

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from PIL import Image, ImageDraw, ImageFont

# ---------- Font helper ----------
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

log = logging.getLogger(__name__)

# ---------- Colors ----------
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
GOLD_COLOR = 0xfab387
WARNING_COLOR = 0xf9e2af
ERROR_COLOR = 0xf38ba8
INFO_COLOR = 0x89b4fa

NEON_PINK = (255, 16, 240, 255)
NEON_GREEN = (57, 255, 20, 255)
NEON_YELLOW = (204, 255, 0, 255)

# ---------- Level ranks ----------
LEVEL_RANKS = [
    (0, 5, "Newbie", "🌱"),
    (5, 15, "Active", "⭐"),
    (15, 30, "Expert", "🔥"),
    (30, 50, "Veteran", "🛡️"),
    (50, 80, "Elite", "💎"),
    (80, float('inf'), "Legend", "👑")
]

RANK_ROLES = {
    "Newbie": "Newbie",
    "Active": "Active",
    "Expert": "Expert",
    "Veteran": "Veteran",
    "Elite": "Elite",
    "Legend": "Legend"
}

def get_rank_info(level):
    for low, high, title, badge in LEVEL_RANKS:
        if low <= level < high:
            return title, badge
    return "Legend", "👑"

def get_rank_role_name(level):
    title, _ = get_rank_info(level)
    return RANK_ROLES.get(title)

# ---------- Default XP settings ----------
DEFAULT_XP_TIERS = [
    {"max_words": 10, "xp": 5},
    {"max_words": 30, "xp": 10},
    {"max_words": 999, "xp": 20},
]
DEFAULT_XP_MEDIA = 15
DEFAULT_XP_REACTION = 1
DEFAULT_XP_VOICE_SILENT = 5
DEFAULT_XP_VOICE_TALKING = 15
DEFAULT_MSG_COOLDOWN = 60
DEFAULT_REACT_COOLDOWN = 10
DEFAULT_PROG_TYPE = "arithmetic"
DEFAULT_PROG_BASE = 100
DEFAULT_PROG_STEP = 150

VOICE_INTERVAL_SECS = 180

# ---------- Helper functions ----------
async def _fetch_avatar_image(session: aiohttp.ClientSession, url: str, size: int = 160) -> Image.Image:
    try:
        async with session.get(url) as resp:
            data = await resp.read()
        avatar = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
    except Exception:
        avatar = Image.new("RGBA", (size, size), (88, 101, 242, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    avatar.putalpha(mask)
    return avatar

def _fmt_xp(n: int) -> str:
    if n >= 1_000_000_000_000:
        return f"{n/1_000_000_000_000:.1f}T XP"
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B XP"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M XP"
    return f"{n:,} XP"

def xp_for_level(level: int, cfg: dict | None = None) -> int:
    if cfg is None:
        return DEFAULT_PROG_BASE + level * DEFAULT_PROG_STEP
    ptype = cfg.get("prog_type", DEFAULT_PROG_TYPE)
    base = int(cfg.get("prog_base", DEFAULT_PROG_BASE))
    step = float(cfg.get("prog_step", DEFAULT_PROG_STEP))
    if ptype == "geometric":
        mult = step if step > 1 else 1.5
        return max(1, int(base * (mult ** level)))
    return max(1, base + int(level * step))

def xp_for_message(content: str, cfg: dict | None = None) -> int:
    words = len(content.split()) if content else 0
    tiers = (cfg.get("xp_tiers", DEFAULT_XP_TIERS) if cfg else DEFAULT_XP_TIERS)
    for tier in sorted(tiers, key=lambda t: int(t["max_words"])):
        if words <= int(tier["max_words"]):
            return int(tier["xp"])
    return int(tiers[-1]["xp"]) if tiers else 5

# ---------- Emoji rendering helpers ----------
def is_emoji(char):
    cp = ord(char)
    return any(start <= cp <= end for start, end in [
        (0x1F600, 0x1F64F), (0x1F300, 0x1F5FF), (0x1F680, 0x1F6FF),
        (0x1F1E0, 0x1F1FF), (0x2600, 0x26FF), (0x2700, 0x27BF),
        (0x1F900, 0x1F9FF), (0x1FA00, 0x1FA6F), (0x1FA70, 0x1FAFF),
        (0x200D, 0x200D), (0xFE0F, 0xFE0F),
    ])

def _fetch_emoji_image_sync(emoji_char, size=28):
    code_points = '-'.join(f'{ord(c):x}' for c in emoji_char)
    url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{code_points}.png"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        return img
    except:
        return None

def _draw_text_with_emoji_sync(canvas, draw, x, y, text, font, fill_color, emoji_size=28):
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if is_emoji(ch):
            j = i + 1
            while j < len(text) and (
                text[j] in ('\u200d', '\ufe0f', '\u20e3') or
                ('\U0001f3fb' <= text[j] <= '\U0001f3ff')
            ):
                j += 1
            emoji_seq = text[i:j]
            tokens.append(('emoji', emoji_seq))
            i = j
        else:
            tokens.append(('text', ch))
            i += 1
    cur_x = x
    for typ, val in tokens:
        if typ == 'text':
            draw.text((cur_x, y), val, font=font, fill=fill_color)
            bbox = draw.textbbox((cur_x, y), val, font=font)
            cur_x += bbox[2] - bbox[0]
        else:
            emoji_img = _fetch_emoji_image_sync(val, size=emoji_size)
            if emoji_img:
                canvas.paste(emoji_img, (cur_x, y - 4), emoji_img)
                cur_x += emoji_size + 2
            else:
                draw.text((cur_x, y), val, font=font, fill=fill_color)
                bbox = draw.textbbox((cur_x, y), val, font=font)
                cur_x += bbox[2] - bbox[0]
    return cur_x

# ---------- SQLite configuration helpers ----------
async def get_config(db, guild_id: int) -> dict:
    row = await db.fetchone(
        "SELECT * FROM leveling_config WHERE guild_id = ?", str(guild_id)
    )
    if not row:
        cfg = _default_config()
        await set_config(db, guild_id, cfg)
        return cfg
    try:
        tiers = json.loads(row[13]) if row[13] else DEFAULT_XP_TIERS
    except Exception:
        tiers = DEFAULT_XP_TIERS
    return {
        "enabled": bool(row[1]),
        "announce_channel": row[2],
        "embed_enabled": bool(row[3]),
        "embed_title": row[4] or "🎉 Level Up!",
        "embed_message": row[5] or "{user} just reached **Level {level}**!",
        "embed_color": row[6] or "#e03030",
        "embed_image_url": row[7] or "",
        "embed_thumbnail": row[8] or "",
        "voice_xp_enabled": bool(row[9]),
        "prog_type": row[10] or DEFAULT_PROG_TYPE,
        "prog_base": int(row[11]) if row[11] is not None else DEFAULT_PROG_BASE,
        "prog_step": float(row[12]) if row[12] is not None else DEFAULT_PROG_STEP,
        "xp_tiers": tiers,
        "xp_media": int(row[14]) if row[14] is not None else DEFAULT_XP_MEDIA,
        "xp_reaction": int(row[15]) if row[15] is not None else DEFAULT_XP_REACTION,
        "xp_voice_silent": int(row[16]) if row[16] is not None else DEFAULT_XP_VOICE_SILENT,
        "xp_voice_talking": int(row[17]) if row[17] is not None else DEFAULT_XP_VOICE_TALKING,
        "msg_cooldown": int(row[18]) if row[18] is not None else DEFAULT_MSG_COOLDOWN,
        "react_cooldown": int(row[19]) if row[19] is not None else DEFAULT_REACT_COOLDOWN,
    }

def _default_config() -> dict:
    return {
        "enabled": True, "announce_channel": None,
        "embed_enabled": True,
        "embed_title": "🎉 Level Up!",
        "embed_message": "{user} just reached **Level {level}**!",
        "embed_color": "#e03030",
        "embed_image_url": "",
        "embed_thumbnail": "",
        "voice_xp_enabled": True,
        "prog_type": DEFAULT_PROG_TYPE,
        "prog_base": DEFAULT_PROG_BASE,
        "prog_step": DEFAULT_PROG_STEP,
        "xp_tiers": DEFAULT_XP_TIERS,
        "xp_media": DEFAULT_XP_MEDIA,
        "xp_reaction": DEFAULT_XP_REACTION,
        "xp_voice_silent": DEFAULT_XP_VOICE_SILENT,
        "xp_voice_talking": DEFAULT_XP_VOICE_TALKING,
        "msg_cooldown": DEFAULT_MSG_COOLDOWN,
        "react_cooldown": DEFAULT_REACT_COOLDOWN,
    }

async def set_config(db, guild_id: int, cfg: dict):
    tiers_json = json.dumps(cfg.get("xp_tiers", DEFAULT_XP_TIERS))
    await db.execute(
        """INSERT OR REPLACE INTO leveling_config (
            guild_id, enabled, announce_channel, embed_enabled, embed_title,
            embed_message, embed_color, embed_image_url, embed_thumbnail,
            voice_xp_enabled, prog_type, prog_base, prog_step, xp_tiers,
            xp_media, xp_reaction, xp_voice_silent, xp_voice_talking,
            msg_cooldown, react_cooldown
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        str(guild_id),
        int(cfg.get("enabled", True)),
        cfg.get("announce_channel"),
        int(cfg.get("embed_enabled", True)),
        cfg.get("embed_title", "🎉 Level Up!"),
        cfg.get("embed_message", "{user} just reached **Level {level}**!"),
        cfg.get("embed_color", "#e03030"),
        cfg.get("embed_image_url", ""),
        cfg.get("embed_thumbnail", ""),
        int(cfg.get("voice_xp_enabled", True)),
        cfg.get("prog_type", DEFAULT_PROG_TYPE),
        int(cfg.get("prog_base", DEFAULT_PROG_BASE)),
        float(cfg.get("prog_step", DEFAULT_PROG_STEP)),
        tiers_json,
        int(cfg.get("xp_media", DEFAULT_XP_MEDIA)),
        int(cfg.get("xp_reaction", DEFAULT_XP_REACTION)),
        int(cfg.get("xp_voice_silent", DEFAULT_XP_VOICE_SILENT)),
        int(cfg.get("xp_voice_talking", DEFAULT_XP_VOICE_TALKING)),
        int(cfg.get("msg_cooldown", DEFAULT_MSG_COOLDOWN)),
        int(cfg.get("react_cooldown", DEFAULT_REACT_COOLDOWN))
    )
    await db.commit()

async def get_exceptions(db, guild_id: int) -> dict:
    rows = await db.fetch(
        "SELECT type, target_id FROM leveling_exceptions WHERE guild_id = ?",
        str(guild_id)
    )
    channels = [int(r[1]) for r in rows if r[0] == "channel"]
    users = [int(r[1]) for r in rows if r[0] == "user"]
    return {"channels": channels, "users": users}

async def add_exception(db, guild_id: int, exc_type: str, target_id: int):
    await db.execute(
        "INSERT OR IGNORE INTO leveling_exceptions (guild_id, type, target_id) VALUES (?, ?, ?)",
        str(guild_id), exc_type, target_id
    )
    await db.commit()

async def remove_exception(db, guild_id: int, exc_type: str, target_id: int):
    await db.execute(
        "DELETE FROM leveling_exceptions WHERE guild_id = ? AND type = ? AND target_id = ?",
        str(guild_id), exc_type, target_id
    )
    await db.commit()

async def get_level_roles(db, guild_id: int) -> list[dict]:
    rows = await db.fetch(
        "SELECT level, role_id FROM level_roles WHERE guild_id = ? ORDER BY level",
        str(guild_id)
    )
    return [{"level": r[0], "role_id": r[1]} for r in rows]

async def set_level_role(db, guild_id: int, level: int, role_id: int):
    await db.execute(
        "INSERT OR REPLACE INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)",
        str(guild_id), level, role_id
    )
    await db.commit()

async def delete_level_role(db, guild_id: int, level: int):
    await db.execute(
        "DELETE FROM level_roles WHERE guild_id = ? AND level = ?",
        str(guild_id), level
    )
    await db.commit()

# ---------- User-specific settings helpers ----------
async def get_user_settings(db, guild_id: int, user_id: int) -> dict:
    row = await db.fetchone(
        "SELECT dm_notify, auto_role, hide_profile FROM user_level_settings WHERE guild_id = ? AND user_id = ?",
        str(guild_id), str(user_id)
    )
    if not row:
        return {"dm_notify": False, "auto_role": True, "hide_profile": False}
    return {"dm_notify": bool(row[0]), "auto_role": bool(row[1]), "hide_profile": bool(row[2])}

async def set_user_settings(db, guild_id: int, user_id: int, settings: dict):
    await db.execute(
        "INSERT OR REPLACE INTO user_level_settings (guild_id, user_id, dm_notify, auto_role, hide_profile) VALUES (?, ?, ?, ?, ?)",
        str(guild_id), str(user_id),
        int(settings.get("dm_notify", False)),
        int(settings.get("auto_role", True)),
        int(settings.get("hide_profile", False))
    )
    await db.commit()

# ---------- Rank card rendering ----------
def _render_rank_card(avatar: Image.Image, xp: int, level: int, total_xp: int,
                      rank_pos: int, needed: int, display_name: str,
                      messages: int = 0, voice_hours: float = 0.0,
                      reactions: int = 0) -> io.BytesIO:
    W, H = 1200, 500
    RADIUS = 28
    PAD = 40
    AVA = 180

    BG = (15, 3, 25, 255)
    BAR_BG = (30, 30, 50, 255)
    TEXT = (255, 245, 235, 255)
    TEXT2 = (200, 200, 210, 255)
    ACCENT = (255, 16, 240, 255)
    ACCENT2 = (57, 255, 20, 255)
    ACCENT3 = (204, 255, 0, 255)

    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG)
    draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, outline=ACCENT, width=5)
    draw.rounded_rectangle([4, 4, W-5, H-5], radius=RADIUS-4, outline=ACCENT2, width=2)

    ava_x = PAD
    ava_y = (H - AVA) // 2
    ring_size = AVA + 14
    ring_img = Image.new("RGBA", (ring_size, ring_size), (0,0,0,0))
    ImageDraw.Draw(ring_img).ellipse((0,0,ring_size-1,ring_size-1), outline=ACCENT2, width=6)
    img.paste(ring_img, (ava_x - 7, ava_y - 7), ring_img)
    img.paste(avatar, (ava_x, ava_y), avatar)

    font_name = _load_font(52, True)
    draw.text((ava_x + AVA + 30, 40), display_name[:24], font=font_name, fill=TEXT)

    font_level = _load_font(36, True)
    draw.text((ava_x + AVA + 30, 100), f"Level {level}", font=font_level, fill=ACCENT3)

    bar_x = ava_x + AVA + 30
    bar_y = 150
    bar_w = 600
    bar_h = 28
    progress = xp / needed if needed > 0 else 0
    fill_w = int(bar_w * progress)

    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_BG)
    if fill_w > 0:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h//2, fill=ACCENT)

    font_xp = _load_font(22, False)
    xp_text = f"{xp:,} / {needed:,} XP"
    draw.text((bar_x + bar_w + 20, bar_y + 2), xp_text, font=font_xp, fill=TEXT2)

    font_total = _load_font(24, False)
    draw.text((ava_x + AVA + 30, 200), f"Total XP: {total_xp:,}", font=font_total, fill=TEXT2)

    stat_y = 260
    stat_x = ava_x + AVA + 30
    font_stat = _load_font(28, False)

    _draw_text_with_emoji_sync(img, draw, stat_x, stat_y, f"💬 Messages: {messages:,}", font_stat, TEXT)
    _draw_text_with_emoji_sync(img, draw, stat_x, stat_y + 45, f"🎤 Voice: {voice_hours:.1f}h", font_stat, TEXT)
    _draw_text_with_emoji_sync(img, draw, stat_x, stat_y + 90, f"❤️ Reactions: {reactions:,}", font_stat, TEXT)

    rank_str = f"#{rank_pos}"
    font_rank = _load_font(72, True)
    bbox = draw.textbbox((0, 0), rank_str, font=font_rank)
    rw = bbox[2] - bbox[0]
    rank_x = W - PAD - rw
    rank_y = 30
    draw.text((rank_x, rank_y), rank_str, font=font_rank, fill=ACCENT)

    font_rank_label = _load_font(22, False)
    draw.text((rank_x + rw//2, rank_y + 90), "RANK", font=font_rank_label, fill=TEXT2, anchor="mt")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf

def _render_neon_leaderboard(guild_name: str, rows: list[dict], avatars: list[Image.Image],
                             page_offset: int, user_id: int) -> io.BytesIO:
    W = 1000
    ROW_H = 80
    HEADER_H = 60
    PAD = 30
    AVA_SIZE = 50
    RADIUS = 22

    BG = (12, 12, 28, 255)
    BORDER = NEON_PINK
    TEXT = (255, 255, 255, 255)
    TEXT2 = (200, 200, 210, 255)

    n = len(rows)
    H = HEADER_H + n * ROW_H + 80

    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG)
    draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, outline=BORDER, width=4)

    font_title = _load_font(36, True)
    font_sub = _load_font(24, False)
    font_small = _load_font(20, False)

    title_text = "🏆 LEVEL LEADERBOARD"
    tw = draw.textbbox((0, 0), title_text, font=font_title)[2] - draw.textbbox((0, 0), title_text, font=font_title)[0]
    _draw_text_with_emoji_sync(img, draw, W//2 - tw//2, 25, title_text, font_title, NEON_YELLOW, emoji_size=36)

    for i, r in enumerate(rows):
        y = HEADER_H + i * ROW_H
        rank = page_offset + i + 1
        name = r.get("name", f"ID: {r['user_id']}")[:20]
        level = r['level']
        xp = r['xp']
        total_xp = sum(xp_for_level(l, None) for l in range(level)) + xp
        xp_str = _fmt_xp(total_xp)

        font_rank = _load_font(36, True)
        rank_color = NEON_PINK if rank == 1 else NEON_GREEN if rank == 2 else NEON_YELLOW if rank == 3 else TEXT2
        draw.text((PAD + 10, y + 15), f"#{rank}", font=font_rank, fill=rank_color)

        if i < len(avatars):
            ava = avatars[i]
            img.paste(ava, (PAD + 80, y + 10), ava)

        draw.text((PAD + 150, y + 10), name, font=font_sub, fill=TEXT)
        draw.text((PAD + 150, y + 42), f"Lv.{level}  •  {xp_str}", font=font_small, fill=TEXT2)

    footer_y = H - 40
    draw.text((W//2, footer_y), f"{guild_name}  •  Leaderboard", font=font_small, fill=NEON_PINK, anchor="mt")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf

async def build_neon_leaderboard(guild: discord.Guild, rows: list[dict],
                                 page_offset: int, session: aiohttp.ClientSession,
                                 user_id: int) -> io.BytesIO:
    async def _fetch_safe(r):
        if r.get("avatar_url"):
            return await _fetch_avatar_image(session, r["avatar_url"], 50)
        else:
            return Image.new("RGBA", (50, 50), (88, 60, 60, 255))

    avatars = await asyncio.gather(*[_fetch_safe(r) for r in rows])
    return await asyncio.to_thread(
        _render_neon_leaderboard, guild.name, rows, avatars, page_offset, user_id
    )

def _render_level_up_card(member_name: str, avatar_img: Image.Image,
                          old_level: int, new_level: int,
                          title: str, badge: str,
                          current_xp: int, needed_xp: int) -> io.BytesIO:
    W, H = 934, 282
    RADIUS = 10

    BG = (30, 30, 30, 255)
    ACCENT = (255, 255, 255, 255)
    BAR_BG = (72, 72, 72, 255)
    BAR_FILL = (255, 255, 255, 255)
    TEXT = (255, 255, 255, 255)
    TEXT2 = (200, 200, 200, 255)

    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG)

    ava_size = 110
    ava_x, ava_y = 50, (H - ava_size) // 2
    mask = Image.new("L", (ava_size, ava_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, ava_size, ava_size), fill=255)
    avatar_cropped = avatar_img.copy()
    avatar_cropped.putalpha(mask)
    img.paste(avatar_cropped, (ava_x, ava_y), avatar_cropped)

    font_name = _load_font(36, True)
    draw.text((ava_x + ava_size + 30, 60), member_name[:20], font=font_name, fill=ACCENT)

    font_lvl = _load_font(48, True)
    draw.text((ava_x + ava_size + 30, 110), "LEVEL UP!", font=font_lvl, fill=ACCENT)

    font_lvl_num = _load_font(64, True)
    level_text = f"{new_level}"
    bbox = draw.textbbox((0, 0), level_text, font=font_lvl_num)
    level_w = bbox[2] - bbox[0]
    draw.text((W - 80 - level_w, 50), level_text, font=font_lvl_num, fill=ACCENT)

    bar_x = ava_x + ava_size + 30
    bar_y = 170
    bar_w = 500
    bar_h = 20
    progress = current_xp / needed_xp if needed_xp > 0 else 1
    fill_w = int(bar_w * progress)

    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_BG)
    if fill_w > bar_h:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_FILL)
    else:
        draw.ellipse([bar_x, bar_y, bar_x + bar_h, bar_y + bar_h], fill=BAR_FILL)

    font_xp = _load_font(20, False)
    xp_text = f"{current_xp:,} / {needed_xp:,} XP"
    draw.text((bar_x, bar_y + bar_h + 10), xp_text, font=font_xp, fill=TEXT2)

    font_small = _load_font(16, False)
    draw.text((W - 150, 20), "Gurten | LGC", font=font_small, fill=(150, 150, 150, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf

# ---------- Leaderboard pagination view ----------
class LeaderboardView(discord.ui.View):
    def __init__(self, cog, guild, rows, page, total_pages):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild = guild
        self.rows = rows
        self.page = page
        self.total_pages = total_pages
        self.message = None
        self._refresh()

    def _refresh(self):
        self.prev_btn.disabled = (self.page == 0)
        self.next_btn.disabled = (self.page >= self.total_pages - 1)
        self.page_lbl.label = f"{self.page + 1} / {self.total_pages}"

    @discord.ui.button(label="◀ Өмнөх", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction, button):
        await interaction.response.defer()
        if self.page > 0:
            self.page -= 1
            self._refresh()
            await self.cog._send_lb_page(interaction, self.guild, self.page, self.total_pages, edit=True)

    @discord.ui.button(label="1 / 1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_lbl(self, interaction, button):
        await interaction.response.defer()

    @discord.ui.button(label="Дараах ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction, button):
        await interaction.response.defer()
        if self.page < self.total_pages - 1:
            self.page += 1
            self._refresh()
            await self.cog._send_lb_page(interaction, self.guild, self.page, self.total_pages, edit=True)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except:
                pass

# ---------- Settings Panel Modals and Views ----------
class ChannelModal(Modal, title="Мэдэгдлийн суваг тохируулах"):
    channel_id = TextInput(label="Сувгийн ID", placeholder="123456789", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
        except:
            return await interaction.response.send_message("❌ Буруу сувгийн ID.", ephemeral=True)
        if not channel or not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("❌ Суваг олдсонгүй эсвэл текст суваг биш.", ephemeral=True)
        cfg = await get_config(interaction.client.db, interaction.guild_id)
        cfg["announce_channel"] = channel.id
        await set_config(interaction.client.db, interaction.guild_id, cfg)
        await interaction.response.send_message(f"✅ Мэдэгдэл {channel.mention} сувагт ирнэ.", ephemeral=True)

class XPBoostModal(Modal, title="XP нэмэх/хасах"):
    user_id = TextInput(label="Хэрэглэгчийн ID", required=True)
    amount = TextInput(label="XP хэмжээ (эерэг/сөрөг)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
            xp = int(self.amount.value)
        except:
            return await interaction.response.send_message("❌ Тоон утга оруулна уу.", ephemeral=True)
        member = interaction.guild.get_member(uid)
        if not member:
            return await interaction.response.send_message("❌ Хэрэглэгч олдсонгүй.", ephemeral=True)
        leveling = interaction.client.get_cog("Leveling")
        await leveling._add_xp(uid, interaction.guild_id, xp, member=member)
        await interaction.response.send_message(f"✅ {member.mention}-д {xp} XP оноолоо.", ephemeral=True)

class SettingsView(View):
    def __init__(self, bot, ctx, cfg):
        super().__init__(timeout=300)
        self.bot = bot
        self.ctx = ctx
        self.cfg = cfg

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("⛔ Админ эрх шаардлагатай.", ephemeral=True)
        return False

    @discord.ui.button(label="📢 Мэдэгдлийн суваг", style=discord.ButtonStyle.secondary, row=0)
    async def set_channel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ChannelModal())

    @discord.ui.button(label="🔔 Системийг унтраах/асаах", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_enabled(self, interaction: discord.Interaction, button: Button):
        self.cfg["enabled"] = not self.cfg["enabled"]
        await set_config(self.bot.db, interaction.guild_id, self.cfg)
        status = "ассан" if self.cfg["enabled"] else "унтарсан"
        await interaction.response.send_message(f"✅ Түвшний систем {status}.", ephemeral=True)

    @discord.ui.button(label="🎤 Дуут XP", style=discord.ButtonStyle.secondary, row=0)
    async def voice_xp(self, interaction: discord.Interaction, button: Button):
        self.cfg["voice_xp_enabled"] = not self.cfg["voice_xp_enabled"]
        await set_config(self.bot.db, interaction.guild_id, self.cfg)
        status = "ассан" if self.cfg["voice_xp_enabled"] else "унтарсан"
        await interaction.response.send_message(f"✅ Дуут XP {status}.", ephemeral=True)

    @discord.ui.button(label="⚙️ XP Tiers засах", style=discord.ButtonStyle.secondary, row=1)
    async def set_tiers(self, interaction: discord.Interaction, button: Button):
        modal = Modal(title="XP Tiers (JSON)")
        modal.add_item(TextInput(label="JSON массив", default=json.dumps(self.cfg["xp_tiers"], indent=2), required=True, style=discord.TextStyle.long))

        async def on_submit(inter):
            try:
                new_tiers = json.loads(modal.children[0].value)
                if isinstance(new_tiers, list):
                    self.cfg["xp_tiers"] = new_tiers
                    await set_config(self.bot.db, inter.guild_id, self.cfg)
                    await inter.response.send_message("✅ XP Tiers шинэчлэгдлээ.", ephemeral=True)
                else:
                    await inter.response.send_message("❌ Массив байх ёстой.", ephemeral=True)
            except:
                await inter.response.send_message("❌ JSON буруу байна.", ephemeral=True)
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📊 Прогресс төрөл", style=discord.ButtonStyle.secondary, row=1)
    async def prog_type(self, interaction: discord.Interaction, button: Button):
        select = Select(placeholder="Прогресс төрөл сонгох", options=[
            discord.SelectOption(label="Арифметик", value="arithmetic"),
            discord.SelectOption(label="Геометр", value="geometric")
        ])

        async def select_callback(inter):
            self.cfg["prog_type"] = select.values[0]
            await set_config(self.bot.db, inter.guild_id, self.cfg)
            await inter.response.send_message(f"✅ Прогресс төрөл {select.values[0]} боллоо.", ephemeral=True)
        select.callback = select_callback
        view = View(timeout=30)
        view.add_item(select)
        await interaction.response.send_message("Төрөл сонгоно уу:", view=view, ephemeral=True)

    @discord.ui.button(label="➕/- XP засах", style=discord.ButtonStyle.secondary, row=2)
    async def adjust_xp(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(XPBoostModal())

    @discord.ui.button(label="📊 Үндсэн/Алхам", style=discord.ButtonStyle.secondary, row=2)
    async def base_step(self, interaction: discord.Interaction, button: Button):
        modal = Modal(title="XP Base & Step")
        modal.add_item(TextInput(label="Үндсэн XP", default=str(self.cfg["prog_base"]), required=True))
        modal.add_item(TextInput(label="Алхам", default=str(self.cfg["prog_step"]), required=True))

        async def on_submit(inter):
            try:
                base = int(modal.children[0].value)
                step = float(modal.children[1].value)
                self.cfg["prog_base"] = base
                self.cfg["prog_step"] = step
                await set_config(self.bot.db, inter.guild_id, self.cfg)
                await inter.response.send_message("✅ Тохиргоо шинэчлэгдлээ.", ephemeral=True)
            except:
                await inter.response.send_message("❌ Тоон утга оруулна уу.", ephemeral=True)
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

# ---------- User Settings View ----------
class UserSettingsView(View):
    def __init__(self, cog, ctx, user_settings):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.settings = user_settings

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message("❌ Зөвхөн өөрийн тохиргоог өөрчлөх боломжтой.", ephemeral=True)
        return False

    @discord.ui.button(label="🔔 DM мэдэгдэл", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_dm(self, interaction: discord.Interaction, button: Button):
        self.settings["dm_notify"] = not self.settings["dm_notify"]
        await set_user_settings(self.cog.bot.db, interaction.guild_id, interaction.user.id, self.settings)
        status = "Асах" if self.settings["dm_notify"] else "Унтрах"
        await interaction.response.send_message(f"✅ DM мэдэгдэл: {status}", ephemeral=True)

    @discord.ui.button(label="🏷️ Автомат цол", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_auto_role(self, interaction: discord.Interaction, button: Button):
        self.settings["auto_role"] = not self.settings["auto_role"]
        await set_user_settings(self.cog.bot.db, interaction.guild_id, interaction.user.id, self.settings)
        status = "Асах" if self.settings["auto_role"] else "Унтрах"
        await interaction.response.send_message(f"✅ Автомат цол: {status}", ephemeral=True)

    @discord.ui.button(label="👤 Профайл нууц", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_hide_profile(self, interaction: discord.Interaction, button: Button):
        self.settings["hide_profile"] = not self.settings["hide_profile"]
        await set_user_settings(self.cog.bot.db, interaction.guild_id, interaction.user.id, self.settings)
        status = "Нууц" if self.settings["hide_profile"] else "Нээлттэй"
        await interaction.response.send_message(f"✅ Профайл: {status}", ephemeral=True)

# ---------- Main Leveling Cog ----------
class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self._msg_cooldown = {}
        self._react_cooldown = {}
        self._voice_join = {}
        self._voice_last_xp = {}
        self._voice_xp_task = None

    async def cog_load(self):
        await self.init_db()
        self.session = aiohttp.ClientSession()
        self._voice_xp_task = asyncio.create_task(self._voice_xp_loop())

    async def cog_unload(self):
        if self._voice_xp_task:
            self._voice_xp_task.cancel()
        if self.session:
            await self.session.close()

    async def init_db(self):
        # Fix missing PK
        try:
            table_info = await self.bot.db.fetch("PRAGMA table_info(levels)")
            if table_info:
                has_pk = any(col[5] for col in table_info)
                if not has_pk:
                    log.info("levels хүснэгтэд PRIMARY KEY байхгүй, засаж байна...")
                    await self.bot.db.execute("ALTER TABLE levels RENAME TO levels_old")
                    await self.bot.db.commit()
                    await self.bot.db.execute('''
                        CREATE TABLE levels (
                            user_id TEXT, guild_id TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
                            message_count INTEGER DEFAULT 0, voice_seconds INTEGER DEFAULT 0,
                            reaction_count INTEGER DEFAULT 0, PRIMARY KEY (user_id, guild_id)
                        )
                    ''')
                    await self.bot.db.commit()
                    await self.bot.db.execute('''
                        INSERT INTO levels SELECT user_id, guild_id, MAX(xp), MAX(level), MAX(message_count), MAX(voice_seconds), MAX(reaction_count)
                        FROM levels_old GROUP BY user_id, guild_id
                    ''')
                    await self.bot.db.commit()
                    await self.bot.db.execute("DROP TABLE levels_old")
                    await self.bot.db.commit()
        except Exception as e:
            log.error(f"levels table fix error: {e}")

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS levels (
            user_id TEXT, guild_id TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
            message_count INTEGER DEFAULT 0, voice_seconds INTEGER DEFAULT 0,
            reaction_count INTEGER DEFAULT 0, PRIMARY KEY (user_id, guild_id)
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS leveling_config (
            guild_id TEXT PRIMARY KEY, enabled INTEGER DEFAULT 1, announce_channel INTEGER,
            embed_enabled INTEGER DEFAULT 1, embed_title TEXT DEFAULT '🎉 Level Up!',
            embed_message TEXT DEFAULT '{user} just reached **Level {level}**!',
            embed_color TEXT DEFAULT '#e03030', embed_image_url TEXT, embed_thumbnail TEXT,
            voice_xp_enabled INTEGER DEFAULT 1, prog_type TEXT DEFAULT 'arithmetic',
            prog_base INTEGER DEFAULT 100, prog_step REAL DEFAULT 150, xp_tiers TEXT,
            xp_media INTEGER DEFAULT 15, xp_reaction INTEGER DEFAULT 1,
            xp_voice_silent INTEGER DEFAULT 5, xp_voice_talking INTEGER DEFAULT 15,
            msg_cooldown INTEGER DEFAULT 60, react_cooldown INTEGER DEFAULT 10
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS leveling_exceptions (
            guild_id TEXT, type TEXT, target_id INTEGER, PRIMARY KEY (guild_id, type, target_id)
        )''')
        await self.bot.db.commit()

        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS level_roles (
            guild_id TEXT, level INTEGER, role_id INTEGER, PRIMARY KEY (guild_id, level)
        )''')
        await self.bot.db.commit()

        # New: user settings table
        await self.bot.db.execute('''CREATE TABLE IF NOT EXISTS user_level_settings (
            guild_id TEXT, user_id TEXT, dm_notify INTEGER DEFAULT 0,
            auto_role INTEGER DEFAULT 1, hide_profile INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )''')
        await self.bot.db.commit()

        for col in ["message_count", "voice_seconds", "reaction_count"]:
            try:
                await self.bot.db.execute(f"ALTER TABLE levels ADD COLUMN {col} INTEGER DEFAULT 0")
                await self.bot.db.commit()
            except:
                pass

    def _on_cooldown(self, storage, user_id, seconds, guild_id=0):
        now = time.monotonic()
        key = (guild_id, user_id)
        last = storage.get(key, 0)
        if now - last < seconds:
            return True
        storage[key] = now
        return False

    async def _voice_xp_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = time.monotonic()
                for guild in self.bot.guilds:
                    cfg = await get_config(self.bot.db, guild.id)
                    if not cfg["enabled"] or not cfg.get("voice_xp_enabled", True):
                        continue
                    exc = await get_exceptions(self.bot.db, guild.id)
                    for vc in guild.voice_channels:
                        for member in vc.members:
                            if member.bot or member.id in exc["users"] or member.voice.self_deaf or member.voice.deaf:
                                continue
                            if member.id not in self._voice_join:
                                self._voice_join[member.id] = now
                                self._voice_last_xp[member.id] = now
                            last_xp = self._voice_last_xp.get(member.id, now)
                            if now - last_xp >= VOICE_INTERVAL_SECS:
                                talking = not member.voice.self_mute and not member.voice.mute
                                xp = int(cfg["xp_voice_talking"] if talking else cfg["xp_voice_silent"])
                                self._voice_last_xp[member.id] = now
                                await self._add_xp(member.id, guild.id, xp, member=member, check_mute=False)
                                await self.bot.db.execute(
                                    "INSERT INTO levels (user_id, guild_id, voice_seconds) VALUES (?,?,?) "
                                    "ON CONFLICT(user_id, guild_id) DO UPDATE SET voice_seconds = voice_seconds + ?",
                                    str(member.id), str(guild.id), VOICE_INTERVAL_SECS, VOICE_INTERVAL_SECS
                                )
                                await self.bot.db.commit()
            except Exception as e:
                log.error(f"Voice XP loop error: {e}")
            await asyncio.sleep(30)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and not after.channel:
            self._voice_join.pop(member.id, None)
            self._voice_last_xp.pop(member.id, None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        cfg = await get_config(self.bot.db, message.guild.id)
        if not cfg["enabled"]:
            return
        exc = await get_exceptions(self.bot.db, message.guild.id)
        if message.channel.id in exc["channels"] or message.author.id in exc["users"]:
            return
        if message.author.timed_out_until and message.author.timed_out_until > datetime.now(timezone.utc):
            return
        msg_cd = int(cfg.get("msg_cooldown", 60))
        if self._on_cooldown(self._msg_cooldown, message.author.id, msg_cd, message.guild.id):
            return
        xp = xp_for_message(message.content or "", cfg)
        if message.attachments and message.channel.permissions_for(message.author).attach_files:
            xp += int(cfg.get("xp_media", DEFAULT_XP_MEDIA))
        await self._add_xp(message.author.id, message.guild.id, xp, member=message.author, channel=message.channel)
        await self.bot.db.execute(
            "INSERT INTO levels (user_id, guild_id, message_count) VALUES (?,?,1) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET message_count = message_count + 1",
            str(message.author.id), str(message.guild.id)
        )
        await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id or payload.user_id == self.bot.user.id:
            return
        cfg = await get_config(self.bot.db, payload.guild_id)
        if not cfg["enabled"]:
            return
        exc = await get_exceptions(self.bot.db, payload.guild_id)
        if payload.channel_id in exc["channels"] or payload.user_id in exc["users"]:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        if self._on_cooldown(self._react_cooldown, payload.user_id, cfg.get("react_cooldown", 10), payload.guild_id):
            return
        await self._add_xp(payload.user_id, payload.guild_id, cfg.get("xp_reaction", 1), member=member, check_mute=False)
        await self.bot.db.execute(
            "INSERT INTO levels (user_id, guild_id, reaction_count) VALUES (?,?,1) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET reaction_count = reaction_count + 1",
            str(payload.user_id), str(payload.guild_id)
        )
        await self.bot.db.commit()

    async def _add_xp(self, user_id, guild_id, amount, member=None, check_mute=True, channel=None):
        cafe = self.bot.get_cog("Cafe")
        if cafe:
            buff = cafe.get_buff(user_id, guild_id)
            if buff and buff.get('type') == 'xp_boost':
                amount = int(amount * buff.get('xp_mult', 1.0))
        if member and check_mute:
            if member.timed_out_until and member.timed_out_until > datetime.now(timezone.utc):
                return
            if hasattr(member, 'voice') and member.voice and (member.voice.mute or member.voice.self_mute):
                return
        row = await self.bot.db.fetchone("SELECT xp, level FROM levels WHERE user_id=? AND guild_id=?", str(user_id), str(guild_id))
        xp, level = row if row else (0, 1)
        old_level = level
        new_xp = xp + amount
        cfg = await get_config(self.bot.db, guild_id)
        leveled_up = False
        while True:
            needed = xp_for_level(level, cfg)
            if new_xp >= needed:
                new_xp -= needed
                level += 1
                leveled_up = True
            else:
                break
        await self.bot.db.execute(
            "INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET xp=excluded.xp, level=excluded.level",
            str(user_id), str(guild_id), new_xp, level
        )
        await self.bot.db.commit()
        if leveled_up and member:
            await self._announce_level_up(member, old_level, level, new_xp, channel)

    async def _announce_level_up(self, member, old_level, new_level, current_xp, source_channel):
        guild = member.guild
        cfg = await get_config(self.bot.db, guild.id)
        for entry in await get_level_roles(self.bot.db, guild.id):
            if new_level >= entry["level"]:
                role = guild.get_role(entry["role_id"])
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Leveling: reached level {new_level}")
                    except:
                        pass
        user_set = await get_user_settings(self.bot.db, guild.id, member.id)
        if user_set.get("auto_role", True):
            await self.assign_auto_rank_role(member, new_level)
        channel_id = cfg.get("announce_channel")
        target_channel = guild.get_channel(channel_id) if channel_id else source_channel or guild.system_channel
        if not target_channel:
            return
        title, badge = get_rank_info(new_level)
        next_xp = xp_for_level(new_level, cfg)
        avatar_url = str(member.display_avatar.replace(size=128, format="png").url)
        try:
            async with self.session.get(avatar_url) as resp:
                data = await resp.read()
            avatar_img = Image.open(io.BytesIO(data)).convert("RGBA").resize((110, 110))
        except:
            avatar_img = Image.new("RGBA", (110, 110), (88, 101, 242, 255))
        card_buf = await asyncio.to_thread(_render_level_up_card, member.display_name, avatar_img, old_level, new_level, title, badge, current_xp, next_xp)
        file = discord.File(card_buf, "levelup.png")
        if user_set.get("dm_notify", False):
            try:
                await member.send(content="🎉 Таны түвшин ахилаа!", file=file)
            except:
                pass
        else:
            try:
                await target_channel.send(content=member.mention, file=file)
            except:
                pass

    async def assign_auto_rank_role(self, member, new_level):
        if not member or not member.guild:
            return
        target_role_name = get_rank_role_name(new_level)
        if not target_role_name:
            return
        me = member.guild.me
        if not me.guild_permissions.manage_roles:
            return
        target_role = discord.utils.get(member.guild.roles, name=target_role_name)
        if not target_role:
            try:
                target_role = await member.guild.create_role(name=target_role_name)
                if target_role.position >= me.top_role.position:
                    await target_role.edit(position=max(1, me.top_role.position - 1))
            except:
                return
        if target_role.position >= me.top_role.position:
            return
        for role_name in RANK_ROLES.values():
            if role_name == target_role_name:
                continue
            old_role = discord.utils.get(member.guild.roles, name=role_name)
            if old_role and old_role in member.roles:
                try:
                    await member.remove_roles(old_role, reason="Түвшин ахисан")
                except:
                    pass
        if target_role not in member.roles:
            try:
                await member.add_roles(target_role, reason=f"{new_level} түвшинд хүрсэн")
            except:
                pass

    def get_rank_info(self, level):
        return get_rank_info(level)

    async def add_xp(self, user_id, guild_id, amount, member=None, check_mute=True, channel=None):
        await self._add_xp(user_id, guild_id, amount, member=member, check_mute=check_mute, channel=channel)

    async def add_command_xp(self, user_id, guild_id, member, channel):
        await self._add_xp(user_id, guild_id, 2, member=member, check_mute=True, channel=channel)

    # ---------- User commands ----------
    @commands.hybrid_group(name="leveling", invoke_without_command=True)
    async def leveling_group(self, ctx):
        await ctx.send_help(ctx.command)

    @leveling_group.command(name="user", aliases=["level", "rank"])
    @app_commands.describe(user="Хэрэглэгч (хоосон бол өөрөө)")
    async def user_rank(self, ctx, user: discord.Member | None = None):
        target = user or ctx.author
        user_set = await get_user_settings(self.bot.db, ctx.guild.id, target.id)
        if target != ctx.author and user_set.get("hide_profile", False) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Энэ хэрэглэгч профайлаа нууцалсан.", ephemeral=True)
        await ctx.defer()
        row = await self.bot.db.fetchone(
            "SELECT xp, level, message_count, voice_seconds, reaction_count FROM levels WHERE user_id=? AND guild_id=?",
            str(target.id), str(ctx.guild.id)
        )
        if not row:
            xp, level, messages, voice_secs, reactions = 0, 1, 0, 0, 0
        else:
            xp, level, messages, voice_secs, reactions = row
            messages = messages or 0; voice_secs = voice_secs or 0; reactions = reactions or 0
        cfg = await get_config(self.bot.db, ctx.guild.id)
        total_xp = sum(xp_for_level(l, cfg) for l in range(level)) + xp
        rows = await self.bot.db.fetch(
            "SELECT user_id FROM levels WHERE guild_id=? ORDER BY level DESC, xp DESC", str(ctx.guild.id)
        )
        rank_pos = next((i+1 for i, (uid,) in enumerate(rows) if int(uid) == target.id), len(rows)+1)
        needed = xp_for_level(level, cfg)
        voice_hours = voice_secs / 3600.0
        avatar_url = str(target.display_avatar.replace(size=256, format="png").url)
        avatar = await _fetch_avatar_image(self.session, avatar_url, 180)
        buf = await asyncio.to_thread(
            _render_rank_card, avatar, xp, level, total_xp, rank_pos, needed,
            target.display_name, messages, voice_hours, reactions
        )
        embed = discord.Embed(color=0xFF10F0)
        embed.set_image(url="attachment://rank.png")
        embed.set_footer(text=f"{ctx.guild.name}")
        await ctx.send(embed=embed, file=discord.File(buf, filename="rank.png"))

    @leveling_group.command(name="leaderboard", aliases=["top", "tlb"])
    async def leaderboard_top(self, ctx):
        await ctx.defer()
        rows = await self.bot.db.fetch(
            "SELECT user_id, xp, level FROM levels WHERE guild_id=? ORDER BY level DESC, xp DESC LIMIT 10",
            str(ctx.guild.id)
        )
        if not rows:
            return await ctx.send("Одоогоор түвшний мэдээлэл байхгүй!")
        enriched = []
        for uid, xp, lvl in rows:
            user = ctx.guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
            enriched.append({
                "user_id": str(uid), "xp": xp, "level": lvl,
                "name": user.display_name[:20],
                "avatar_url": str(user.display_avatar.replace(size=64, format="png").url) if user.avatar else None,
            })
        buf = await build_neon_leaderboard(ctx.guild, enriched, 0, self.session, ctx.author.id)
        embed = discord.Embed(color=0xFF10F0)
        embed.set_image(url="attachment://leaderboard.png")
        embed.set_footer(text=f"{ctx.guild.name}  •  ТОП 10")
        file = discord.File(buf, filename="leaderboard.png")
        total_pages = (len(enriched)+9)//10
        view = LeaderboardView(self, ctx.guild, enriched, 0, total_pages)
        msg = await ctx.send(embed=embed, file=file, view=view)
        view.message = msg

    async def _send_lb_page(self, interaction, guild, page, total_pages, edit=False):
        offset = page * 10
        rows = await self.bot.db.fetch(
            "SELECT user_id, xp, level FROM levels WHERE guild_id=? ORDER BY level DESC, xp DESC LIMIT 10 OFFSET ?",
            str(guild.id), offset
        )
        if not rows:
            return
        enriched = []
        for uid, xp, lvl in rows:
            user = guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
            enriched.append({
                "user_id": str(uid), "xp": xp, "level": lvl,
                "name": user.display_name[:20],
                "avatar_url": str(user.display_avatar.replace(size=64, format="png").url) if user.avatar else None,
            })
        buf = await build_neon_leaderboard(guild, enriched, offset, self.session, interaction.user.id)
        file = discord.File(buf, filename="leaderboard.png")
        embed = discord.Embed(color=0xFF10F0)
        embed.set_image(url="attachment://leaderboard.png")
        embed.set_footer(text=f"{guild.name}  •  ТОП {offset+1}-{offset+len(rows)}")
        if edit:
            await interaction.edit_original_response(embed=embed, attachments=[file], view=interaction.message.view)
        else:
            await interaction.followup.send(embed=embed, file=file, view=interaction.message.view)

    @commands.hybrid_command(name="rank", aliases=["grank"])
    @app_commands.describe(user="Хэрэглэгч (хоосон бол өөрөө)")
    async def rank_command(self, ctx, user: discord.Member | None = None):
        await self.user_rank(ctx, user)

    # ---------- User settings command ----------
    @leveling_group.command(name="mysettings", description="Өөрийн түвшний тохиргоо")
    async def my_settings(self, ctx):
        settings = await get_user_settings(self.bot.db, ctx.guild.id, ctx.author.id)
        embed = discord.Embed(title="⚙️ Таны түвшний тохиргоо", color=INFO_COLOR)
        embed.add_field(name="🔔 DM мэдэгдэл", value="Асах" if settings["dm_notify"] else "Унтрах", inline=True)
        embed.add_field(name="🏷️ Автомат цол", value="Асах" if settings["auto_role"] else "Унтрах", inline=True)
        embed.add_field(name="👤 Профайл нууц", value="Нууц" if settings["hide_profile"] else "Нээлттэй", inline=True)
        view = UserSettingsView(self, ctx, settings)
        await ctx.send(embed=embed, view=view)

    # ---------- Admin commands ----------
    @leveling_group.command(name="set", description="Мэдэгдэл суваг тохируулах")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, ctx):
        cfg = await get_config(self.bot.db, ctx.guild.id)
        cfg["announce_channel"] = ctx.channel.id
        await set_config(self.bot.db, ctx.guild.id, cfg)
        await ctx.send(f"✅ Мэдэгдэл {ctx.channel.mention} сувагт ирнэ.", ephemeral=True)

    @leveling_group.command(name="stop", description="Мэдэгдэл унтраах")
    @app_commands.checks.has_permissions(administrator=True)
    async def stop_announce(self, ctx):
        cfg = await get_config(self.bot.db, ctx.guild.id)
        cfg["announce_channel"] = None
        await set_config(self.bot.db, ctx.guild.id, cfg)
        await ctx.send("✅ Мэдэгдэл унтарлаа.", ephemeral=True)

    @leveling_group.command(name="toggle", description="Систем идэвхжүүлэх/унтраах")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(state=[app_commands.Choice(name="Enable", value="on"), app_commands.Choice(name="Disable", value="off")])
    async def toggle_leveling(self, ctx, state: str):
        cfg = await get_config(self.bot.db, ctx.guild.id)
        cfg["enabled"] = (state == "on")
        await set_config(self.bot.db, ctx.guild.id, cfg)
        await ctx.send(f"✅ Систем {'идэвхжлээ' if state=='on' else 'унтарлаа'}.", ephemeral=True)

    @leveling_group.command(name="exception", description="Онцгой тохиолдолуудыг нэмэх эсвэл устгах")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(action=[app_commands.Choice(name="Add", value="add"), app_commands.Choice(name="Remove", value="remove")],
                          exc_type=[app_commands.Choice(name="Channel", value="channel"), app_commands.Choice(name="User", value="user")])
    async def exception(self, ctx, action: str, exc_type: str,
                        channel: discord.TextChannel = None, user: discord.Member = None):
        if exc_type == "channel" and not channel:
            return await ctx.send("Суваг сонгоно уу.", ephemeral=True)
        if exc_type == "user" and not user:
            return await ctx.send("Хэрэглэгч сонгоно уу.", ephemeral=True)
        target_id = channel.id if exc_type == "channel" else user.id
        target_name = channel.mention if exc_type == "channel" else user.mention
        if action == "add":
            await add_exception(self.bot.db, ctx.guild.id, exc_type, target_id)
            await ctx.send(f"✅ {target_name} онцгой тохиолдолд нэмэгдлээ.", ephemeral=True)
        else:
            await remove_exception(self.bot.db, ctx.guild.id, exc_type, target_id)
            await ctx.send(f"✅ {target_name} онцгой тохиолдлоос хасагдлаа.", ephemeral=True)

    @leveling_group.command(name="exceptions", description="Онцгой тохиолдолуудыг жагсаах")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_exceptions(self, ctx):
        exc = await get_exceptions(self.bot.db, ctx.guild.id)
        if not exc["channels"] and not exc["users"]:
            return await ctx.send("Онцгой тохиолдол байхгүй.", ephemeral=True)
        embed = discord.Embed(title="Leveling онцгой тохиолдлууд", color=INFO_COLOR)
        if exc["channels"]:
            embed.add_field(name="Сувгууд", value=", ".join(f"<#{c}>" for c in exc["channels"]), inline=False)
        if exc["users"]:
            embed.add_field(name="Хэрэглэгчид", value=", ".join(f"<@{u}>" for u in exc["users"]), inline=False)
        await ctx.send(embed=embed, ephemeral=True)

    @leveling_group.command(name="setxp", description="Хэрэглэгчийн XP-ийг тохируулах")
    @app_commands.checks.has_permissions(administrator=True)
    async def setxp(self, ctx, user: discord.Member, amount: int):
        if amount < 0:
            return await ctx.send("XP 0-с бага байж болохгүй.", ephemeral=True)
        cfg = await get_config(self.bot.db, ctx.guild.id)
        level = 1
        remaining = amount
        while True:
            needed = xp_for_level(level, cfg)
            if remaining >= needed:
                remaining -= needed
                level += 1
            else:
                break
        await self.bot.db.execute(
            "INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = excluded.xp, level = excluded.level",
            str(user.id), str(ctx.guild.id), remaining, level
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ {user.display_name} → Level {level} ({remaining} XP).", ephemeral=True)

    @leveling_group.command(name="reset", description="Хэрэглэгчийн XP устгах")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, ctx, user: discord.Member):
        await self.bot.db.execute(
            "DELETE FROM levels WHERE user_id = ? AND guild_id = ?",
            str(user.id), str(ctx.guild.id)
        )
        await self.bot.db.commit()
        await ctx.send(f"✅ {user.display_name}-ийн XP устгагдлаа.", ephemeral=True)

    @leveling_group.command(name="setrole", description="Түвшний роль оноох")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_level_role(self, ctx, level: int, role: discord.Role):
        await set_level_role(self.bot.db, ctx.guild.id, level, role.id)
        await ctx.send(f"✅ {role.mention} ролийг {level}-р түвшинд оноолоо.", ephemeral=True)

    @leveling_group.command(name="removerole")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_level_role(self, ctx, level: int):
        await delete_level_role(self.bot.db, ctx.guild.id, level)
        await ctx.send(f"✅ {level}-р түвшний роль устгагдлаа.", ephemeral=True)

    @leveling_group.command(name="roles", description="Түвшний ролиудыг жагсаах")
    async def list_level_roles(self, ctx):
        entries = await get_level_roles(self.bot.db, ctx.guild.id)
        if not entries:
            return await ctx.send("Түвшний роль тохируулаагүй байна.", ephemeral=True)
        embed = discord.Embed(title="🎖️ Түвшний ролиуд", color=GOLD_COLOR)
        for e in entries:
            role = ctx.guild.get_role(e["role_id"])
            embed.add_field(name=f"Level {e['level']}", value=role.mention if role else f"<@&{e['role_id']}>", inline=True)
        await ctx.send(embed=embed, ephemeral=True)

    @leveling_group.command(name="addxp", description="Зөвхөн бот эзэмшигч. Хэрэглэгчид XP нэмэх.")
    async def addxp_owner(self, ctx, member: discord.Member, amount: int):
        if not await self.bot.is_owner(ctx.author):
            return await ctx.send("⛔ Зөвхөн бот эзэмшигч ашиглах боломжтой.", ephemeral=True)
        if amount <= 0:
            return await ctx.send("Эерэг тоо оруулна уу.", ephemeral=True)
        await self._add_xp(member.id, ctx.guild.id, amount, member=member)
        await ctx.send(f"✅ {member.mention}-д {amount} XP нэмлээ.")

    @leveling_group.command(name="removexp", description="Зөвхөн бот эзэмшигч. Хэрэглэгчээс XP хасах.")
    async def removexp_owner(self, ctx, member: discord.Member, amount: int):
        if not await self.bot.is_owner(ctx.author):
            return await ctx.send("⛔ Зөвхөн бот эзэмшигч ашиглах боломжтой.", ephemeral=True)
        if amount <= 0:
            return await ctx.send("Эерэг тоо оруулна уу.", ephemeral=True)
        await self._add_xp(member.id, ctx.guild.id, -amount, member=member)
        await ctx.send(f"✅ {member.mention}-ээс {amount} XP хасагдлаа.")

    @leveling_group.command(name="test", description="Туршилтын level-up карт илгээх (админ)")
    @app_commands.checks.has_permissions(administrator=True)
    async def levelup_test(self, ctx):
        member = ctx.author
        row = await self.bot.db.fetchone(
            "SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?",
            str(member.id), str(ctx.guild.id)
        )
        if row:
            xp, level = row
        else:
            xp, level = 0, 1

        cfg = await get_config(self.bot.db, ctx.guild.id)
        needed = xp_for_level(level, cfg)
        title, badge = get_rank_info(level)

        avatar_url = str(member.display_avatar.replace(size=128, format="png").url)
        try:
            async with self.session.get(avatar_url) as resp:
                avatar_data = await resp.read()
            avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA").resize((110, 110))
        except Exception:
            avatar_img = Image.new("RGBA", (110, 110), (88, 101, 242, 255))

        buf = await asyncio.to_thread(
            _render_level_up_card, member.display_name, avatar_img,
            level, level + 1, title, badge, xp, needed
        )
        file = discord.File(buf, filename="levelup_test.png")
        await ctx.send(f"🎉 **Туршилтын Level-Up карт** (Lv.{level} → Lv.{level+1})", file=file)

    @leveling_group.command(name="settings", description="Админ тохиргооны самбар")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_settings(self, ctx):
        cfg = await get_config(self.bot.db, ctx.guild.id)
        embed = discord.Embed(title="🛠️ Leveling тохиргоо (админ)", color=INFO_COLOR)
        embed.add_field(name="Идэвхтэй", value="✅" if cfg["enabled"] else "❌", inline=True)
        embed.add_field(name="Мэдэгдлийн суваг", value=f"<#{cfg['announce_channel']}>" if cfg["announce_channel"] else "Тохируулаагүй", inline=True)
        embed.add_field(name="Дуут XP", value="✅" if cfg["voice_xp_enabled"] else "❌", inline=True)
        embed.add_field(name="Прогресс төрөл", value=cfg["prog_type"], inline=True)
        embed.add_field(name="Үндсэн/Алхам", value=f"{cfg['prog_base']}/{cfg['prog_step']}", inline=True)
        embed.add_field(name="Tiers", value=json.dumps(cfg["xp_tiers"]), inline=False)
        embed.add_field(name="Msg/Rct CD", value=f"{cfg['msg_cooldown']}с/{cfg['react_cooldown']}с", inline=True)
        view = SettingsView(self.bot, ctx, cfg)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
