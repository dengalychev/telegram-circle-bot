import os
import subprocess
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error("BOT_TOKEN не найден!")
    exit(1)

# Состояния для ConversationHandler
WAITING_FOR_VIDEO = 1

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
        [InlineKeyboardButton("🔄 Превратить в кружочек", callback_data="circle")],
        [InlineKeyboardButton("🎞️ Превратить в GIF", callback_data="gif")],
    ]
    return InlineKeyboardMarkup(keyboard)

# === ФУНКЦИЯ КОНВЕРТАЦИИ ===
async def convert_video(update: Update, choice: str, video_file):
    """Универсальная функция конвертации"""
    try:
        # Скачиваем видео
        await video_file.download_to_drive("input.mp4")
        logger.info(f"Видео скачано, формат: {choice}")
        
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
        
        return True, None
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Неизвестная ошибка"
        logger.error(f"FFmpeg ошибка: {error_msg}")
        return False, "Ошибка конвертации. Видео слишком длинное или повреждено."
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False, str(e)[:200]
    finally:
        for f in ["input.mp4", "output.mp4", "output.gif"]:
            if os.path.exists(f):
                os.remove(f)

# === ОБРАБОТЧИКИ ===
async def start(update: Update, context):
    """Начало работы - показываем меню"""
    await update.message.reply_text(
        "🎬 Привет! Я превращаю видео в кружочки и GIF!\n\n"
        "👇 Нажми на кнопку, выбери формат:",
        reply_markup=get_main_menu()
    )
    return ConversationHandler.END

async def menu_callback(update: Update, context):
    """Обработка нажатия кнопки"""
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    user_id = query.from_user.id
    
    # Сохраняем выбор пользователя
    user_choice[user_id] = choice
    
    # Редактируем сообщение: удаляем кнопки, показываем запрос видео
    text = "🎬 Выбран формат: "
    text += "**кружочек**" if choice == "circle" else "**GIF**"
    text += "\n\n📤 Отправь мне видео для конвертации:"
    
    # Убираем кнопки из предыдущего сообщения
    await query.edit_message_text(
        text,
        parse_mode="Markdown"
    )
    
    # Отправляем дополнительное сообщение с подтверждением
    await query.message.reply_text(
        "⏳ Жду видео... Пришли его сюда:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]])
    )
    
    return WAITING_FOR_VIDEO

async def cancel_callback(update: Update, context):
    """Отмена операции"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_choice:
        del user_choice[user_id]
    
    await query.edit_message_text(
        "❌ Операция отменена.\n\nВернуться в меню — /start"
    )
    return ConversationHandler.END

async def handle_video(update: Update, context):
    """Обработка полученного видео"""
    user_id = update.message.from_user.id
    
    # Проверяем, есть ли выбор пользователя
    if user_id not in user_choice:
        await update.message.reply_text(
            "❌ Сначала выбери формат через /start"
        )
        return ConversationHandler.END
    
    choice = user_choice[user_id]
    video = update.message.video
    
    # Сообщение о начале конвертации
    status_msg = await update.message.reply_text("⏳ Конвертирую... (до 30 секунд)")
    
    # Конвертируем
    success, error_msg = await convert_video(update, choice, video)
    
    if success:
        # Удаляем сообщение о процессе
        await status_msg.delete()
        
        # Показываем меню для новых конвертаций
        await update.message.reply_text(
            "✅ Готово! Хочешь сконвертировать ещё одно видео?",
            reply_markup=get_main_menu()
        )
    else:
        await status_msg.edit_text(f"❌ Ошибка: {error_msg}")
        # Возвращаем меню
        await update.message.reply_text(
            "Попробовать снова?",
            reply_markup=get_main_menu()
        )
    
    # Очищаем выбор пользователя (можно конвертировать новое видео с новым выбором)
    if user_id in user_choice:
        del user_choice[user_id]
    
    return ConversationHandler.END

async def help_command(update: Update, context):
    await update.message.reply_text(
        "📖 **Справка**\n\n"
        "1. Напиши /start\n"
        "2. Нажми на кнопку с нужным форматом\n"
        "3. Отправь видео\n\n"
        "📌 После конвертации меню появится снова!\n\n"
        "**Ограничения:**\n"
        "• Кружочек — до 60 секунд\n"
        "• GIF — до 30 секунд\n\n"
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
    
    # Conversation handler для плавного диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_VIDEO: [
                CallbackQueryHandler(cancel_callback, pattern="cancel"),
                MessageHandler(filters.VIDEO, handle_video),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video),  # Если отправят текст
            ],
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("help", help_command)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^(circle|gif)$"))
    
    logger.info("✅ Бот с меню успешно запущен!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
