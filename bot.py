async def scrape_productos():
    global productos_cache, ultima_actualizacion
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(WEBSITE_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Extraer directamente el objeto products definido en la página
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

            # Guardar en cache los primeros 20 productos
            productos_cache = {
                str(i+1): {
                    "nombre": prod['nombre'][:50],
                    "precio_antes": "",
                    "precio_ahora": f"₡{prod['precio']:,}",  # formato con separador de miles
                    "descuento": "NUEVO",
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
