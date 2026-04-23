import os
import subprocess
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import Command

TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command('start'))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я превращаю видео в кружочки!\n\n"
        "Просто отправь мне видео, затем ответь на него командой /circle"
    )

@dp.message(Command('circle'))
async def to_circle(message: types.Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.answer("❌ Ответь на видео командой /circle")
        return
    
    video = message.reply_to_message.video
    input_file = await bot.download(video.file_id)
    
    output_path = "circle_video.mp4"
    
    cmd = [
        "ffmpeg", "-i", "pipe:0",
        "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=480:480",
        "-t", "60",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]
    
    await message.answer("⏳ Конвертирую в кружочек...")
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    await process.communicate(input=input_file.read())
    
    result = FSInputFile(output_path)
    await bot.send_video_note(message.chat.id, result)
    os.remove(output_path)

async def main():
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
