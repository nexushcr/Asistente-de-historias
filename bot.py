"""
(Full file content below)
"""

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

from image_utils import crear_imagen_producto

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://www.nexushcr.com")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

productos_cache = []
ultima_actualizacion = None


async def scrape_productos():
    global productos_cache, ultima_actualizacion
    
    try:
        print("Cargando productos desde nexushcr.com/productos.json...")
        
        json_url = WEBSITE_URL + "/productos.json"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(json_url, headers=headers, timeout=20)
        response.raise_for_status()
        
        print(f"JSON descargado ({len(response.text)} caracteres)")
        
        data = response.json()
        productos_json = data.get('productos', [])
        
        if not productos_json:
            print("No se encontraron productos en el JSON")
            return
        
        productos_encontrados = []
        
        for prod in productos_json:
            imagen = prod.get('imagen', '')
            
            if imagen.startswith('/'):  
                imagen_url = WEBSITE_URL + imagen
            elif imagen.startswith('http'):
                imagen_url = imagen
            else:
                imagen_url = WEBSITE_URL + '/' + imagen
            
            productos_encontrados.append({
                'id': prod.get('id'),
                'nombre': prod.get('nombre', '').strip(),
                'precio': prod.get('precio', 0),
                'imagen_url': imagen_url,
                'categoria': prod.get('categoria', '').strip(),
                'descripcion': prod.get('descripcion', '').strip()
            })
        
        productos_cache = productos_encontrados
        ultima_actualizacion = datetime.now()
        print(f"{len(productos_cache)} productos cargados correctamente")
        
        categorias = {} 
        for p in productos_cache:
            cat = p['categoria']
            categorias[cat] = categorias.get(cat, 0) + 1
        
        print("Productos por categoria:")
        for cat, count in categorias.items():
            print(f"   {cat}: {count}")
        
        # Keep backward-compatible scraping attempts if needed
        # (existing code had a regex path which may still be useful)
        try:
            # This is a no-op unless you have additional parsing to add
            pass
        except Exception:
            pass
        
    except Exception as e:
        print(f"Error en scraping: {e}")
        import traceback
        traceback.print_exc()


async def publicar_producto_aleatorio(context: ContextTypes.DEFAULT_TYPE):
    if not productos_cache:
        print("No hay productos para publicar, intentando actualizar...")
        await scrape_productos()
        if not productos_cache:
            print("No se pudieron cargar productos")
            return
    
    producto = random.choice(productos_cache)
    print(f"Preparando publicacion: {producto['nombre']}")
    
    try:
        img = crear_imagen_producto(producto)
        bio = BytesIO()
        bio.name = f"producto_{producto['id']}.png"
        img.save(bio, "PNG", quality=95, optimize=True)
        bio.seek(0)
        
        mensaje = f"OFERTA DESTACADA\n\n"
        mensaje += f"{producto['nombre']}\n\n"
        
        if producto['descripcion']:
            desc_corta = producto['descripcion'][:80] + "..." if len(producto['descripcion']) > 80 else producto['descripcion']
            mensaje += f"{desc_corta}\n\n"
        
        mensaje += f"Precio: C{producto['precio']:,}\n"
        mensaje += f"Categoria: {producto['categoria'].title()}\n\n"
        mensaje += f"Visita: {WEBSITE_URL}\n"
        mensaje += f"Contactanos para mas informacion"
        
        if CHANNEL_ID:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=bio,
                caption=mensaje
            )
            print(f"Publicado exitosamente: {producto['nombre']}")
        else:
            print("No hay CHANNEL_ID configurado")
            
    except Exception as e:
        print(f"Error al publicar: {e}")
        import traceback
        traceback.print_exc()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "Bienvenido al Bot de NexusHCR\n\n"
        "Comandos disponibles:\n"
        "/productos - Ver catalogo completo\n"
        "/aleatorio - Producto sorpresa\n"
        "/categorias - Ver por categoria\n"
        "/actualizar - Actualizar catalogo\n"
        "/estado - Estado del sistema\n\n"
        f"Sitio web: {WEBSITE_URL}"
    )
    await update.message.reply_text(mensaje)


async def ver_productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not productos_cache:
        await update.message.reply_text("Cargando productos por primera vez...")
        await scrape_productos()
    
    if not productos_cache:
        await update.message.reply_text("No se pudieron cargar los productos. Intenta /actualizar")
        return
    
    productos_mostrar = productos_cache[:8]
    
    await update.message.reply_text(
        f"Mostrando {len(productos_mostrar)} de {len(productos_cache)} productos disponibles..."
    )
    
    for prod in productos_mostrar:
        try:
            img = crear_imagen_producto(prod)
            bio = BytesIO()
            bio.name = f"producto_{prod['id']}.png"
            img.save(bio, "PNG", quality=85)
            bio.seek(0)
            
            caption = (
                f"{prod['nombre']}\n"
                f"C{prod['precio']:,}\n"
                f"{prod['categoria'].title()}"
            )
            
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=bio,
                caption=caption
            )
            
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Error enviando producto {prod['id']}: {e}")


async def producto_aleatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not productos_cache:
        await update.message.reply_text("Cargando productos...")
        await scrape_productos()
    
    if not productos_cache:
        await update.message.reply_text("No hay productos disponibles")
        return
    
    prod = random.choice(productos_cache)
    
    try:
        img = crear_imagen_producto(prod)
        bio = BytesIO()
        bio.name = f"producto_{prod['id']}.png"
        img.save(bio, "PNG", quality=90)
        bio.seek(0)
        
        caption = (
            f"Producto Aleatorio\n\n"
            f"{prod['nombre']}\n\n"
            f"{prod['descripcion']}\n\n"
            f"Precio: C{prod['precio']:,}\n"
            f"Categoria: {prod['categoria'].title()}"
        )
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=bio,
            caption=caption
        )
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("Error al generar la imagen")


async def ver_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not productos_cache:
        await update.message.reply_text("Cargando productos...")
        await scrape_productos()
    
    if not productos_cache:
        await update.message.reply_text("No hay productos disponibles")
        return
    
    categorias = {}
    for prod in productos_cache:
        cat = prod['categoria']
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(prod)
    
    mensaje = "Productos por Categoria\n\n"
    
    for cat, prods in categorias.items():
        mensaje += f"{cat.upper()} ({len(prods)} productos)\n"
        for p in prods[:3]:
            mensaje += f"  {p['nombre']} - C{p['precio']:,}\n"
        if len(prods) > 3:
            mensaje += f"  ... y {len(prods) - 3} mas\n"
        mensaje += "\n"
    
    await update.message.reply_text(mensaje)


async def actualizar_catalogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Actualizando catalogo desde nexushcr.com...")
    
    try:
        await scrape_productos()
        
        if productos_cache:
            categorias = {}
            for p in productos_cache:
                cat = p['categoria']
                categorias[cat] = categorias.get(cat, 0) + 1
            
            resumen = "Catalogo actualizado exitosamente\n\n"
            resumen += f"Total de productos: {len(productos_cache)}\n\n"
            resumen += "Por categoria:\n"
            for cat, count in categorias.items():
                resumen += f"{cat.title()}: {count}\n"
            
            await update.message.reply_text(resumen)
        else:
            await update.message.reply_text("Error al actualizar catalogo. Verifica la conexion.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def estado_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tiempo_desde_actualizacion = "Nunca"
    if ultima_actualizacion:
        delta = datetime.now() - ultima_actualizacion
        minutos = int(delta.total_seconds() / 60)
        if minutos < 60:
            tiempo_desde_actualizacion = f"Hace {minutos} minutos"
        else:
            horas = minutos // 60
            tiempo_desde_actualizacion = f"Hace {horas} horas"
    
    categorias_count = {}
    for p in productos_cache:
        cat = p['categoria']
        categorias_count[cat] = categorias_count.get(cat, 0) + 1
    
    mensaje = (
        "Estado del Sistema NexusHCR\n\n"
        f"Productos cargados: {len(productos_cache)}\n"
        f"Ultima actualizacion: {tiempo_desde_actualizacion}\n"
        f"Sitio web: {WEBSITE_URL}\n"
        f"Publicaciones automaticas: {'Activas' if CHANNEL_ID else 'No configuradas'}\n\n"
    )
    
    if categorias_count:
        mensaje += "Productos por categoria:\n"
        for cat, count in categorias_count.items():
            mensaje += f"{cat.title()}: {count}\n"
    
    await update.message.reply_text(mensaje)


async def post_init(application: Application):
    print("Iniciando Bot de NexusHCR...")
    print("Realizando scraping inicial...")
    
    await asyncio.sleep(2)
    
    intentos = 3
    for i in range(intentos):
        await scrape_productos()
        if productos_cache:
            break
        if i < intentos - 1:
            print(f"Intento {i+1} fallo, reintentando en 5 segundos...")
            await asyncio.sleep(5)
    
    if not productos_cache:
        print("No se pudieron cargar productos en el inicio")
    
    scheduler = AsyncIOScheduler()
    
    hora_aleatoria = random.randint(9, 21)
    minuto_aleatorio = random.randint(0, 59)
    
    scheduler.add_job(
        publicar_producto_aleatorio,
        'cron',
        hour=hora_aleatoria,
        minute=minuto_aleatorio,
        args=[application]
    )
    
    print(f"Publicacion automatica programada para las {hora_aleatoria:02d}:{minuto_aleatorio:02d} diariamente")
    
    if CHANNEL_ID:
        print(f"Canal configurado: {CHANNEL_ID}")
    else:
        print("CHANNEL_ID no configurado")
    
    scheduler.start()
    print("Sistema completamente inicializado")


def main():
    if not TELEGRAM_TOKEN:
        print("ERROR: Variable TELEGRAM_TOKEN no esta configurada")
        return
    
    print("BOT NEXUSHCR - Sistema de Publicaciones")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("productos", ver_productos))
    app.add_handler(CommandHandler("aleatorio", producto_aleatorio))
    app.add_handler(CommandHandler("categorias", ver_categorias))
    app.add_handler(CommandHandler("actualizar", actualizar_catalogo))
    app.add_handler(CommandHandler("estado", estado_bot))
    
    app.post_init = post_init
    
    print("Bot iniciado correctamente")
    print("Esperando mensajes en Telegram...")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()