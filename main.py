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

# Хранилище выбора пользователя
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
        [InlineKeyboardButton("🔄 Кружочек", callback_data="circle")],
        [InlineKeyboardButton("🎞️ GIF", callback_data="gif")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_menu():
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)

# === КОМАНДЫ ===
async def start(update: Update, context):
    await update.message.reply_text(
        "🎬 Привет! Выбери формат:",
        reply_markup=get_main_menu()
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    user_id = query.from_user.id
    user_choice[user_id] = choice
    
    text = "✅ Выбран: " + ("кружочек" if choice == "circle" else "GIF")
    text += "\n\n📤 Отправь видео:"
    
    await query.edit_message_text(text)
    await query.message.reply_text(
        "Жду видео...",
        reply_markup=get_cancel_menu()
    )

async def cancel_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_choice:
        del user_choice[user_id]
    
    await query.message.delete()
    await query.message.reply_text("❌ Отменено. Выбери действие:", reply_markup=get_main_menu())

async def video_handler(update: Update, context):
    user_id = update.message.from_user.id
    
    if user_id not in user_choice:
        await update.message.reply_text("❌ Сначала /start и выбери формат")
        return
    
    choice = user_choice[user_id]
    video = update.message.video
    
    msg = await update.message.reply_text("⏳ Конвертирую... (до 30 секунд)")
    
    try:
        file = await video.get_file()
        await file.download_to_drive("input.mp4")
        logger.info("Видео скачано")
        
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
        
        await msg.delete()
        await update.message.reply_text("✅ Готово! Ещё?", reply_markup=get_main_menu())
        
    except subprocess.CalledProcessError as e:
        error = e.stderr.decode() if e.stderr else "Ошибка FFmpeg"
        logger.error(f"FFmpeg ошибка: {error}")
        await msg.edit_text("❌ Ошибка: видео слишком длинное или повреждено")
        await update.message.reply_text("Попробовать снова?", reply_markup=get_main_menu())
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:100]}")
        await update.message.reply_text("Попробовать снова?", reply_markup=get_main_menu())
    finally:
        for f in ["input.mp4", "output.mp4", "output.gif"]:
            if os.path.exists(f):
                os.remove(f)
        if user_id in user_choice:
            del user_choice[user_id]

# === ЗАПУСК ===
def main():
    Thread(target=run_http, daemon=True).start()
    logger.info(f"✅ HTTP сервер на порту {PORT}")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(circle|gif)$"))
    app.add_handler(CallbackQueryHandler(cancel_handler, pattern="^cancel$"))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    
    logger.info("✅ Бот с кнопками запущен!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
