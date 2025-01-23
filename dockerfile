FROM python:3.9-slim

# Instalar ffmpeg y las dependencias necesarias
RUN apt-get update && apt-get install -y ffmpeg

# Verifica que ffprobe esté disponible
RUN ffprobe -version

# Copiar el código fuente de tu aplicación
COPY . /app

# Instalar las dependencias de tu proyecto
WORKDIR /app
RUN pip install -r requirements.txt

# Comando para iniciar la aplicación
CMD ["python", "app.py"]