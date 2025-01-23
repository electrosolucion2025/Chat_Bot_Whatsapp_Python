FROM python:3.9-slim

# Actualizar el sistema e instalar ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Asegurarse de que ffmpeg y ffprobe estén en el PATH
ENV PATH="/usr/local/bin:${PATH}"

# Verificar si ffmpeg y ffprobe están en el PATH
RUN which ffmpeg
RUN which ffprobe

# Copiar el código fuente de tu aplicación
COPY . /app

# Instalar las dependencias del proyecto
WORKDIR /app
RUN pip install -r requirements.txt

# Comando para iniciar la aplicación
CMD ["python", "app.py"]
