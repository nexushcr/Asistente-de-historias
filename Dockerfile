FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema necesarias para Pillow, rembg y (opcional) Real-ESRGAN
RUN apt-get update && apt-get install -y \ 
    libjpeg-dev \ 
    zlib1g-dev \ 
    libfreetype6-dev \ 
    liblcms2-dev \ 
    libopenjp2-7-dev \ 
    libtiff-dev \ 
    fontconfig \ 
    ffmpeg \ 
    libgl1-mesa-glx \ 
    libglib2.0-0 \ 
    build-essential \ 
    git \ 
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias de Python
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \ 
    pip install --no-cache-dir -r requirements.txt

# Copiar fuentes (asegúrate de añadir fonts/ al repo)
COPY fonts /usr/share/fonts/truetype/custom
RUN fc-cache -f -v || true

# Copiar el resto del código
COPY . .

CMD ["python", "bot.py"]