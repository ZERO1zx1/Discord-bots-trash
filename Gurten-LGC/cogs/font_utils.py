import os
from PIL import ImageFont

# Фонт хавтасны үнэмлэхүй зам
FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

# Зөвхөн энэ нэг файлыг ашиглах
SINGLE_FONT_FILE = "DejaVu Sans Bold.ttf"

def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """
    Төвлөрсөн фонт ачаалагч (ганц фонттой хувилбар).
    - Эхлээд `cogs/fonts/` доторх заасан файлыг ачаална.
    - Олдохгүй бол системийн нөөц фонтуудыг туршина.
    - Эцэст нь Pillow-ийн default фонтыг буцаана.
    """
    # 1. Локал ганц фонт файл
    local_path = os.path.join(FONTS_DIR, SINGLE_FONT_FILE)
    if os.path.exists(local_path):
        try:
            return ImageFont.truetype(local_path, size)
        except Exception:
            pass

    # 2. Системийн нөөц фонтууд (Windows / Linux)
    if bold:
        system_fonts = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    else:
        system_fonts = [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

    for path in system_fonts:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    # 3. Pillow-ийн анхдагч фонт
    return ImageFont.load_default()