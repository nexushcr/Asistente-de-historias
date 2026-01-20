import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from playwright.async_api import async_playwright

# Configuración
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
WEBSITE_URL = "https://nexushcr.com"

productos_cache = {}
ultima_actualizacion = None

# -------------------------------
# Funciones de scraping
# -------------------------------
async def scrape_productos():
    global productos_cache, ultima_actualizacion
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(WEBSITE_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            productos = await page.evaluate("""() => {
                const items = [];
                const productCards = document.querySelectorAll('.product, .producto, [class*="product"], [class*="card"], .item');
                productCards.forEach((card, index) => {
                    const nombre = card.querySelector('h1,h2,h3,h4,.title,.name,[class*="title"],[class*="name"]')?.textContent?.trim();
                    const precios = Array.from(card.querySelectorAll('[class*="price"],[class*="precio"],.price,.precio')).map(p => p.textContent.trim());
                    const img = card.querySelector('img');
                    const imagen = img?.src || img?.dataset?.src;
                    const desc = card.querySelector('p,.description,[class*="desc"]')?.textContent?.trim();
                    if (nombre) {
                        items.push({id:index+1,nombre,precios,imagen,descripcion:desc||''});
                    }
                });
                return items;
            }""")

            await browser.close()

            productos_cache = {
                str(i+1): {
                    "nombre": prod['nombre'][:50],
                    "precio_antes": prod['precios'][0] if len(prod['precios']) > 1 else "",
                    "precio_ahora": prod['precios'][-1] if prod['precios'] else "",
                    "descuento": "NUEVO",
                    "descripcion": prod.get('descripcion','')[:100],
                    "imagen_url": prod.get('imagen','')
                }
                for i, prod in enumerate(productos[:10])
            }
            ultima_actualizacion = datetime.now()
            print(f"✅ {len(productos_cache)} productos cargados")
    except Exception as e:
        print(f"❌ Error scraping: {e}")

# -------------------------------
# Handlers de Telegram
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar Productos", callback_data='actualizar')],
        [InlineKeyboardButton("📦 Ver Productos", callback_data='ver_productos')]
    ]
    mensaje = f"¡Hola! 👋 Soy tu asistente.\nProductos cargados: {len(productos_cache)}"
    await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'actualizar':
        await scrape_productos()
        await query.edit_message_text(f"✅ Productos actualizados: {len(productos_cache)}")
    elif query.data == 'ver_productos':
        texto = "📦 Productos:\n\n"
        for i, prod in enumerate(productos_cache.values(), start=1):
            texto += f"{i}. {prod['nombre']} - {prod['precio_ahora']}\n"
        await query.edit_message_text(texto)

# -------------------------------
# Scraping inicial
# -------------------------------
async def iniciar_scraping_inicial(app: Application):
    await asyncio.sleep(5)
    await scrape_productos()

# -------------------------------
# Main
# -------------------------------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Hook para lanzar scraping inicial al arrancar
    app.post_init = iniciar_scraping_inicial

    print("🤖 Bot iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
