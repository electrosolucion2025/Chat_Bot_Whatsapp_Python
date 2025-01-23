FROM python:3.9-slim

# Instalar ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copiar el código fuente de tu aplicación
COPY . /app

# Instalar dependencias de tu proyecto
WORKDIR /app
RUN pip install -r requirements.txt

# Comando para iniciar tu aplicación
CMD ["python", "main.py"]
