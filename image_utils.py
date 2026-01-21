# image_utils.py
# Helpers and improved crear_imagen_producto to generate more professional Instagram images.

import math
import io
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import logging

logger = logging.getLogger(__name__)

def load_font(path_candidates, size):
    """
    Try to load the first available font from path_candidates.
    Returns an ImageFont (or default font if all fail).
    """
    for p in path_candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def create_radial_gradient(size, inner_color, outer_color, center=None, radius=None):
    """Create a soft radial background in RGB mode."""
    w, h = size
    if center is None:
        center = (w // 2, int(h * 0.35))
    if radius is None:
        radius = math.hypot(w, h) / 1.2
    base = Image.new("RGB", size, outer_color)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    step = max(4, int(radius / 120))
    for i in range(int(radius), 0, -step):
        f = i / radius
        r = int(inner_color[0] * (1 - f) + outer_color[0] * f)
        g = int(inner_color[1] * (1 - f) + outer_color[1] * f)
        b = int(inner_color[2] * (1 - f) + outer_color[2] * f)
        a = int(200 * (1 - f))
        draw.ellipse(
            [center[0] - i, center[1] - i, center[0] + i, center[1] + i],
            fill=(r, g, b, a),
        )
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

def add_drop_shadow(im, offset=(15, 15), background_color=(255, 255, 255), shadow_color=(0, 0, 0, 160), border=30, iterations=6):
    """
    Return a new image with a soft projected shadow.
    im: PIL.Image (RGBA preferred).
    """
    total_w = im.width + abs(offset[0]) + 2 * border
    total_h = im.height + abs(offset[1]) + 2 * border
    back = Image.new("RGBA", (total_w, total_h), background_color + (255,))
    shadow = Image.new("RGBA", im.size, shadow_color)
    shadow_left = border + max(offset[0], 0)
    shadow_top = border + max(offset[1], 0)
    back.paste(shadow, (shadow_left, shadow_top), shadow)
    for i in range(iterations):
        back = back.filter(ImageFilter.GaussianBlur(radius=4))
    img_left = border + max(-offset[0], 0)
    img_top = border + max(-offset[1], 0)
    back.paste(im, (img_left, img_top), im)
    return back

def crear_imagen_producto(prod):
    """
    Generate a more professional Instagram-style image.
    Renders at 2x and downsamples for improved sharpness.
    Returns a PIL.Image sized 1080x1080 RGB.
    """
    SCALE = 2
    W, H = 1080, 1080
    RW, RH = W * SCALE, H * SCALE

    colores_fondo = [
        ((255, 93, 177), (155, 81, 224)),
        ((67, 233, 123), (56, 249, 215)),
        ((251, 200, 212), (151, 149, 240)),
        ((255, 159, 64), (255, 99, 132)),
        ((54, 209, 220), (91, 134, 229)),
    ]
    color_idx = hash(prod.get('categoria', '')) % len(colores_fondo)
    inner_c, outer_c = colores_fondo[color_idx]

    canvas = create_radial_gradient((RW, RH), inner_color=inner_c, outer_color=outer_c)
    draw = ImageDraw.Draw(canvas)

    fonts_bold = [
        "fonts/Poppins-Bold.ttf",
        "fonts/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "arialbd.ttf",
    ]
    fonts_regular = [
        "fonts/Poppins-Regular.ttf",
        "fonts/Montserrat-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arial.ttf",
    ]

    font_logo = load_font(fonts_bold, 72 * SCALE)
    font_nombre = load_font(fonts_bold, 46 * SCALE)
    font_precio_grande = load_font(fonts_bold, 120 * SCALE)
    font_precio_label = load_font(fonts_regular, 40 * SCALE)
    font_cta = load_font(fonts_bold, 46 * SCALE)

    card_w = int(RW * 0.72)
    card_h = int(RH * 0.4)
    card_x = (RW - card_w) // 2
    card_y = int(RH * 0.18)
    corner = int(30 * SCALE)

    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    mask = Image.new("L", (card_w, card_h), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=corner, fill=255)
    card.putalpha(mask)

    producto_img = None
    try:
        resp = requests.get(prod.get("imagen_url", ""), timeout=15)
        if resp.status_code == 200 and resp.content:
            producto_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            max_h = int(card_h * 0.85)
            max_w = int(card_w * 0.85)
            producto_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            tmp_card = Image.new("RGBA", card.size, (255, 255, 255, 0))
            tmp_card.paste(producto_img, ((card_w - producto_img.width) // 2, (card_h - producto_img.height) // 2), producto_img)
            card = tmp_card
    except Exception as e:
        logger.exception("Error cargando imagen producto: %s", e)
        producto_img = None

    card_with_shadow = add_drop_shadow(card, offset=(20 * SCALE, 26 * SCALE), border=28 * SCALE)
    cx = (RW - card_with_shadow.width) // 2
    cy = card_y - int(12 * SCALE)
    canvas.paste(card_with_shadow, (cx, cy), card_with_shadow)

    draw = ImageDraw.Draw(canvas)

    draw.text((RW // 2, int(60 * SCALE)), "NEXUS HCR", font=font_logo, fill=(255, 255, 255), anchor="mm",
              stroke_width=int(2 * SCALE), stroke_fill=(0, 0, 0))

    nombre = prod.get("nombre", "")
    max_chars = 28
    lines = []
    if len(nombre) > max_chars:
        words = nombre.split()
        line = ""
        for w in words:
            if len(line + " " + w) <= max_chars:
                line = (line + " " + w).strip()
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
    else:
        lines = [nombre]

    text_y = cy + card_with_shadow.height + int(40 * SCALE)
    for i, ln in enumerate(lines[:2]):
        draw.text((RW // 2, text_y + i * (48 * SCALE)), ln, font=font_nombre, fill=(30, 30, 30), anchor="mm",
                  stroke_width=int(1 * SCALE), stroke_fill=(255, 255, 255))

    precio_text = f"₡{prod.get('precio', 0):,}"
    precio_y = text_y + int(140 * SCALE)
    circle_r = int(120 * SCALE)
    draw.ellipse([(RW // 2 - circle_r, precio_y - circle_r), (RW // 2 + circle_r, precio_y + circle_r)], fill=(255, 230, 0))
    draw.text((RW // 2, precio_y - int(20 * SCALE)), "SOLO", font=font_precio_label, fill=(139, 0, 0), anchor="mm")
    draw.text((RW // 2, precio_y + int(30 * SCALE)), precio_text, font=font_precio_grande, fill=(139, 0, 0), anchor="mm")

    cta_y = RH - int(110 * SCALE)
    draw.text((RW // 2, cta_y), "¡COMPRA AHORA!", font=font_cta, fill=(255, 80, 120), anchor="mm",
              stroke_width=int(2 * SCALE), stroke_fill="white")

    try:
        canvas = canvas.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
    except Exception:
        pass

    final = canvas.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

    try:
        final = ImageOps.autocontrast(final, cutoff=1)
    except Exception:
        pass

    return final
