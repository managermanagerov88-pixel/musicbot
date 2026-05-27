import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ======================
# НАСТРОЙКИ
# ======================
BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ======================
# START
# ======================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        "🎵 Бот запущен!\n\n"
        "Отправь мне:\n"
        "🎤 голосовое\n"
        "🔵 кружок\n"
        "🎧 аудио\n\n"
        "Я попробую найти песню."
    )

# ======================
# MUSIC RECOGNITION
# ======================
@dp.message_handler(content_types=['voice', 'audio', 'video_note'])
async def handle_audio(message: types.Message):
    await message.answer("🎧 Получил файл, ищу трек...")

    try:
        # определяем тип файла
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        elif message.video_note:
            file_id = message.video_note.file_id
        else:
            await message.answer("❌ Неизвестный формат")
            return

        # получаем файл из Telegram
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

        # отправляем в AudD
        data = {
            "api_token": AUDD_API_KEY,
            "url": file_url
        }

        r = requests.post("https://api.audd.io/", data=data, timeout=25)
        result = r.json()

        print("AUDD RESULT:", result)

        if result.get("result"):
            song = result["result"]["title"]
            artist = result["result"]["artist"]
            await message.answer(f"🎵 {artist} - {song}")
        else:
            await message.answer("❌ Не удалось распознать трек")

    except Exception as e:
        print("ERROR:", e)
        await message.answer("❌ Ошибка при обработке файла")

# ======================
# RUN
# ======================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)