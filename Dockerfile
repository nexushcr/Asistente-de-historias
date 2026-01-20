# Usa la imagen oficial de Playwright para Python
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto
COPY . .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala las dependencias de sistema necesarias para Playwright
RUN playwright install-deps

# Instala los navegadores de Playwright
RUN playwright install

# Comando de inicio
CMD ["python", "bot.py"]
