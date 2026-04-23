import os
import subprocess
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Получаем токен из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я превращаю видео в кружочки!\n\n"
        "Отправь мне видео, а потом ответь на него командой /circle"
    )

# Команда /circle — конвертация видео в кружочек
async def circle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что пользователь ответил на видео
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /circle")
        return
    
    await update.message.reply_text("⏳ Конвертирую в кружочек... (до 30 секунд)")
    
    # Скачиваем видео
    file = await reply.video.get_file()
    input_path = "input.mp4"
    await file.download_to_drive(input_path)
    
    # Конвертируем через FFmpeg
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
    
    try:
        # Запускаем конвертацию
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Отправляем готовый кружочек
        with open(output_path, "rb") as f:
            await update.message.reply_video_note(video_note=f.read())
        
        await update.message.reply_text("✅ Готово!")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка конвертации: {e}")
    
    finally:
        # Удаляем временные файлы
        for f in [input_path, output_path]:
            if os.path.exists(f):
                os.remove(f)

# Команда /gif — конвертация в GIF
async def gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /gif")
        return
    
    await update.message.reply_text("⏳ Конвертирую в GIF... (до 30 секунд)")
    
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
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        
        with open(output_path, "rb") as f:
            await update.message.reply_document(document=f, filename="video.gif")
        
        await update.message.reply_text("✅ Готово!")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка конвертации: {e}")
    
    finally:
        for f in [input_path, output_path]:
            if os.path.exists(f):
                os.remove(f)

# Запуск бота
async def main():
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("circle", circle))
    app.add_handler(CommandHandler("gif", gif))
    
    print("✅ Бот запущен!")
    
    # Запускаем polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Держим бота запущенным
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
