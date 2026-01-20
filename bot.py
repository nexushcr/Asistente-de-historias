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

# -------------------------------
# Tus funciones scrape_productos, crear_historia_promocion,
# start, button_handler, envio_automatico, auto_on, auto_off
# se mantienen exactamente igual que en tu código original.
# -------------------------------

async def iniciar_scraping_inicial():
    """Scraping inicial al arrancar el bot"""
    await asyncio.sleep(5)  # Espera 5 segundos después de iniciar
    await scrape_productos()

async def main():
    """Función principal asíncrona"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Scraping inicial como tarea en segundo plano
    asyncio.create_task(iniciar_scraping_inicial())
    
    print("🤖 Bot iniciado con scraping web...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    asyncio.run(main())
