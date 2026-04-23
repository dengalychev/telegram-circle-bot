import os
import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN не найден!")
    exit(1)

logger.info("Бот запускается...")

async def start(update: Update, context):
    await update.message.reply_text("👋 Отправь видео и ответь /circle")

async def circle(update: Update, context):
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /circle")
        return
    
    await update.message.reply_text("⏳ Конвертирую...")
    
    file = await reply.video.get_file()
    await file.download_to_drive("input.mp4")
    
    cmd = [
        "ffmpeg", "-i", "input.mp4",
        "-vf", "crop=min(iw,ih):min(iw,ih),scale=480:480",
        "-t", "60", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "circle.mp4", "-y"
    ]
    
    subprocess.run(cmd, check=True)
    
    with open("circle.mp4", "rb") as f:
        await update.message.reply_video_note(f.read())
    
    os.remove("input.mp4")
    os.remove("circle.mp4")
    await update.message.reply_text("✅ Готово!")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("circle", circle))
    
    logger.info("✅ Бот успешно запущен!")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
