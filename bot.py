import os
import asyncio
from datetime import datetime
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from playwright.async_api import async_playwright

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://www.nexushcr.com")

productos_cache = {}
ultima_actualizacion = None

# -------------------------------
# Scraping de productos
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
                if (typeof products !== 'undefined') {
                    const items = [];
                    for (const categoria in products) {
                        products[categoria].forEach(prod => {
                            items.push({
                                id: prod.id,
                                nombre: prod.name,
                                precio: prod.price,
                                imagen: prod.image,
                                descripcion: prod.description,
                                categoria: prod.category
                            });
                        });
                    }
                    return items;
                }
                return [];
            }""")

            await browser.close()

            productos_cache = {
                str(i+1): {
                    "nombre": prod['nombre'][:50],
                    "precio_ahora": f"₡{prod['precio']:,}",
                    "descripcion": prod.get('descripcion','')[:100],
                    "imagen_url": prod.get('imagen',''),
                    "categoria": prod.get('categoria','')
                }
                for i, prod in enumerate(productos[:20])
            }
            ultima_actualizacion = datetime.now()
            print(f"✅ {len(productos_cache)} productos cargados")
    except Exception as e:
        print(f"❌ Error scraping: {e}")

# -------------------------------
# Generar imagen promocional
# -------------------------------
def crear_imagen_producto(prod):
    try:
        response = requests.get(prod["imagen_url"])
        img_producto = Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        img_producto = Image.new("RGBA", (400, 400), "white")

    canvas = Image.new("RGBA", (600, 600), "white")
    canvas.paste(img_producto.resize((400, 400)), (100, 50))

    draw = ImageDraw.Draw(canvas)
    try:
        font_title = ImageFont.truetype("arial.ttf", 28)
        font_price = ImageFont.truetype("arial.ttf", 36)
    except:
        font_title = ImageFont.load_default()
        font_price = ImageFont.load_default()

    draw.text((50, 470), prod["nombre"], font=font_title, fill="black")
    draw.text((50, 520), prod["precio_ahora"], font=font_price, fill="red")

    return canvas

# -------------------------------
# Handlers de Telegram
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hola 👋, el bot está vivo")
    if productos_cache:
        await update.message.reply_text(f"Productos cargados: {len(productos_cache)}")
    else:
        await update.message.reply_text("No hay productos en cache todavía.")

async def ver_productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not productos_cache:
        await update.message.reply_text("No hay productos cargados todavía.")
        return

    for prod in productos_cache.values():
        img = crear_imagen_producto(prod)
        bio = BytesIO()
        bio.name = "producto.png"
        img.save(bio, "PNG")
        bio.seek(0)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=bio)

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
    app.add_handler(CommandHandler("productos", ver_productos))

    app.post_init = iniciar_scraping_inicial

    print("🤖 Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
