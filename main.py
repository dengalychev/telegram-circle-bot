import os
import subprocess
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error("BOT_TOKEN не найден!")
    exit(1)

# === HEALTH-СЕРВЕР ДЛЯ RENDER ===
app_flask = Flask('')

@app_flask.route('/')
@app_flask.route('/health')
def health():
    return "OK", 200

def run_http():
    """Запускает HTTP сервер в отдельном потоке"""
    app_flask.run(host='0.0.0.0', port=PORT)

# === ФУНКЦИЯ КОНВЕРТАЦИИ (ОБЩАЯ) ===
async def convert_video(update: Update, context, output_format: str, is_circle: bool = False):
    """
    Универсальная функция для конвертации видео.
    is_circle=True → кружочек (video_note)
    is_circle=False → GIF
    """
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео командой /circle или /gif")
        return
    
    await update.message.reply_text(f"⏳ Конвертирую в {output_format}... (до 30 секунд)")
    
    try:
        # Скачиваем видео
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
            
            # Отправляем кружочек
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
            
            # Отправляем GIF
            with open("output.gif", "rb") as f:
                await update.message.reply_document(document=f, filename="video.gif")
        
        await update.message.reply_text("✅ Готово!")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg ошибка: {e.stderr.decode() if e.stderr else 'Unknown error'}")
        await update.message.reply_text("❌ Ошибка конвертации. Проверьте формат видео.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")
    
    finally:
        # Удаляем временные файлы
        for f in ["input.mp4", "output.mp4", "output.gif"]:
            if os.path.exists(f):
                os.remove(f)
                logger.info(f"Удалён файл: {f}")

# === ФУНКЦИЯ СКАЧИВАНИЯ (YOUTUBE, INSTAGRAM, TIKTOK И ДР.) ===
async def download_media(update: Update, context):
    url = update.message.text.strip()
    
    # Проверяем, что это ссылка
    if not url.startswith(('http://', 'https://')):
        return
    
    await update.message.reply_text("⏳ Скачиваю видео... (до 45 секунд)")
    
    try:
        # Команда для yt-dlp
        # --js-runtimes deno: решает проблему с JavaScript на YouTube
        # --no-check-certificate: помогает с SSL ошибками
        cmd = [
            "yt-dlp",
            "--js-runtimes", "deno",
            "--no-check-certificate",
            "-f", "best[ext=mp4]/best",
            "--no-playlist",
            "-o", "downloaded.mp4",
            url
        ]
        
        logger.info(f"Запуск yt-dlp для URL: {url}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = result.stderr[:300]
            logger.error(f"yt-dlp ошибка: {error_msg}")
            await update.message.reply_text(f"❌ Не удалось скачать: {error_msg}")
            return
        
        if os.path.exists("downloaded.mp4") and os.path.getsize("downloaded.mp4") > 0:
            with open("downloaded.mp4", "rb") as f:
                await update.message.reply_video(
                    video=f, 
                    caption="✅ Вот ваше видео!",
                    supports_streaming=True
                )
            os.remove("downloaded.mp4")
            logger.info("Видео успешно скачано и отправлено")
        else:
            await update.message.reply_text("❌ Не удалось скачать видео. Файл не создан.")
        
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")

# === КОМАНДЫ БОТА ===
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 Привет! Я умею:\n\n"
        "📌 **Конвертировать видео:**\n"
        "   • Отправь мне видео\n"
        "   • Ответь на него командой /circle (кружочек)\n"
        "   • Или /gif (GIF-анимация)\n\n"
        "📌 **Скачивать из соцсетей:**\n"
        "   • Просто отправь ссылку\n"
        "   • Поддерживаются: YouTube, Instagram, TikTok, Twitter, Reddit\n\n"
        "📌 /help — подробная справка"
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "📖 **Подробная справка**\n\n"
        "**Конвертация видео:**\n"
        "1. Отправь видео в чат\n"
        "2. Нажми на него, выбери 'Ответить'\n"
        "3. Введи команду:\n"
        "   • /circle — превратит в квадратный кружок (до 60 сек)\n"
        "   • /gif — создаст GIF-анимацию (до 30 сек)\n\n"
        "**Скачивание из интернета:**\n"
        "Просто отправь ссылку на видео из:\n"
        "• YouTube (обычные видео и Shorts)\n"
        "• Instagram (Reels и обычные посты)\n"
        "• TikTok\n"
        "• Twitter / X\n"
        "• Reddit\n\n"
        "**Ограничения:**\n"
        "• Видео не более 50 MB\n"
        "• Длительность до 60 секунд для кружков\n"
        "• При скачивании больших видео может потребоваться до 40 секунд\n\n"
        "📧 Поддержка: @dengalychev"
    )

async def circle(update: Update, context):
    await convert_video(update, context, "кружочек", is_circle=True)

async def gif(update: Update, context):
    await convert_video(update, context, "GIF", is_circle=False)

# === ЗАПУСК БОТА ===
def main():
    # Запускаем HTTP сервер для health checks
    http_thread = Thread(target=run_http, daemon=True)
    http_thread.start()
    logger.info(f"✅ HTTP сервер запущен на порту {PORT}")
    
    # Создаём и настраиваем Telegram бота
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("circle", circle))
    app.add_handler(CommandHandler("gif", gif))
    
    # Регистрируем обработчик ссылок (для скачивания)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_media))
    
    logger.info("✅ Бот успешно запущен!")
    
    # Запускаем polling
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
