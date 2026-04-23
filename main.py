import os
import subprocess
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error("BOT_TOKEN не найден!")
    exit(1)

# Хранилище для выбора пользователя (временно)
user_choice = {}

# === HTTP сервер для Render ===
app_flask = Flask('')

@app_flask.route('/')
@app_flask.route('/health')
def health():
    return "OK", 200

def run_http():
    app_flask.run(host='0.0.0.0', port=PORT)

# === КНОПКИ МЕНЮ ===
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🔄 Превратить в кружочек", callback_data="circle")],
        [InlineKeyboardButton("🎞️ Превратить в GIF", callback_data="gif")],
    ]
    return InlineKeyboardMarkup(keyboard)

# === ОБРАБОТЧИКИ ===
async def start(update: Update, context):
    await update.message.reply_text(
        "🎬 Привет! Я превращаю видео в кружочки и GIF!\n\n"
        "👇 Нажми на кнопку ниже, выбери формат, а потом отправь видео.",
        reply_markup=get_main_menu()
    )

async def menu_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    user_id = query.from_user.id
    
    # Сохраняем выбор пользователя
    user_choice[user_id] = choice
    
    # Меняем сообщение, показывая выбранный формат
    if choice == "circle":
        text = "✅ Выбран формат: **кружочек**\n\nТеперь отправь мне видео, и я сконвертирую его."
    else:
        text = "✅ Выбран формат: **GIF**\n\nТеперь отправь мне видео, и я сконвертирую его."
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

async def handle_video(update: Update, context):
    user_id = update.message.from_user.id
    
    # Проверяем, выбрал ли пользователь формат
    if user_id not in user_choice:
        await update.message.reply_text(
            "❌ Сначала выбери формат конвертации через кнопки в меню.\n\n"
            "Напиши /start"
        )
        return
    
    choice = user_choice[user_id]
    video = update.message.video
    
    # Отправляем сообщение о начале
    msg = await update.message.reply_text("⏳ Конвертирую... (до 30 секунд)")
    
    try:
        # Скачиваем видео
        file = await video.get_file()
        await file.download_to_drive("input.mp4")
        logger.info(f"Видео скачано от user {user_id}")
        
        if choice == "circle":
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
        
        # Удаляем сообщение о конвертации
        await msg.delete()
        
        # Отправляем кнопку для новой конвертации
        await update.message.reply_text(
            "✅ Готово! Хочешь сконвертировать ещё одно видео?",
            reply_markup=get_main_menu()
        )
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg ошибка: {e.stderr.decode() if e.stderr else 'Unknown'}")
        await msg.edit_text("❌ Ошибка конвертации. Видео слишком длинное или повреждено.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")
    
    finally:
        # Очищаем временные файлы
        for f in ["input.mp4", "output.mp4", "output.gif"]:
            if os.path.exists(f):
                os.remove(f)
        
        # Не удаляем выбор пользователя, чтобы можно было конвертировать несколько видео подряд

async def help_command(update: Update, context):
    await update.message.reply_text(
        "📖 **Справка**\n\n"
        "1. Напиши /start\n"
        "2. Нажми на кнопку с нужным форматом\n"
        "3. Отправь видео\n\n"
        "**Ограничения:**\n"
        "• Кружочек — до 60 секунд\n"
        "• GIF — до 30 секунд\n"
        "• Видео до 30 MB\n\n"
        "Поддержка: @dengalychev",
        parse_mode="Markdown"
    )

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
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    logger.info("✅ Бот с кнопками успешно запущен!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
