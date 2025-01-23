FROM python:3.9-slim

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y wget

# Descargar e instalar una versión estática de FFmpeg (que incluye ffprobe)
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz && \
    tar -xvf ffmpeg-release-i686-static.tar.xz && \
    mv ffmpeg-*/ffmpeg /usr/local/bin/ && \
    mv ffmpeg-*/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg-release-i686-static.tar.xz ffmpeg-*

# Verificar si ffprobe está disponible
RUN ffprobe -version

# Copiar el código fuente de tu aplicación
COPY . /app

# Instalar dependencias del proyecto
WORKDIR /app
RUN pip install -r requirements.txt

# Comando para iniciar la aplicación
CMD ["python", "app.py"]
