import logging
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
        "🎵 Привет!\n\n"
        "Отправь:\n"
        "🎤 голосовое\n"
        "🔵 кружок\n"
        "🎧 аудио\n\n"
        "Я найду песню и дам ссылки."
    )

# ======================
# ФУНКЦИЯ ССЫЛОК
# ======================
def create_links(artist, title):
    query = f"{artist} {title}"

    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "🎧 Spotify",
            url=f"https://open.spotify.com/search/{query}"
        ),
        InlineKeyboardButton(
            "🎵 Яндекс Музыка",
            url=f"https://music.yandex.ru/search?text={query}"
        ),
        InlineKeyboardButton(
            "🍎 Apple Music",
            url=f"https://music.apple.com/search?term={query}"
        ),
        InlineKeyboardButton(
            "📖 Genius Lyrics",
            url=f"https://genius.com/search?q={query}"
        )
    )

    return keyboard


# ======================
# РАСПОЗНАВАНИЕ МУЗЫКИ
# ======================
@dp.message_handler(content_types=['voice', 'audio', 'video_note'])
async def handle_audio(message: types.Message):
    await message.answer("🎧 Анализирую аудио...")

    try:
        # определяем файл
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        elif message.video_note:
            file_id = message.video_note.file_id
        else:
            await message.answer("❌ Неизвестный формат")
            return

        # скачиваем файл Telegram
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

        # отправляем в AudD
        data = {
            "api_token": AUDD_API_KEY,
            "url": file_url
        }

        r = requests.post("https://api.audd.io/", data=data, timeout=25)
        result = r.json()

        print("AUDD:", result)

        if result.get("result"):
            artist = result["result"]["artist"]
            title = result["result"]["title"]

            keyboard = create_links(artist, title)

            await message.answer(
                f"🎵 {artist} - {title}",
                reply_markup=keyboard
            )
        else:
            await message.answer("❌ Не удалось распознать трек")

    except Exception as e:
        print("ERROR:", e)
        await message.answer("❌ Ошибка обработки файла")


# ======================
# RUN
# ======================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)