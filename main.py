import os
import subprocess
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error("BOT_TOKEN не найден!")
    exit(1)

app_flask = Flask('')

@app_flask.route('/')
@app_flask.route('/health')
def health():
    return "OK", 200

def run_http():
    app_flask.run(host='0.0.0.0', port=PORT)

# === ФУНКЦИЯ КОНВЕРТАЦИИ (общая) ===
async def convert_video(update: Update, context, output_format, is_circle=False):
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой")
        return
    
    await update.message.reply_text(f"⏳ Конвертирую в {output_format}... (до 30 секунд)")
    
    try:
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
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")
    
    finally:
        for f in ["input.mp4", "output.mp4", "output.gif"]:
            if os.path.exists(f):
                os.remove(f)

# === ФУНКЦИЯ СКАЧИВАНИЯ (YouTube, Instagram, TikTok) ===
async def download_media(update: Update, context):
    url = update.message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        return
    
    await update.message.reply_text("⏳ Скачиваю видео... (до 30 секунд)")
    
    try:
        # Используем yt-dlp для скачивания
        cmd = [
            "yt-dlp", "-f", "best[ext=mp4]/best",
            "--no-playlist",
            "-o", "downloaded.mp4",
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            await update.message.reply_text(f"❌ Не удалось скачать: {result.stderr[:200]}")
            return
        
        if os.path.exists("downloaded.mp4"):
            with open("downloaded.mp4", "rb") as f:
                await update.message.reply_video(video=f, caption="✅ Вот ваше видео!")
            os.remove("downloaded.mp4")
        else:
            await update.message.reply_text("❌ Не удалось найти скачанный файл")
        
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")

# === КОМАНДЫ БОТА ===
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 Привет! Что умею:\n\n"
        "📌 Отправь видео, затем:\n"
        "  🔘 /circle — сделать кружочек\n"
        "  🎞️ /gif — сделать GIF\n\n"
        "📌 Или просто отправь ссылку:\n"
        "  📹 YouTube, Instagram, TikTok\n"
        "  — я скачаю видео!\n\n"
        "📌 /help — подробная справка"
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "📖 **Справка**\n\n"
        "**Конвертация видео:**\n"
        "1. Отправь видео\n"
        "2. Ответь на него:\n"
        "   /circle — кружочек (до 60 сек)\n"
        "   /gif — GIF-анимация (до 30 сек)\n\n"
        "**Скачивание из соцсетей:**\n"
        "Просто отправь ссылку на:\n"
        "• YouTube (видео/Shorts)\n"
        "• Instagram (Reels/посты)\n"
        "• TikTok\n"
        "• Twitter/X\n"
        "• Reddit\n\n"
        "**Ограничения:**\n"
        "• Видео до 50 MB\n"
        "• Длительность до 60 сек для кружка\n\n"
        "Поддержка: @dengalychev"
    )

async def circle(update: Update, context):
    await convert_video(update, context, "кружочек", is_circle=True)

async def gif(update: Update, context):
    await convert_video(update, context, "GIF", is_circle=False)

# === ЗАПУСК ===
def main():
    # HTTP сервер
    http_thread = Thread(target=run_http, daemon=True)
    http_thread.start()
    logger.info(f"HTTP сервер на порту {PORT}")
    
    # Telegram бот
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("circle", circle))
    app.add_handler(CommandHandler("gif", gif))
    
    # Обработка ссылок (для скачивания)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_media))
    
    logger.info("✅ Бот успешно запущен!")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
