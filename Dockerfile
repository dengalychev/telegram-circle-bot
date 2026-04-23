FROM python:3.11-slim

WORKDIR /app

# Устанавливаем FFmpeg и необходимые зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Проверяем установку FFmpeg
RUN ffmpeg -version

# Копируем файлы
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Запускаем бота
CMD ["python", "main.py"]
