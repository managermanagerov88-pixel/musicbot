import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("🎵 Бот работает! Отправь мне голосовое или аудио.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)
    AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
    import requests

@dp.message_handler(content_types=['voice'])
async def handle_voice(message: types.Message):
    await message.answer("🎧 Получил голосовое, обрабатываю...")

    file = await bot.get_file(message.voice.file_id)
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    data = {
        "api_token": AUDD_API_KEY,
        "url": file_url
    }

    try:
        r = requests.post("https://api.audd.io/", data=data, timeout=20)
        result = r.json()

        if result.get("result"):
            song = result["result"]["title"]
            artist = result["result"]["artist"]
            await message.answer(f"🎵 {artist} - {song}")
        else:
            await message.answer("❌ Не распознал трек")
    except Exception as e:
        await message.answer("❌ Ошибка обработки аудио")
        print(e)