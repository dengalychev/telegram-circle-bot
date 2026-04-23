import os
import subprocess
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error("BOT_TOKEN не найден!")
    exit(1)

# === Health-сервер для Render ===
app_flask = Flask('')

@app_flask.route('/')
@app_flask.route('/health')
def health():
    return "OK", 200

def run_http():
    """Запускает HTTP сервер на порту PORT"""
    app_flask.run(host='0.0.0.0', port=PORT)

# === Telegram бот ===
async def start(update: Update, context):
    await update.message.reply_text("👋 Отправь видео и ответь /circle")

async def circle(update: Update, context):
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /circle")
        return
    
    await update.message.reply_text("⏳ Конвертирую...")
    
    try:
        file = await reply.video.get_file()
        await file.download_to_drive("input.mp4")
        logger.info("Видео скачано")
        
        cmd = [
            "ffmpeg", "-i", "input.mp4",
            "-vf", "crop=min(iw,ih):min(iw,ih),scale=480:480",
            "-t", "60", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "circle.mp4", "-y"
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("FFmpeg завершил работу")
        
        with open("circle.mp4", "rb") as f:
            await update.message.reply_video_note(video_note=f.read())
        
        await update.message.reply_text("✅ Готово!")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")
    
    finally:
        for f in ["input.mp4", "circle.mp4"]:
            if os.path.exists(f):
                os.remove(f)

# === Запуск ===
def main():
    # Запускаем HTTP сервер в отдельном потоке
    http_thread = Thread(target=run_http, daemon=True)
    http_thread.start()
    logger.info(f"HTTP сервер запущен на порту {PORT}")
    
    # Запускаем Telegram бота
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("circle", circle))
    
    logger.info("✅ Бот успешно запущен!")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
