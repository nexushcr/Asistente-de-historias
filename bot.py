import os
import asyncio
import random
import re
from datetime import datetime
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://www.nexushcr.com")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")  # Tu canal o chat ID para publicar

# Cache de productos
productos_cache = []
ultima_actualizacion = None

# -------------------------------
# Scraping de productos optimizado para nexushcr.com
# -------------------------------
async def scrape_productos():
    """Extrae productos del sitio web nexushcr.com"""
    global productos_cache, ultima_actualizacion
    
    try:
        print("🔍 Iniciando scraping de nexushcr.com...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(WEBSITE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        print(f"📄 Código HTML descargado ({len(response.text)} caracteres)")
        
        # Buscar el objeto products en el código JavaScript - Versión mejorada
        # Intentar múltiples patrones
        productos_encontrados = []
        
        # Patrón 1: const products = {...}
        patron_products_1 = r'const products\s*=\s*(\{[\s\S]*?\});'
        match = re.search(patron_products_1, response.text)
        
        if not match:
            # Patrón 2: var products = {...}
            patron_products_2 = r'var products\s*=\s*(\{[\s\S]*?\});'
            match = re.search(patron_products_2, response.text)
        
        if not match:
            # Patrón 3: let products = {...}
            patron_products_3 = r'let products\s*=\s*(\{[\s\S]*?\});'
            match = re.search(patron_products_3, response.text)
        
        if match:
            productos_js = match.group(1)
            print("✅ Encontrado objeto products en el código")
            print(f"📦 Extrayendo datos ({len(productos_js)} caracteres)...")
            
            # Extraer todos los productos usando regex mejorado
            # Patrón más flexible que acepta espacios y saltos de línea
            patron_producto = r'\{\s*id:\s*(\d+)\s*,\s*name:\s*[\'"]([^\'"]+)[\'"]\s*,\s*price:\s*(\d+)\s*,\s*image:\s*[\'"]([^\'"]+)[\'"]\s*,\s*category:\s*[\'"]([^\'"]+)[\'"]\s*,\s*description:\s*[\'"]([^\'"]*)[\'"]'
            
            matches = list(re.finditer(patron_producto, productos_js))
            print(f"🔎 Encontrados {len(matches)} productos con regex")
            
            for match_prod in matches:
                prod_id, nombre, precio, imagen, categoria, descripcion = match_prod.groups()
                
                # Construir URL completa de la imagen
                if imagen.startswith('/'):
                    imagen_url = WEBSITE_URL + imagen
                elif imagen.startswith('http'):
                    imagen_url = imagen
                else:
                    imagen_url = WEBSITE_URL + '/' + imagen
                
                productos_encontrados.append({
                    'id': int(prod_id),
                    'nombre': nombre.strip(),
                    'precio': int(precio),
                    'imagen_url': imagen_url,
                    'categoria': categoria.strip(),
                    'descripcion': descripcion.strip()
                })
            
            if productos_encontrados:
                productos_cache = productos_encontrados
                ultima_actualizacion = datetime.now()
                print(f"✅ {len(productos_cache)} productos cargados correctamente")
                
                # Mostrar resumen por categoría
                categorias = {}
                for p in productos_cache:
                    cat = p['categoria']
                    categorias[cat] = categorias.get(cat, 0) + 1
                
                print("📊 Productos por categoría:")
                for cat, count in categorias.items():
                    print(f"   • {cat}: {count}")
            else:
                print("⚠️ No se encontraron productos con el patrón regex")
                # Mostrar muestra del código para debug
                print("📝 Muestra del código JavaScript encontrado:")
                print(productos_js[:500])
        else:
            print("❌ No se encontró el objeto products en la página")
            # Buscar si existe la palabra 'products' en el código
            if 'products' in response.text:
                print("⚠️ La palabra 'products' existe pero no coincide con los patrones")
                # Mostrar contexto
                idx = response.text.find('products')
                print(f"📝 Contexto: {response.text[max(0, idx-100):idx+200]}")
            else:
                print("❌ La palabra 'products' no existe en el HTML")
            
    except Exception as e:
        print(f"❌ Error en scraping: {e}")
        import traceback
        traceback.print_exc()


# -------------------------------
# Generar imagen promocional mejorada
# -------------------------------
def crear_imagen_producto(prod):
    """Crea una imagen publicitaria atractiva para redes sociales"""
    
    # Crear canvas 1080x1080 (formato Instagram)
    canvas = Image.new("RGB", (1080, 1080), "#ffffff")
    draw = ImageDraw.Draw(canvas)
    
    # Colores de la marca (ajusta según tus colores)
    color_primario = (26, 115, 232)  # Azul
    color_acento = (52, 168, 83)     # Verde
    color_fondo = (248, 249, 250)    # Gris claro
    
    # Fondo degradado sutil
    for i in range(1080):
        intensity = int(248 - (i / 1080) * 15)
        draw.rectangle([(0, i), (1080, i+1)], fill=(intensity, intensity, 255))
    
    # Barra superior decorativa
    draw.rectangle([(0, 0), (1080, 120)], fill=color_primario)
    
    # Logo/Marca (ajusta según tu logo)
    try:
        font_logo = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 55)
    except:
        font_logo = ImageFont.load_default()
    
    draw.text((540, 60), "NEXUS HCR", font=font_logo, fill="white", anchor="mm")
    
    # Descargar y procesar imagen del producto
    try:
        response = requests.get(prod["imagen_url"], timeout=15)
        img_producto = Image.open(BytesIO(response.content)).convert("RGBA")
        
        # Redimensionar manteniendo aspecto
        img_producto.thumbnail((700, 700), Image.Resampling.LANCZOS)
        
        # Crear fondo blanco para la imagen
        bg_white = Image.new("RGBA", (750, 750), "white")
        
        # Centrar imagen del producto en el fondo blanco
        offset = ((750 - img_producto.width) // 2, (750 - img_producto.height) // 2)
        bg_white.paste(img_producto, offset, img_producto if img_producto.mode == 'RGBA' else None)
        
        # Pegar en el canvas principal
        canvas.paste(bg_white, (165, 150), bg_white)
        
    except Exception as e:
        print(f"⚠️ Error cargando imagen {prod['imagen_url']}: {e}")
        # Crear placeholder elegante
        draw.rectangle([(165, 150), (915, 900)], fill="#f0f0f0", outline="#cccccc", width=3)
        try:
            font_placeholder = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
        except:
            font_placeholder = ImageFont.load_default()
        draw.text((540, 525), "🖼️", font=font_placeholder, fill="#999999", anchor="mm")
    
    # Cargar fuentes
    try:
        font_nombre = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 38)
        font_precio = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 70)
        font_desc = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
        font_categoria = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except:
        try:
            font_nombre = ImageFont.truetype("arial.ttf", 38)
            font_precio = ImageFont.truetype("arial.ttf", 70)
            font_desc = ImageFont.truetype("arial.ttf", 26)
            font_categoria = ImageFont.truetype("arial.ttf", 28)
        except:
            font_nombre = ImageFont.load_default()
            font_precio = ImageFont.load_default()
            font_desc = ImageFont.load_default()
            font_categoria = ImageFont.load_default()
    
    # Sección inferior con información
    draw.rectangle([(0, 920), (1080, 1080)], fill="#1a1a1a")
    
    # Categoría (badge)
    categoria_text = prod['categoria'].upper()
    draw.rounded_rectangle([(40, 935), (260, 975)], radius=10, fill=color_acento)
    draw.text((150, 955), categoria_text, font=font_categoria, fill="white", anchor="mm")
    
    # Nombre del producto
    nombre = prod['nombre'][:35]
    draw.text((540, 1000), nombre, font=font_nombre, fill="white", anchor="mm")
    
    # Precio destacado
    precio_text = f"₡{prod['precio']:,}"
    
    # Fondo para el precio
    bbox = draw.textbbox((0, 0), precio_text, font=font_precio)
    precio_width = bbox[2] - bbox[0]
    draw.rounded_rectangle(
        [(540 - precio_width//2 - 30, 1025), (540 + precio_width//2 + 30, 1075)],
        radius=15,
        fill=color_acento
    )
    draw.text((540, 1050), precio_text, font=font_precio, fill="white", anchor="mm")
    
    return canvas


# -------------------------------
# Publicación automática diaria
# -------------------------------
async def publicar_producto_aleatorio(context: ContextTypes.DEFAULT_TYPE):
    """Publica un producto aleatorio en el canal configurado"""
    
    if not productos_cache:
        print("⚠️ No hay productos para publicar, intentando actualizar...")
        await scrape_productos()
        if not productos_cache:
            print("❌ No se pudieron cargar productos")
            return
    
    # Seleccionar producto aleatorio
    producto = random.choice(productos_cache)
    
    print(f"📤 Preparando publicación: {producto['nombre']}")
    
    # Generar imagen
    try:
        img = crear_imagen_producto(producto)
        bio = BytesIO()
        bio.name = f"producto_{producto['id']}.png"
        img.save(bio, "PNG", quality=95, optimize=True)
        bio.seek(0)
        
        # Crear mensaje promocional atractivo
        mensaje = f"🎯 *¡OFERTA DESTACADA!*\n\n"
        mensaje += f"📦 *{producto['nombre']}*\n\n"
        
        if producto['descripcion']:
            desc_corta = producto['descripcion'][:80] + "..." if len(producto['descripcion']) > 80 else producto['descripcion']
            mensaje += f"📝 {desc_corta}\n\n"
        
        mensaje += f"💰 Precio: *₡{producto['precio']:,}*\n"
        mensaje += f"📂 Categoría: {producto['categoria'].title()}\n\n"
        mensaje += f"🛒 Visita: {WEBSITE_URL}\n"
        mensaje += f"📞 Contáctanos para más información\n\n"
        mensaje += f"#NexusHCR #{producto['categoria']}"
        
        # Publicar
        if CHANNEL_ID:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=bio,
                caption=mensaje,
                parse_mode='Markdown'
            )
            print(f"✅ Publicado exitosamente: {producto['nombre']}")
        else:
            print("⚠️ No hay CHANNEL_ID configurado. Define la variable de entorno CHANNEL_ID")
            
    except Exception as e:
        print(f"❌ Error al publicar: {e}")
        import traceback
        traceback.print_exc()


# -------------------------------
# Comandos del bot
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    mensaje = (
        "👋 *¡Bienvenido al Bot de NexusHCR!*\n\n"
        "🤖 Soy tu asistente para ver productos y ofertas.\n\n"
        "*Comandos disponibles:*\n"
        "• /productos - Ver catálogo completo\n"
        "• /aleatorio - Producto sorpresa\n"
        "• /categorias - Ver por categoría\n"
        "• /actualizar - Actualizar catálogo\n"
        "• /estado - Estado del sistema\n\n"
        f"🌐 Sitio web: {WEBSITE_URL}"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')


async def ver_productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /productos - Muestra todos los productos"""
    
    if not productos_cache:
        await update.message.reply_text("⏳ Cargando productos por primera vez...")
        await scrape_productos()
    
    if not productos_cache:
        await update.message.reply_text("❌ No se pudieron cargar los productos. Intenta /actualizar")
        return
    
    # Limitar a 8 productos para no saturar el chat
    productos_mostrar = productos_cache[:8]
    
    await update.message.reply_text(
        f"📦 Mostrando {len(productos_mostrar)} de {len(productos_cache)} productos disponibles..."
    )
    
    for prod in productos_mostrar:
        try:
            img = crear_imagen_producto(prod)
            bio = BytesIO()
            bio.name = f"producto_{prod['id']}.png"
            img.save(bio, "PNG", quality=85)
            bio.seek(0)
            
            caption = (
                f"*{prod['nombre']}*\n"
                f"💰 ₡{prod['precio']:,}\n"
                f"📂 {prod['categoria'].title()}"
            )
            
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=bio,
                caption=caption,
                parse_mode='Markdown'
            )
            
            # Pequeña pausa para evitar flood
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Error enviando producto {prod['id']}: {e}")


async def producto_aleatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /aleatorio - Muestra un producto al azar"""
    
    if not productos_cache:
        await update.message.reply_text("⏳ Cargando productos...")
        await scrape_productos()
    
    if not productos_cache:
        await update.message.reply_text("❌ No hay productos disponibles")
        return
    
    prod = random.choice(productos_cache)
    
    try:
        img = crear_imagen_producto(prod)
        bio = BytesIO()
        bio.name = f"producto_{prod['id']}.png"
        img.save(bio, "PNG", quality=90)
        bio.seek(0)
        
        caption = (
            f"🎲 *Producto Aleatorio*\n\n"
            f"*{prod['nombre']}*\n\n"
            f"{prod['descripcion']}\n\n"
            f"💰 Precio: *₡{prod['precio']:,}*\n"
            f"📂 Categoría: {prod['categoria'].title()}"
        )
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=bio,
            caption=caption,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error al generar la imagen")


async def ver_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /categorias - Muestra productos por categoría"""
    
    if not productos_cache:
        await update.message.reply_text("⏳ Cargando productos...")
        await scrape_productos()
    
    if not productos_cache:
        await update.message.reply_text("❌ No hay productos disponibles")
        return
    
    # Agrupar por categoría
    categorias = {}
    for prod in productos_cache:
        cat = prod['categoria']
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(prod)
    
    mensaje = "*📂 Productos por Categoría*\n\n"
    
    for cat, prods in categorias.items():
        mensaje += f"*{cat.upper()}* ({len(prods)} productos)\n"
        for p in prods[:3]:  # Primeros 3 de cada categoría
            mensaje += f"  • {p['nombre']} - ₡{p['precio']:,}\n"
        if len(prods) > 3:
            mensaje += f"  ... y {len(prods) - 3} más\n"
        mensaje += "\n"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')


async def actualizar_catalogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /actualizar - Actualiza el catálogo de productos"""
    
    await update.message.reply_text("🔄 Actualizando catálogo desde nexushcr.com...")
    
    try:
        await scrape_productos()
        
        if productos_cache:
            # Agrupar por categoría para el resumen
            categorias = {}
            for p in productos_cache:
                cat = p['categoria']
                categorias[cat] = categorias.get(cat, 0) + 1
            
            resumen = "*✅ Catálogo actualizado exitosamente*\n\n"
            resumen += f"📦 Total de productos: *{len(productos_cache)}*\n\n"
            resumen += "*Por categoría:*\n"
            for cat, count in categorias.items():
                resumen += f"• {cat.title()}: {count}\n"
            
            await update.message.reply_text(resumen, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Error al actualizar catálogo. Verifica la conexión.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def estado_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /estado - Muestra el estado del bot"""
    
    tiempo_desde_actualizacion = "Nunca"
    if ultima_actualizacion:
        delta = datetime.now() - ultima_actualizacion
        minutos = int(delta.total_seconds() / 60)
        if minutos < 60:
            tiempo_desde_actualizacion = f"Hace {minutos} minutos"
        else:
            horas = minutos // 60
            tiempo_desde_actualizacion = f"Hace {horas} horas"
    
    # Categorías disponibles
    categorias_count = {}
    for p in productos_cache:
        cat = p['categoria']
        categorias_count[cat] = categorias_count.get(cat, 0) + 1
    
    mensaje = (
        "🤖 *Estado del Sistema NexusHCR*\n\n"
        f"📦 Productos cargados: *{len(productos_cache)}*\n"
        f"🕐 Última actualización: {tiempo_desde_actualizacion}\n"
        f"🌐 Sitio web: {WEBSITE_URL}\n"
        f"📢 Publicaciones automáticas: {'✅ Activas' if CHANNEL_ID else '⚠️ No configuradas'}\n\n"
    )
    
    if categorias_count:
        mensaje += "*📊 Productos por categoría:*\n"
        for cat, count in categorias_count.items():
            mensaje += f"• {cat.title()}: {count}\n"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')


# -------------------------------
# Inicialización
# -------------------------------
async def post_init(application: Application):
    """Se ejecuta después de iniciar el bot"""
    print("🚀 Iniciando Bot de NexusHCR...")
    
    # Scraping inicial con retry
    print("📥 Realizando scraping inicial...")
    await asyncio.sleep(2)
    
    intentos = 3
    for i in range(intentos):
        await scrape_productos()
        if productos_cache:
            break
        if i < intentos - 1:
            print(f"⚠️ Intento {i+1} falló, reintentando en 5 segundos...")
            await asyncio.sleep(5)
    
    if not productos_cache:
        print("❌ No se pudieron cargar productos en el inicio")
    
    # Configurar publicaciones automáticas diarias
    scheduler = AsyncIOScheduler()
    
    # Publicar todos los días a una hora aleatoria entre 9:00 y 21:00
    hora_aleatoria = random.randint(9, 21)
    minuto_aleatorio = random.randint(0, 59)
    
    scheduler.add_job(
        publicar_producto_aleatorio,
        'cron',
        hour=hora_aleatoria,
        minute=minuto_aleatorio,
        args=[application]
    )
    
    print(f"⏰ Publicación automática programada para las {hora_aleatoria:02d}:{minuto_aleatorio:02d} diariamente")
    
    if CHANNEL_ID:
        print(f"📢 Canal configurado: {CHANNEL_ID}")
    else:
        print("⚠️ CHANNEL_ID no configurado - Las publicaciones automáticas no funcionarán")
    
    scheduler.start()
    print("✅ Sistema completamente inicializado")


# -------------------------------
# Main
# -------------------------------
def main():
    """Función principal"""
    
    if not TELEGRAM_TOKEN:
        print("❌ ERROR CRÍTICO: Variable TELEGRAM_TOKEN no está configurada")
        print("   Configúrala en Railway: Settings > Variables")
        return
    
    print("=" * 50)
    print("🤖 BOT NEXUSHCR - Sistema de Publicaciones")
    print("=" * 50)
    
    # Crear aplicación
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Registrar comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("productos", ver_productos))
    app.add_handler(CommandHandler("aleatorio", producto_aleatorio))
    app.add_handler(CommandHandler("categorias", ver_categorias))
    app.add_handler(CommandHandler("actualizar", actualizar_catalogo))
    app.add_handler(CommandHandler("estado", estado_bot))
    
    # Post init
    app.post_init = post_init
    
    # Iniciar bot
    print("✅ Bot iniciado correctamente")
    print("📱 Esperando mensajes en Telegram...")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()