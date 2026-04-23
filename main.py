import os
import subprocess
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error("BOT_TOKEN не найден!")
    exit(1)

# === HTTP сервер для Render ===
app_flask = Flask('')

@app_flask.route('/')
@app_flask.route('/health')
def health():
    return "OK", 200

def run_http():
    app_flask.run(host='0.0.0.0', port=PORT)

# === КОНВЕРТАЦИЯ ВИДЕО ===
async def convert_video(update: Update, context, is_circle: bool):
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /circle или /gif")
        return
    
    await update.message.reply_text("⏳ Конвертирую... (до 30 секунд)")
    
    try:
        # Скачиваем видео от пользователя
        file = await reply.video.get_file()
        await file.download_to_drive("input.mp4")
        logger.info("Видео скачано")
        
        if is_circle:
            # Кружочек
            cmd = [
                "ffmpeg", "-i", "input.mp4",
                "-vf", "crop='min(iw,ih):min(iw,ih)',scale=480:480",
                "-t", "60",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                "output.mp4", "-y"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            with open("output.mp4", "rb") as f:
                await update.message.reply_video_note(video_note=f.read())
        else:
            # GIF
            cmd = [
                "ffmpeg", "-i", "input.mp4",
                "-vf", "fps=10,scale=320:-1:flags=lanczos",
                "-t", "30",
                "-loop", "0",
                "output.gif", "-y"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            with open("output.gif", "rb") as f:
                await update.message.reply_document(document=f, filename="video.gif")
        
        await update.message.reply_text("✅ Готово!")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg ошибка: {e.stderr.decode() if e.stderr else 'Unknown'}")
        await update.message.reply_text("❌ Ошибка конвертации. Проверьте формат видео.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")
    
    finally:
        for f in ["input.mp4", "output.mp4", "output.gif"]:
            if os.path.exists(f):
                os.remove(f)

# === КОМАНДЫ ===
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 Привет! Я превращаю видео в кружочки и GIF.\n\n"
        "📌 Отправь мне видео, затем ответь на него:\n"
        "   🔘 /circle — сделать кружочек (до 60 сек)\n"
        "   🎞️ /gif — сделать GIF (до 30 сек)\n\n"
        "📌 /help — подробная справка"
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "📖 **Справка**\n\n"
        "**Как пользоваться:**\n"
        "1. Отправь видео в чат\n"
        "2. Нажми на видео, выбери 'Ответить'\n"
        "3. Введи команду:\n"
        "   • /circle — превратит в квадратный кружочек\n"
        "   • /gif — создаст GIF-анимацию\n\n"
        "**Ограничения:**\n"
        "• Видео до 50 MB\n"
        "• Длительность до 60 сек для кружков\n"
        "• GIF создаётся до 30 сек\n\n"
        "Поддержка: @dengalychev"
    )

async def circle(update: Update, context):
    await convert_video(update, context, is_circle=True)

async def gif(update: Update, context):
    await convert_video(update, context, is_circle=False)

# === ЗАПУСК ===
def main():
    # HTTP сервер
    http_thread = Thread(target=run_http, daemon=True)
    http_thread.start()
    logger.info(f"HTTP сервер на порту {PORT}")
    
    # Telegram бот
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("circle", circle))
    app.add_handler(CommandHandler("gif", gif))
    
    logger.info("✅ Бот успешно запущен!")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
