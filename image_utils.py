# image_utils.py
# Versión mejorada con estilo basado en la referencia suministrada (fondo cálido, bokeh, producto grande a la derecha,
# sombra a partir de alpha, caja de texto inferior).
#
# Requisitos opcionales:
# - rembg (para eliminar fondo automáticamente)
# - esrgan_wrapper.py (opcional) si activas ENABLE_ESRGAN=1 y tienes los pesos instalados
# - fonts/Poppins-Regular.ttf y fonts/Poppins-Bold.ttf en fonts/
#
# Uso: crear_imagen_producto(prod) — prod debe contener 'imagen_url', 'nombre', 'precio', 'categoria', 'descripcion'
# Opcional: prod['packaging_url'] para la caja/packaging.

import os
import io
import math
import random
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Intentar importar rembg y esrgan wrapper si están instalados.
try:
    from rembg import remove as rembg_remove
    _HAS_REMBG = True
except Exception:
    _HAS_REMBG = False

# Intentar importar wrapper ESRGAN si existe (esrgan_wrapper.py)
try:
    import esrgan_wrapper
    _HAS_ESRGAN = True
except Exception:
    _HAS_ESRGAN = False

def load_font(path_candidates, size):
    for p in path_candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def create_warm_bokeh_background(size, inner_color=(50,30,20), outer_color=(20,10,8), bokeh_count=30):
    """Crea un fondo cálido con degradado radial y bokeh procedimental."""
    w, h = size
    # Gradiente radial
    base = Image.new("RGB", size, outer_color)
    overlay = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    radius = math.hypot(w, h) / 1.2
    center = (int(w*0.55), int(h*0.35))
    step = max(4, int(radius/120))
    for i in range(int(radius), 0, -step):
        f = i / radius
        r = int(inner_color[0] * (1 - f) + outer_color[0] * f)
        g = int(inner_color[1] * (1 - f) + outer_color[1] * f)
        b = int(inner_color[2] * (1 - f) + outer_color[2] * f)
        a = int(180 * (1 - f))
        draw.ellipse((center[0]-i, center[1]-i, center[0]+i, center[1]+i), fill=(r,g,b,a))
    bg = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    # Añadir bokeh: círculos brillantes desenfocados
    bokeh_layer = Image.new("RGBA", size, (0,0,0,0))
    bdraw = ImageDraw.Draw(bokeh_layer)
    for i in range(bokeh_count):
        bx = random.randint(0, w)
        by = random.randint(0, h)
        br = random.randint(int(w*0.02), int(w*0.10))
        color = (
            random.randint(200,255),
            random.randint(160,230),
            random.randint(120,200),
            random.randint(120,200)
        )
        bdraw.ellipse((bx-br, by-br, bx+br, by+br), fill=color)
    bokeh_layer = bokeh_layer.filter(ImageFilter.GaussianBlur(radius=40))
    bg = Image.alpha_composite(bg.convert("RGBA"), bokeh_layer).convert("RGB")
    # ligera textura de grano (ruido)
    noise = Image.effect_noise(size, 12)
    noise = ImageOps.colorize(noise.convert("L"), (10,6,4), (30,20,18)).filter(ImageFilter.GaussianBlur(1))
    bg = Image.blend(bg, noise, 0.05)
    return bg

def add_shadow_from_alpha(fg_rgba, offset=(20,30), blur_radius=36, shadow_color=(0,0,0,150)):
    """Genera una sombra a partir del alpha channel de fg_rgba."""
    alpha = fg_rgba.split()[-1]
    # Crear sombra base del tamaño del fg
    shadow = Image.new("RGBA", fg_rgba.size, (0,0,0,0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.bitmap((0,0), alpha, fill=shadow_color)
    # Desplazar y difuminar la sombra
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    # Expandir canvas para offset
    total_w = fg_rgba.width + abs(offset[0]) + 80
    total_h = fg_rgba.height + abs(offset[1]) + 80
    back = Image.new("RGBA", (total_w, total_h), (0,0,0,0))
    shadow_left = 40 + max(offset[0], 0)
    shadow_top = 40 + max(offset[1], 0)
    back.paste(shadow, (shadow_left, shadow_top), shadow)
    # Pegar fg en su posición correcta
    fg_left = 40 + max(-offset[0], 0)
    fg_top = 40 + max(-offset[1], 0)
    back.paste(fg_rgba, (fg_left, fg_top), fg_rgba)
    return back

def download_image_bytes(url, timeout=15):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
    except Exception as e:
        logger.warning("Error descargando imagen %s : %s", url, e)
        return None

def remove_background_if_possible(image_bytes):
    if not _HAS_REMBG:
        return None
    try:
        out_bytes = rembg_remove(image_bytes)
        return out_bytes
    except Exception as e:
        logger.warning("rembg fallo: %s", e)
        return None

def prepare_product_image_from_url(url, target_box, use_rembg=True, esrgan_fallback=True):
    """Descarga, opcionalmente elimina el fondo y escala la imagen del producto para caber en target_box.
    target_box = (max_w, max_h)
    Retorna PIL.Image RGBA o None."""
    content = download_image_bytes(url)
    if not content:
        return None
    # Opcional: intentar remover fondo
    img = None
    if use_rembg and _HAS_REMBG:
        try:
            bg_removed = remove_background_if_possible(content)
            if bg_removed:
                img = Image.open(io.BytesIO(bg_removed)).convert("RGBA")
        except Exception:
            img = None
    if img is None:
        try:
            img = Image.open(io.BytesIO(content)).convert("RGBA")
        except Exception:
            return None

    # Upscale opcional con ESRGAN si está activado y disponible
    if _HAS_ESRGAN and os.getenv("ENABLE_ESRGAN", "0") == "1":
        try:
            img = esrgan_wrapper.upscale_with_esrgan_if_available(img)
            img = img.convert("RGBA")
        except Exception:
            pass

    # Ajustar tamaño manteniendo aspect ratio
    max_w, max_h = target_box
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)
    new_w = int(w * scale)
    new_h = int(h * scale)
    if scale < 1.0:
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    else:
        # si es pequeña, queremos ocupar más espacio: escalar hasta target (pero no forzar demasiado)
        scale_up = min(max_w / w, max_h / h, 2.5)  # evitar upscales exagerados
        if scale_up > 1.0:
            img = img.resize((int(w*scale_up), int(h*scale_up)), Image.Resampling.LANCZOS)
    return img

def color_grade_warm(pil_img):
    """Aplicar un pequeño grading cálido para asemejar el estilo de la referencia."""
    # ajustar contraste y color
    enh = ImageEnhance.Color(pil_img)
    pil_img = enh.enhance(1.05)
    enh = ImageEnhance.Contrast(pil_img)
    pil_img = enh.enhance(1.06)
    # overlay cálido
    overlay = Image.new("RGB", pil_img.size, (40, 18, 10))
    return Image.blend(pil_img, overlay, 0.06)

def crear_imagen_producto(prod):
    """Nueva versión que crea una composición inspirada en la referencia:
    - Producto dominante a la derecha
    - (Opcional) packaging_url detrás a la izquierda si está presente
    - Fondo cálido con bokeh procedimental
    - Sombra realista generada desde alpha
    - Zona inferior semitransparente para nombre/descripcion/precio"""
    # Tamaño final (Instagram feed)
    W, H = 1080, 1080

    # Render a 2x para mayor nitidez y luego downscale
    SCALE = 2
    RW, RH = W*SCALE, H*SCALE

    # Fondo cálido con bokeh
    bg = create_warm_bokeh_background((RW, RH),
                                     inner_color=(110, 70, 50),
                                     outer_color=(28, 14, 8),
                                     bokeh_count=45)

    canvas = bg.convert("RGBA")

    # Cargar fuentes (Poppins recomendada)
    fonts_bold = [
        "fonts/Poppins-Bold.ttf",
        "/usr/share/fonts/truetype/custom/Poppins-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    fonts_regular = [
        "fonts/Poppins-Regular.ttf",
        "/usr/share/fonts/truetype/custom/Poppins-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    font_title = load_font(fonts_bold, 56*SCALE)
    font_sub = load_font(fonts_regular, 36*SCALE)
    font_price_big = load_font(fonts_bold, 100*SCALE)
    font_cta = load_font(fonts_bold, 44*SCALE)

    # Preparar caja de producto si hay packaging_url
    packaging_img = None
    if prod.get("packaging_url"):
        pkg = prepare_product_image_from_url(prod["packaging_url"], target_box=(int(RW*0.36), int(RH*0.6)))
        if pkg:
            # colocar packaging detrás en la izquierda (detrás del producto)
            pkg_w, pkg_h = pkg.size
            pkg_x = int(RW*0.08)
            pkg_y = int(RH*0.25)
            # aplicar ligera sombra y desenfoque al packaging para profundidad
            pkg_bg = pkg.filter(ImageFilter.GaussianBlur(radius=6)).convert("RGBA")
            canvas.paste(pkg_bg, (pkg_x, pkg_y), pkg_bg)
            canvas.paste(pkg, (pkg_x, pkg_y), pkg)

    # Preparar imagen principal del producto
    prod_img = prepare_product_image_from_url(prod.get("imagen_url",""), target_box=(int(RW*0.55), int(RH*0.75)))
    if prod_img is None:
        # fallback: un placeholder simple (círculo)
        prod_img = Image.new("RGBA", (int(RW*0.4), int(RH*0.5)), (220,220,220,255))
        d = ImageDraw.Draw(prod_img)
        d.ellipse([(0,0),(prod_img.width, prod_img.height)], fill=(190,190,190))
    # Generar sombra desde alpha
    prod_with_shadow = add_shadow_from_alpha(prod_img, offset=(int(22*SCALE), int(28*SCALE)), blur_radius=40, shadow_color=(0,0,0,160))

    # Pegar producto (derecha)
    px = int(RW*0.58)
    py = int(RH*0.18)
    # Ajustar si la imagen con sombra es más grande que el canvas
    if prod_with_shadow.width + px > RW:
        px = RW - prod_with_shadow.width - int(40*SCALE)
    canvas.paste(prod_with_shadow, (px, py), prod_with_shadow)

    # Añadir pequeñas fibras/pelusas procedurales en primer plano (opcional, para la estética de referencia)
    foreground = Image.new("RGBA", (RW, RH), (0,0,0,0))
    fdraw = ImageDraw.Draw(foreground)
    # dibujar unas "bolitas" de lana como brush suave
    for i in range(6):
        fx = int(RW*(0.18 + i*0.06))
        fy = int(RH*(0.78 + (i%2)*0.02))
        fr = random.randint(int(RW*0.03), int(RW*0.05))
        fdraw.ellipse((fx-fr, fy-fr, fx+fr, fy+fr), fill=(220,220,210,200))
    foreground = foreground.filter(ImageFilter.GaussianBlur(radius=8))
    canvas = Image.alpha_composite(canvas, foreground)

    # Zona inferior semitransparente para texto
    info_h = int(RH*0.32)
    info_box = Image.new("RGBA", (RW, info_h), (10,10,10,210))
    # agregar un degradado en la parte superior de la caja para suavizar la transición
    grad = Image.new("L", (1, info_h))
    for y in range(info_h):
        grad.putpixel((0,y), int(255 * (y / info_h)))
    alpha_grad = grad.resize((RW, info_h))
    black = Image.new("RGBA", (RW, info_h), (6,6,6,200))
    info_box.putalpha(alpha_grad)
    # aplicar info_box al canvas abajo
    canvas.paste(info_box, (0, RH - info_h), info_box)

    draw = ImageDraw.Draw(canvas)

    # Escribir título grande (centrado en parte superior)
    title = prod.get("nombre", "").upper()
    # limitar texto a 2 líneas de tamaño responsivo
    max_chars = 30
    lines = []
    if len(title) > max_chars:
        words = title.split()
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
        lines = [title]

    title_y = RH - info_h + int(28*SCALE)
    for i, ln in enumerate(lines[:2]):
        draw.text((int(RW*0.08), title_y + i*(48*SCALE)), ln, font=font_title, fill=(255,240,225))

    # Precio grande a la derecha dentro de la zona inferior (alineado con la parte baja)
    price_text = f"₡{prod.get('precio',0):,}"
    price_x = int(RW*0.87)
    price_y = RH - int(info_h*0.55)
    draw.text((price_x, price_y), price_text, font=font_price_big, fill=(255,210,140), anchor="rm")

    # Pequeña descripción debajo del título
    desc = prod.get("descripcion","")
    if desc:
        desc_lines = []
        max_chars_desc = 60
        if len(desc) > max_chars_desc:
            words = desc.split()
            line = ""
            for w in words:
                if len(line + " " + w) <= max_chars_desc:
                    line = (line + " " + w).strip()
                else:
                    desc_lines.append(line)
                    line = w
            if line:
                desc_lines.append(line)
        else:
            desc_lines = [desc]
        for i, ln in enumerate(desc_lines[:2]):
            draw.text((int(RW*0.08), title_y + int(120*SCALE) + i*(36*SCALE)), ln, font=font_sub, fill=(230,230,230))

    # CTA pequeño centrado abajo
    cta = "¡COMPRA AHORA!"
    draw.text((RW//2, RH - int(36*SCALE)), cta, font=font_cta, fill=(255,120,100), anchor="mm")

    # Correcciones finales: color grade cálido y unsharp
    final = canvas.convert("RGB")
    final = color_grade_warm(final)
    try:
        final = final.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=3))
    except Exception:
        pass

    # Downscale a W x H si render 2x
    final = final.resize((W, H), Image.Resampling.LANCZOS)
    return final
