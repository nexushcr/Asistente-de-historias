import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont
import io

# Configuración
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Se configura en Railway
CHAT_ID = os.getenv('CHAT_ID')  # Tu chat ID de Telegram

# Base de datos simple de productos (puedes expandir esto)
productos = {
    "1": {
        "nombre": "Producto Ejemplo 1",
        "precio_antes": "$100",
        "precio_ahora": "$79",
        "descuento": "21% OFF",
        "descripcion": "¡Oferta limitada!"
    },
    "2": {
        "nombre": "Producto Ejemplo 2",
        "precio_antes": "$150",
        "precio_ahora": "$120",
        "descuento": "20% OFF",
        "descripcion": "¡Solo por hoy!"
    }
}

def crear_historia_promocion(producto_data, template="moderno"):
    """Crea una imagen de historia de Instagram con la promoción"""
    
    # Tamaño de historia de Instagram: 1080x1920
    width, height = 1080, 1920
    
    if template == "moderno":
        # Fondo degradado moderno
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # Degradado simple
        for i in range(height):
            r = int(26 + (47 - 26) * i / height)
            g = int(26 + (69 - 26) * i / height)
            b = int(46 + (94 - 46) * i / height)
            draw.rectangle([(0, i), (width, i+1)], fill=(r, g, b))
    
    elif template == "minimalista":
        img = Image.new('RGB', (width, height), color='#ffffff')
        draw = ImageDraw.Draw(img)
    
    else:  # template vibrante
        img = Image.new('RGB', (width, height), color='#ff6b6b')
        draw = ImageDraw.Draw(img)
    
    # Intentar cargar fuentes (con fallback)
    try:
        font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        font_precio_grande = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_precio_antes = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
        font_descuento = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
        font_desc = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
    except:
        font_titulo = ImageFont.load_default()
        font_precio_grande = ImageFont.load_default()
        font_precio_antes = ImageFont.load_default()
        font_descuento = ImageFont.load_default()
        font_desc = ImageFont.load_default()
    
    # Colores según template
    if template == "minimalista":
        color_texto = "#000000"
        color_descuento = "#ff4757"
        color_precio_antes = "#95a5a6"
    else:
        color_texto = "#ffffff"
        color_descuento = "#ffd93d"
        color_precio_antes = "#bdc3c7"
    
    # Dibujar contenido centrado
    y_pos = 400
    
    # Nombre del producto
    nombre = producto_data["nombre"]
    bbox = draw.textbbox((0, 0), nombre, font=font_titulo)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) // 2
    draw.text((x_pos, y_pos), nombre, fill=color_texto, font=font_titulo)
    
    y_pos += 150
    
    # Precio anterior (tachado)
    precio_antes = producto_data["precio_antes"]
    bbox = draw.textbbox((0, 0), precio_antes, font=font_precio_antes)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) // 2
    draw.text((x_pos, y_pos), precio_antes, fill=color_precio_antes, font=font_precio_antes)
    # Línea tachada
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
    
    # Rectángulo del badge
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
    descripcion = producto_data["descripcion"]
    bbox = draw.textbbox((0, 0), descripcion, font=font_desc)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) // 2
    draw.text((x_pos, y_pos), descripcion, fill=color_texto, font=font_desc)
    
    # Call to action al final
    y_pos = 1700
    cta = "¡DESLIZA PARA COMPRAR!"
    bbox = draw.textbbox((0, 0), cta, font=font_desc)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) // 2
    draw.text((x_pos, y_pos), cta, fill=color_texto, font=font_desc)
    
    # Convertir a bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    keyboard = [
        [InlineKeyboardButton("📦 Ver Productos", callback_data='ver_productos')],
        [InlineKeyboardButton("🎨 Crear Historia", callback_data='crear_historia')],
        [InlineKeyboardButton("⚙️ Configurar Auto-envío", callback_data='config_auto')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '¡Hola! 👋\n\n'
        'Soy tu asistente para crear historias de Instagram con promociones.\n\n'
        '¿Qué quieres hacer?',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los botones"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ver_productos':
        texto = "📦 Productos disponibles:\n\n"
        for id, prod in productos.items():
            texto += f"{id}. {prod['nombre']}\n"
            texto += f"   Precio: {prod['precio_antes']} → {prod['precio_ahora']}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data='volver')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(texto, reply_markup=reply_markup)
    
    elif query.data == 'crear_historia':
        keyboard = []
        for id, prod in productos.items():
            keyboard.append([InlineKeyboardButton(
                f"{prod['nombre']} - {prod['descuento']}", 
                callback_data=f'generar_{id}'
            )])
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data='volver')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            '🎨 Selecciona el producto para crear la historia:',
            reply_markup=reply_markup
        )
    
    elif query.data.startswith('generar_'):
        producto_id = query.data.split('_')[1]
        await query.edit_message_text('⏳ Generando historia...')
        
        # Generar para cada template
        templates = ["moderno", "minimalista", "vibrante"]
        
        for template in templates:
            img_bytes = crear_historia_promocion(productos[producto_id], template)
            
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=img_bytes,
                caption=f"✨ Historia con template: {template.upper()}\n\n"
                        f"📱 Descarga y publica en Instagram"
            )
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ ¡Listo! Te envié 3 versiones diferentes.\n"
                 "Elige la que más te guste y publícala en Instagram."
        )
    
    elif query.data == 'config_auto':
        await query.edit_message_text(
            '⚙️ Configuración de auto-envío:\n\n'
            'Usa estos comandos:\n'
            '/auto_on - Activar envío automático diario (9 AM)\n'
            '/auto_off - Desactivar envío automático\n'
            '/set_hora HH:MM - Cambiar hora de envío\n\n'
            'Ejemplo: /set_hora 14:30'
        )
    
    elif query.data == 'volver':
        keyboard = [
            [InlineKeyboardButton("📦 Ver Productos", callback_data='ver_productos')],
            [InlineKeyboardButton("🎨 Crear Historia", callback_data='crear_historia')],
            [InlineKeyboardButton("⚙️ Configurar Auto-envío", callback_data='config_auto')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            '¿Qué quieres hacer?',
            reply_markup=reply_markup
        )

async def envio_automatico(context: ContextTypes.DEFAULT_TYPE):
    """Función para envío automático diario"""
    # Selecciona un producto aleatorio o el primero
    producto_id = "1"
    
    img_bytes = crear_historia_promocion(productos[producto_id], "moderno")
    
    await context.bot.send_photo(
        chat_id=CHAT_ID,
        photo=img_bytes,
        caption=f"🌅 ¡Buenos días!\n\n"
                f"Aquí está tu historia del día de: {productos[producto_id]['nombre']}\n\n"
                f"📱 Lista para publicar en Instagram"
    )

async def auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el envío automático"""
    # Programa para las 9 AM todos los días
    context.job_queue.run_daily(
        envio_automatico,
        time=datetime.strptime("09:00", "%H:%M").time(),
        chat_id=update.effective_chat.id,
        name=str(update.effective_chat.id)
    )
    
    await update.message.reply_text(
        '✅ Envío automático activado!\n\n'
        'Recibirás una historia lista cada día a las 9:00 AM'
    )

async def auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desactiva el envío automático"""
    jobs = context.job_queue.get_jobs_by_name(str(update.effective_chat.id))
    for job in jobs:
        job.schedule_removal()
    
    await update.message.reply_text('❌ Envío automático desactivado')

def main():
    """Función principal"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Iniciar el bot
    print("🤖 Bot iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()