FROM python:3.11-slim

WORKDIR /app

# Устанавливаем FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Проверяем установку FFmpeg (для логов сборки)
RUN ffmpeg -version

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY main.py .

# Запускаем бота
CMD ["python", "main.py"]
