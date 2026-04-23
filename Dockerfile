# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем переменную окружения, чтобы избежать интерактивных запросов
ENV DEBIAN_FRONTEND=noninteractive

# Обновляем списки пакетов и устанавливаем необходимые зависимости
# curl и unzip нужны для установки Deno, ffmpeg - для конвертации видео
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Deno (JavaScript-рантайм) через официальный скрипт
RUN curl -fsSL https://deno.land/install.sh | sh

# Добавляем Deno в PATH, чтобы он был доступен из командной строки
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# Устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY main.py .

# Команда для запуска бота
CMD ["python", "main.py"]
