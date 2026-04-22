import os
import subprocess
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context):
    await update.message.reply_text("Отправь видео и ответь /circle")

async def circle(update: Update, context):
    reply = update.message.reply_to_message
    if not reply or not reply.video:
        await update.message.reply_text("❌ Ответь на видео")
        return
    
    await update.message.reply_text("⏳ Конвертирую...")
    
    file = await reply.video.get_file()
    await file.download_to_drive("input.mp4")
    
    cmd = [
        "ffmpeg", "-i", "input.mp4",
        "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=480:480",
        "-t", "60", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "circle.mp4", "-y"
    ]
    subprocess.run(cmd)
    
    with open("circle.mp4", "rb") as f:
        await update.message.reply_video_note(f.read())
    
    os.remove("input.mp4")
    os.remove("circle.mp4")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("circle", circle))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
