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
CHANNEL_USERNAME = "@sp_rap"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

favorites = {}
history = {}

# ======================
# ПРОВЕРКА ПОДПИСКИ
# ======================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ======================
# КНОПКИ
# ======================
def make_buttons(artist, title):
    q = f"{artist} {title}"

    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton("🎧 Spotify", url=f"https://open.spotify.com/search/{q}"),
        InlineKeyboardButton("🎵 Яндекс Музыка", url=f"https://music.yandex.ru/search?text={q}"),
        InlineKeyboardButton("🍎 Apple Music", url=f"https://music.apple.com/search?term={q}"),
        InlineKeyboardButton("📖 Genius", url=f"https://genius.com/search?q={q}")
    )

    return kb

# ======================
# 🔥 100% РАБОЧАЯ ОБЛОЖКА (iTunes)
# ======================
def get_cover(artist, title):
    try:
        q = f"{artist} {title}"
        url = "https://itunes.apple.com/search"

        params = {
            "term": q,
            "media": "music",
            "limit": 1
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data["resultCount"] > 0:
            return data["results"][0]["artworkUrl100"].replace("100x100", "600x600")

        return None

    except Exception as e:
        print("cover error:", e)
        return None

# ======================
# START
# ======================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(f"❌ Подпишитесь на {CHANNEL_USERNAME}")
        return

    await message.answer("🎵 Отправь голосовое или кружок")

# ======================
# РАСПОЗНАВАНИЕ
# ======================
@dp.message_handler(content_types=['voice', 'audio', 'video_note'])
async def music(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(f"❌ Подпишитесь на {CHANNEL_USERNAME}")
        return

    await message.answer("🎧 Распознаю...")

    try:
        # файл
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        else:
            file_id = message.video_note.file_id

        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

        # AudD запрос
        data = {
            "api_token": AUDD_API_KEY,
            "url": file_url
        }

        r = requests.post("https://api.audd.io/", data=data, timeout=25)
        result = r.json()

        print(result)

        if result.get("result"):

            artist = result["result"]["artist"]
            title = result["result"]["title"]

            text = f"🎵 {artist} - {title}"

            # 🔥 ОБЛОЖКА (100% РАБОТАЕТ)
            image = get_cover(artist, title)

            kb = make_buttons(artist, title)

            history.setdefault(message.from_user.id, [])
            history[message.from_user.id].append(text)

            if image:
                await bot.send_photo(
                    message.chat.id,
                    photo=image,
                    caption=text,
                    reply_markup=kb
                )
            else:
                await message.answer(text, reply_markup=kb)

        else:
            await message.answer("❌ Не найдено")

    except Exception as e:
        print("ERROR:", e)
        await message.answer("❌ Ошибка обработки")

# ======================
# RUN
# ======================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)