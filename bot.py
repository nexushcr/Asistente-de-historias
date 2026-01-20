import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from PIL import Image, ImageDraw, ImageFont
import io
from playwright.async_api import async_playwright
import re

# Configuración
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
WEBSITE_URL = "https://nexushcr.com"

# Cache de productos
productos_cache = {}
ultima_actualizacion = None

async def scrape_productos():
    """Extrae productos del sitio web usando Playwright"""
    global productos_cache, ultima_actualizacion
    
    print("🔍 Iniciando scraping de productos...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navega al sitio
            await page.goto(WEBSITE_URL, wait_until="networkidle", timeout=30000)
            
            # Espera a que se carguen los productos (ajusta el selector según tu sitio)
            await page.wait_for_timeout(3000)
            
            # Extrae los productos (ajustaremos los selectores según tu estructura)
            productos = await page.evaluate("""
                () => {
                    const items = [];
                    
                    // Intenta diferentes selectores comunes
                    const productCards = document.querySelectorAll(
                        '.product, .producto, [class*="product"], [class*="card"], .item'
                    );
                    
                    productCards.forEach((card, index) => {
                        // Busca nombre
                        const nombre = card.querySelector('h1, h2, h3, h4, .title, .name, [class*="title"], [class*="name"]')?.textContent?.trim();
                        
                        // Busca precios
                        const precios = Array.from(card.querySelectorAll('[class*="price"], [class*="precio"], .price, .precio'));
                        const precioTextos = precios.map(p => p.textContent.trim());
                        
                        // Busca imagen
                        const img = card.querySelector('img');
                        const imagen = img?.src || img?.dataset?.src;
                        
                        // Busca descripción
                        const desc = card.querySelector('p, .description, [class*="desc"]')?.textContent?.trim();
                        
                        if (nombre) {
                            items.push({
                                id: index + 1,
                                nombre: nombre,
                                precios: precioTextos,
                                imagen: imagen,
                                descripcion: desc || ''
                            });
                        }
                    });
                    
                    return items;
                }
            """)
            
            await browser.close()
            
            # Procesar productos extraídos
            productos_procesados = {}
            for idx, prod in enumerate(productos[:10]):  # Limita a 10 productos
                # Intenta detectar precio antes/ahora
                precios = prod.get('precios', [])
                precio_antes = ""
                precio_ahora = ""
                descuento = ""
                
                if len(precios) >= 2:
                    precio_antes = precios[0]
                    precio_ahora = precios[1]
                elif len(precios) == 1:
                    precio_ahora = precios[0]
                
                # Calcula descuento si hay dos precios
                if precio_antes and precio_ahora:
                    try:
                        # Extrae números de los precios
                        num_antes = float(re.sub(r'[^\d.]', '', precio_antes))
                        num_ahora = float(re.sub(r'[^\d.]', '', precio_ahora))
                        if num_antes > num_ahora:
                            desc_pct = int(((num_antes - num_ahora) / num_antes) * 100)
                            descuento = f"{desc_pct}% OFF"
                    except:
                        descuento = "OFERTA"
                else:
                    descuento = "NUEVO"
                
                productos_procesados[str(idx + 1)] = {
                    "nombre": prod['nombre'][:50],  # Limita longitud
                    "precio_antes": precio_antes or precio_ahora,
                    "precio_ahora": precio_ahora,
                    "descuento": descuento,
                    "descripcion": prod.get('descripcion', '¡Disponible ahora!')[:100],
                    "imagen_url": prod.get('imagen', '')
                }
            
            productos_cache = productos_procesados
            ultima_actualizacion = datetime.now()
            
            print(f"✅ Se encontraron {len(productos_procesados)} productos")
            return productos_procesados
            
    except Exception as e:
        print(f"❌ Error en scraping: {e}")
        # Productos de ejemplo si falla el scraping
        return {
            "1": {
                "nombre": "Producto de ejemplo",
                "precio_antes": "$100",
                "precio_ahora": "$79",
                "descuento": "21% OFF",
                "descripcion": "Actualiza el scraper con los selectores correctos",
                "imagen_url": ""
            }
        }

def crear_historia_promocion(producto_data, template="moderno"):
    """Crea una imagen de historia de Instagram con la promoción"""
    
    width, height = 1080, 1920
    
    if template == "moderno":
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        for i in range(height):
            r = int(26 + (47 - 26) * i / height)
            g = int(26 + (69 - 26) * i / height)
            b = int(46 + (94 - 46) * i / height)
            draw.rectangle([(0, i), (width, i+1)], fill=(r, g, b))
    
    elif template == "minimalista":
        img = Image.new('RGB', (width, height), color='#ffffff')
        draw = ImageDraw.Draw(img)
    
    else:
        img = Image.new('RGB', (width, height), color='#ff6b6b')
        draw = ImageDraw.Draw(img)
    
    try:
        font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
        font_precio_grande = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 110)
        font_precio_antes = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 55)
        font_descuento = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 65)
        font_desc = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45)
    except:
        font_titulo = ImageFont.load_default()
        font_precio_grande = ImageFont.load_default()
        font_precio_antes = ImageFont.load_default()
        font_descuento = ImageFont.load_default()
        font_desc = ImageFont.load_default()
    
    if template == "minimalista":
        color_texto = "#000000"
        color_descuento = "#ff4757"
        color_precio_antes = "#95a5a6"
    else:
        color_texto = "#ffffff"
        color_descuento = "#ffd93d"
        color_precio_antes = "#bdc3c7"
    
    y_pos = 400
    
    # Nombre del producto (divide en líneas si es muy largo)
    nombre = producto_data["nombre"]
    palabras = nombre.split()
    lineas = []
    linea_actual = ""
    
    for palabra in palabras:
        test_linea = f"{linea_actual} {palabra}".strip()
        bbox = draw.textbbox((0, 0), test_linea, font=font_titulo)
        if bbox[2] - bbox[0] > 900:
            lineas.append(linea_actual)
            linea_actual = palabra
        else:
            linea_actual = test_linea
    lineas.append(linea_actual)
    
    for linea in lineas[:2]:  # Max 2 líneas
        bbox = draw.textbbox((0, 0), linea, font=font_titulo)
        text_width = bbox[2] - bbox[0]
        x_pos = (width - text_width) // 2
        draw.text((x_pos, y_pos), linea, fill=color_texto, font=font_titulo)
        y_pos += 90
    
    y_pos += 60
    
    # Precio anterior (si existe)
    if producto_data["precio_antes"] and producto_data["precio_antes"] != producto_data["precio_ahora"]:
        precio_antes = producto_data["precio_antes"]
        bbox = draw.textbbox((0, 0), precio_antes, font=font_precio_antes)
        text_width = bbox[2] - bbox[0]
        x_pos = (width - text_width) // 2
        draw.text((x_pos, y_pos), precio_antes, fill=color_precio_antes, font=font_precio_antes)
        draw.line([(x_pos, y_pos + 30), (x_pos + text_width, y_pos + 30)], 
                  fill=color_precio_antes, width=4)
        y_pos += 120
    
    # Precio actual
    precio_ahora = producto_data["precio_ahora"]
    bbox = draw.textbbox((0, 0), precio_ahora, font=font_precio_grande)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) // 2
    draw.text((x_pos, y_pos), precio_ahora, fill=color_descuento, font=font_precio_grande)
    
    y_pos += 180
    
    # Badge de descuento
    descuento = producto_data["descuento"]
    bbox = draw.textbbox((0, 0), descuento, font=font_descuento)
    text_width = bbox[2] - bbox[0]
    badge_x = (width - text_width - 80) // 2
    badge_y = y_pos - 20
    
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + text_width + 80, badge_y + 100)],
        radius=20,
        fill=color_descuento
    )
    draw.text((badge_x + 40, badge_y + 15), descuento, 
              fill="#000000" if template == "minimalista" else "#1a1a2e", 
              font=font_descuento)
    
    y_pos += 200
    
    # Descripción
    descripcion = producto_data["descripcion"][:80]
    bbox = draw.textbbox((0, 0), descripcion, font=font_desc)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) // 2
    draw.text((x_pos, y_pos), descripcion, fill=color_texto, font=font_desc)
    
    # Logo/marca
    y_pos = 1650
    marca = "NEXUS CR"
    bbox = draw.textbbox((0, 0), marca, font=font_titulo)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) // 2
    draw.text((x_pos, y_pos), marca, fill=color_texto, font=font_titulo)
    
    # Call to action
    y_pos = 1750
    cta = "¡DESLIZA PARA COMPRAR!"
    bbox = draw.textbbox((0, 0), cta, font=font_desc)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) // 2
    draw.text((x_pos, y_pos), cta, fill=color_texto, font=font_desc)
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar Productos", callback_data='actualizar')],
        [InlineKeyboardButton("📦 Ver Productos", callback_data='ver_productos')],
        [InlineKeyboardButton("🎨 Crear Historia", callback_data='crear_historia')],
        [InlineKeyboardButton("⚙️ Auto-envío", callback_data='config_auto')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensaje = '¡Hola! 👋\n\n'
    mensaje += 'Soy tu asistente para crear historias de Instagram.\n\n'
    if ultima_actualizacion:
        mensaje += f'📅 Última actualización: {ultima_actualizacion.strftime("%H:%M:%S")}\n'
    mensaje += f'🛍️ Productos cargados: {len(productos_cache)}\n\n'
    mensaje += '¿Qué quieres hacer?'
    
    await update.message.reply_text(mensaje, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los botones"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'actualizar':
        await query.edit_message_text('🔄 Actualizando productos desde nexushcr.com...\nEsto puede tardar unos segundos.')
        
        productos = await scrape_productos()
        
        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data='volver')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f'✅ Productos actualizados!\n\n'
            f'Se encontraron {len(productos)} productos en tu sitio.\n'
            f'Hora: {datetime.now().strftime("%H:%M:%S")}',
            reply_markup=reply_markup
        )
    
    elif query.data == 'ver_productos':
        if not productos_cache:
            await query.edit_message_text('⏳ Cargando productos por primera vez...')
            await scrape_productos()
        
        texto = "📦 Productos disponibles:\n\n"
        for id, prod in list(productos_cache.items())[:5]:
            texto += f"{id}. {prod['nombre']}\n"
            texto += f"   💰 {prod['precio_ahora']}\n"
            if prod['descuento']:
                texto += f"   🏷️ {prod['descuento']}\n"
            texto += "\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data='actualizar')],
            [InlineKeyboardButton("🔙 Volver", callback_data='volver')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(texto, reply_markup=reply_markup)
    
    elif query.data == 'crear_historia':
        if not productos_cache:
            await query.edit_message_text('⏳ Cargando productos...')
            await scrape_productos()
        
        keyboard = []
        for id, prod in list(productos_cache.items())[:5]:
            texto_boton = f"{prod['nombre'][:30]}"
            if prod['descuento']:
                texto_boton += f" - {prod['descuento']}"
            keyboard.append([InlineKeyboardButton(texto_boton, callback_data=f'generar_{id}')])
        
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data='volver')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            '🎨 Selecciona el producto para crear la historia:',
            reply_markup=reply_markup
        )
    
    elif query.data.startswith('generar_'):
        producto_id = query.data.split('_')[1]
        await query.edit_message_text('⏳ Generando historias...')
        
        if producto_id not in productos_cache:
            await query.edit_message_text('❌ Producto no encontrado. Actualiza los productos.')
            return
        
        templates = ["moderno", "minimalista", "vibrante"]
        
        for template in templates:
            img_bytes = crear_historia_promocion(productos_cache[producto_id], template)
            
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=img_bytes,
                caption=f"✨ Template: {template.upper()}\n"
                        f"📱 Lista para Instagram Stories"
            )
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ ¡Listo! Descarga la que más te guste y publícala."
        )
    
    elif query.data == 'config_auto':
        await query.edit_message_text(
            '⚙️ Configuración de auto-envío:\n\n'
            'Comandos disponibles:\n'
            '/auto_on - Activar (9 AM diario)\n'
            '/auto_off - Desactivar\n\n'
            'El bot enviará automáticamente una historia\n'
            'con un producto aleatorio cada día.'
        )
    
    elif query.data == 'volver':
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar Productos", callback_data='actualizar')],
            [InlineKeyboardButton("📦 Ver Productos", callback_data='ver_productos')],
            [InlineKeyboardButton("🎨 Crear Historia", callback_data='crear_historia')],
            [InlineKeyboardButton("⚙️ Auto-envío", callback_data='config_auto')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('¿Qué quieres hacer?', reply_markup=reply_markup)

async def envio_automatico(context: ContextTypes.DEFAULT_TYPE):
    """Envío automático diario"""
    if not productos_cache:
        await scrape_productos()
    
    if productos_cache:
        producto_id = list(productos_cache.keys())[0]
        img_bytes = crear_historia_promocion(productos_cache[producto_id], "moderno")
        
        await context.bot.send_photo(
            chat_id=CHAT_ID,
            photo=img_bytes,
            caption=f"🌅 ¡Buenos días!\n\n"
                    f"Historia del día: {productos_cache[producto_id]['nombre']}\n\n"
                    f"📱 Lista para publicar"
        )

async def auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa envío automático"""
    context.job_queue.run_daily(
        envio_automatico,
        time=datetime.strptime("09:00", "%H:%M").time(),
        chat_id=update.effective_chat.id,
        name=str(update.effective_chat.id)
    )
    
    await update.message.reply_text(
        '✅ Envío automático activado!\n\n'
        'Recibirás una historia diaria a las 9:00 AM'
    )

async def auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desactiva envío automático"""
    jobs = context.job_queue.get_jobs_by_name(str(update.effective_chat.id))
    for job in jobs:
        job.schedule_removal()
    
    await update.message.reply_text('❌ Envío automático desactivado')

async def iniciar_scraping_inicial():
    """Scraping inicial al arrancar el bot"""
    await asyncio.sleep(5)  # Espera 5 segundos después de iniciar
    await scrape_productos()

def main():
    """Función principal"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Scraping inicial
    asyncio.create_task(iniciar_scraping_inicial())
    
    print("🤖 Bot iniciado con scraping web...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()