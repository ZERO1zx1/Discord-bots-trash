import io, os
from PIL import Image, ImageDraw, ImageFont

def draw_rating_card(username: str, data: dict) -> io.BytesIO:
    W, H = 600, 520
    bg_path = os.path.join(os.path.dirname(__file__), "cards", "background.png")
    base = Image.open(bg_path).convert("RGBA").resize((W, H)) if os.path.exists(bg_path) else Image.new("RGBA", (W, H), (30, 30, 30, 255))
    draw = ImageDraw.Draw(base)

    font_path = os.path.join(os.path.dirname(__file__), "utils", "fonts", "Inter-Bold.ttf")
    try:
        font_title = ImageFont.truetype(font_path, 36) if os.path.exists(font_path) else ImageFont.load_default()
        font_score = ImageFont.truetype(font_path, 28) if os.path.exists(font_path) else ImageFont.load_default()
        font_body = ImageFont.truetype(font_path, 18) if os.path.exists(font_path) else ImageFont.load_default()
        font_small = ImageFont.truetype(font_path, 14) if os.path.exists(font_path) else ImageFont.load_default()
    except:
        font_title = font_score = font_body = font_small = ImageFont.load_default()

    draw.text((W//2, 30), username, fill=(255,255,255), font=font_title, anchor="mt")
    draw.text((W//2, 80), f"{data['overall']:.1f} / 10", fill=(255,215,0), font=font_score, anchor="mt")

    bars = [
        ("Эрүүний хэлбэр", data["jawline"]),
        ("Нүд", data["eyes"]),
        ("Шанааны хэлбэр", data["cheekbones"]),
        ("Тэгш хэм", data["symmetry"]),
        ("Арьс", data["skin"]),
    ]
    y = 130
    for label, value in bars:
        draw.text((100, y), label, fill=(255,255,255), font=font_body)
        bar_x, bar_w, bar_h = 280, 220, 20
        draw.rectangle((bar_x, y, bar_x+bar_w, y+bar_h), outline=(255,255,255), width=1)
        fill_w = int(bar_w * (value/10))
        draw.rectangle((bar_x, y, bar_x+fill_w, y+bar_h), fill=(255,215,0))
        draw.text((bar_x+bar_w+10, y), f"{value:.1f}", fill=(255,255,255), font=font_body)
        y += 40

    draw.text((50, y+20), "AI дүгнэлт", fill=(255,255,255), font=font_title)
    import textwrap
    summary = data.get("summary", "")
    summary_lines = textwrap.wrap(summary, width=60)
    for line in summary_lines[:3]:
        draw.text((50, y+60), line, fill=(200,200,200), font=font_body)
        y += 25

    advice = data.get("advice", "")
    if advice:
        y += 15
        draw.text((50, y+60), "💡 Хөгжүүлэх зөвлөгөө", fill=(255,215,0), font=font_body)
        advice_lines = textwrap.wrap(advice, width=70)
        for line in advice_lines[:4]:
            y += 22
            draw.text((50, y+60), line, fill=(200,200,200), font=font_small)

    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return buf