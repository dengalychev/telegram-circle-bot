FROM python:3.11-slim

WORKDIR /app

# Устанавливаем FFmpeg и yt-dlp
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY main.py .

# Запускаем бота
CMD ["python", "main.py"]
