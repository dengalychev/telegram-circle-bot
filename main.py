import os
import subprocess
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка подробного логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN не найден в переменных окружения!")
    exit(1)

logger.info(f"Токен получен, первые 5 символов: {TOKEN[:5]}...")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Получена команда /start от {update.effective_user.id}")
    await update.message.reply_text(
        "👋 Привет! Я превращаю видео в кружочки!\n\n"
        "Отправь мне видео, а потом ответь на него командой /circle"
    )

# Команда /circle
async def circle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Получена команда /circle от {update.effective_user.id}")
    
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /circle")
        return
    
    await update.message.reply_text("⏳ Конвертирую в кружочек... (до 30 секунд)")
    
    try:
        file = await reply.video.get_file()
        input_path = "input.mp4"
        logger.info(f"Скачиваю видео: {file.file_id}")
        await file.download_to_drive(input_path)
        
        output_path = "circle.mp4"
        cmd = [
            "ffmpeg", "-i", input_path,
            "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=480:480",
            "-t", "60",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path, "-y"
        ]
        
        logger.info(f"Запускаю FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg ошибка: {result.stderr}")
            await update.message.reply_text(f"❌ Ошибка конвертации: {result.stderr[:200]}")
            return
        
        logger.info("FFmpeg завершил работу, отправляю кружочек")
        
        with open(output_path, "rb") as f:
            await update.message.reply_video_note(video_note=f.read())
        
        await update.message.reply_text("✅ Готово!")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")
    
    finally:
        for f in ["input.mp4", "circle.mp4"]:
            if os.path.exists(f):
                os.remove(f)
                logger.info(f"Удалён файл: {f}")

# Команда /gif
async def gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Получена команда /gif от {update.effective_user.id}")
    
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /gif")
        return
    
    await update.message.reply_text("⏳ Конвертирую в GIF... (до 30 секунд)")
    
    try:
        file = await reply.video.get_file()
        input_path = "input.mp4"
        await file.download_to_drive(input_path)
        
        output_path = "output.gif"
        cmd = [
            "ffmpeg", "-i", input_path,
            "-vf", "fps=10,scale=320:-1:flags=lanczos",
            "-t", "30", "-loop", "0",
            output_path, "-y"
        ]
        
        logger.info(f"Запускаю FFmpeg для GIF")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg ошибка: {result.stderr}")
            await update.message.reply_text(f"❌ Ошибка конвертации: {result.stderr[:200]}")
            return
        
        with open(output_path, "rb") as f:
            await update.message.reply_document(document=f, filename="video.gif")
        
        await update.message.reply_text("✅ Готово!")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")
    
    finally:
        for f in ["input.mp4", "output.gif"]:
            if os.path.exists(f):
                os.remove(f)

# Запуск бота
async def main():
    logger.info("Запуск main()")
    
    if not TOKEN:
        logger.error("Нет токена!")
        return
    
    app = Application.builder().token(TOKEN).build()
    logger.info("Application создан")
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("circle", circle))
    app.add_handler(CommandHandler("gif", gif))
    logger.info("Хендлеры добавлены")
    
    logger.info("Запускаю polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("✅ Бот успешно запущен и работает!")
    
    # Держим бота запущенным
    await asyncio.Event().wait()

if __name__ == "__main__":
    logger.info("Скрипт main.py запущен")
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
