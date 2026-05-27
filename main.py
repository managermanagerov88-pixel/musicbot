import logging
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ======================
# НАСТРОЙКИ
# ======================
BOT_TOKEN = "ВСТАВЬ_ТОКЕН"
AUDD_API_KEY = "ВСТАВЬ_AUDD_KEY"
CHANNEL_USERNAME = "@YOUR_CHANNEL"  # <- сюда свой канал

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ======================
# ПРОСТАЯ ПАМЯТЬ (в RAM)
# ======================
user_favorites = {}
user_history = {}

# ======================
# ПРОВЕРКА ПОДПИСКИ
# ======================
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ======================
# START
# ======================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if not await is_subscribed(message.from_user.id):
        await message.answer(
            f"❌ Подпишись на канал {CHANNEL_USERNAME}, чтобы пользоваться ботом."
        )
        return

    await message.answer(
        "🎵 Бот активирован!\n\n"
        "Отправь:\n"
        "🎤 голосовое\n"
        "🔵 кружок\n"
        "🎧 аудио"
    )

# ======================
# КНОПКИ ССЫЛОК + ИЗБРАННОЕ
# ======================
def create_keyboard(user_id, artist, title):
    query = f"{artist} {title}"

    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton("🎧 Spotify", url=f"https://open.spotify.com/search/{query}"),
        InlineKeyboardButton("🎵 Яндекс Музыка", url=f"https://music.yandex.ru/search?text={query}"),
        InlineKeyboardButton("🍎 Apple Music", url=f"https://music.apple.com/search?term={query}"),
        InlineKeyboardButton("📖 Genius", url=f"https://genius.com/search?q={query}")
    )

    fav_key = f"{artist} - {title}"

    keyboard.add(
        InlineKeyboardButton(
            "⭐ В избранное",
            callback_data=f"fav|{fav_key}"
        )
    )

    return keyboard

# ======================
# CALLBACK (избранное)
# ======================
@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def add_fav(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    song = callback_query.data.split("|")[1]

    user_favorites.setdefault(user_id, [])
    user_favorites[user_id].append(song)

    await callback_query.answer("Добавлено в избранное ⭐")

# ======================
# РАСПОЗНАВАНИЕ
# ======================
@dp.message_handler(content_types=['voice', 'audio', 'video_note'])
async def handle_audio(message: types.Message):

    if not await is_subscribed(message.from_user.id):
        await message.answer(f"❌ Подпишись на {CHANNEL_USERNAME}")
        return

    await message.answer("🎧 Анализирую...")

    try:
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        else:
            file_id = message.video_note.file_id

        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

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
            image = result["result"].get("album_image")

            # история
            user_history.setdefault(message.from_user.id, [])
            user_history[message.from_user.id].append(f"{artist} - {title}")

            keyboard = create_keyboard(message.from_user.id, artist, title)

            text = f"🎵 {artist} - {title}"

            if image:
                await bot.send_photo(
                    message.chat.id,
                    photo=image,
                    caption=text,
                    reply_markup=keyboard
                )
            else:
                await message.answer(text, reply_markup=keyboard)

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