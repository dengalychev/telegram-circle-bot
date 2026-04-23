import os
import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN не найден!")
    exit(1)

# Проверяем FFmpeg при запуске
try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    logger.info(f"FFmpeg version: {result.stdout.splitlines()[0]}")
except Exception as e:
    logger.error(f"FFmpeg не найден: {e}")

logger.info("Бот запускается...")

async def start(update: Update, context):
    await update.message.reply_text("👋 Отправь видео и ответь /circle")

async def circle(update: Update, context):
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /circle")
        return
    
    await update.message.reply_text("⏳ Конвертирую... (может занять до 30 секунд)")
    
    try:
        # Скачиваем видео
        file = await reply.video.get_file()
        await file.download_to_drive("input.mp4")
        logger.info("Видео скачано")
        
        # Конвертируем через FFmpeg
        cmd = [
            "ffmpeg", "-i", "input.mp4",
            "-vf", "crop=min(iw,ih):min(iw,ih),scale=480:480",
            "-t", "60",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "circle.mp4", "-y"
        ]
        
        logger.info(f"Запуск FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg ошибка: {result.stderr}")
            await update.message.reply_text(f"❌ Ошибка конвертации: {result.stderr[:200]}")
            return
        
        logger.info("FFmpeg завершил работу")
        
        # Отправляем кружочек
        with open("circle.mp4", "rb") as f:
            await update.message.reply_video_note(video_note=f.read())
        
        await update.message.reply_text("✅ Готово!")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")
    
    finally:
        # Чистим временные файлы
        for f in ["input.mp4", "circle.mp4"]:
            if os.path.exists(f):
                os.remove(f)
                logger.info(f"Удалён файл: {f}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("circle", circle))
    
    logger.info("✅ Бот успешно запущен!")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
